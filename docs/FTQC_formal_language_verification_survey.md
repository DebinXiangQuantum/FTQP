# FTQC 形式化语言与验证调研报告

检索日期：2026-04-27

本文目的：补齐 programming languages / formal methods 背景概念，梳理容错量子计算（FTQC）、量子纠错（QEC）相关的形式化验证工作，并说明 `Code-indexed probabilistic resource calculus for universal FTQC` 与现有工作的差异、瓶颈和社区贡献。

## 1. 先补几个 PL / 形式化概念

### 1.1 Calculus 是什么

在 PL 论文里，`calculus` 通常不是“微积分”，而是一个足够小、足够精确的核心语言。

它一般包含：

- **Syntax**：程序长什么样，例如 `gate q`、`measure q`、`switch q from c1 to c2`。
- **Type system**：哪些程序是合法的，例如不能复制未知量子态，不能在不支持 T gate 的 code 上直接做 T。
- **Operational semantics**：程序如何一步步执行，例如测量后产生 classical bit，再更新 Pauli frame。
- **Denotational semantics**：程序整体代表什么数学对象，例如 unitary、quantum channel、stabilizer relation。
- **Equational theory / rewrite rules**：哪些程序等价，哪些优化是合法的。
- **Soundness theorem**：如果程序通过类型检查或证明系统，那么它真的满足语义性质。

对你的课题来说，calculus 的作用是把 FTQC 的复杂对象压缩成一个可证明的核心：

```text
Q[code, distance, basis]      encoded logical qubit
TState[epsilon]               consumable magic-state resource
Switch[c1 -> c2]              code-indexed typestate transition
MeasureL[op]                  logical measurement effect
Decode                        classical effect with latency / assumptions
Factory                       probabilistic resource provider
```

这不是为了替代真实后端，而是为了定义一个“可验证的接口层”。

### 1.2 Type、Indexed Type、Refinement Type、Typestate

普通类型回答“这是什么东西”：

```text
q : Qubit
```

Indexed type 把参数放进类型里：

```text
q : Q[SurfaceCode, d=15]
```

这表示 `q` 不只是一个 logical qubit，而是处于 Surface Code、distance 15 的 encoded state。

Refinement type 给类型加逻辑约束：

```text
TState[epsilon] where epsilon <= 1e-10
```

Typestate 表示对象的“当前状态”在类型里变化：

```text
Q[ColorCode, d] -> Q[SurfaceCode, d']
```

Code switching 最自然的 PL 表达就是 typestate transition。它的价值在于：后端协议不再是裸 circuit macro，而是一个有 precondition、postcondition、resource effect 和 correctness certificate 的 typed rule。

### 1.3 Linear / affine type

量子程序语言经常用 linear type，因为未知 quantum data 不能复制、不能随便丢弃。

- **Linear**：必须使用一次。
- **Affine**：最多使用一次，可以不用。

Magic state、logical ancilla、factory output、patch resource 都很像 linear / affine resource：

```text
TState[e] + Q[c,d] -> Q[c,d]
```

这里的 `TState[e]` 被消耗一次。它不能被复制成两个 T gate 使用。

### 1.4 Effect system

Effect system 用来记录程序除了“返回值”之外还发生了什么。

经典语言里，effect 可以是：

```text
read file
write memory
throw exception
allocate
```

FTQC 里，effect 更像：

```text
logical_error <= 1e-12
qubit_rounds <= 1e9
factory_demand = 128 T states
failure_probability <= 1e-6
decoder_latency <= 5 us
postselection = may_fail
```

这就是为什么 FTQC 适合做 resource/effect calculus：容错程序是否可用，不只取决于 logical circuit 正确，还取决于资源、失败概率、错误预算和 classical feedback。

### 1.5 Modal type

Modal type 的核心是区分“不同世界/阶段/可用性”的值。

Proto-Quipper with Dynamic Lifting 用 modal type 区分：

- **parameter**：circuit generation time 已知；
- **state**：circuit execution time 才知道；
- measurement result 是否可以被 lift 成参数，影响后续 circuit generation。

来源：Proto-Quipper with Dynamic Lifting, POPL 2023  
Link: https://quantumpl.github.io/bib/publication/Fu2023/

FTQC 里也有类似阶段问题：

- algorithm-level logical program；
- fault-tolerant logical schedule；
- syndrome measurement runtime；
- decoder result；
- Pauli frame update；
- hardware control timing。

所以 modal/effect typing 可以防止一个常见错误：把 runtime decoder information 当成 compile-time known value 使用。

### 1.6 Automata

Automata 是有限状态机及其扩展，用来表示无限或巨大集合。

为什么量子验证里会用 automata？因为一个 n-qubit state vector 是指数大；如果某类 quantum state family 有重复结构，可以用自动机紧凑表示。

POPL 2025 的 LSTA 工作用 level-synchronized tree automata 表示 quantum state sets，并支持 union/intersection、emptiness/inclusion 等判定。  
Link: https://arxiv.org/abs/2410.18540

POPL 2026 的 SWTA 工作进一步验证 parameterized quantum programs，也就是输入规模变化时生成的电路族。  
Link: https://arxiv.org/abs/2511.19897

对 FTQC 来说，这非常重要，因为很多对象天然是参数化的：

- code distance `d`；
- syndrome rounds `r`；
- factory levels `k`；
- lattice surgery patch size；
- logical circuit size；
- code-switch schedule length。

### 1.7 自动化数学推理和验证工具

常见工具可以分四类。

**Proof assistant / interactive theorem prover**

用于机器检查证明。证明通常需要人写，但可信度最高。

- Rocq/Coq：基于 Calculus of Inductive Constructions，适合做语义、类型系统、编译器正确性证明。官方说明：Rocq 是交互式定理证明器，可机器检查证明并抽取程序。  
  Link: https://rocq-prover.org/about
- Lean：依赖类型 theorem prover，数学库强，适合现代数学形式化。  
  Link: https://www.microsoft.com/en-us/research/project/lean/
- Isabelle/HOL：高阶逻辑 proof assistant，适合程序语义、协议验证、系统验证。

**SMT solver**

自动判断一阶逻辑、整数线性算术、bitvector、数组、有限域编码等公式是否可满足。

- Z3、CVC5、Alt-Ergo 常用。
- 优点是自动化强；缺点是表达力受限，复杂量子语义需要先化约。

**Deductive verification platform**

把程序规格转成 verification conditions，再交给 SMT 或 proof assistant。

- Why3：提供 WhyML 规格/程序语言，依赖外部自动或交互 prover discharge VCs。  
  Link: https://why3.org/
- QBricks 基于 Why3，把 quantum circuit-building program 的 specification 化约成 first-order proof obligations，并使用 SMT 自动化。  
  Link: https://qbricks.github.io/

**Domain-specific verifier**

面向特定量子对象写专门算法：

- VOQC/SQIR：Coq 中验证 quantum circuit optimizer。
- CoqQ：Coq 中验证 quantum programs。
- Veri-QEC：QEC program logic + SMT/Coq verifier。
- Stim/Sinter：QEC stabilizer circuit simulation and sampling，不是 proof assistant，但已成为很多 QEC workflow 的低层事实标准。

## 2. 一个理想的 FTQC 语言应该具备什么

理想 FTQC 语言不是“更漂亮的 OpenQASM”，而应该覆盖 FTQC 软件栈里目前最混乱的抽象边界。

### 2.1 一等 encoded logical data

语言不能只写：

```text
q : Qubit
```

而要写：

```text
q : Q[code = Surface, distance = 15, basis = PauliFrame]
```

因为 FTQC 程序里的 qubit 当前属于哪个 code、distance 多少、logical operator basis 怎么编码，直接决定哪些 gate、measurement、switch、decoder 合法。

### 2.2 Backend capability interface

不同后端支持不同操作：

- surface code 支持 lattice surgery 和 patch operations；
- color code 可能支持某些 transversal gates；
- Steane/color/code switching 提供 universal gate set；
- QLDPC/high-rate code 对 logical measurement、decoder、nonlocal checks 有不同假设；
- neutral atom / trapped ion / superconducting backend 的 connectivity 和 latency 完全不同。

因此语言应支持 capability rule：

```text
Capability:
  Transversal[H, ColorCode]
  Switch[ColorCode -> SurfaceCode]
  Cultivate[TState, SurfaceCode]
  MeasureLogical[op, QLDPC]
```

### 2.3 Measurement、decoder、Pauli frame、classical control

FTQC 不是静态 unitary circuit。它包含：

- syndrome measurement；
- mid-circuit measurement；
- decoder；
- Pauli frame update；
- feedforward；
- repeat-until-success；
- postselection；
- runtime scheduling。

OpenQASM 3 已经明确把 classical control、timing、extern classical computation 纳入语言设计目标。  
Link: https://openqasm.com/versions/3.1/intro.html

但 OpenQASM/QIR 的目标是通用 IR / hardware interface，不负责证明 FTQC resource/error soundness。因此我们的语言应在更高层表达 FTQC-specific typed effects。

### 2.4 Probabilistic and resource effects

FTQC 语言必须能表达：

- logical error bound；
- physical qubit-rounds；
- latency；
- factory throughput；
- success/failure probability；
- acceptance probability；
- postselection condition；
- decoder latency；
- noise model assumption。

尤其是 magic-state cultivation、factory scheduling、postselected code switching 都是概率资源过程。

### 2.5 Parameterization

理想语言不能只验证一个固定 distance 的 gadget，而要支持：

```text
for all distance d >= 3
for all syndrome rounds r >= d
for all factory level k
```

这需要 refinement/indexed types、automata、SMT、Coq/Lean 或 symbolic verification 结合。

### 2.6 Rule certification and extensibility

后端 rule 不能靠信任。理想架构是：

```text
backend protocol spec
        -> candidate capability rule
        -> proof obligation / certificate
        -> rule checker
        -> certified capability library
        -> typed compiler
```

这允许自动生成 rule，但不自动相信 rule。

### 2.7 Interoperability

它应该能对接：

- OpenQASM/QIR：通用 quantum IR 与硬件接口；
- Stim：QEC stabilizer circuit format / detector error model；
- Qiskit/Cirq/tket：前端或 benchmark；
- existing resource estimators；
- Coq/Why3/Z3/CVC5：证明和自动化验证。

QIR 的定位是 language- and hardware-agnostic intermediate representation，基于 LLVM，作为多语言和多平台之间的 common interface。  
Link: https://learn.microsoft.com/en-us/azure/quantum/concepts-qir

我们的 FTQC calculus 可以看作 QIR/OpenQASM 之上的 certified FTQC layer，而不是替代它们。

## 3. 相关工作调研

### 3.1 QWIRE

QWIRE 是 POPL 2017 的 core language，用于在 classical host language 中定义 quantum circuits。它有 type system、operational semantics、density-matrix denotational semantics，并证明 safety / normalization 等性质。

Link: https://rand.cs.uchicago.edu/publication/paykin-2017-qwire/

贡献：

- 把 quantum circuit 抽象成小核心语言；
- 用 linear wire types 保证 circuit well-formed；
- 给出形式语义。

局限：

- 关注 circuit construction；
- 不处理 QEC code、logical qubit、fault model、resource/error effects。

对我们有用：

- 学习“小而硬 core language + type safety + denotational semantics”的写法。

### 3.2 SQIR / VOQC

VOQC 是 POPL 2021 的 verified quantum circuit optimizer。SQIR 是 Coq 中的 small quantum IR；优化 pass 是 Coq functions，并相对 SQIR semantics 证明正确。

Link: https://popl21.sigplan.org/details/POPL-2021-research-papers/37/A-Verified-Optimizer-for-Quantum-Circuits  
Code: https://github.com/inQWIRE/SQIR

贡献：

- 证明 quantum optimizer correctness；
- symbolic matrix semantics 支持 arbitrary number of qubits；
- 有 benchmark，与工业编译器比较。

局限：

- circuit-level optimizer；
- 不表达 encoded data、fault tolerance、magic resources、decoder。

与我们不同：

- VOQC 验证“低层 circuit rewrite 不改语义”；
- 我们要验证“FTQC compilation rule / resource effect / code transition 是 sound 的”。

### 3.3 CoqQ

CoqQ 是 POPL 2023 的 foundational quantum program verification framework。它在 Coq 中深嵌入 quantum programming language，提供 program logic，并基于 MathComp / MathComp Analysis 形式化 soundness。

Link: https://dl.acm.org/doi/10.1145/3571222

贡献：

- 高可信 foundational verification；
- 支持 Dirac-style assertions；
- 支持 local and parallel reasoning；
- 用例覆盖多篇文献中的程序。

局限：

- 通用 quantum program verification；
- 不直接处理 FTQC resource/failure/code switching/cultivation。

对我们有用：

- 可以作为 mechanized proof backend；
- 如果我们实现 proof assistant 版本，CoqQ 是最接近的基础设施。

### 3.4 Proto-Quipper with Dynamic Lifting

Proto-Quipper-Dyn 解决 circuit generation time 与 circuit execution time 之间的 staging 问题。Dynamic lifting 允许 measurement result 影响后续 circuit generation；modal type system 跟踪这种跨阶段行为，并给出 categorical semantics soundness。

Link: https://quantumpl.github.io/bib/publication/Fu2023/

贡献：

- 形式化 measurement feedback；
- modal types 区分 parameter/state；
- 对 FTQC 的 decoder/feedforward 很关键。

局限：

- 不处理 QEC code 和 fault-tolerant resource；
- 关注 circuit description language 的 staging。

与我们不同：

- 它解决“测量结果如何进入下一段 circuit generation”；
- 我们进一步问“测量/decoder/feedforward 在 FTQC resource/error semantics 中是否合法，代价是什么”。

### 3.5 QBricks

QBricks 是基于 Why3 的 automated formal verification environment。它把 quantum circuit-building programs 的 I/O specification 和 resource requirement 化约成 first-order proof obligations，并交给 SMT solvers。

Link: https://qbricks.github.io/

贡献：

- 自动化程度高；
- 支持算法级 verified implementation；
- 为什么 SMT/Why3 可用于量子程序提供了路线。

局限：

- 主要验证 circuit-building algorithms；
- 不专门处理 FTQC/QEC code/fault-tolerance。

对我们有用：

- 可以借鉴 “generate VC -> SMT discharge” 的工具链。

### 3.6 LSTA：Verifying Quantum Circuits with Level-Synchronized Tree Automata

POPL 2025 工作，用 LSTA 紧凑表示 quantum state sets，并提供 fully automated symbolic verification algorithm。它支持 closure、emptiness、inclusion，且 gate operation 复杂度至多 quadratic。

Link: https://arxiv.org/abs/2410.18540

贡献：

- 自动化强；
- 能处理比之前 symbolic verifiers / simulators 更大的 circuit verification；
- 对 parameterized verification 有潜力。

局限：

- 主要是 circuit/state set verification；
- 不建模 FTQC 的 fault model、decoder、magic resource、code switching capability。

对我们有用：

- 如果要证明 parameterized syndrome schedule 或 repeated gadget family，automata 是候选技术。

### 3.7 SWTA：Parameterized Verification of Quantum Circuits

POPL 2026 工作，提出 synchronized weighted tree automata，用于验证 parameterized quantum programs 的 relational properties，如 correctness 和 equivalence。验证被化约为 functional inclusion/equivalence checking。

Link: https://arxiv.org/abs/2511.19897

贡献：

- 首个 fully automatic framework for relational verification of parameterized quantum programs；
- 适合验证无限 circuit family；
- 实现中多个例子毫秒到秒级完成。

局限：

- 不面向 FTQC resource/effect；
- 不处理 QEC-specific fault-tolerance criteria。

对我们有用：

- FTQC 的 code distance、syndrome rounds、factory levels 都是参数。SWTA 思路可用于验证规则 schema。

### 3.8 Veri-QEC：Efficient Formal Verification of Quantum Error Correcting Programs

PLDI 2025 工作，直接面向 QEC programs。它定义 QEC-specific assertion logic 和 program logic，建立 sound proof system。对 Pauli errors，把 verification conditions 化约为 classical assertions，交给 SMT；对 non-Pauli errors，提供 heuristic。还在 Coq 中形式化 program logic，并实现自动 verifier Veri-QEC，验证 14 个 stabilizer codes。

Link: https://arxiv.org/abs/2504.07732  
ACM DOI: https://dl.acm.org/doi/10.1145/3729293  
Artifact: https://doi.org/10.5281/zenodo.15267327

贡献：

- 这是目前最直接相关的 QEC formal verification 工作之一；
- 同时有 Coq-based verified verifier 和 Python/SMT automated verifier；
- 覆盖多种 stabilizer code 和 fault-tolerant scenarios。

局限：

- 当前投影逻辑不处理概率；
- gate set 受限；
- 目标是验证 QEC program/gadget，而不是设计 FTQC compiler IR 或 resource calculus；
- 更关注 code/program correctness，而不是跨后端 code switching + magic resource + scheduling 的组合式编译。

与我们不同：

- Veri-QEC 是“给定 QEC program，证明它满足 QEC correctness/fault scenario”；
- 我们是“把 verified QEC/FT protocols 封装成 capability rules，并让 compiler 组合这些 rules 时仍然保持 logical/resource/error soundness”。

### 3.9 Verifying Fault-Tolerance of Quantum Error Correction Codes

CAV 2025 工作，形式化 QECC implementation 的 fault-tolerance，扩展 classical-quantum program semantics 来建模 faulty executions，并用 quantum symbolic execution 自动验证 fault tolerance。它把 continuous errors 离散化到 input states 和 Pauli errors，并处理 loops、non-Clifford components。

Link: https://arxiv.org/abs/2501.14380  
Springer: https://link.springer.com/chapter/10.1007/978-3-031-98685-7_1

贡献：

- 直接形式化 fault-tolerance criteria；
- 提供自动 symbolic execution tool；
- 能在不同 QECCs 上验证 state preparation、gate、measurement、error correction 等 gadget；
- 可输出违反 fault tolerance 的 error propagation path。

局限：

- 目标是验证 QECC gadget fault-tolerance；
- 不提供面向通用 FTQC 编译的 typed resource/capability abstraction；
- 不解决 heterogeneous backend 之间的资源选择、rule composition、magic-resource scheduling。

与我们不同：

- 它证明“一个 gadget 是 fault-tolerant”；
- 我们用这种证明结果作为 capability certificate，并证明“由这些 certified rules 组合出的 FTQC program 是 sound 的”。

### 3.10 Analyzing Decoders for Quantum Error Correction

2026 arXiv 工作，提出 QEC core language formal semantics，捕获 de facto standard Stim circuit format，并用 verifier 量化 decoder accuracy 和对 physical error-rate drift 的 robustness。它用 structured search 和 constrained polynomial optimization 替代单纯 Monte Carlo simulation。

Link: https://arxiv.org/abs/2603.20127

贡献：

- 把 decoder analysis 从 Monte Carlo 推向 formal analysis；
- 显式处理 decoder accuracy 和 robustness；
- Stim circuit format 获得形式语义基础。

局限：

- 关注 decoder evaluation；
- 不直接处理 FTQC language design、code-indexed typing、magic-resource calculus。

对我们有用：

- Decoder 应在我们的 calculus 中作为 effectful classical oracle/capability，其 assumptions、latency、accuracy、robustness 应进入 effect index。

### 3.11 Stabiliser quantum program semantics

2025 arXiv / PLanQC 2026 工作，为 stabiliser operations 建立 sound、universal、complete denotational semantics，包含 measurement、classically-controlled Pauli operators、affine classical operations，并把 QEC codes 作为 first-class objects。操作解释为 finite fields 上的 affine relations，并给出 proof-of-concept stabiliser programming language 的 fully abstract denotational semantics。

Link: https://arxiv.org/abs/2511.22734

贡献：

- 非常接近 FTQC formal foundation；
- 把 stabilizer/QEC code 提升为一等语义对象；
- 提供比 operator-algebraic semantics 更可计算的语义。

局限：

- 主要是 stabilizer fragment；
- 还不是 universal FTQC resource/effect language；
- 不处理 magic-state resources、probabilistic factories、cross-backend optimization。

对我们有用：

- 可以作为我们 core semantics 的 stabilizer/QEC fragment；
- 对 code switching / logical measurement rules 的 denotational foundation 很有价值。

### 3.12 Stim / Sinter

Stim 是高性能 stabilizer circuit simulator，常用于 QEC circuits。官方描述其目标是 high-performance simulation and analysis of stabilizer circuits, especially QEC circuits。

Link: https://github.com/quantumlib/Stim  
Paper DOI: https://doi.org/10.22331/q-2021-07-06-497

贡献：

- 实用 QEC workflow 的底层事实标准之一；
- detector error model 与 sampling pipeline 很重要；
- 可处理大规模 surface-code-like circuits。

局限：

- 它不是形式证明系统；
- sampling/statistical evidence 不等于 theorem；
- 不提供 typed language semantics 或 compiler correctness theorem。

对我们有用：

- 可作为后端 trace / detector model / benchmark 接口。

### 3.13 ZX calculus and lattice surgery

ZX calculus 可作为 quantum circuits / measurement / lattice surgery 的图形推理语言。The ZX calculus is a language for surface code lattice surgery 将 surface-code lattice surgery operations 与 ZX diagrams 对应起来。

Link: https://dblp.org/rec/journals/quantum/BeaudrapH20  
VyZX: https://chiqp.cs.uchicago.edu/publication/lehmann-2022-vyzx/

贡献：

- 适合表达 surface-code lattice surgery；
- 图形 rewrite 适合优化和等价证明；
- VyZX 在 Coq 中尝试验证 ZX calculus。

局限：

- ZX 很适合等价和图形优化，但不天然表达概率资源、factory throughput、decoder latency、heterogeneous backend capability。

对我们有用：

- 可作为某些 lattice-surgery rules 的 certificate language。

## 4. 我们的工作与现有工作的区别

现有工作大致分成四类：

| 类别 | 代表 | 主要解决 | 主要缺口 |
|---|---|---|---|
| 通用量子语言语义 | QWIRE, Qunity, Proto-Quipper | quantum/classical language foundation | 不处理 FTQC code/resource/fault model |
| 通用程序验证 | CoqQ, QBricks, qRHL/QHL | quantum program correctness | 不专门处理 FTQC protocol composition |
| circuit / parameterized verification | VOQC, LSTA, SWTA | circuit optimizer correctness / circuit family verification | 不表达 QEC code switching、magic resource、decoder effects |
| QEC / fault-tolerance verification | Veri-QEC, CAV 2025 QECC verification, decoder analysis | 验证给定 QEC program/gadget/decoder | 不提供通用 FTQC compiler IR 和 resource/effect abstraction |

我们的 proposed work 应该定位为：

> A certified abstraction layer for composing fault-tolerant quantum protocols.

也就是：

- 不重新发明 QEC verifier；
- 不只验证一个 gadget；
- 不只做 circuit equivalence；
- 不只做 resource estimator；
- 而是把这些工具的结果统一封装成 **certified capability rules**，并在一个 typed/effectful/probabilistic FTQC IR 里组合。

## 5. 具体解决什么瓶颈

### 5.1 Protocol zoo 缺少统一软件接口

最新 FTQC 有 code switching、lattice surgery、magic-state cultivation、distillation、QLDPC logical measurement、decoder、Pauli frame、hardware-specific rotation。现在这些往往通过 backend-specific scripts 和 informal spreadsheets 组合。

我们的解决：

```text
protocol-specific proof
        -> certified capability rule
        -> typed FTQC compiler
```

### 5.2 资源估计与正确性分离

目前 resource estimator 往往只算 cost，不证明 compiler pass 不破坏 assumptions。

我们的解决：

```text
typing judgment:
  Gamma |- P : A ! E

E contains:
  cost, latency, logical_error, failure_probability, factory_demand
```

并证明 resource soundness。

### 5.3 QEC verifier 只验证局部 gadget，缺少组合定理

Veri-QEC 和 CAV 2025 工作可以证明某个 QEC program/gadget 的性质，但 universal FTQC compiler 需要组合很多 gadget。

我们的解决：

```text
rule soundness + type/effect composition
        -> program-level FTQC soundness
```

### 5.4 Classical control / decoder assumptions 不可见

很多 FTQC 后端隐含了 decoder latency、perfect decoder、postselection、frame update assumptions。

我们的解决：

把 decoder/feedforward 建模为 indexed effects：

```text
Decode[M, latency, accuracy, drift_bound]
FrameUpdate[PauliFrame]
Postselect[p_accept]
```

### 5.5 后端差异太大，编译器不可移植

Surface code、color code、QLDPC、neutral atom、superconducting backend 的 constraints 不同。

我们的解决：

capability library，而不是 monolithic backend：

```text
Backend = set of certified rules
Compiler = search/optimize over rules
```

## 6. 对社区的贡献

一个成熟版本可以贡献四件事。

### 6.1 一个 FTQC core calculus

给出 encoded qubits、code transitions、magic resources、logical measurements、decoder effects、probabilistic resource effects 的最小语言。

### 6.2 一个 certified capability rule framework

规则包含：

```text
name
precondition
postcondition
logical semantics
resource effect
fault model assumption
certificate / proof obligation
```

这能把 Veri-QEC、symbolic execution、ZX、stabilizer semantics、manual theorem 产生的结果统一导入。

### 6.3 一组 soundness theorems

至少包括：

- type preservation；
- logical soundness；
- resource/effect soundness；
- capability composition soundness；
- optimization correctness。

### 6.4 prototype compiler and evaluation

建议实现：

- input：logical circuit / small FTQC IR；
- backend：surface-code cultivation + code switching + logical measurement examples；
- optimizations：switch placement、magic-resource scheduling、distance/resource inference；
- verification：rule checker + SMT/Coq/Stim-assisted validation；
- benchmarks：QFT fragment、phase estimation、Hamiltonian simulation kernel、arithmetic circuits、T/CCZ-heavy workloads。

## 7. Rule 能否形式化证明或自动生成

可以，但要分层。

### 7.1 Rule 的结构

```text
Rule R:
  pre:   Gamma |- inputs well-typed
  op:    backend protocol / gadget
  post:  Gamma' |- outputs well-typed
  eff:   cost, latency, error, failure
  cert:  proof obligations
```

例如 code switching：

```text
Switch[c1 -> c2]:
  pre:  q : Q[c1, d]
  post: q : Q[c2, d']
  eff:  switch_cost + fail_prob + logical_error_bound
  cert:
    stabilizer/code-space mapping correct
    logical operators mapped correctly
    measured checks commute as required
    faults up to t satisfy criterion under model M
```

### 7.2 什么可以自动验证

对 stabilizer / Clifford / CSS / code switching 类规则：

- stabilizer matrix 检查；
- symplectic tableau 检查；
- logical operator mapping；
- commutation checking；
- syndrome extraction consistency；
- bounded fault enumeration；
- SMT encoding of Pauli error propagation；
- symbolic execution；
- automata-based parameterized checking。

对 magic resource / cultivation / factory：

- output fidelity bound 通常来自 protocol theorem 或 numerical proof；
- acceptance probability 可进入 effect；
- injection correctness 可用 stabilizer + non-stabilizer resource semantics；
- scheduling correctness 可作为 resource/effect theorem。

### 7.3 什么可以自动生成

可以生成候选 rule：

- 从 stabilizer code 自动发现 transversal Clifford capability；
- 从 logical operator map 生成 code-switch candidate；
- 从 lattice-surgery template 生成 measurement rule；
- 从 factory/cultivation profile 生成 resource provider rule；
- 从 capability graph 生成 switch schedule；
- 从 cost model 生成 optimization plan。

但最终必须是：

```text
generator proposes
verifier checks
compiler imports verified rules only
```

这是最稳妥的 POPL 叙事。

## 8. 最需要详细阅读的 POPL 论文

按对当前课题的重要性排序。

### 第一组：必须精读

**Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages**  
为什么读：这是最接近 “type system + resource bound soundness + tool evaluation” 的模板。你的 resource/effect system 可以直接借鉴它的结构。

**On Circuit Description Languages, Indexed Monads, and Resource Analysis**  
为什么读：它解释如何给 circuit generation + resource analysis 建语义底座。你的 FTQC calculus 需要类似 indexed/effect semantics。

**Proto-Quipper with Dynamic Lifting**  
为什么读：FTQC 的 decoder/feedforward/staging 与 dynamic lifting 问题高度相似。modal typing 是你处理 runtime classical information 的关键参考。

**Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime**  
为什么读：学习如何把量子资源管理写成 PL 社区熟悉的 affine/lifetime 类型系统。magic states、patches、ancilla 都可以类比。

**Parameterized Verification of Quantum Circuits**  
为什么读：你的很多 FTQC rules 都是参数化的。SWTA 这篇能帮你理解如何把 infinite circuit families 变成自动验证问题。

### 第二组：验证和逻辑核心

**CoqQ: Foundational Verification of Quantum Programs**  
为什么读：如果你要做 mechanized proof 或 rule checker，CoqQ 是最接近的 foundational platform。

**An Expressive Assertion Language for Quantum Programs**  
为什么读：学习如何设计 assertion language，并证明 weakest precondition / relative completeness 这类硬定理。你需要类似语言表达 code membership、syndrome constraints、resource invariants。

**RapunSL: Untangling Quantum Computing with Separation, Linear Combination and Mixing**  
为什么读：FTQC 的 patch locality、factory locality、syndrome locality 都适合借鉴 separation logic 的 frame rule 思想。

**Verifying Quantum Circuits with Level-Synchronized Tree Automata**  
为什么读：帮助理解 symbolic representation + decidability + implementation benchmark 的 POPL 写法。

**Automating Equational Proofs in Dirac Notation**  
为什么读：如果你的 rule certificate 涉及 logical operator identities、Pauli frame identities、stabilizer algebra，这篇提供“自动化数学推理”的写法模板。

### 第三组：语言抽象和叙事

**Qudit Quantum Programming with Projective Cliffords**  
为什么读：它把 Clifford/Pauli structure 变成类型化编程对象。你的 code capabilities 和 logical operator typing 可以借鉴。

**Qunity: A Unified Language for Quantum and Classical Computing**  
为什么读：学习如何把一个领域的“低层操作集合”重构成统一语言概念。FTQC 也需要把 code、resource、syndrome、frame 变成一等语言 construct。

**Quantum Circuits Are Just a Phase**  
为什么读：学习如何提出一个有传播力的 conceptual reframing。你的 hook 可以是 “Fault-tolerant programs are typed resource transitions.”

**Generating Compilers for Qubit Mapping and Routing**  
为什么读：它把多后端碎片化转化为生成式编译框架。你的 capability library + rule-based compiler 与它在叙事上接近。

### 第四组：有余力再读

**Hadamard-Pi / With a Few Square Roots**  
适合理解 equational characterization，但与你的工程目标距离稍远。

**Quantum Bisimilarity via Barbs and Contexts**  
适合学习“指出 naive observer/context power 太强，然后修复语义假设”的写法。对 decoder oracle assumptions 有启发。

**Enriched Presheaf Model of Quantum FPC**  
理论门槛高，除非你准备走 pure semantics / full abstraction 路线，否则不应作为当前主线。

## 9. 建议的学习路线

### 第 1 阶段：PL 基础最小包

先掌握：

- operational semantics；
- denotational semantics；
- type soundness；
- Hoare logic；
- effect system；
- SMT / proof assistant 基本区别。

建议以 QWIRE、Flexible Resource Estimation、Proto-Quipper-Dyn 为主。

### 第 2 阶段：量子验证工具链

读：

- CoqQ；
- SQIR/VOQC；
- QBricks；
- Veri-QEC；
- CAV 2025 QECC fault-tolerance verification。

目标是理解“哪些证明适合 Coq，哪些适合 SMT，哪些适合 symbolic execution”。

### 第 3 阶段：FTQC-specific abstraction

读：

- Veri-QEC；
- Verifying Fault-Tolerance of QECCs；
- Analyzing Decoders for QEC；
- Denotational semantics for stabiliser quantum programs；
- ZX calculus for lattice surgery；
- 最新 code switching / cultivation / QLDPC 文献。

目标是确定 capability rule 的 proof obligations。

## 10. 最终判断

这个方向能满足 POPL 的四个标准，但要把边界说清楚。

**软件痛点**：FTQC protocol zoo 缺少 compositional programming abstraction；资源、错误、失败概率、decoder assumptions 不可见。

**小而硬形式核心**：code-indexed probabilistic resource calculus，包含 typed rules、effects、operational/denotational semantics。

**正确性叙事**：rule soundness、type preservation、logical soundness、resource/effect soundness、optimization correctness。

**非玩具证据**：prototype compiler、certified rule library、SMT/Coq/Stim-assisted verifier、真实 protocol case studies、T/CCZ-heavy benchmarks。

最重要的是：这项工作不应声称“我们比 Veri-QEC 更会验证 QEC code”，也不应声称“我们发明了更好的 FTQC protocol”。更稳的贡献是：

> We make verified FTQC protocols compositional, programmable, resource-aware, and optimizable.

换句话说，现有工作证明一个个局部部件是正确的；你的工作让这些部件可以作为 typed, certified, probabilistic resource rules 被编译器安全地组合。
