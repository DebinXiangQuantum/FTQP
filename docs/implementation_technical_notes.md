# CiPR-FTQC MVP 技术说明与核对清单

本文档说明当前项目实现的技术边界、自动验证能力、需要人工核对的内容，以及后续仍需解决的问题。它面向论文写作和后续实现交接，不把当前 MVP 夸大成完整物理级 FTQC 证明。

## 1. 当前目标

当前实现验证的是一个编译器/IR 层面的研究原型：

```text
logical QEC program
  -> code-indexed FTQC IR
  -> acquisition plan: native / switch / resource-state
  -> effect + layout + certificate sidecar
  -> checker + Z3 obligations + GF(2) Pauli certificates
```

核心思想是把下面这些原本分散在后端脚本、论文表格和资源估算表里的内容，提升为可组合的程序对象：

- 当前 logical qubit 所在 code；
- 当前 code 支持的 native/transversal gates；
- code switching 作为 typestate transition；
- magic/resource-state factory 作为线性资源；
- logical error、acceptance、cycle、qubit-round、switch/factory count 等 quantitative effects；
- 固定 backend 上的 topology/workspace/layout side conditions；
- 可被自动检查的 protocol certificate。

当前系统不是量子物理模拟器，也不是完整 fault-tolerance 证明器。它更接近一个 **typed FTQC compiler IR + proof-obligation generator**。

## 2. 项目结构

主要代码位于：

```text
cipr/
  ir.py          # LogicalOp, QType, Effect, FTStep
  rules.py       # CodeProfile, RuleProfile, paper-annotated rule library
  layout.py      # fixed backend + layout/free-qubit accounting
  planner.py     # logical program -> FT steps / acquisition plans
  checker.py     # capability/resource/layout checker
  stabilizer.py  # GF(2) Pauli symbolic certificates
  theorem.py     # Z3/SMT proof obligations

experiments/
  run_mvp.py          # case study and negative tests
  verify_mvp.py       # Z3 verification for compiled plans
  verify_protocols.py # GF(2) protocol-certificate checks
```

依赖管理：

```text
pyproject.toml  # declares z3-solver
uv.lock         # locks z3-solver version
```

推荐命令：

```bash
uv run python experiments/run_mvp.py
uv run python experiments/verify_protocols.py
uv run python experiments/verify_mvp.py
```

## 3. IR 和效果系统

### 3.1 LogicalOp

`LogicalOp` 表示用户层逻辑程序，目前支持：

- `prepare(q, state)`
- `apply(gate, *qubits)`
- `ec(*qubits, decoder=...)`
- `measure(target, observable, *qubits)`
- `branch(bit, then_ops, else_ops)`
- `barrier(label)`

case study 中的 logical program 包含：

- prepare；
- surface-code QEC round；
- ordinary gates: `H`, `CNOT`, `T`, `CCZ`, `S`；
- dense acquisition region；
- measurement；
- classical control。

### 3.2 QType

`QType` 当前只记录：

```text
Q[code, distance, mode]
```

它不携带 hardware model。硬件模型是全局编译上下文，见第 5 节。

### 3.3 Effect

`Effect` 记录编译后步骤的资源和概率效果：

- `err`
- `fail`
- `accept`
- `qubits_peak`
- `cycles`
- `qubit_rounds`
- `switch_count`
- `factory_count`
- `measurements`
- `resets`
- `two_qubit_gates`
- `three_qubit_gates`
- `decoder_latency`
- `certs`
- `assumptions`
- `rules`

顺序组合使用：

```text
err: additive upper bound
fail: capped additive upper bound
accept: multiplicative lower bound
qubits_peak: max
cycles/qubit_rounds/counts: additive
```

分支组合使用：

```text
err/fail/counts/cycles: max
accept: min
```

这是一个保守的 effect algebra。它足够支持 compiler-level resource soundness，但还不是精确概率语义。

## 4. Rule Library

`rules.py` 中有两类对象：

### 4.1 CodeProfile

每个 code profile 包含：

- `name`
- `distance`
- supported gates；
- gate kind: `native` 或 `transversal`；
- `footprint_qubits`
- `supported_topologies`
- paper source metadata。

当前 code：

```text
SurfaceD5
Steane3
Tetra15
QLDPC12  # negative-control profile, requires long_range topology
```

`QLDPC12` 不是物理论文主张，只是用于验证：在 `Grid2D_SurfaceLike` backend 上不允许把 surface code 任意切换到需要 nonlocal connectivity 的 qLDPC-like code。

### 4.2 RuleProfile

每个 rule profile 包含：

- rule name；
- rule kind: prepare / gate / switch / resource_gate；
- certificate level: `Checked`, `Certified`, `Assumed`；
- effect；
- assumptions；
- sources；
- supported topologies；
- workspace requirement；
- layout note。

当前包含的 rule 类型：

- direct/native/transversal gate；
- code switch；
- resource-state acquisition；
- QEC；
- measurement。

## 5. 固定 Backend 和 Layout

用户指出的关键问题是：硬件模型不应该在程序中动态变化，但 code switch 必须受硬件拓扑约束。当前实现采用：

```text
compile(program, backend = Grid2D_SurfaceLike)
```

而不是：

```text
Q[code, hardware]
```

### 5.1 BackendSpec

`layout.py` 中定义：

```text
Grid2D_SurfaceLike:
  topology = grid2d
  capacity_qubits = 4096

LongRange_Modular:
  topology = long_range
  capacity_qubits = 4096
```

当前 case study 默认使用 `Grid2D_SurfaceLike`。

### 5.2 LayoutState

`LayoutState` 维护：

- 当前 backend；
- live logical qubit -> physical region；
- used/free physical qubits；
- prepare/switch/workspace reservation 的 layout event。

每个 relevant FT step 会生成 `layout_event`：

- `backend`
- `topology`
- `free_before`
- `free_after`
- `allocated`
- `old_footprint`
- `new_footprint`
- `workspace_reserved`
- `freed_qubits`
- `freed_regions`

这样可以表达：

- code switch 后哪些物理 footprint 被释放；
- factory 临时工作区是否超过可用 qubit；
- qLDPC-like code 是否能嵌入当前 topology。

### 5.3 当前 Layout 抽象的限制

当前 layout 只是 footprint/workspace 级别，不是真正二维坐标几何布局。它没有检查：

- patch 的具体形状；
- nearest-neighbor routing；
- lattice surgery boundary 对齐；
- shuttling/movement；
- long-range link contention；
- 并行操作冲突；
- factory 与 data patch 的空间距离。

因此它能拒绝明显 backend-incompatible 的 rule，但不能证明真实硬件布局最优或可路由。

## 6. 编译和规划

`Compiler` 做的工作：

1. 从 logical program 建立 `env: logical qubit -> QType`。
2. 建立固定 backend 的 `LayoutState`。
3. 对每个 gate 判断当前 code 是否支持。
4. 若支持，直接生成 direct gate FT step。
5. 若不支持，生成候选 acquisition plans：
   - switch to a supporting code, apply gate, switch back；
   - resource-state factory + consume/inject；
   - hybrid region: dense gate block 一次切换到 `Tetra15`，执行多个 gate，再切回来。
6. 根据 strategy 选择候选：
   - `magic_only`
   - `switch_only`
   - `hybrid`
   - `best`
   - `random`
7. 输出 FT steps、effect、layout、diagnostics。

### 6.1 Case Study

`experiments/run_mvp.py` 的程序刻意包含：

- `SurfaceD5` 不直接支持的 `CNOT`；
- `T`；
- `CCZ`；
- dense region；
- QEC；
- measurement；
- classical control。

因此编译器必须使用 switch 或 resource-state acquisition。

### 6.2 Negative Tests

当前负例：

1. `invalid_direct_cnot`
   - 在 `SurfaceD5` 上直接执行 `CNOT`；
   - checker 应拒绝。

2. `invalid_duplicate_resource`
   - 同一个 resource 被消费两次；
   - checker 应拒绝。

3. `invalid_qldpc_switch_on_grid`
   - 在 `Grid2D_SurfaceLike` 上执行 `SurfaceD5 -> QLDPC12`；
   - checker 应拒绝，因为 `QLDPC12` 和对应 switch rule 需要 `long_range`。

## 7. 自动验证覆盖范围

当前有三层自动验证。

### 7.1 Checker

`checker.py` 检查：

- direct gate 是否被当前 code 支持；
- switch rule 是否存在；
- code/rule 是否兼容 fixed backend topology；
- resource 是否线性生产和消费；
- layout event 的 backend/topology 是否匹配；
- layout event 的 free-qubit accounting 是否一致；
- `Assumed` rule 在 strict mode 下是否导致失败。

### 7.2 Z3 / SMT

`theorem.py` 和 `verify_mvp.py` 检查：

- 所有 effect 字段非负；
- direct gate step 有 `Native*` 或 `Transv*` witness；
- resource produced/consumed exactly once；
- layout events preserve fixed backend and free counts；
- total effect conservatively bounds flattened steps；
- Z3 证明以下 bound 的反例不可满足：
  - `err_bound_is_conservative`
  - `accept_lower_bound_is_conservative`
  - `cycles_bound_is_conservative`
  - `factory_count_is_conservative`
  - `switch_count_is_conservative`
  - `two_qubit_count_is_conservative`

输出：

```text
experiments/outputs/verification_report.json
experiments/outputs/smt/*.smt2
```

### 7.3 GF(2) / Pauli Symbolic Certificates

`stabilizer.py` 和 `verify_protocols.py` 检查 protocol-level algebraic core。

当前 `GaugeSwitchSpec` 检查：

- 所有 Pauli 向量长度正确；
- common logical `X/Z` 反对易；
- target stabilizers 互相对易；
- target stabilizers 保持 common logicals；
- gauge corrections 不改变 logical state；
- gauge corrections span target syndrome space。

当前 `MagicDistillationSpec` skeleton 检查：

- distillation checks commute；
- accepted low-weight input Pauli errors 不会实现 declared output logical error。

输出：

```text
experiments/outputs/protocol_certificates.json
```

## 8. 与 Butt et al. 2024 Code Switching 的对应关系

Butt et al., *Fault-Tolerant Code-Switching Protocols for Near-Term Quantum Processors*, PRX Quantum 5, 020345 (2024)，Sec. IV 的关键点是：

- code switching 可看作同一个 subsystem/gauge code 的两个 stabilizer-code variants；
- 两个 code 的 codestate 可分解为同一个 logical state 与不同 gauge state；
- `G \ S` 中的 gauge operator 只改变 gauge state，不改变 logical state；
- 通过测量 target stabilizers 并应用 gauge corrections，可将 state 固定到 target codespace；
- Steane code 与 tetrahedral code 有 common logical representation，见 Eq. (16)。

当前 `verify_protocols.py` 中的 `Butt2024_Steane_Tetra15_GaugeFixing_Core` 只验证这一 ideal algebraic core：

- target Steane X faces；
- common logical X/Z；
- gauge corrections 的 syndrome span；
- gauge corrections preserve logicals。

重要限制：

- 当前没有导入完整 subsystem code generator set；
- 只导入了一个论文显式提到的 `BZ_BG = Z2 Z5 Z11 Z13` 例子；
- 另外两个 correction 是 syndrome-equivalent compact basis，用于验证 algebraic mechanism；
- 尚未从 Appendix 中导入完整 face labels 和 protocol circuits；
- 尚未枚举 Sec. V 的 flag-qubit circuit-level single faults。

因此该 certificate 只能支持这样的表述：

> The implementation automatically checks the algebraic gauge-fixing condition underlying the Steane/tetrahedral code switch.

不能写成：

> We have fully mechanized Butt et al.'s complete fault-tolerant switching protocol.

## 9. Magic Distillation 验证的当前状态

当前 `MagicDistillationSpec` 是 skeleton，不是真实 15-to-1 或 zero-level distillation 的完整证书。

它能验证的问题是：

- 给定 stabilizer checks；
- 给定 output logical error；
- 枚举低权输入错误；
- 检查 accepted low-weight errors 是否可能翻转 output logical。

它不能验证：

- 真实 distillation circuit；
- injection circuit；
- noisy measurement；
- postselection probability；
- output error polynomial；
- Clifford correction；
- correlated input noise；
- factory scheduling。

后续要把真实 magic distillation 做成 `Certified`，需要人工导入或自动解析：

- 15-to-1 Bravyi-Kitaev / Reed-Muller check matrix；
- Wan 2024 constant-time distillation 的 exact check/circuit profile；
- Itogawa 2025 zero-level distillation 的 Steane-code verification + teleportation/conversion circuit；
- accepted syndrome set；
- logical output map；
- physical/logical error model；
- claimed error polynomial 的符号或枚举证明。

## 10. 需要人工核对的内容

以下内容当前不能只相信代码，必须人工核对。

### 10.1 论文数值和页码

在 `rules.py` 中，每个 paper-backed rule 都有 `SourceRef`。需要人工核对：

- Zotero key 是否对应正确论文；
- DOI/arXiv 链接是否正确；
- page/figure/table locator 是否准确；
- Table I 的 qubit count/CNOT count 是否被正确抄入；
- error/failure/acceptance 数值是否来自论文，还是 prototype instantiation；
- `p=1e-3`、`d=5` 等实例化参数是否在文中明确说明。

特别要核对：

- Butt et al. 2024 Table I：
  - `[[7,1,3]] -> [[15,1,3]]`
  - `[[15,1,3]] -> [[7,1,3]]`
  - qubits / CNOT count；
- Wan 2024：
  - `35 p^3`
  - `6` cycles；
  - `111 d^2` qubit-cycles；
- Itogawa 2025：
  - `100 p^2`
  - `70%` / `95%` acceptance；
  - depth `25`；
- Butt et al. 2025 measurement-free code switching 相关表述是否只用于背景，还是被实现为 rule。

### 10.2 Assumed Rules

以下 rule 当前不能作为物理结论：

- `Switch_SurfaceD5_to_Steane3`
- `Switch_Steane3_to_SurfaceD5`
- `Switch_SurfaceD5_to_Tetra15`
- `Switch_Tetra15_to_SurfaceD5`
- `BellTeleportCNOT_SurfaceD5`
- `CCZFactoryThenInject_SurfaceD5`
- `QLDPC12` 相关 negative-control rule。

它们目前用于测试 compiler path 和 checker 行为。论文中必须标注为 prototype assumptions，除非后续替换为文献支持或机械化证书。

### 10.3 Code/Topology 关系

需要人工确认：

- `SurfaceD5` 的 footprint `25` 是否只是 `d^2` 简化；
- `Steane3` footprint `7` 是否适合当前 layout abstraction；
- `Tetra15` footprint `15` 是否可在 `grid2d` backend 上使用；
- tetrahedral/color-code protocol 在目标硬件上是否需要 3D connectivity、shuttling、long-range gates 或 equivalent emulation；
- `supported_topologies={"grid2d","long_range"}` 是否过于宽松。

当前 `grid2d` 支持 `Tetra15` 是为了运行 hybrid case study，不应直接写成真实 2D nearest-neighbor hardware 已自然支持 tetrahedral code。

### 10.4 Layout 数值

需要人工核对：

- `workspace_qubits` 是否来自论文表格或只是 derived/prototype；
- `freed_qubits` 的解释是否与真实 code switch 中 bulk reuse/measurement/destructive readout 一致；
- factory 的 `qubits_peak` 是否应当临时占用，而不是当前只做 reservation；
- 多个 factory 是否能并行；
- workspace 是否能与 data patch 复用；
- layout event 是否应记录具体坐标和 region shape。

### 10.5 Effect Algebra

需要人工确认：

- `err` additive upper bound 是否适合所有组合；
- `fail` capped additive 是否过粗；
- `accept` multiplicative 是否合理；
- branch 使用 max/min 是否符合程序语义；
- `qubits_peak` 对 nested acquisition region 是否正确；
- `decoder_latency` additive 是否合理，还是应该 max/critical path；
- `cycles` 是否是 serial schedule，未考虑并行 scheduling。

### 10.6 Protocol Certificates

需要人工核对：

- Steane/tetrahedral target stabilizers index 是否与 Butt et al. Fig. 3/7 一致；
- `Gauge_Z_for_red_face_BZ_BG = Z2 Z5 Z11 Z13` 是否与文中例子一致；
- 另外两个 gauge corrections 当前是 syndrome-equivalent basis，不是论文 face label；
- common logical Eq. (16) 是否按论文索引导入；
- subsystem stabilizers 当前为空，后续必须导入；
- flag circuit fault sets 当前没有枚举。

### 10.7 Magic Distillation Skeleton

需要人工核对：

- 当前 toy repetition skeleton 是否只作为 verifier demo；
- 不要把 toy checker 的通过结果写成真实 magic distillation proof；
- 真实 distillation 需要 exact check matrix、acceptance set、logical output map。

## 11. 还需要进一步解决的问题

### 11.1 完整 Stabilizer/Subsystem Import

需要建立机器可读 code specification：

```text
CodeSpec:
  n, k, d
  stabilizer_generators
  logical_operators
  gauge_generators
  transversal_gates
  supported_topologies
```

然后从 `CodeSpec` 自动检查：

- stabilizers commute；
- logicals commute with stabilizers；
- logical X/Z anti-commute；
- distance lower bound；
- transversal gate preserves stabilizer group and maps logical operators correctly；
- code switch source/target are variants of common subsystem code。

### 11.2 完整 Code-Switch Certificate

要把 `Assumed/Certified` 区分做实，需要：

- 导入 Butt et al. Appendix A 的完整 protocol；
- 导入 all target stabilizer measurements；
- 导入 all gauge corrections；
- 导入 flag circuits；
- 枚举 single component faults：
  - data faults；
  - auxiliary faults；
  - measurement faults；
  - initialization faults；
  - one- and two-qubit gate faults；
- 检查每个 single fault 的 residual error 在 target code 上可纠正或被 postselected。

这可以扩展为：

```text
ProtocolCert:
  algebraic_gauge_fixing_ok
  single_fault_tolerance_ok
  resource_count_matches_table_ok
```

### 11.3 完整 Magic Distillation Certificate

真实 distillation certificate 应检查：

- check matrix/circuit 是否 stabilizer-valid；
- accepted syndrome set；
- output logical operator；
- low-weight input error suppression；
- output error polynomial；
- postselection acceptance；
- Clifford correction；
- correlated noise assumptions；
- factory composition。

可能的实现路线：

1. 用 GF(2) 矩阵枚举低权 Pauli errors；
2. 对 Clifford 部分使用 stabilizer tableau；
3. 对 acceptance/output map 用 symbolic polynomial；
4. 对大规模 protocol 使用 SAT/SMT 或 BDD/automata 压缩。

### 11.4 Compiler Correctness

当前 checker 是 post-hoc validation。后续应证明或机械化：

- well-typed source program 编译后不产生 unsupported direct gate；
- acquisition plan preserves logical semantics；
- resource linearity；
- layout preservation；
- effect soundness；
- optimization correctness。

可以考虑 Lean/Coq/Isabelle 中定义核心 calculus，再让 Python 实现生成 proof-carrying sidecar。

### 11.5 Backend Geometry

当前只做 topology tag + footprint/workspace。后续需要：

- physical coordinate graph；
- patch shape；
- embedding；
- routing；
- movement/shuttling；
- parallel scheduling；
- collision checks；
- decoder locality；
- factory/data patch separation。

### 11.6 Resource Optimization

当前 candidate selection 是 heuristic score：

```text
cycles + 0.01 * qubit_rounds + 25 * switch_count + 35 * factory_count + 1e6 * err + 20 * fail
```

后续应替换为：

- multi-objective optimization；
- user-specified constraints；
- error-budget allocation；
- factory throughput scheduling；
- switch minimization；
- backend-specific cost model；
- Pareto frontier 输出。

### 11.7 Reproducibility

当前输出 JSON 会被实验脚本覆盖。后续应：

- 固定 experiment manifest；
- 保存 rule library version；
- 保存 paper-source hash；
- 区分 generated outputs 和 source artifacts；
- 增加 pytest；
- 增加 CI 命令：
  - compileall；
  - run_mvp；
  - verify_protocols；
  - verify_mvp。

## 12. 当前可用于论文的谨慎表述

可以比较稳妥地写：

> We implement a prototype compiler IR that tracks code-indexed logical qubits, resource acquisition, probabilistic effects, fixed-backend layout side conditions, and certificate metadata. The generated proof obligations are checked using Z3, while algebraic protocol certificates are checked using a GF(2) Pauli representation.

可以写：

> The prototype demonstrates that code switching can be treated as a typed transition guarded by both backend/layout constraints and a gauge-fixing certificate.

可以写：

> For Butt et al.'s Steane/tetrahedral code-switching construction, we mechanize the algebraic core: common logical operators are preserved, gauge corrections commute with logicals, and the correction basis spans the target syndrome space.

不应写：

> We fully verify the complete fault-tolerant circuit-level protocol of Butt et al.

也不应写：

> The current magic-state distillation checker certifies real 15-to-1 or zero-level distillation protocols.

除非后续导入完整 protocol/circuit/check matrix 并完成 fault enumeration。

## 13. 建议的下一步

短期最有价值的工作顺序：

1. 将 Butt et al. 2024 的完整 face/gauge labels 和 Appendix A protocol 导入为机器可读 `CodeSpec/ProtocolSpec`。
2. 把当前 Steane/tetrahedral certificate 从 compact basis 升级为 exact paper-label certificate。
3. 为 switch protocol 增加 single-fault enumeration。
4. 导入一个真实 magic distillation protocol 的 check matrix，替换 toy skeleton。
5. 将 `Assumed` rule 分级：
   - `AssumedPrototype`
   - `PaperBacked`
   - `AlgebraicallyCertified`
   - `CircuitFaultCertified`
6. 增加 pytest/CI，保证 README 中的三个 `uv run` 命令稳定通过。

