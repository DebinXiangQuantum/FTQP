# FTQP / CiPR-FTQC POPL Remaining Work Plan

整理日期：2026-06-02

本文基于当前仓库文档、`cipr/` 原型代码、`experiments/` 验证脚本，以及 `docs/POPL_quantum_FTQC_survey.md` 和 `docs/latest_FTQC_papers_and_POPL_topics.md` 中对 POPL 量子论文的判断，梳理 FTQP / CiPR-FTQC 距离一篇 POPL 级论文还需要补齐的工作。

当前最重要的判断是：

> 项目已经有一个可以展示想法的 compiler/checker MVP，但还没有一套可作为论文核心的、独立于 Python 实现的形式化语言定义、类型/效果系统、程序逻辑和 soundness theorem。

因此，下一阶段主线不应先扩展更多物理协议常数，而应集中完成：

1. 编程语言设计；
2. 形式化语法、语义、类型与效果；
3. preservation / progress / logical soundness / resource soundness 证明；
4. 面向 FTQC protocol 的程序逻辑；
5. rule library 与编译计划的合法性校验；
6. 一个能支撑论文实验的原型与 case studies。

## 1. 当前项目已经具备什么

### 1.1 已有核心想法

仓库当前的核心定位是：

```text
logical QEC program
  -> code-indexed FTQC IR
  -> acquisition plan: direct / switch / resource-state / hybrid
  -> effect + layout + certificate sidecar
  -> checker + SMT obligations + GF(2) protocol certificates
```

这已经对 POPL 主线有明显价值，因为它把 FTQC 中原本分散的工程对象提升为程序对象：

- encoded logical qubit 当前所在 code；
- code capability, 如 native gate、transversal gate、logical measurement；
- code switching 作为 typestate transition；
- magic/resource state 作为 linear probabilistic resource；
- postselection、acceptance、failure、logical error 和 resource effect；
- fixed backend 下的 topology/workspace/layout side condition；
- rule certificate level: `Checked` / `Certified` / `Assumed`；
- compiler 生成可审计 sidecar。

### 1.2 已有实现能力

当前 `cipr/` 已经包含：

- `ir.py`: `LogicalOp`, `QType`, `Effect`, `FTStep`；
- `rules.py`: code profile、rule profile、paper-annotated rule library；
- `planner.py`: acquisition planner，支持 magic-only、switch-only、hybrid、best、random 策略；
- `checker.py`: capability、certificate、resource linearity、layout/topology 检查；
- `layout.py`: fixed backend 和 footprint/workspace 级 layout event；
- `stabilizer.py`: GF(2) Pauli checker，覆盖 gauge-switch core 和 magic distillation skeleton；
- `theorem.py`: Z3/SMT proof obligation generation and checking。

当前 `experiments/run_mvp.py` 也已经有 case study 和 negative tests：

- direct unsupported gate rejection；
- duplicate resource rejection；
- grid backend 上 qLDPC-like switch rejection；
- magic-only / switch-only / hybrid acquisition strategy comparison。

### 1.3 当前主要短板

目前短板不是没有 demo，而是论文核心还不够硬：

- Python 数据结构还没有被抽象为 formal calculus；
- effect algebra 还只是实现约定，不是语义定义和定理对象；
- checker 是 post-hoc validator，还没有和 typing derivation / operational semantics 建立定理；
- `Assumed` rule 太多，尤其是 SurfaceD5 与 Steane/Tetra 之间的桥；
- GF(2) certificate 只覆盖 ideal algebraic core，不覆盖完整 FT protocol；
- magic distillation checker 仍是 toy skeleton；
- layout 只有 footprint/workspace，没有 patch geometry、routing、并行冲突；
- benchmarks 数量和对比维度不足以支撑 POPL 实验部分。

## 2. POPL 论文需要的目标形态

结合已有 POPL 量子论文的写作范式，本文最合适的论文主张应是：

> A code-indexed, probabilistic, resource-aware calculus for compiling universal fault-tolerant quantum programs from logical operations to certified acquisition plans.

POPL 版本不应声称：

- 发明新的 FTQC 物理协议；
- 自动证明任意 gadget 的 threshold；
- 解决全部 patch-level routing 和 hardware scheduling；
- 完全替代 Stim / OpenQASM / QIR / resource estimator。

应该声称：

- 给出一个小而硬的 FTQC core calculus；
- 用 indexed types 和 linear probabilistic resources 表达 encoded data、magic states、code switching 和 logical measurement；
- 用 effect algebra 组合 logical error、space、time、failure / acceptance；
- 用 certificate-aware rule library 区分 checked、imported theorem 和 assumption；
- 证明 well-typed acquisition plans preserve logical semantics and resource bounds；
- 实现 prototype compiler/checker，并在若干 FTQC case studies 上展示非法组合会被拒绝、不同 acquisition paths 可比较。

## 3. 必须完成的工作包

### WP1: Core Language Design

目标：把当前 Python IR 提炼为论文中的 small core language。

需要定义 source language：

```text
e ::= prepare q | gate g qs | measure M qs as b
    | if b then e1 else e2 | let x = e1 in e2
```

需要定义 FTQC target language：

```text
t ::= alloc q:C
    | transv g q
    | native g q
    | switch q C1 C2
    | produce r:R
    | consume r for g q
    | measureL O q
    | decode s
    | frame f
    | postselect p
    | reset_clean a
    | t1 ; t2
    | if b then t1 else t2
```

必须明确哪些是 primitive，哪些是 derived forms：

- primitive proof atoms: `alloc`, `consume`, `clifford`, `transv`, `pauli_check`, `decode`, `frame`, `postselect`, `reset_clean`；
- derived protocol macros: `Switch`, `InjectT`, `Distill`, `Cultivate`, `Teleport`, `HybridRegionAcquire`；
- compiler acquisition goal: `Acquire[g, q]`。

需要特别避免一个过强 primitive：

```text
apply U
```

如果允许任意 `apply U`，protocol 证明会被藏在 opaque macro 里，论文的 checker 和 soundness theorem 会失去价值。

交付物：

- `docs/formal_calculus.md`；
- 语法定义；
- source 到 target 的 elaboration 关系；
- 当前 `LogicalOp` / `FTStep` 与 calculus construct 的映射表。

### WP2: Type System and Typestate

目标：让 code-indexed encoded qubit 成为论文形式系统的核心，而不是实现细节。

需要定义 quantum context：

```text
Gamma ::= q : Q[C, d, mu]
mu ::= State | Observable
```

需要定义 resource context：

```text
Delta ::= r : TState[eps] | r : CCZState[eps] | r : BellPair[eps]
```

需要定义 capability context：

```text
K ::= Cap(C, g)
    | Switch(C1, C2)
    | Factory(R)
    | Measure(C, O)
    | Backend(topology, capacity, latency)
```

核心 typing judgment 建议写成：

```text
K ; Gamma ; Delta |- t : Gamma' ; Delta' ! E
```

含义是：在 capability context `K` 下，target program `t` 把 quantum context `Gamma` 和 linear resource context `Delta` 转换为 `Gamma'` / `Delta'`，并产生 effect `E`。

必须完成的规则：

- prepare rule；
- native/transversal gate rule；
- code switch typestate transition；
- resource produce rule；
- resource consume/injection rule；
- logical measurement rule；
- decoder/frame/feedforward rule；
- branch rule；
- sequencing rule；
- certificate restriction rule；
- backend topology side condition。

必须补齐的检查：

- resource 必须线性消费；
- branch 两侧必须返回兼容 quantum context 和 layout context；
- `Observable` mode 不能被传给要求 `State` mode 的 rule；
- `Assumed` rule 不能在 strict theorem mode 中出现；
- runtime decoder bit 不能被当成 compile-time parameter 使用。

交付物：

- typing rules；
- `QType.mode` 的实际使用；
- strict/certified typing mode；
- negative examples 和拒绝证明。

### WP3: Effect Algebra and Probabilistic Semantics

目标：把当前 `Effect.seq` / `Effect.branch` 升级为论文里的 effect algebra。

建议核心 effect 不要过宽，论文主 effect 可先定义为：

```text
E = <epsilon, fail, accept, space, time>
```

其中：

- `epsilon`: logical error upper bound；
- `fail`: failure upper bound；
- `accept`: acceptance lower bound；
- `space`: physical qubits / peak workspace；
- `time`: FTQC cycles / latency。

工程 sidecar 可以继续记录：

- qubit rounds；
- switch count；
- factory count；
- two-qubit gates；
- decoder latency；
- assumptions；
- certificate levels；
- source references。

需要形式化：

- sequential composition；
- branch composition；
- repeat-until-success 或 postselection 的 expected-time semantics；
- conservative upper/lower bound order；
- effect weakening；
- resource-bound soundness。

当前实现中的组合约定可以作为起点：

```text
seq:
  epsilon additive upper bound
  fail capped additive upper bound
  accept multiplicative lower bound
  space max
  time additive

branch:
  epsilon/fail/time max
  accept min
  space max
```

需要补齐的理论边界：

- 这些组合是 conservative，不是 exact probability semantics；
- independence assumption 只在特定 rule 中声明；
- correlated noise model 需要 effect index 参数化；
- decoder latency 对并行 schedule 不能简单 additive，论文中要说明当前是 serial upper bound。

交付物：

- effect preorder；
- effect composition lemma；
- resource soundness theorem；
- `theorem.py` 与形式 effect 定义的对应关系。

### WP4: Operational and Denotational Semantics

目标：证明 target FTQC program 实现 source logical program，而不只是生成一串步骤。

需要定义至少两层语义：

1. Logical semantics：

```text
[[source]] : logical state -> distribution over logical outcomes
```

2. FTQC target semantics：

```text
[[target]]_K : encoded physical state -> distribution over accepted outcomes + failure
```

为了让证明可控，可以用抽象语义，不必直接展开完整物理 Hilbert space：

- code signature 给出 encode/decode relation；
- rule certificate 给出 local soundness contract；
- target semantics 组合 rule contracts；
- sidecar 记录 certificate obligations。

关键要定义 correctness modality：

```text
StateSound:
  accepted target channel approximates ideal logical channel

ObservableSound:
  accepted target final measurement distribution approximates ideal distribution
```

这对应文档里已经提出的 `State` / `Observable` mode。

需要证明：

- direct/native/transversal gate preserves logical semantics under capability certificate；
- switch preserves logical state or observable guarantee；
- injection consumes resource and implements logical non-Clifford gate within error bound；
- measure/decode/frame does not leak unsupported control information；
- sequencing composes error/resource bounds。

交付物：

- small-step 或 big-step semantics；
- rule contract semantics；
- logical soundness theorem statement；
- accepted-run semantics and failure semantics。

### WP5: Program Logic for FTQC Protocols

目标：为 code switch、magic injection、logical measurement 等 protocol 给出可检查的局部证明接口。

建议程序逻辑不要一开始覆盖所有量子程序，而是聚焦 FTQC protocol proof atoms：

```text
{P} atom {Q ; E}
```

断言语言至少需要表达：

- qubit 属于某个 code space；
- stabilizer / gauge stabilizer 条件；
- logical operator representation；
- syndrome condition；
- Pauli frame；
- resource ownership；
- backend region ownership；
- certificate level；
- error budget。

可以借鉴 separation logic 的 frame rule，但应保持 FTQC 特定：

```text
patch(q, C, region) * resource(r, TState[eps]) * frame(F)
```

关键 frame rules：

- 对不相交 logical patches 的 local operation 不影响其余 patch；
- factory workspace 在 produce 后释放或转为 linear resource；
- switch 只改变目标 qubit 的 code typestate；
- measurement 只产生 classical bit / syndrome effect，不赋予 compile-time information。

程序逻辑应支撑三类 certificate：

1. Stabilizer algebra certificate；
2. Single-fault-tolerance certificate；
3. Resource/layout certificate。

交付物：

- assertion syntax；
- Hoare triples for proof atoms；
- frame rule；
- code-switch proof outline；
- magic-injection proof outline；
- checker 可生成或消费的 certificate schema。

### WP6: Legality Checker and Certificate Schema

目标：把当前 checker 从 ad hoc post-hoc 检查升级为论文中的 rule legality infrastructure。

需要定义机器可读 `CodeSpec`：

```text
CodeSpec:
  name
  n, k, d
  stabilizer_generators
  gauge_generators
  logical_operators
  transversal_actions
  measurement_capabilities
  supported_topologies
```

需要定义机器可读 `RuleSpec`：

```text
RuleSpec:
  name
  precondition
  postcondition
  effect
  required_resources
  produced_resources
  consumed_resources
  backend_constraints
  proof_obligations
  certificate_level
  source_refs
```

checker 至少要验证：

- code stabilizers commute；
- logicals commute with stabilizers；
- logical X/Z anti-commute；
- transversal action preserves stabilizer group and maps logical operators correctly；
- switch source/target share a valid subsystem/gauge relation；
- rule precondition matches input context；
- rule postcondition matches output context；
- resource production/consumption is linear；
- layout/workspace constraints hold on fixed backend；
- `Assumed` rules are not silently used in theorem mode；
- cited numeric effects are tagged as measured / derived / assumed / imported。

交付物：

- `CodeSpec` / `RuleSpec` JSON schema or Python dataclasses；
- checker output as typed derivation tree；
- strict mode with zero `Assumed` rules；
- certificate sidecar schema。

### WP7: Protocol Certificate Completion

目标：把至少 1 到 2 个真实 FTQC protocol 从 `Assumed` 或 skeleton 推到 `Certified`。

优先路线 A：Butt et al. Steane / tetrahedral code switching。

当前已检查：

- common logical X/Z anti-commute；
- target stabilizers commute；
- gauge corrections preserve logicals；
- corrections span target syndrome space。

还需要：

- 导入完整 subsystem stabilizers；
- 导入 Appendix / figure 中完整 face labels；
- 导入全部 target stabilizer measurements；
- 导入全部 gauge corrections；
- 检查 source/target 是 common subsystem code 的两个 gauge fixing；
- 导入 flag-qubit circuits；
- 枚举 single component faults；
- 检查 residual error is correctable or detected；
- resource count 与论文表格一致。

优先路线 B：真实 magic-state distillation / zero-level distillation。

当前只是 toy skeleton，还需要：

- Reed-Muller / 15-to-1 check matrix；
- output logical map；
- accepted syndrome set；
- low-weight Pauli error enumeration；
- output error polynomial；
- acceptance probability derivation；
- injection circuit / correction rule；
- correlated input noise assumptions。

POPL 论文不一定需要把所有 protocol 都完全 mechanize，但至少需要一个非玩具级 protocol 证书作为 evidence。否则审稿人会认为 certificate-aware design 还停在包装层。

交付物：

- one complete certified code-switch protocol or one complete certified magic protocol；
- certificate JSON；
- checker proof report；
- 文档明确哪些 protocol 仍为 `Assumed`。

### WP8: Compiler Correctness

目标：从 current planner 走向可证明的 elaboration。

需要定义 source-to-target elaboration judgment：

```text
K ; Gamma |- e ~~> t : Gamma' ! E
```

需要证明：

- elaboration preserves typing；
- if source gate is unsupported in current code, generated target plan contains an acquisition path；
- generated target plan has no unsupported direct gate；
- generated target plan consumes each produced resource at most once and exactly once when required；
- generated effect conservatively bounds target steps；
- optimization pass preserves logical semantics and does not under-report effect。

需要给至少两个优化 pass 一个正式规格：

1. Code-switch placement / hybrid region formation；
2. Magic-resource provider selection or pooling。

当前 `planner.py` 的 `hybrid` 策略可以成为第一个优化 pass：

```text
switch in once; run dense gate block; switch back
```

需要补齐：

- dense block formation 的 precondition；
- 与逐 gate acquisition 的语义等价；
- effect comparison 不低估；
- branch / measurement 边界不能跨越；
- mode / resource / layout context preserved。

交付物：

- elaboration rules；
- planner invariant；
- optimization correctness theorem；
- implementation checks against theorem assumptions。

### WP9: Mechanized Proof Strategy

目标：确定论文证明到什么程度机械化。

可选路线：

1. Paper proof + executable checker + Z3 obligations；
2. Lean / Coq / Isabelle mechanized core calculus；
3. Why3 / SMT-style verification-condition generator；
4. Hybrid: paper theorem for calculus, Python checker for artifacts, Z3 for arithmetic/resource obligations。

建议最稳路线：

- POPL submission 前至少机械化一个小 core 的 context/resource/effect preservation；
- resource arithmetic 继续用 Z3；
- stabilizer obligations 用 domain-specific GF(2) checker；
- full protocol soundness 作为 imported certificate contract。

最小 mechanization 范围：

- contexts；
- linear resource consumption；
- sequential and branch typing；
- effect composition；
- no unsupported direct gate lemma；
- no double consumption lemma。

交付物：

- `formal/` 目录；
- Lean/Coq proof skeleton；
- proof README；
- CI command。

### WP10: Evaluation and Case Studies

目标：让论文实验不只是一个 toy kernel。

需要增加 4 到 6 个 benchmark：

- T-heavy arithmetic / phase polynomial；
- QFT / phase estimation；
- small Hamiltonian simulation kernel；
- logical measurement heavy workload；
- code-switch dense region；
- magic-factory heavy workload。

需要比较的策略：

- magic-only；
- switch-only；
- hybrid；
- high-fidelity factory；
- backend-constrained plan；
- strict-certified-only plan。

需要报告：

- logical error bound；
- acceptance lower bound；
- fail upper bound；
- cycles；
- qubit rounds；
- peak physical qubits；
- factory count；
- switch count；
- certificate distribution；
- assumption count；
- rejected illegal plans。

需要至少两个 backend context：

- grid2d surface-like；
- long-range / modular / qLDPC-like。

注意边界：

- 当前 layout 是 footprint abstraction，不应声称真实 geometric routing；
- 如果没有真实 geometry，就把结果写成 capability/resource-layer evaluation。

交付物：

- benchmark suite；
- generated sidecars；
- plots/tables；
- strict vs assumed comparison；
- reproducible command list。

## 4. 建议优先级

### P0: 论文核心必须先完成

1. `formal_calculus.md`: 语法、类型、效果、semantics、rule contracts；
2. `CodeSpec` / `RuleSpec` schema；
3. type/effect judgment；
4. logical/resource soundness theorem statements；
5. current implementation 到 formal calculus 的映射；
6. strict mode 下的 theorem boundary。

没有 P0，项目会像一个资源估算和 checker demo，而不是 POPL 论文。

### P1: 证明和 checker 做实

1. effect algebra 形式化；
2. resource linearity theorem；
3. no unsupported direct gate theorem；
4. code-switch certificate 完整化或 magic certificate 完整化二选一；
5. Z3 obligations 与 theorem 对齐；
6. sidecar schema 稳定化。

### P2: 原型和实验增强

1. 更多 benchmark；
2. hybrid optimization theorem；
3. strict-certified-only strategy；
4. backend comparison；
5. plots and reproducibility scripts。

### P3: 可以延后

1. 完整 patch geometry；
2. full routing and parallel scheduler；
3. full physical threshold proof；
4. large-scale factory scheduling；
5. automatic extraction from arbitrary protocol papers。

这些很重要，但不是当前 POPL 主线的最低必要条件。

## 5. 近期 4 周执行计划

### Week 1: 固化语言和类型

- 写 `docs/formal_calculus.md`；
- 定义 syntax / contexts / typing judgment；
- 明确 `State` 与 `Observable` mode；
- 给每个当前 `FTStep.op` 一个 calculus construct；
- 补充 5 到 8 个 rejected examples。

### Week 2: 固化 effect 和 theorem

- 写 effect algebra；
- 定义 effect preorder；
- 写 preservation / resource soundness / logical soundness theorem statement；
- 把 `theorem.py` 中的 Z3 obligations 改名和整理，使其与论文 theorem 对齐；
- 增加 strict theorem mode 的验证输出。

### Week 3: RuleSpec / CodeSpec 和 certificate

- 新增 machine-readable `CodeSpec`；
- 新增 machine-readable `RuleSpec`；
- 从当前 `rules.py` 迁移或镜像 rule library；
- 扩展 stabilizer checker；
- 选择一个 protocol 做深度 certificate。

### Week 4: 原型评估和论文骨架

- 增加 3 个 benchmark；
- 输出 strategy comparison table；
- 输出 strict vs assumed table；
- 写论文 outline；
- 明确 claims / non-claims；
- 生成 artifact README。

## 6. 论文结构建议

建议论文结构：

1. Introduction: universal FTQC implementation choice is a PL problem；
2. Overview: one logical program, multiple acquisition plans, illegal plan rejection；
3. Core calculus: syntax, contexts, resources, effects；
4. Capability rules and certificates；
5. Type/effect system；
6. Semantics and soundness；
7. Compiler elaboration and optimization；
8. Implementation；
9. Evaluation；
10. Related work；
11. Limitations and future work。

最关键的写作边界：

- 不要把 `Assumed` bridge 写成物理结论；
- 不要把 toy magic checker 写成真实 distillation proof；
- 不要声称 footprint layout 等价于 hardware geometry；
- 要强调本工作的贡献是 compositional PL layer。

## 7. 最小可投稿闭环

如果时间有限，最小可投稿闭环应是：

1. 一个正式 calculus；
2. 一个 type/effect system；
3. 一个 logical/resource soundness theorem；
4. 一个 certificate-aware rule library；
5. 一个真实或半真实 protocol certificate；
6. 一个 planner/checker prototype；
7. 4 个 benchmark；
8. strict vs assumed 的审计报告。

当前最该优先做的不是增加更多 gate 或更多数值，而是让这句话可以被严格证明：

> If the FTQP compiler accepts a program under certified rules, then the generated acquisition plan implements the source logical program on accepted runs and its reported error/resource effects are conservative bounds.
