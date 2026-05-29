# Code-Indexed Probabilistic Resource Calculus for Universal FTQC

检索与整理日期：2026-04-27

依据的 Zotero collections：

- `QEC/magic state distillation`
- `QEC/fault-tolerance operation`

本文给出一套可作为论文核心的 calculus 定义、规则组织方式、正确性叙事和一个 case study。目标不是取代物理协议，而是把已有 FTQC/QEC 协议包装成可组合、可检查、可优化的 typed capability rules。

最新设计补充：本文不把 magic-state distillation 和 code switching 看成两个孤立技巧，而把它们统一为 **non-Clifford / universal-resource acquisition** 问题。也就是说，一个逻辑 `T`、`CCZ` 或一般非 Clifford 能力，可以通过 magic resource injection、code switching/gauge fixing、logical teleportation、pieceable FT、hardware-tailored direct rotation、measurement-free coherent feedback 等不同路径获得。CiPR-FTQC 的核心价值是让这些路径作为带证书的 rule 被编译器组合、比较、选择和验证。

## 0. Problem, motivation, and contribution story

### 0.1 这项工作要解决的具体问题

当前 FTQC 软件栈里，一个逻辑程序通常先被看成普通 logical circuit，然后后端再用某种工程流程实现非 Clifford gate、code switching、factory scheduling、decoder/feedforward 和 error-budget allocation。这个流程的核心问题是：

```text
logical program:
  H; T; CCZ; measure

FTQC implementation decisions:
  Which code is each logical qubit currently in?
  Is T acquired by magic state injection, code switching, teleportation,
  pieceable FT, or hardware-native rotation?
  Which magic resources are linear and already consumed?
  Which decoder/feedforward assumptions are required?
  Which branch is postselected, and what is the acceptance probability?
  Does an intermediate state have State soundness or only Observable soundness?
  What is the combined logical-error/resource bound?
```

这些信息在现有工作中往往分散在三类地方：

- 物理论文：证明一个特定 gadget / protocol 是 fault-tolerant；
- resource estimator：统计 T-count、factory volume、cycles 或 surface-code resources；
- backend compiler：把已选定的 protocol 降到某个硬件 schedule。

缺失的是中间的 PL/compiler 层：

```text
Given many certified FTQC implementation paths,
how do we safely compose them,
choose among them,
and preserve logical correctness, resource bounds,
and explicit assumptions end to end?
```

CiPR-FTQC 解决的不是“发明一个新的 T gate protocol”，而是解决：

```text
universal FTQC implementation choice
as a typed, probabilistic, resource-aware, certificate-carrying
program elaboration problem.
```

### 0.2 为什么这个问题重要

FTQC 正在从单一 surface-code + magic-state-factory 叙事走向异构实现：

- 有些 code 支持 transversal Clifford；
- 有些 color/tetrahedral/3D code 支持 transversal non-Clifford；
- 有些方案通过 code switching / gauge fixing 获得 universal gates；
- 有些后端可能 mid-circuit measurement 慢，因此偏好 coherent feedback / measurement-free switching；
- 有些早期 FTQC 设备 qubit 很少，可能偏好 zero-level / small factory；
- 大规模算法又可能偏好 high-throughput factories。

因此，“一个 logical `T` 怎么实现”不再是固定答案，而是一个带约束的编译选择：

```text
Acquire[T,q] under K
```

其中 `K` 可以包括：

```text
error_budget
space_budget
time_budget
factory_slots
measurement_latency
decoder_latency
allowed_certificate_level
backend_capabilities
```

如果没有形式化接口，这些选择会停留在手工工程判断里。结果是：

- compiler 很难证明不同 protocol 混合后仍实现同一个 logical program；
- resource comparison 很难复现，因为 assumption scattered；
- backend-specific optimizations 很难安全复用；
- 新 protocol 进入软件栈时需要重新写大量 ad hoc logic。

### 0.3 为什么现有工作没有直接解决

现有工作各自解决了重要子问题，但边界不同。

**QEC / FTQC protocol verification** 通常问：

```text
Given this gadget, is it fault-tolerant?
```

例如验证一个 code-switching gadget、一个 distillation circuit、一个 syndrome extraction circuit。它们给出 local correctness，但不回答：

```text
How should a compiler compose many such gadgets
while preserving resource linearity, error bounds,
postselection effects, and assumption boundaries?
```

**Resource estimators** 通常问：

```text
Given a chosen architecture and protocol family,
what is the cost?
```

它们擅长估算 factory footprint、surface-code cycles、logical error 等，但通常默认某条 implementation path 已经选定。它们不把：

```text
magic injection vs code switching vs teleportation vs measurement-free path
```

建模成一个 typed rule-selection problem。

**Quantum programming languages / circuit IRs** 通常关注：

```text
How to express quantum algorithms or circuits safely?
```

它们处理 no-cloning、measurement、classical control、circuit generation、resource counting 等问题，但通常不把 encoded logical qubit 当前所在 code、decoder-mediated effects、magic-state linear resources、postselection failure、code switching 和 FTQC certificate levels 作为核心类型/效果对象。

**Backend compilers / routing tools** 通常关注：

```text
Given an operation schedule, how to place/route/lower it?
```

它们解决硬件约束和 layout 问题，但不提供一个高层 theorem：

```text
typed acquisition plan + valid certificates
  => logical semantics preserved
  => resource/effect bounds preserved
```

因此，我们的切入点不是替代这些工作，而是补它们之间的缺口：

```text
local FTQC protocol certificates
  -> typed capability rules
  -> compositional acquisition planner
  -> verified effect/certificate sidecar
```

### 0.4 我们方案的核心创新

#### Innovation 1: Universal-resource acquisition as a typed planning problem

把 `T`、`CCZ`、`Rz(theta)` 这类 universal capability 的获得统一写成：

```text
Acquire[g,q]
```

而不是分别写成孤立的 magic-state distillation、code switching、teleportation 或 hardware-native gate。

这带来一个 conceptual shift：

```text
old view:
  T-count is an input statistic.

CiPR view:
  acquiring each non-Clifford capability is a typed,
  optimizable, certificate-carrying elaboration problem.
```

#### Innovation 2: Code-indexed typestate for encoded logical data

逻辑 qubit 的类型不只是：

```text
q : LogicalQubit
```

而是：

```text
q : Q[code, distance, correctness_mode]
```

这让 compiler 可以静态拒绝：

```text
transv T q
```

如果当前 code 不支持 transversal `T`；也可以拒绝把 only-observable-correct 的中间态当作 state-level magic injection 输入。

#### Innovation 3: Probabilistic linear resources

Magic states、Bell pairs、auxiliary encoded states、factory outputs 都是 linear resource：

```text
m : TState[c,d,eps]
```

一旦用于 injection / teleportation，就从 resource context 消失。这防止“同一个 magic state 被两个 T gate 重用”这类在普通 resource spreadsheet 里不容易暴露的错误。

#### Innovation 4: Effect algebra for FTQC-specific costs and assumptions

Effect 不应展开成一大堆工程字段，而应集中在 FTQC 最核心的三元 tradeoff：

```text
E = <logical_error, physical_qubits, ftqc_cycles>
```

这允许 planner 比较：

```text
CodeSwitchT vs ZeroLevelT vs Surface15to1 vs TeleportT vs SwitchMF_T
```

postselection、decoder、reset、certificate level 等仍然记录，但作为 metadata / side conditions，不作为主 effect 维度。这样论文主线更清楚：所有 acquisition path 都投影到同一个 `(error, space, time)` 坐标系。

#### Innovation 5: Proof atoms + certified protocol macros

我们不把 `distill`、`switch`、`inject` 当作最底层原语，而是把它们展开成更基本的 proof atoms：

```text
alloc / consume / clifford / transv / pauli_check
decode / frame / postselect / coherent_syndrome / coherent_frame / reset_clean
```

关键是不能有一个泛化的 `apply U`，否则任何 protocol 都能被藏进去。每个 atom 必须对应明确 checker：

```text
clifford:
  symplectic tableau / stabilizer update

transv:
  code signature + logical operator action

pauli_check:
  commutation, syndrome, detector/logical observable relation

decode:
  decoder certificate / statistical or theorem bound

coherent_syndrome:
  equivalence to a Pauli-check syndrome extraction

reset_clean:
  disentanglement / no logical information leakage certificate
```

这比“列很多 primitive”更有抽象深度，也更接近 POPL 论文中的 small core + derived forms。

#### Innovation 6: Certificate-aware compilation

每条 rule 有 certificate level：

```text
Checked / Certified / Assumed
```

soundness theorem 默认只对 `Checked` / `Certified` 成立。`Assumed` 仍可用于探索，但 sidecar 必须写清楚 conditional soundness。

这给 FTQC 工程带来一个重要能力：

```text
The compiler can tell the difference between
"proved by checker",
"imported theorem",
and "engineering assumption".
```

### 0.5 对 FTQC 社区的实际价值

#### Value 1: 把 protocol 变成可复用的软件接口

FTQC 社区不断提出新的 code switching、factory、cultivation、teleportation、measurement-free feedback protocol。CiPR-FTQC 提供一个进入 compiler 的统一接口：

```text
protocol paper result
  -> capability rule
  -> certificate / assumptions
  -> effect profile
  -> reusable compiler component
```

这样新 protocol 不只是论文里的 isolated construction，而可以进入一个可比较、可组合的 rule library。

#### Value 2: 让不同 universal strategies 可以公平比较

同一个 logical operation 可以通过多条路径实现：

```text
T:
  code switch + transversal T
  zero-level T state + inject
  15-to-1 distillation + inject
  logical teleportation
  measurement-free coherent switch
```

CiPR-FTQC 让这些路径在同一个 effect algebra 下比较：

```text
logical error vs physical qubits vs FTQC cycles
```

acceptance loss、decoder latency、certificate level 等放进 sidecar metadata，用于解释或派生 expected time，但不作为核心 effect 维度。

这对架构选择、实验设计、resource estimation 和 compiler optimization 都有直接价值。

#### Value 3: 防止非法 FTQC 组合

实际 FTQC 软件中很多错误不是单个 gadget 错，而是组合错：

- 在不支持 `T` 的 code 上直接用 transversal `T`；
- magic state 被重复消费；
- postselection failure 被当作确定性过程；
- observable-only guarantee 被传给需要 state-level guarantee 的 rule；
- decoder latency / calibration assumption 在 lowering 后丢失；
- `Assumed` protocol 被当作 theorem 使用。

CiPR-FTQC 的 type/effect/certificate checker 可以在编译时暴露这些问题。

#### Value 4: 生成可审计的 certificate/effect sidecar

最终输出不只是 QASM/Stim/QIR，而是：

```text
(backend trace, certificate/effect sidecar)
```

sidecar 记录：

```text
chosen rules
typing derivation
effect bounds
certificate levels
assumptions
postselection policy
decoder requirements
```

这对实验复现、resource-estimation audit、跨团队 protocol comparison 很重要。

#### Value 5: 支持异构和早期 FTQC 设备

早期 FTQC 设备资源稀缺，且不同平台有不同优势：

- neutral atoms / ions 可能有 strong transversal or nonlocal operations；
- superconducting surface-code systems 可能更适合 factories；
- measurement-slow architectures 可能偏好 coherent feedback；
- small devices 可能偏好 zero-level or low-overhead schemes。

CiPR-FTQC 可以把这些差异写成 constraints and effects，而不是为每个平台重写一套 compiler logic。

### 0.6 最终论文主张

一句话版本：

> CiPR-FTQC turns universal fault-tolerant quantum computation from a collection of protocol-specific engineering choices into a typed, probabilistic, resource-aware, certificate-carrying compilation problem.

更具体地：

```text
Given:
  a logical program,
  a library of certified FTQC capability rules,
  backend/resource constraints,

CiPR-FTQC provides:
  a code-indexed type system,
  probabilistic linear resources,
  proof-atom based protocol macros,
  effect algebra,
  acquisition planner,
  and certificate/effect sidecar,

such that:
  accepted compiled plans preserve logical semantics,
  compose resource/error bounds,
  expose assumptions,
  and reject invalid FTQC compositions.
```

### 0.7 需要明确的边界

为了避免过度声称，论文应明确：

```text
We do not claim:
  automatically invent arbitrary new FTQC protocols;
  replace detailed physical verification of each gadget;
  solve all backend routing and scheduling problems.

We claim:
  once protocols are expressed as capability rules with certificates,
  the compiler can compose, compare, select, and audit them
  with formal logical/resource guarantees.
```

## 1. 从两个 collection 得到的设计约束

### 1.1 Magic-state distillation collection 的启发

这个 collection 覆盖了几类不同 magic-resource provider：

1. **经典 magic-state distillation**
   - Bravyi-Kitaev 说明 Clifford + magic states 足以实现 universal quantum computation。
   - 15-to-1 / 7-to-1 / 5-to-1 等协议可看成：

```text
k noisy magic resources
    -> probabilistic / postselected protocol
    -> 1 cleaner magic resource
```

2. **Surface-code factory optimization**
   - Litinski 强调 distillation 不应只看 T-count，而要看 code distance allocation、space-time volume、factory layout。
   - Constant-time magic state distillation 用 transversal CNOT + iterative decoder，把 7-to-1 / 15-to-1 的时间复杂度降到 O(1) code cycles，并保留 `p -> O(p^3)` 的 error suppression。

3. **Zero-level distillation**
   - Zero-level distillation 在 physical level 使用 Steane-code-style verification，输出 surface-code logical magic state。
   - 关键 profile：

```text
ZeroLevelT:
  output_error ~= 100 p^2
  accept_rate ~= 70% at p = 1e-3
  accept_rate ~= 95% at p = 1e-4
  depth = 25 for teleportation-based rotated-surface output
```

4. **Logical MSD experiment**
   - 2025 neutral-atom logical magic state distillation 展示了 logical-level 5-to-1 factory。
   - 核心结构：

```text
5 logical magic inputs
  -> transversal Clifford distillation circuit
  -> measure 4 syndrome logical qubits
  -> postselect / stabilizer flagging
  -> 1 higher-fidelity logical magic output
```

5. **Constant-overhead magic state distillation**
   - 使用 asymptotically good codes with transversal non-Clifford gates，实现 constant overhead。
   - 对 calculus 的启发是：factory rule 不能写死为 15-to-1；应该允许不同 protocol family 作为 resource provider。

6. **Bell-pair / entanglement distillation**
   - Bell-pair distillation、constant-rate repeaters 表明 magic resources 不是唯一 resource；Bell pairs、encoded entanglement 也应以同样方式建模。

结论：magic resource 在 calculus 里应是 **linear probabilistic resource**，distillation/cultivation/zero-level/factory 是 **resource provider rule**，带有 success probability、output error、latency、space-time cost、postselection condition 和 decoder assumptions。

### 1.2 Fault-tolerance operation collection 的启发

这个 collection 给出三类 fault-tolerant operation：

1. **Measurement-based code switching**
   - PRX Quantum 2024 在 [[7,1,3]] Steane / 2D color code 与 [[15,1,3]] tetrahedral / 3D color code 间切换。
   - 核心结构：

```text
Q[CodeA]
  -> measure target stabilizers
  -> apply gauge / Pauli correction based on outcomes
  -> Q[CodeB]
```

2. **One-way transversal-CNOT code switching**
   - Quantum 2025 使用 one-way transversal CNOT 和 logical teleportation 实现 2D/3D color code switching。
   - 对 calculus 的约束：
     - code switching 可以是 deterministic，也可以依赖 auxiliary logical states。
     - switching rule 需要记录 directionality、auxiliary state requirement、connectivity、measurement latency。

3. **Measurement-free FT code switching**
   - Science Advances 2025 用 coherent syndrome extraction + quantum feedback + reset 替代 mid-circuit measurement/feedforward。
   - 对 calculus 的约束：
     - classical feedback 不是唯一控制模式；
     - 需要区分 `classical feedback effect` 和 `coherent feedback/reset effect`。

4. **Transversal algorithmic FT**
   - Low-overhead transversal FT 表明某些方案不要求每个中间 gadget 都 individually FT。
   - 它保证的是 final logical measurement distribution，而不是每一步都 close to codespace。
   - 对 calculus 的关键影响：语义需要区分两种 correctness modality：

```text
state-soundness:
  physical trace realizes logical channel/state

observable-soundness:
  final logical measurement distribution is correct,
  even if intermediate state is not close to code space
```

结论：calculus 不能只表达 unitary gate list。它必须表达 code-state transitions、measure/decode/feedforward、coherent feedback/reset、decoder assumptions、postselection 和不同形式的 soundness。

## 2. Calculus 总览

暂名：**CiPR-FTQC**

全称：**Code-indexed Probabilistic Resource Calculus for Fault-Tolerant Quantum Computation**

核心判断：

> FTQC program is not just a logical circuit. It is a typed transition system over encoded logical states, probabilistic resources, and decoder-mediated effects.

### 2.1 Universal-resource acquisition view

CiPR-FTQC 的中心抽象不是“某一个 T-gate gadget”，而是一个 acquisition goal：

```text
Acquire[g, q]
```

其中 `g` 可以是：

```text
T, CCZ, Toffoli, Rz(theta), non-Clifford family G
```

`Acquire[g, q]` 的含义是：在当前 code、noise、resource、backend 约束下，为逻辑对象 `q` 获取并实现能力 `g`，同时产生可检查的 effect bound 和 correctness certificate。

同一个 acquisition goal 可以被不同 rule family 实现：

```text
Acquire[T, q]
  -> switch Steane3 -> Tetra15; transv T; switch back
  -> prepare/distill TState; inject T
  -> logical measurement / teleportation gadget
  -> pieceable FT protocol
  -> hardware-tailored direct logical rotation
  -> measurement-free coherent switching protocol
```

这个抽象的边界要写清楚：calculus 和 compiler 可以从 certified rule library 中组合、搜索、比较实现路径，也可以从 rule templates 生成 proof obligations；但它不声称自动发明任意新的物理 FTQC 协议。新的协议必须先通过模板化 verifier、外部证明或显式 assumption 进入 rule library。

### 2.2 三层对象

CiPR-FTQC 分三层：

1. **Logical layer**
   - 用户想表达的算法：Clifford、T/CCZ、measurement、classical control。

2. **FTQC typed layer**
   - encoded logical qubits；
   - code switching；
   - magic resources；
   - logical measurement；
   - decoder/feedforward；
   - resource/error/failure effects。

3. **Backend trace layer**
   - Stim / OpenQASM / QIR / hardware-specific schedule；
   - detector annotations；
   - logical observables；
   - sidecar certificate。

本文的 calculus 定义第二层，并给第一层到第二层、第二层到第三层的 soundness story。

## 3. Static objects

### 3.1 Code signatures

一个 code family 定义为：

```text
C = {
  name: CodeName,
  params: d, n, k, ...
  stabilizers: S_X, S_Z, S_general,
  logicals: L_X, L_Z,
  distance: d,
  decoder: Dec,
  capabilities: CapSet
}
```

例子：

```text
Steane3:
  code = [[7,1,3]]
  transversal = {H, S, CNOT}

Tetra15:
  code = [[15,1,3]]
  transversal = {T, CNOT}

Surface(d):
  code = rotated surface code
  native = {syndrome extraction, lattice surgery, measurement}

Color(d):
  native = transversal Clifford
```

### 3.2 Correctness mode

不同 FTQC protocol 保证的东西不同。定义 correctness mode：

```text
mu ::= State | Observable
```

- `State`：intermediate encoded state is close to ideal logical state / codeword。
- `Observable`：最终 logical measurement distribution 正确，但中间态不一定 close to codespace。

类型里记录这个 mode：

```text
Q[c, d, mu]
```

例子：

```text
q : Q[Surface, 15, State]
q : Q[Surface, 15, Observable]
```

`Observable` mode 用于表达 transversal algorithmic FT 这类工作。

### 3.3 Resource kinds

资源种类：

```text
rho ::= TState[c,d,eps]
      | CCZState[c,d,eps]
      | SHState[c,d,eps]
      | Bell[c,d,eps]
      | AuxState[c,d,psi,eps]
      | Factory[kind, profile]
```

资源是 linear 的：默认只能消耗一次。

```text
m : TState[Surface, d, eps]
```

表示一个 encoded T magic state，所在 code 是 `Surface`，logical error / infidelity bound 是 `eps`。

同时定义 acquisition goal：

```text
g ::= T | CCZ | Toffoli | Rz(theta) | GateFamily[name, params]
```

注意：`g` 不是普通 linear resource。它是编译器要实现的逻辑能力，可以通过两类方式满足：

- **resource-producing path**：先产生 `TState`、`CCZState`、`Bell`、`AuxState`，再通过 injection/teleportation 消耗；
- **capability-changing path**：通过 code switching、gauge fixing、pieceable FT 或 hardware-specific operation 临时进入支持 `g` 的 code/backend context。

因此，`Acquire[g,q]` 是一个 elaboration construct：它最终必须被展开为普通 primitive commands 和 certified capability rules。

### 3.4 Contexts

typing judgment 使用三个上下文：

```text
Omega; Gamma; Delta |- P : A ! E
```

含义：

- `Omega`：classical context，记录 bits、syndromes、decoder output、Pauli frame。
- `Gamma`：quantum context，记录 encoded logical data。
- `Delta`：linear resource context，记录 magic states、Bell pairs、auxiliary code states。
- `A`：返回值或输出 context。
- `E`：effect bound。

例子：

```text
Omega;
Gamma = q : Q[Steane3, 3, State];
Delta = m : TState[Steane3, 3, 1e-8]
|- injectT(q,m) : Q[Steane3, 3, State] ! E
```

## 4. Effect algebra

### 4.1 Core effect: three quantities

Effect 不应该变成 telemetry record。对 FTQC 主论文来说，核心 effect 只保留三个量：

```text
E = <epsilon_L, S, T>
```

含义：

- `epsilon_L`：logical error rate / logical failure probability upper bound。
- `S`：space，peak physical qubits required by the protocol。
- `T`：time，number of FTQC cycles / code cycles on the critical path。

也可以写成：

```math
E(P) = \langle \epsilon(P),\; S(P),\; T(P) \rangle
```

这三个量对应 FTQC 社区最关心的 tradeoff：

```text
How reliable is it?   -> logical error rate
How large is it?      -> physical qubits
How long does it run? -> FTQC cycles
```

Space-time volume 不是独立主 effect，而是派生指标：

```math
V(P) = S(P)\cdot T(P)
```

如果需要更精细的 schedule volume，可以在实现中计算 `sum_i S_i T_i`，但论文的 effect system 不应把它作为第四个主维度。

### 4.2 Metadata is not effect

有些信息仍然需要记录，但它们不应和三元 effect 混在一起。它们属于 metadata / side conditions：

```text
M = {
  success_probability / acceptance_bound,
  retry_policy,
  decoder_assumptions,
  measurement_or_reset_requirements,
  connectivity_assumptions,
  certificate_level,
  certificate_ids
}
```

因此 rule profile 应写成：

```text
profile(R) = (E_R, M_R)

E_R = <epsilon_R, S_R, T_R>
M_R = assumptions/certificates/control metadata
```

例子：

```text
ZeroLevelT:
  E = <100 p^2, S_zl, 25>
  M = {
    accept >= 0.70 at p=1e-3,
    retry_policy = restart_factory_prefix,
    cert = cert_zero_level
  }
```

如果 planner 需要把 probabilistic retry 折算进时间，可以从 metadata 派生：

```math
T_{\mathsf{expected}} = T / \alpha
```

其中 `alpha` 是 acceptance lower bound。注意这仍然是 time metric 的一个解释方式，不是新的主 effect。

### 4.3 Sequential composition

如果：

```text
P ! <eps1, S1, T1>
Q ! <eps2, S2, T2>
```

则：

```math
E(P;Q)
=
\left\langle
  \epsilon_1+\epsilon_2,\;
  \max(S_1,S_2),\;
  T_1+T_2
\right\rangle
```

解释：

- logical error 用 union bound；
- 顺序执行的 peak space 是两个阶段 peak 的最大值；
- time 是 critical-path cycles 相加。

Metadata 单独组合：

```text
M(P;Q) =
  assumptions(P) join assumptions(Q),
  certs(P) union certs(Q),
  retry/acceptance policy composed when needed
```

### 4.4 Parallel composition

如果 `P || Q` 作用在 disjoint qubits/resources：

```math
E(P\parallel Q)
=
\left\langle
  \epsilon_P+\epsilon_Q,\;
  S_P+S_Q,\;
  \max(T_P,T_Q)
\right\rangle
```

解释：

- logical error 仍保守相加；
- 并行空间相加；
- 并行时间取 critical path。

### 4.5 Bounded iteration and symbolic effects

Parameterized case studies 只需要三元组上的符号表达。

Sequential repetition:

```math
E(\mathsf{repeat}_{seq}\;n\;P)
=
\langle
  n\epsilon(P),\;
  S(P),\;
  nT(P)
\rangle
```

Parallel repetition:

```math
E(\mathsf{repeat}_{par}\;n\;P)
=
\langle
  n\epsilon(P),\;
  nS(P),\;
  T(P)
\rangle
```

For symbolic planning:

```math
E(n,d,k)
=
\langle
  \epsilon(n,d,k),\;
  S(n,d,k),\;
  T(n,d,k)
\rangle
```

The checker mainly proves obligations such as:

```math
\epsilon(n,d,k) \le \epsilon_{\mathsf{budget}}
\qquad
S(n,d,k) \le S_{\mathsf{max}}
\qquad
T(n,d,k) \le T_{\mathsf{max}}
```

This keeps the calculus focused: other fields are useful for engineering audit, but the formal effect theorem is about logical error, space, and time.

## 5. Syntax

### 5.1 Terms

这里的 `P ::= ...` 是 BNF-style grammar：它不是说用户必须手写很多种“程序”，而是在定义 calculus 里程序项 `P` 可以有哪些形状。

为了避免把 calculus 写成 protocol catalog，核心语法应尽量小。真正的核心只有两类东西：

1. **composition forms**：顺序、并行、参数化重复；
2. **rule application forms**：申请一个 high-level capability，或应用一条已经认证的 capability rule。

因此，最小核心语法可以写成：

```text
P ::= skip
    | let x = P in P
    | P ; P
    | P || P
    | repeat n P
    | acquire g q under K
    | use R(v1,...,vk)
```

解释：

- `skip`、`;`、`||`、`repeat` 是普通程序组合。
- `let x = P in Q` 绑定一个 rule application 的结果，例如 syndrome、frame、magic resource。
- `acquire g q under K` 是编译期 goal，不是物理 primitive。Lowering 前必须被 elaboration 消去。
- `use R(v1,...,vk)` 是唯一的低层核心动作：应用一条 rule library 中已经 `Checked` / `Certified` / explicitly `Assumed` 的 capability rule。

这样核心 calculus 很小；后面出现的 `switch`、`distill`、`inject` 等不是新的核心语义构造，而是更易读的 surface notation。

例如：

```text
transv T q
```

只是：

```text
use TransvT_Tetra15(q)
```

而：

```text
m = distill Surface15to1(raw_1,...,raw_15)
```

只是：

```text
m = use Surface15to1(raw_1,...,raw_15)
```

论文正文和 case study 可以继续用 `transv/switch/inject/distill` 这类名字，因为它们可读性更好；形式化核心中则只需要 `use R(...)`。

### 5.2 Rule-family classes

这些不是额外的 core primitives，也不应叫真正的“原子命令”。它们是 rule family / surface aliases。每个 family 都通过同一个核心形式 `use R(...)` 进入 calculus：

```text
Transversal gate:
  transv g q
  == use Transv[g,c,d](q)

Code transition:
  switch pi q
  == use Switch[pi](q)

Magic-resource provider:
  distill D(...)
  cultivate C(...)
  prepare rho using pi
  == use Provider[D or C or pi](...)

Resource consumption:
  inject k q m
  == use Inject[k,c,d](q,m)

Measurement and classical control:
  measureL O q
  decode dec syndrome
  frame_update q f
  == use Measure / Decode / FrameUpdate

Measurement-free control:
  coherent_syndrome
  coherent_frame
  reset_clean
  == use MeasurementFreeStep / ResetClean

Universal-resource acquisition:
  acquire g q under K
```

`acquire g q under K` 是编译期形式，不是物理后端指令。它要求 planner 在约束 `K` 下选择一条已认证 implementation path，例如 `switch+transv+switch`、`distill+inject` 或 `logical teleportation`。Lowering 前必须消去所有 `acquire`，只留下 `use R(...)` 形式的 certified rule applications。

因此，判断“原语是不是太多”的标准是：

```text
core calculus primitive:
  skip / let / ; / || / repeat / acquire / use

rule-library family:
  transv / switch / distill / inject / measure / decode / reset / ...
```

前者应保持极少；后者可以多，因为它们是可扩展的库接口，不改变 calculus 的 soundness proof 结构。

### 5.3 Deeper atomic abstraction

上面的 `switch/distill/inject/teleport` 仍然太像 protocol 名字。更深入的抽象应把它们看成由少量 **proof atoms** 组成的 protocol macro。

核心思想：

```text
core syntax:
  how programs compose

proof atoms:
  what primitive proof steps exist

protocol rules:
  reusable certified macros built from proof atoms

acquisition plans:
  compiler-selected compositions of protocol rules
```

`apply U` 不能作为 atom，因为它太强：任意 physical schedule、任意 coherent feedback、甚至整个 distillation protocol 都可以伪装成一个 `U`。这样的 atom 没有解释力，也无法带来共享验证基础。

更合理的 atom 集合应该按 **verification method** 划分，而不是按 protocol 名字划分：

```text
alpha ::= alloc rho as x
        | consume x
        | clifford C on B
        | transv g on B under c
        | pauli_check P on B as s
        | decode D on H as f
        | frame F(f) on B
        | postselect phi(H,f)
        | coherent_syndrome S on B into r
        | coherent_frame F(r) on B
        | reset_clean r
```

含义：

- `alloc rho as x`：引入 typed resource，例如 clean ancilla、Bell pair、raw magic state、syndrome register。
- `consume x`：线性消费一个 resource，防止 magic state / aux state 重用。
- `clifford C on B`：只允许 Clifford/stabilizer-preserving layer；checker 用 symplectic tableau 验证 stabilizer/logical action。
- `transv g on B under c`：只允许 code signature 声明的 transversal/native protected layer；checker 验证 physical tensor-product action induces declared logical gate。
- `pauli_check P on B as s`：测量 stabilizer、gauge、logical Pauli product 或 Bell observable；checker 验证 commutation、detector relation 和 logical observable annotation。
- `decode D on H as f`：从 syndrome history `H` 得到 Pauli/gauge frame 或 accept/reject decision；checker 导入 decoder bound。
- `frame F(f) on B`：只更新 Pauli/gauge/logical correction frame，不等于任意物理 gate。
- `postselect phi(H,f)`：声明 accepted branch；failure/acceptance 进入 metadata，并可派生 expected time。
- `coherent_syndrome S on B into r`：measurement-free syndrome extraction；checker 证明它等价于对应 `pauli_check` 的 syndrome map。
- `coherent_frame F(r) on B`：由 syndrome register 控制的有限 correction network；不是 arbitrary unitary，必须对应一个 classical correction table。
- `reset_clean r`：只有在 `r` 与 logical data disentangled 且不含 logical information 时允许 reset。

这些 atoms 不是物理硬件最底层 gate set，而是 FTQC verification 的最小公共接口。它们的粒度比 `distill`、`switch` 更小，但又不低到每个物理 CNOT 都进入 calculus。

每个 atom 都有明确的 verification hook：

```text
Atom                    Checker / proof method
alloc                   resource-kind and preparation certificate
consume                 linear context update
clifford                stabilizer tableau / symplectic action
transv                  code signature + logical operator map
pauli_check             commutation + detector/logical observable checks
decode                  decoder theorem / simulation certificate
frame                   frame algebra, no physical state change unless lowered
postselect              predicate coverage + acceptance bound metadata
coherent_syndrome       equivalence to Pauli syndrome extraction
coherent_frame          finite correction table + controlled-Pauli network
reset_clean             disentanglement / clean reset certificate
```

形式上，每条 protocol rule 可以有一个 atom expansion：

```math
R(\vec v) \Downarrow \alpha_1;\alpha_2;\cdots;\alpha_n
```

并由 atom-level soundness 推出 rule-level soundness：

$$
\frac{
  R(\vec v)\Downarrow P_R
  \qquad
  P_R = \alpha_1;\cdots;\alpha_n
  \qquad
  \bigwedge_i \mathsf{AtomSound}(\alpha_i)
  \qquad
  \Omega;\Gamma;\Delta\vdash P_R:A_R\;!\;E_R
}{
  \mathsf{RuleSound}(R,\Omega,\Gamma,\Delta,\vec v)
}
\quad\text{Rule-From-Atoms}
$$

因此 `use R(...)` 有两种可信来源：

```text
Checked:
  R expands to proof atoms, and atom-level VCs are discharged.

Certified:
  R is imported as an external theorem/certificate,
  optionally with an atom expansion used for explanation and resource checking.
```

#### Protocols as atom compositions

Code switching can be written as:

```text
Switch(c1 -> c2):
  pauli_check target_stabilizers / gauge_checks as H
  decode dec_switch on H as f
  frame corr_switch(f)
```

Measurement-based teleportation:

```text
TeleportT:
  alloc teleport_resource as a
  pauli_check Bell_logical(q,a) as b
  decode dec on H as f
  frame T_correction(b,f)
  consume a
```

Magic-state injection:

```text
InjectT:
  pauli_check injection_observable(q,m) as b
  decode dec on H as f
  frame S_or_Pauli_correction(b,f)
  consume m
```

15-to-1 distillation:

```text
Surface15to1:
  consume raw_1,...,raw_15
  clifford Clifford_distillation_layer on factory_block
  pauli_check distillation_checks as H
  decode distill_decoder on H as f
  postselect accept(H,f)
  frame output_frame(f)
  alloc TState[Surface,d,eps_out] as m_out
```

Zero-level distillation:

```text
ZeroLevelT:
  alloc physical_T_candidates
  clifford verification_layer
  pauli_check verification_checks as H
  decode zero_level_decoder on H as f
  postselect accept(H,f)
  frame output_surface_frame(f)
  alloc TState[Surface,3,100p^2] as m_out
```

Measurement-free switching:

```text
SwitchMF(c1 -> c2):
  alloc syndrome_register as r
  coherent_syndrome switch_checks on q into r
  coherent_frame corr_switch(r) on q
  reset_clean r
```

The point is that many named FTQC protocols are not fundamental. They are reusable certified macros over a small atom vocabulary. This makes the calculus look less like a list of primitives and more like a proof-generating language interface.

## 6. Types

### 6.1 Value types

```text
A ::= Unit
    | Bit
    | Syndrome[c]
    | Frame[c]
    | Q[c,d,mu]
    | Res[rho]
    | A * A
    | Prob[A]
```

`Prob[A]` 表示 probabilistic / postselected computation，实际可建模为 subdistribution monad。

### 6.2 Resource linearity

资源上下文 `Delta` 线性使用：

```text
Delta, m : TState[c,d,eps] |- inject T q m ...
```

这里 `inject T q m` 是 `use InjectT(q,m)` 的 readable alias。`m` 在 rule conclusion 后从 `Delta` 中消失。

### 6.3 Protection mode subtyping

可以允许：

```text
Q[c,d,State] <: Q[c,d,Observable]
```

因为 state-level correctness implies observable-level correctness。

反方向不成立。

这对 Low-Overhead Transversal FT 很重要：某些 constant-round SE protocol 可以保持 observable correctness，但不应被错误地当成 state-close codeword 输入给需要 state guarantee 的 rule。

## 7. Capability rules

### 7.1 Rule schema

所有后端规则统一为：

```text
rule R {
  params: theta
  pre:    precondition over Omega, Gamma, Delta
  op:     backend protocol / schedule template
  atoms:  optional expansion alpha_1;...;alpha_n
  post:   output Omega', Gamma', Delta'
  effect: E(theta)
  cert:   proof obligations / certificate
}
```

编译器只导入 verified rule：

```text
Candidate rule -> checker -> certified rule library
```

Candidate rule 可以来自手写协议描述、论文 profile、自动模板生成或外部证明工具，但进入 rule library 时必须带 certificate level。没有证书的 rule 只能作为 planning hypothesis，不能作为默认 soundness theorem 的前提。

下面各小节用 `transv`、`switch`、`distill`、`inject` 等名字写 typing rules，是为了可读性。形式化时它们都可以 desugar 成：

```text
Omega; Gamma; Delta |- use R(v1,...,vk) : A ! E_R
```

其中 `R` 是带 precondition、postcondition、effect 和 certificate 的 capability rule。

更正式地，统一 rule application 可以写成：

```math
\frac{
  R \in \mathcal{L}
  \qquad
  \mathsf{CertOK}(R)
  \qquad
  \mathsf{Pre}_R(\Omega,\Gamma,\Delta,\vec v)
}{
  \Omega;\Gamma;\Delta
  \vdash
  \mathsf{use}\;R(\vec v)
  :
  A_R
  \;!\;
  E_R
}
\quad\text{T-Use}
```

其中：

```math
\mathcal{L}
  = \{R \mid R\text{ is an imported capability rule}\}
```

`T-Use` 是核心规则。后面的 `T-Transversal`、`T-Switch`、`T-Distill` 等都可以看作 `T-Use` 的命名实例。

### 7.1.1 Universal-resource acquisition

`Acquire` 把不同 universal FTQC 技术放在同一个 typed planning 问题里：

```text
[T-Acquire]
Goal(g, q)
Impl_i in CertifiedRules
Impl_i implements g under constraints K
pre(Impl_i) holds over Omega, Gamma, Delta
planner selects Impl*
----------------------------------------------------------
Omega; Gamma; Delta |- acquire g q under K
  : A_Impl* ! E_Impl*
```

用 elaboration 关系写得更像 PL 论文：

```math
\frac{
  \mathsf{Plan}_{K,\mathcal L}(g,q,\Omega,\Gamma,\Delta)=P
  \qquad
  \Omega;\Gamma;\Delta\vdash P:A\;!\;E
  \qquad
  \mathsf{erase}(P)=g(q)
}{
  \Omega;\Gamma;\Delta
  \vdash
  \mathsf{acquire}\;g\;q\;\mathsf{under}\;K
  \leadsto
  P
  :
  A\;!\;E
}
\quad\text{Elab-Acquire}
```

这里 `\leadsto` 表示 compile-time elaboration。`acquire` 不进入 backend trace：

```math
\mathsf{lower}(\mathsf{acquire}\;g\;q) \text{ is undefined}
\qquad
\mathsf{lower}(P) \text{ is defined after elaboration.}
```

`Acquire` 的 conclusion 由被选中的 implementation 决定。典型情况：

```text
CodeSwitchT:
  Q[Steane3,d,State] -> Q[Steane3,d,State]

MagicInjectT:
  Q[Surface,d,State] * TState[Surface,d,eps] -> Q[Surface,d,State]

DistillThenInjectT:
  Q[Surface,d,State] -> Q[Surface,d,State]

TeleportT:
  Q[c,d,State] * AuxState[...] -> Q[c,d,State]
```

这条 rule 的意义不是引入新的物理 primitive，而是把 high-level non-Clifford demand elaborated into a certified plan。Elaboration 后程序中不再出现 `acquire`，只剩下 `use R(...)` 形式的低层 rule applications；论文中写成 `switch`、`transv`、`distill`、`inject`、`measureL`、`decode`、`frame_update`、`reset` 只是 surface notation。

对于论文叙事，这一点很关键：magic-state distillation、code switching、pieceable FT、logical teleportation 都是 acquisition implementations；它们在 effect/certificate 层可比较，在 type/correctness 层可组合。

### 7.2 Transversal gate

```text
[T-Transversal]
CapTrans(c, g, d, mu, cert)
q : Q[c,d,mu] in Gamma
-----------------------------------------
Omega; Gamma |- transv g q : Q[c,d,mu] ! E_g
```

Certificate obligations：

- physical transversal gate preserves stabilizer group；
- logical operator action equals `g`；
- fault propagation is bounded under declared noise model；
- resource profile is valid。

Examples：

```text
CapTrans(Steane3, H)
CapTrans(Steane3, S)
CapTrans(Steane3, CNOT)
CapTrans(Tetra15, T)
```

### 7.3 Code switching

```text
[T-Switch]
CapSwitch(pi : c1 -> c2, d1, d2, mu_in, mu_out, cert)
q : Q[c1,d1,mu_in]
requirements(pi) subset Delta
--------------------------------------------------------
Omega; Gamma; Delta |- switch pi q
  : Q[c2,d2,mu_out] ! E_switch(pi)
```

Certificate obligations：

- common logical operator representation or explicit logical map；
- target stabilizer projection / gauge fixing preserves encoded logical state；
- measurement outcomes / coherent feedback implement correct correction；
- dangerous data/ancilla/measurement errors are detected/corrected/postselected；
- output mode is correctly classified as `State` or `Observable`；
- resource bound is certified。

Examples from the collection：

```text
SwitchFlag_7_15:
  Steane3 -> Tetra15
  measurement-based, flag FT

SwitchFlag_15_7:
  Tetra15 -> Steane3
  measurement-based, flag FT

SwitchOneWay_7_15:
  Steane3 -> Tetra15
  logical teleportation via one-way transversal CNOT

SwitchMF_7_15:
  measurement-free coherent switching
```

### 7.4 Magic-state resource provider

Generic distillation:

```text
[T-Distill]
CapDistill(D, kind, k, f_err, f_accept, cert)
m1 : Magic[kind,c,d,eps1], ..., mk : Magic[kind,c,d,epsk] in Delta
-------------------------------------------------------------------
Omega; Gamma; Delta |- distill D(m1,...,mk)
  : Res[Magic[kind,c,d,f_err(eps1,...,epsk)]] ! E_D
```

Resource consumption:

```text
[T-Inject]
CapInject(c, kind, gate, cert)
q : Q[c,d,State]
m : Magic[kind,c,d,eps_m]
----------------------------------------------------------
Omega; Gamma; Delta |- inject gate q m
  : Q[c,d,State] ! E_inj(err = eps_m + eps_inj)
```

Important: `inject` generally requires `State`, not merely `Observable`, unless a protocol-specific certificate says otherwise.

### 7.5 Zero-level distillation

From the zero-level distillation paper:

```text
[T-ZeroLevel]
CapZeroLevelT(
  output = TState[Surface,d=3],
  err(p) ~= 100 p^2,
  accept(p) ~= 0.70 at p=1e-3, 0.95 at p=1e-4,
  depth = 25,
  cert
)
----------------------------------------------------------
Omega; Gamma; Delta |- prepare T using ZeroLevel
  : Res[TState[Surface,3,100 p^2]] ! E_ZL
```

If code distance expansion is used:

```text
[T-Expand]
CapExpand(Surface, d1 -> d2, cert)
m : TState[Surface,d1,eps]
----------------------------------------------------------
expand m : TState[Surface,d2, eps + eps_expand] ! E_expand
```

### 7.6 Constant-time 15-to-1 distillation

From constant-time magic state distillation:

```text
[T-15to1-CT]
CapDistill(
  D = Surface15to1,
  kind = T,
  k = 15,
  f_err(eps) = 35 eps^3 + eps_circ(d,p),
  f_accept(eps) >= 1 - O(15 eps),
  cycles = 6,
  qubit_rounds = 111 d^2,
  decoder = IterativeTransversalCNOT
)
```

Typing:

```text
m1,...,m15 : TState[Surface,d,eps]
----------------------------------------------------------
distill Surface15to1(m1,...,m15)
  : TState[Surface,d,35 eps^3 + eps_circ(d,p)] ! E_15
```

The exact `eps_circ` is imported from the rule certificate or numerical verifier.

### 7.7 Logical 5-to-1 MSD

From the logical MSD experiment:

```text
[T-5to1-Logical]
CapDistill(
  D = Logical5to1,
  kind = SH,
  k = 5,
  code = Color(d),
  f_err = quadratic suppression + circuit_noise,
  accept_ideal = 1/6,
  postselection = distillation syndrome + optional stabilizer flags
)
```

This rule is useful because it demonstrates resource-state factory as a logical circuit over encoded qubits, not merely a physical protocol.

### 7.8 Measurement and decoder

```text
[T-MeasureL]
CapMeasure(c, O, basis, cert)
q : Q[c,d,mu]
----------------------------------------------------------
measureL O q : Bit ! E_meas
```

Decoder effect:

```text
[T-Decode]
CapDecode(dec, c, d, noise, latency, accuracy, cert)
s : Syndrome[c]
----------------------------------------------------------
decode dec s : Frame[c] ! E_dec
```

The decoder is not invisible. It contributes:

```text
decoder_latency
decoder_failure_bound
assumptions
```

### 7.9 Algorithmic FT rule

This rule captures the Low-Overhead Transversal FT style.

```text
[T-AlgFT]
CapAlgFT(
  code_family = c(d),
  ops = transversal Clifford + magic inputs + feedforward,
  decoder = correlated decoder,
  se_rounds = O(1),
  guarantee = observable distribution,
  err(d,p) = exp(-Theta(d)),
  cert
)
P uses only allowed ops
----------------------------------------------------------
Omega; Gamma |- algft P : ObservableOutput ! E_alg
```

Output mode is `Observable`, not `State`.

This prevents unsound composition such as:

```text
algft_state -> used as high-fidelity magic state input
```

unless an additional rule certifies state-level quality.

### 7.10 Measurement-free rule

Measurement-free code switching has coherent syndrome extraction and reset:

```text
[T-MF-Switch]
CapMFSwitch(pi : c1 -> c2, aux, feedback, reset, cert)
q : Q[c1,d,State]
aux : AuxState[...]
----------------------------------------------------------
switch_mf pi q : Q[c2,d,State] ! E_mf
```

Effect includes:

```text
resets
coherent_feedback_gates
toffoli_or_ccz_count
entropy_disposal_assumption
```

## 8. Semantics

### 8.1 Logical erasure

Erasure removes code/resource annotations:

```text
erase(Q[c,d,mu]) = LogicalQubit
erase(transv H q) = H q
erase(switch pi q) = identity on logical state
erase(inject T q m) = T q
erase(distill D(...)) = resource-state preparation
```

Code switching erases to logical identity, possibly with frame update.

### 8.2 Physical trace semantics

Each certified rule lowers to a physical/backend trace:

```text
lower_R(theta) = Trace
```

Trace may include:

- physical gates；
- stabilizer measurements；
- detector declarations；
- logical observable annotations；
- decoder calls；
- Pauli frame updates；
- resets；
- postselection branches；
- resource accounting metadata。

The semantics is a subdistribution:

```text
[[P]]_phys : InputState -> SubDist(OutputState + Fail)
```

### 8.3 Correctness relation

For `State` mode:

```text
[[P]]_phys approx_epsilon [[erase(P)]]_logical
```

For `Observable` mode:

```text
Dist(final_measurements([[P]]_phys),
     final_measurements([[erase(P)]]_logical)) <= epsilon
```

This distinction is necessary to include algorithmic FT.

### 8.4 Formal verification relations

为了让逻辑验证部分像 PL 论文一样可引用，可以把语义关系整理成一组固定 judgment。

#### Typed program judgment

```math
\Omega;\Gamma;\Delta \vdash P : A\;!\;E
```

含义：

```text
在 classical context Omega、quantum context Gamma、
linear resource context Delta 下，程序 P 返回 A，
并产生三元 effect bound E = <epsilon_L, S, T>。
```

#### Atom judgment

如果使用 proof atoms，可以给 atoms 一个更细的 judgment：

```math
\Omega;\Gamma;\Delta
\vdash_{\alpha}
\alpha
:
(\Omega',\Gamma',\Delta')
\;!\;
E_{\alpha}
```

含义是 atom `alpha` 把 context 从 `(\Omega,\Gamma,\Delta)` 转到 `(\Omega',\Gamma',\Delta')`，并产生 effect `E_alpha`。

Atom soundness 是所有 protocol verification 的最小公理/引理集合：

```math
\mathsf{AtomSound}(\alpha)
\;\triangleq\;
\mathsf{AtomCorr}_{E_{\alpha}.\epsilon_L}(\alpha)
\land
\mathsf{EffOK}(\alpha,E_{\alpha})
```

Protocol rule 的验证可以写成 atom composition：

```math
\frac{
  R(\vec v)\Downarrow \alpha_1;\cdots;\alpha_n
  \qquad
  \Omega_0;\Gamma_0;\Delta_0
    \vdash_{\alpha}
    \alpha_1;\cdots;\alpha_n
    :
    (\Omega_n,\Gamma_n,\Delta_n)
    \;!\;
    E
}{
  \Omega_0;\Gamma_0;\Delta_0
    \vdash
    \mathsf{use}\;R(\vec v)
    :
    A_R
    \;!\;
    E
}
\quad\text{Use-Expanded}
```

#### Erasure judgment

```math
\mathsf{erase}(P)=L
```

其中 `L` 是普通 logical quantum program。例如：

```math
\mathsf{erase}(\mathsf{use}\;\mathsf{Switch}_{c_1,c_2}(q)) = \mathsf{id}(q)
```

```math
\mathsf{erase}(\mathsf{use}\;\mathsf{TransvT}_{\mathsf{Tetra15}}(q)) = T(q)
```

```math
\mathsf{erase}(\mathsf{use}\;\mathsf{InjectT}(q,m)) = T(q)
```

#### Physical semantics

对于已消去 `acquire` 的程序：

```math
\llbracket P \rrbracket_{\mathsf{phys}}
:
\mathsf{EncState}(\Gamma,\Delta)
\to
\mathsf{SubDist}(\mathsf{EncState}(A)+\mathsf{Fail})
```

逻辑程序语义为：

```math
\llbracket L \rrbracket_{\mathsf{log}}
:
\mathsf{LogState}(\mathsf{erase}(\Gamma))
\to
\mathsf{Dist}(\mathsf{LogState}(A))
```

#### State correctness

令：

```math
\mathsf{Dec}_{\Gamma}
:
\mathsf{EncState}(\Gamma)
\to
\mathsf{LogState}(\mathsf{erase}(\Gamma))
```

则 state-level correctness 可以写成：

```math
\mathsf{StateCorr}_{\epsilon}(P,L)
\;\triangleq\;
\forall \rho.\;
D\!\left(
  \mathsf{Dec}_{A}
    \left(
      \llbracket P \rrbracket_{\mathsf{phys}}
        (\mathsf{Enc}_{\Gamma}(\rho))
      \mid \mathsf{accept}
    \right),
  \llbracket L \rrbracket_{\mathsf{log}}(\rho)
\right)
\le \epsilon
```

这里 `D` 可以取 trace distance 或论文中固定的 logical-state distance。`|\mathsf{accept}` 表示对 postselected accepted 分支归一化。

#### Observable correctness

对于只保证最终测量分布的 protocol：

```math
\mathsf{ObsCorr}_{\epsilon}(P,L,O)
\;\triangleq\;
\forall \rho.\;
\mathsf{TV}\!\left(
  \mathsf{Meas}_{O}
    \left(
      \llbracket P \rrbracket_{\mathsf{phys}}
        (\mathsf{Enc}_{\Gamma}(\rho))
      \mid \mathsf{accept}
    \right),
  \mathsf{Meas}_{O}
    \left(
      \llbracket L \rrbracket_{\mathsf{log}}(\rho)
    \right)
\right)
\le \epsilon
```

其中 `TV` 是 total variation distance。

#### Effect validity

```math
\mathsf{EffOK}(P,E)
\;\triangleq\;
\begin{aligned}
&\epsilon_{\mathsf{phys}}(P) \le E.\epsilon_L
\\
&S_{\mathsf{phys}}(\mathsf{lower}(P)) \le E.S
\\
&T_{\mathsf{phys}}(\mathsf{lower}(P)) \le E.T
\end{aligned}
```

Postselection、decoder、reset、connectivity 和 certificate 信息由 metadata judgment 记录：

```math
\mathsf{MetaOK}(P,M)
```

它不属于核心 effect theorem，但用于审计、conditional soundness 和 expected-time 派生。

## 9. Main theorems

### 9.1 Type preservation

If:

```text
Omega; Gamma; Delta |- P : A ! E
```

and `P -> P'`, then there exist `Omega'`, `Gamma'`, `Delta'`, `A'`, `E'` such that:

```text
Omega'; Gamma'; Delta' |- P' : A' ! E'
```

and `E' <= E` for remaining trace budget.

### 9.2 Capability soundness

Every imported capability rule must satisfy:

```math
\mathsf{CertOK}(R)
\Longrightarrow
\forall \Omega,\Gamma,\Delta,\vec v.\;
\mathsf{Pre}_R(\Omega,\Gamma,\Delta,\vec v)
\Longrightarrow
\mathsf{RuleSound}(R,\Omega,\Gamma,\Delta,\vec v)
```

where:

```math
\mathsf{RuleSound}(R,\Omega,\Gamma,\Delta,\vec v)
\;\triangleq\;
\begin{cases}
\mathsf{StateCorr}_{E_R.\mathsf{err}}
  (\mathsf{use}\;R(\vec v),\mathsf{erase}(R))
\land
\mathsf{EffOK}(\mathsf{use}\;R(\vec v),E_R),
& \mu_R=\mathsf{State}
\\[4pt]
\mathsf{ObsCorr}_{E_R.\mathsf{err}}
  (\mathsf{use}\;R(\vec v),\mathsf{erase}(R),O_R)
\land
\mathsf{EffOK}(\mathsf{use}\;R(\vec v),E_R),
& \mu_R=\mathsf{Observable}
\end{cases}
```

This theorem is usually proved per rule family:

- stabilizer/transversal rules by symplectic tableau；
- code-switching rules by stabilizer/logical operator mapping + fault enumeration；
- magic distillation by protocol theorem / numerical certificate；
- decoder rules by decoder correctness or statistical certificate。

### 9.3 Program logical soundness

If:

$$
\Omega;\Gamma;\Delta\vdash P:A\;!\;E\triangleright M
\qquad
\mathsf{AllCertOK}(M.\mathsf{certs})
$$

then:

```math
\frac{
  \Omega;\Gamma;\Delta\vdash P:A\;!\;E\triangleright M
  \qquad
  \mathsf{AllCertOK}(M.\mathsf{certs})
  \qquad
  \mathsf{mode}(A)=\mathsf{State}
}{
  \mathsf{StateCorr}_{E.\epsilon_L}(P,\mathsf{erase}(P))
  \land
  \mathsf{EffOK}(P,E)
  \land
  \mathsf{MetaOK}(P,M)
}
\quad\text{Sound-State}
```

and:

```math
\frac{
  \Omega;\Gamma;\Delta\vdash P:A\;!\;E\triangleright M
  \qquad
  \mathsf{AllCertOK}(M.\mathsf{certs})
  \qquad
  \mathsf{mode}(A)=\mathsf{Observable}
}{
  \mathsf{ObsCorr}_{E.\epsilon_L}(P,\mathsf{erase}(P),O_A)
  \land
  \mathsf{EffOK}(P,E)
  \land
  \mathsf{MetaOK}(P,M)
}
\quad\text{Sound-Obs}
```

The exact relation is state-level or observable-level depending on output mode.

### 9.4 Resource soundness

For any physical trace `t` produced by `lower(P)`:

```math
\frac{
  \Omega;\Gamma;\Delta\vdash P:A\;!\;E\triangleright M
  \qquad
  t \in \mathsf{Traces}(\mathsf{lower}(P))
}{
  S(t) \le E.S
  \quad\land\quad
  T(t) \le E.T
}
\quad\text{Resource-Sound}
```

where `S(t)` is peak physical qubits and `T(t)` is FTQC/code cycles. Measurements, resets, decoder assumptions, and certificate references are recorded in `M`, not in the core effect.

### 9.5 Optimization correctness

For an optimizer:

```math
\mathsf{opt}(P)=P'
```

prove:

```math
\frac{
  \Omega;\Gamma;\Delta\vdash P:A\;!\;E
  \qquad
  \mathsf{opt}(P)=P'
}{
  \Omega;\Gamma;\Delta\vdash P':A\;!\;E'
  \quad\land\quad
  \mathsf{erase}(P')=\mathsf{erase}(P)
  \quad\land\quad
  E' \preceq_{\mathcal M} E
}
\quad\text{Opt-Sound}
```

Here `\preceq_{\mathcal M}` means improvement under the selected metric set or Pareto preorder.

Examples:

- choose code-switch implementation versus magic-state implementation；
- minimize switch count；
- choose zero-level + 15-to-1 versus direct high-distance factory；
- schedule factories in parallel。

## 10. Rule certificates and automatic generation

核心设计原则：

```text
protocol sketch / template parameters
  -> proof-generating template
  -> verification conditions
  -> checker / solver / external proof
  -> certified capability rule
```

编译器不信任“自动生成出来的 rule”。它只信任生成后被 checker 接受的 rule，或者显式记录为 assumption 的 rule。

### 10.0 Certificate levels

每条 rule 带 certificate level：

```text
Checked:
  fully checked by the CiPR rule checker

Certified:
  checked by an external proof artifact, simulator certificate,
  Coq/Lean/SMT proof, or domain-specific verifier,
  then imported through a small trusted interface

Assumed:
  based on a published theorem, numerical profile, or hardware claim,
  recorded explicitly in E.assumptions and in the sidecar
```

Soundness theorem 默认只对 `Checked` 和 `Certified` rules 成立。`Assumed` rules 仍可用于探索和工程比较，但最终论文必须把 assumption boundary 写清楚：

```text
typed derivation + checked/certified rules
  => end-to-end soundness

typed derivation + assumed rules
  => conditional soundness under listed assumptions
```

### 10.1 Stabilizer rule certificate

For a stabilizer / Clifford / code-switching rule:

```text
cert_stab = {
  stabilizer_before,
  stabilizer_after,
  logical_map,
  physical_circuit,
  fault_model,
  fault_tolerance_check,
  resource_profile
}
```

Checker obligations:

- stabilizers commute；
- physical circuit maps stabilizers correctly；
- logical operators map as specified；
- faults up to threshold are detected/corrected/postselected；
- resource profile matches circuit。

### 10.2 Magic factory certificate

```text
cert_factory = {
  input_kind,
  output_kind,
  distillation_code,
  suppression_function,
  acceptance_bound,
  circuit_noise_bound,
  resource_profile,
  postselection_condition
}
```

The suppression function can be symbolic:

```text
15-to-1: eps_out <= 35 eps_in^3 + eps_circ
7-to-1:  eps_out <= 7 eps_in^3 + eps_circ
ZeroLevel: eps_out <= 100 p^2
```

### 10.3 Rule-family templates

为了支持“自动生成 rule 并验证”，本文采用 rule-family templates。模板负责把协议参数转化成 verification conditions；checker 负责判断这些 obligations 是否成立。

更具体地，template 不应只生成一个黑箱 rule。它最好生成：

```text
protocol parameters
  -> atom expansion alpha_1;...;alpha_n
  -> typing obligations for atom composition
  -> protocol-specific semantic VCs
  -> effect expression E(theta)
```

这样 `CodeSwitch`、`MagicDistill`、`Teleportation` 等模板共享同一个 atom-level proof infrastructure，而不是各自拥有完全不同的验证器。

#### CodeSwitch template

Inputs:

```text
source code c1
target code c2
logical map L
stabilizer/gauge measurement schedule S
correction function corr
fault model F
```

Obligations:

- measured operators commute with required stabilizers or have a declared gauge interpretation；
- logical map preserves the intended logical state；
- correction function maps outcomes to valid Pauli frame / gauge frame updates；
- faults up to the claimed order are detected, corrected, or pushed into the declared residual error；
- output mode is correctly classified as `State` or `Observable`；
- resource profile counts measurements, resets, ancilla, cycles, and decoder latency。

#### MagicDistill template

Inputs:

```text
distillation code D
input kind rho_in
output kind rho_out
Clifford circuit C
postselection predicate b
noise model F
```

Obligations:

- circuit maps ideal accepted inputs to the desired output magic state；
- rejection predicate detects the specified error set；
- suppression bound `eps_out <= f(eps_in,p)` is proved symbolically or imported as certified；
- acceptance lower bound is proved or imported；
- all consumed magic states are linear resources；
- output code and distance match the injection rule that will consume the result。

#### PieceableFT template

Inputs:

```text
logical operation g
pieces P1,...,Pk
interleaved EC / syndrome extraction rounds
decoder assumptions
```

Obligations:

- each piece has bounded fault spread before the next correction point；
- interleaved correction restores the required invariant；
- composed logical action equals `g`；
- total residual error is bounded under the declared composition rule。

#### LogicalMeasurement / Teleportation template

Inputs:

```text
resource state rho
measurement pattern M
classical correction function f
target logical operation g
```

Obligations:

- measurement pattern implements the desired logical channel up to Pauli frame；
- all branches are covered by correction function `f`；
- resource state fidelity contributes linearly or by a certified bound；
- classical latency/feedforward assumptions are recorded。

#### HardwareTailoredRotation template

Inputs:

```text
backend b
native operation op(theta)
calibrated noise profile N
logical embedding c
```

Obligations:

- native operation realizes the declared logical map within bound；
- leakage/crosstalk/drift assumptions are explicit；
- calibration-dependent bounds are versioned in the certificate；
- lowering target records the hardware-specific schedule and validity window。

#### MeasurementFree template

Inputs:

```text
coherent syndrome extractor
feedback unitary
reset/disposal model
auxiliary states
```

Obligations:

- coherent extraction carries the same syndrome information as the measurement-based rule or a certified equivalent；
- feedback unitary implements the required correction coherently；
- reset/disposal does not leak unmodelled logical information；
- entropy disposal, reset fidelity, and extra non-Clifford/control cost are recorded。

这些 templates 支持自动化，但自动化的边界是明确的：template 可以枚举 candidate schedules、candidate switches、candidate factories；checker 必须接受 VCs 后，candidate 才能成为 usable rule。Template-free arbitrary protocol discovery 不属于本文第一版目标。

### 10.4 What can be generated

Candidate rules can be generated by:

- computing transversal gates from stabilizer/logical operator action；
- finding code-switch mappings between shared logical operators；
- synthesizing stabilizer measurement schedules；
- importing factory profiles from protocol descriptions；
- fitting resource/error models from simulation data；
- generating Stim/OpenQASM lowering and checking resource metadata。

But the compiler should use:

```text
generated rule + checked certificate
```

not:

```text
generated rule by trust
```

## 11. Compiler architecture

The prototype compiler should have four components:

```text
Frontend logical IR
    -> type/effect elaboration
    -> rule-based planner / optimizer
    -> backend lowering
    -> certificate/resource sidecar
```

### 11.1 Input

Small logical IR:

```text
qreg q[1];
H q;
T q;
Measure q;
```

or a small embedded DSL in Python/Rust/OCaml.

### 11.2 Rule library

Example:

```text
Backend ColorSwitch:
  Steane3
  Tetra15
  SwitchOneWay_7_15
  SwitchOneWay_15_7
  TransvT_Tetra15
  TransvH_Steane3

Backend SurfaceMagic:
  Surface(d)
  ZeroLevelT
  Surface15to1
  InjectT_Surface
  ExpandSurface

Backend HybridUniversal:
  AcquireT
  AcquireCCZ
  RegionSwitchT
  RegionSwitchCCZ
  MagicInjectT
  DistillThenInjectT
  TeleportT
```

### 11.3 Planner

Planner 的输入不是单个 gate rule lookup，而是一组 acquisition goals：

```text
Acquire[T, q]
Acquire[CCZ, q1,q2,q3]
Acquire[Rz(theta), q]
```

每个 goal 会展开成候选 implementation path：

```text
Acquire[T, q]:
  candidates =
    MagicInjectT
    ZeroLevelThenInjectT
    DistillThenInjectT
    CodeSwitchT
    LogicalTeleportT
    PieceableT
    HardwareTailoredT
    MeasurementFreeSwitchT
```

选择由约束和目标函数决定：

```text
constraints:
  epsilon_L <= epsilon_budget
  space <= N
  time <= T_max
  backend in {surface, color, neutral_atom, ion_trap}
  measurements_slow = true/false
  mid_circuit_measurement_allowed = true/false
  factory_slots <= F

objective:
  minimize weighted_sum(
    logical_error,
    physical_qubits,
    ftqc_cycles
  )

metadata preferences:
  avoid Assumed certificates
  prefer no mid-circuit measurement when measurements_slow
  account for acceptance/retry when deriving expected time
```

混合策略是第一等需求。Planner 不应在整篇程序层面固定为 “magic only” 或 “code-switch only”，而应按 region 做选择：

```text
dense non-Clifford region:
  switch once into code with transversal T/CCZ
  run many non-Clifford gates
  switch back

isolated T gate:
  use available TState
  or run small/zero-level factory then inject

measurement-slow backend:
  prefer measurement-free switch or coherent feedback

factory-rich surface-code backend:
  prefer distillation + injection
```

这也是本文和传统 resource estimator 的区别之一：传统工具常把 T-count/T-depth 当作输入统计量；CiPR-FTQC 把“怎样获得非 Clifford 能力”本身作为 typed, certified optimization problem。

### 11.4 Lowering

Produce:

```text
program.stim          // stabilizer/QEC fragments
program.qasm          // dynamic circuit fragments
program.ftqc.json     // sidecar certificate/effect metadata
```

Sidecar example:

```json
{
  "logical_program": "T q",
  "chosen_rules": ["ZeroLevelT", "ExpandSurface", "InjectT"],
  "logical_error_bound": "100*p^2 + eps_expand + eps_inject",
  "acceptance_lower_bound": "0.70 at p=1e-3",
  "qubit_rounds": "...",
  "certificates": ["cert_zero_level", "cert_expand", "cert_inject"],
  "certificate_levels": {
    "ZeroLevelT": "Certified",
    "ExpandSurface": "Checked",
    "InjectT": "Checked"
  },
  "assumptions": ["noise_model=phenomenological_depolarizing"]
}
```

## 12. Case study: compiling one logical T gate

### 12.0 POPL-style evaluation standard

参考 `POPL/pdfs/` 中几类论文的写法，case study 不应只说明“这个协议可以用”。它应该回答四个 PL 问题：

```text
abstraction:
  这个 calculus 把哪个原本分散在后端论文里的对象变成了一等程序对象？

static guarantee:
  类型、线性资源、effect 或 certificate checker 静态排除了什么错误？

formal bridge:
  typed elaboration、physical trace 和 logical semantics 之间的 theorem 是什么？

empirical / artifact evidence:
  原型输出什么 artifact，checker 检查什么，planner 比较什么 metric？
```

这对应四种 POPL 量子论文常见证据形式：

- resource typing 论文会展示同一程序在 width/depth/gate-count 等不同 metric interpretation 下的 sound upper bound；
- parameterized verification 论文会展示不是只验证一个固定 circuit，而是验证一族由参数生成的程序；
- compiler-generation 论文会展示同一个抽象接口覆盖多个后端，并和手写/基线方案比较；
- affine/lifetime 论文会展示类型系统不仅接受正确程序，也拒绝微妙但不物理可实现的资源释放/重用。

CiPR-FTQC 的 case study 因此应覆盖：

```text
positive cases:
  same logical T, multiple certified acquisition paths

negative cases:
  programs that look plausible but are rejected by code/effect/resource typing

parameterized cases:
  same proof/effect rules scale with code distance d, factory level k, and T-region size n

artifact cases:
  emitted sidecar records derivation, effects, certificates, and assumptions
```

### 12.1 Goal

Show that the same logical operation:

```text
T q
```

can be compiled through multiple FTQC protocols under one calculus:

1. code-switching implementation；
2. zero-level magic resource implementation；
3. constant-time 15-to-1 factory implementation；
4. logical teleportation implementation；
5. measurement-free coherent switching implementation；
6. hybrid implementation that mixes region-level code switching and local magic injection；
7. negative examples that demonstrate static rejection and assumption boundaries。

The case study demonstrates:

- code-indexed typing；
- linear magic-resource consumption；
- probabilistic success/failure；
- rule selection；
- resource/effect comparison；
- hybrid acquisition planning；
- parameterized resource analysis；
- formal verification-condition tracking；
- lowering target feasibility。

### 12.2 Logical source

```text
fun main(q : LogicalQubit) {
  T q;
  return q;
}
```

The logical erasure target is simply:

```text
erase(main) = T
```

### 12.2.1 Case-study template

每个 case study 都应该按同一套结构呈现，否则容易退化成“列出某个 FTQC gadget”。建议固定包含：

1. **Goal and context**
   - logical source；
   - initial `Omega; Gamma; Delta`；
   - backend constraints `K`；
   - certificate levels allowed by the experiment。

2. **Primitive elaboration**
   - `acquire g q` 被展开成哪些 calculus primitives；
   - 每个 primitive 消耗/产生的 typed object；
   - lowering target 是 Stim、OpenQASM 3、QIR 还是 JSON sidecar。

3. **Verification logic**
   - rule template 产生哪些 verification conditions；
   - 哪些 VC 由 checker 直接验证，哪些由外部 artifact / published theorem 导入；
   - 哪些假设进入 `E.assumptions`。

4. **Formal soundness explanation**
   - 写出该 case 的 typed derivation；
   - 写出 erased logical program；
   - 写出物理 trace 和 logical semantics 的关系；
   - 明确是 `State` soundness 还是 `Observable` soundness。

5. **Effect analysis**
   - core effect: `epsilon_L`、`S`、`T`；
   - metadata: accept/retry、decoder assumptions、reset assumptions、certificate level；
   - sequential / parallel composition 如何计算；
   - 如果存在 restart，说明它如何派生 expected time。

最小形式化输出格式：

```text
Case C:
  source       : logical program L
  elaboration  : P
  erase(P)     : L
  derivation   : Omega; Gamma; Delta |- P : A ! E
  certs        : {R_i : level_i}
  theorem      : ValidCerts(certs) => lower(P) approx_E erase(P)
  effect       : E = compose(E_1,...,E_n)
```

### 12.3 Backend A: code-switching T on color codes

Initial type:

```text
q : Q[Steane3, 3, State]
```

Rule library:

```text
CapTrans(Steane3, H)
CapTrans(Steane3, S)
CapTrans(Steane3, CNOT)
CapTrans(Tetra15, T)
CapSwitch(Steane3 -> Tetra15, SwitchOneWay_7_15)
CapSwitch(Tetra15 -> Steane3, SwitchOneWay_15_7)
```

Compiler elaboration:

```text
q1 = switch SwitchOneWay_7_15 q
q2 = transv T q1
q3 = switch SwitchOneWay_15_7 q2
return q3
```

Typing derivation:

```text
q  : Q[Steane3,3,State]
---------------------------------- [T-Switch]
q1 : Q[Tetra15,3,State]
---------------------------------- [T-Transversal]
q2 : Q[Tetra15,3,State]
---------------------------------- [T-Switch]
q3 : Q[Steane3,3,State]
```

Effect:

```text
E_code_switch =
  E_switch_7_15 ;
  E_transv_T ;
  E_switch_15_7
```

So:

```text
err <= eps_7_15 + eps_T + eps_15_7
accept = accept_7_15 * accept_15_7
cycles = cycles_7_15 + cycles_T + cycles_15_7
```

If using deterministic switching:

```text
accept = 1
fail = 0
```

If using postselected / nondeterministic switching:

```text
accept < 1
fail > 0
```

What this case checks:

- The compiler will reject `transv T q` directly on `Steane3` because no `CapTrans(Steane3,T)` exists.
- It accepts the three-step implementation because the intermediate type is `Q[Tetra15,3,State]`.
- Resource/effect accounting includes switch cost and auxiliary state requirement.

Verification logic:

```text
Rule SwitchOneWay_7_15:
  template = LogicalMeasurement / Teleportation + CodeSwitch
  level    = Checked or Certified
  VCs:
    VC-CS-1  source and target logical bases define the same one-qubit logical space
    VC-CS-2  transversal CNOT / teleportation circuit implements the declared logical identity map
    VC-CS-3  all measurement outcomes are covered by correction function corr_7_15
    VC-CS-4  Pauli frame update preserves logical X/Z interpretation after switching
    VC-CS-5  all single faults under the declared distance-3 fault model are detected,
             corrected, or included in eps_7_15
    VC-CS-6  auxiliary logical states are consumed linearly
    VC-CS-7  output is classified as State, not merely Observable

Rule TransvT_Tetra15:
  template = TransversalNonClifford
  level    = Certified
  VCs:
    VC-T-1  transversal physical T preserves the Tetra15 codespace
    VC-T-2  induced action on encoded basis states is logical T up to known Pauli/phase frame
    VC-T-3  transversal fault propagation is bounded by eps_T under the imported noise model
    VC-T-4  resource profile counts 15 physical T applications and one logical cycle

Rule SwitchOneWay_15_7:
  same obligations as SwitchOneWay_7_15 with inverse logical map
```

Formal verification explanation:

```text
P_switch =
  switch SwitchOneWay_7_15 q ;
  transv T q ;
  switch SwitchOneWay_15_7 q

erase(P_switch) =
  id ; T ; id = T

Theorem for this case:
  ValidCert(SwitchOneWay_7_15)
  and ValidCert(TransvT_Tetra15)
  and ValidCert(SwitchOneWay_15_7)
  ------------------------------------------------------------
  [[lower(P_switch)]]_phys approx_{E_code_switch.err} T
  with failure <= E_code_switch.fail
  and cost    <= E_code_switch.cost
```

This is a `State`-soundness case. The output type is again:

```text
Q[Steane3,3,State]
```

so the result can be safely passed to another state-level rule, including magic injection, further code switching, or logical measurement.

Core effect analysis:

```text
E_switch_7_15 = <eps_7_15, S_7_15, tau_7_15>
E_transv_T    = <eps_T,    15,     1>
E_switch_15_7 = <eps_15_7, S_15_7, tau_15_7>

E_code_switch =
  E_switch_7_15 ; E_transv_T ; E_switch_15_7

epsilon_L(E_code_switch)
  <= eps_7_15 + eps_T + eps_15_7

S(E_code_switch)
  = max(S_7_15, 15, S_15_7)

T(E_code_switch)
  = tau_7_15 + 1 + tau_15_7
```

Metadata:

```text
accept >= alpha_7_15 * alpha_15_7
certs  = {cert_switch_7_15, cert_transv_T_tetra15, cert_switch_15_7}
decoder/measurement assumptions are recorded in the sidecar
```

If the switch rule is one-way and requires a prepared encoded Bell/resource state, the resource context makes that explicit:

```text
Delta =
  b1 : Bell[Steane3,Tetra15,eps_b1],
  b2 : Bell[Tetra15,Steane3,eps_b2]

After elaboration:
  b1 and b2 are absent from Delta
```

This is the first place where the case study should look like a PL result: the compiler does not merely choose a circuit macro; it checks a typed transition, consumes auxiliary resources, composes effect bounds, and proves the erased behavior is the original `T`.

### 12.4 Backend B: zero-level T-state then injection on surface code

Initial type:

```text
q : Q[Surface,d,State]
```

Rule library:

```text
CapZeroLevelT
CapExpand(Surface, 3 -> d)
CapInject(Surface, T)
```

Compiler elaboration:

```text
m0 = prepare T using ZeroLevel
m1 = expand m0 from Surface(3) to Surface(d)
q1 = inject T q m1
return q1
```

Typing derivation:

```text
---------------------------------- [T-ZeroLevel]
m0 : TState[Surface,3,100 p^2]

m0 : TState[Surface,3,100 p^2]
---------------------------------- [T-Expand]
m1 : TState[Surface,d,100 p^2 + eps_expand]

q : Q[Surface,d,State]
m1 : TState[Surface,d,eps_m]
---------------------------------- [T-Inject]
q1 : Q[Surface,d,State]
```

Effect:

```text
E_zero =
  E_zero_level ;
  E_expand ;
  E_inject
```

For example, using the zero-level paper profile:

```text
err_magic ~= 100 p^2
accept ~= 0.70 at p=1e-3
accept ~= 0.95 at p=1e-4
depth = 25 before expansion
```

What this case checks:

- Magic state is a linear resource: `m1` is consumed by `inject`.
- Postselection appears as an effect, not an informal note.
- Code conversion / expansion is a typed resource transition:

```text
TState[Surface,3,eps] -> TState[Surface,d,eps']
```

Primitive implementation detail:

```text
prepare T using ZeroLevel =
  prepare physical noisy T candidates
  run Steane-style verification checks
  postselect accept bit b_zl
  output encoded rotated-surface T state at d=3

expand Surface(3 -> d) =
  grow / patch-expand / code-deform the logical magic state
  run r_expand syndrome rounds
  decode expansion syndrome
  update frame if needed

inject T q m =
  logical teleportation / injection measurement
  decode measurement syndrome
  apply S/P frame correction depending on measurement branch
```

Verification logic:

```text
Rule ZeroLevelT_Surface:
  template = MagicDistill / ResourceProvider
  VCs:
    VC-ZL-1  accepted ideal inputs produce the encoded logical |T> state
    VC-ZL-2  verification predicate rejects all first-order dangerous faults
    VC-ZL-3  accepted output has eps_out <= 100 p^2 under declared noise model
    VC-ZL-4  acceptance lower bound alpha_zl(p) is imported or checked
    VC-ZL-5  failed branch touches only factory ancillas, not data q
    VC-ZL-6  output resource kind is exactly TState[Surface,3,eps_zl]

Rule ExpandSurface_3_d:
  template = CodeDistanceTransition
  VCs:
    VC-EX-1  logical operators before and after expansion are identified
    VC-EX-2  expansion schedule preserves the logical magic state up to eps_expand
    VC-EX-3  decoder assumptions and syndrome rounds are recorded
    VC-EX-4  output resource kind matches injection precondition

Rule InjectT_Surface:
  template = LogicalMeasurement / Teleportation
  VCs:
    VC-INJ-1 ideal |T> resource and measurement pattern implement logical T
    VC-INJ-2 all measurement branches are covered by frame correction
    VC-INJ-3 resource-state infidelity contributes at most eps_m
    VC-INJ-4 injection circuit/measurement noise contributes eps_inj
    VC-INJ-5 consumed resource m is removed from Delta
```

Formal verification explanation:

```text
P_zero =
  let m0 = prepare T using ZeroLevel in
  let m1 = expand m0 from Surface(3) to Surface(d) in
  inject T q m1

erase(P_zero) =
  prepare logical |T> resource ;
  inject logical T resource into q
  = T q
```

Because zero-level preparation may reject, its physical semantics is a subdistribution:

```text
[[prepare T using ZeroLevel]]_phys
  : Unit -> SubDist(TState[Surface,3,eps_zl] + Fail)
```

The end-to-end theorem is conditional on acceptance:

```text
ValidCert(ZeroLevelT)
and ValidCert(ExpandSurface_3_d)
and ValidCert(InjectT_Surface)
----------------------------------------------------------
[[lower(P_zero) | accept]]_phys approx_{E_zero.err} T
Pr[accept] >= E_zero.accept
```

Effect analysis:

```text
eps_zl(p)      = 100 p^2
eps_m          = eps_zl(p) + eps_expand(d,p)

err(E_zero)
  <= eps_zl(p) + eps_expand(d,p) + eps_inject(d,p)

accept(E_zero)
  >= alpha_zl(p) * alpha_expand(d,p) * alpha_inject(d,p)
```

Usually `expand` and `inject` are deterministic in the logical sense, so:

```text
alpha_expand = 1
alpha_inject = 1
accept(E_zero) >= alpha_zl(p)
```

For restart semantics, the factory prefix can be repeated until success before data `q` is touched:

```text
P_zero_retry =
  repeat prepare+expand until accept;
  inject T q m

expected_factory_qubit_rounds
  <= (qr_zero_level + qr_expand) / alpha_zl(p)

committed_data_error
  <= eps_m + eps_inject
```

This distinction is important: a failed zero-level attempt increases expected resource cost but does not corrupt `q` if the compiler schedules factory preparation as an independent prefix. The sidecar should therefore record both:

```text
committed_data_effect:
  err <= eps_m + eps_inject

retry_prefix_effect:
  expected_qubit_rounds <= (qr_zero_level + qr_expand) / alpha_zl
  failure_policy = restart_until_success
```

### 12.5 Backend C: constant-time 15-to-1 surface-code distillation

Initial type:

```text
q : Q[Surface,d,State]
raw_i : TState[Surface,d,eps_raw]  for i = 1..15
```

Rule library:

```text
CapDistill(Surface15to1)
CapInject(Surface,T)
CapDecode(IterativeTransversalCNOT)
```

Compiler elaboration:

```text
m = distill Surface15to1(raw_1,...,raw_15)
q1 = inject T q m
return q1
```

Typing:

```text
raw_1,...,raw_15 : TState[Surface,d,eps_raw]
-------------------------------------------------- [T-15to1-CT]
m : TState[Surface,d,35 eps_raw^3 + eps_circ(d,p)]

q : Q[Surface,d,State]
m : TState[Surface,d,eps_m]
-------------------------------------------------- [T-Inject]
q1 : Q[Surface,d,State]
```

Effect profile imported from the constant-time MSD paper:

```text
cycles = 6
qubit_rounds ~= 111 d^2   // excluding physical ancilla/injection cost
err_out <= 35 eps_raw^3 + eps_circ(d,p)
discard ~= O(15 eps_raw)  // low input-error regime
decoder = iterative transversal CNOT decoder
```

What this case checks:

- The same `T` logical gate can choose a high-accuracy factory path.
- Decoder assumptions are explicit.
- The rule can be lowered to Stim for stabilizer proxy / detector-error-model validation, with non-Clifford resource handled as sidecar/resource input.

Primitive implementation detail:

```text
distill Surface15to1(raw_1,...,raw_15) =
  allocate factory patches
  run transversal Clifford / CNOT distillation schedule
  collect syndrome and flag bits
  decode using IterativeTransversalCNOT
  postselect syndrome_accept
  output one encoded TState[Surface,d,eps_out]

inject T q m =
  consume the distilled state exactly once
  perform injection measurement and frame correction
```

Verification logic:

```text
Rule Surface15to1:
  template = MagicDistill
  level    = Certified
  VCs:
    VC-15-1  ideal Clifford distillation circuit maps 15 ideal inputs to one ideal |T>
    VC-15-2  postselection predicate detects all weight-1 and weight-2 input magic errors
    VC-15-3  leading logical error satisfies eps_out <= 35 eps_raw^3 + eps_circ(d,p)
    VC-15-4  acceptance satisfies alpha_15 >= 1 - c_accept eps_raw - eps_acc_circ(d,p)
    VC-15-5  iterative decoder failure is bounded by eps_dec_15
    VC-15-6  all 15 raw magic states are consumed linearly
    VC-15-7  resource profile matches the six-cycle constant-time schedule
```

Formal verification explanation:

```text
P_15 =
  let m = distill Surface15to1(raw_1,...,raw_15) in
  inject T q m

erase(P_15) =
  distill logical |T> resource ;
  inject logical T resource
  = T q
```

The resource context before distillation is:

```text
Delta =
  raw_1 : TState[Surface,d,eps_raw],
  ...
  raw_15 : TState[Surface,d,eps_raw]
```

The resource context after distillation and before injection is:

```text
Delta' =
  m : TState[Surface,d,35 eps_raw^3 + eps_circ(d,p)]
```

After injection:

```text
Delta'' = empty
```

So the type derivation simultaneously proves the magic factory output is present exactly once and no raw input can be reused by another acquisition goal.

Effect analysis with parallel raw-state preparation:

```text
P_raw =
  prepare raw_1 || ... || prepare raw_15

E_raw_parallel:
  err        <= 15 eps_raw_prepare
  accept     >= alpha_raw^15
  cycles      = max_i cycles(raw_i)
  qubits_peak = sum_i qubits(raw_i)
  qubit_rounds = sum_i qubit_rounds(raw_i)

E_15_total =
  E_raw_parallel ;
  E_15_distill ;
  E_inject

err(E_15_total)
  <= 15 eps_raw_prepare
     + 35 eps_raw^3
     + eps_circ(d,p)
     + eps_dec_15
     + eps_inject(d,p)

accept(E_15_total)
  >= alpha_raw^15 * alpha_15

cycles(E_15_total)
  = cycles(raw_parallel) + 6 + cycles(inject)
```

If the 15 raw states are themselves produced by zero-level factories, the case study should show both profiles:

```text
space-rich profile:
  run 15 zero-level providers in parallel
  lower latency, higher qubits_peak

space-limited profile:
  run zero-level providers serially or in batches
  lower qubits_peak, higher expected cycles
```

This directly mirrors POPL-style resource analysis: the same typed program has a family of sound effect interpretations, and planner choice depends on the selected metric rather than on a single hard-coded cost model.

### 12.6 Backend D: logical teleportation implementation

This case is close to injection, but it is useful as a separate case because the primitive boundary is different: the non-Clifford capability is acquired by a logical measurement pattern and branch-dependent frame correction, not by treating `inject` as an opaque one-line rule.

Initial type:

```text
q : Q[c,d,State]
a : AuxState[c,d,T_Teleport,eps_a]
```

Rule library:

```text
CapMeasure(c, BellBasisLogical)
CapDecode(dec, c, d)
CapFrameUpdate(c, TCorrection)
CapTeleport(T, c)
```

Compiler elaboration:

```text
(b1,b2) = measureL BellBasisLogical (q,a)
f       = decode dec (b1,b2,syndrome)
q1      = frame_update q_out (TCorrection(f,b1,b2))
return q1
```

Typing:

```text
q : Q[c,d,State]
a : AuxState[c,d,T_Teleport,eps_a]
-------------------------------------------------- [T-MeasureL]
(b1,b2) : Bit * Bit

(b1,b2), syndrome : Syndrome[c]
-------------------------------------------------- [T-Decode]
f : Frame[c]

q_out : Q[c,d,State]
f : Frame[c]
-------------------------------------------------- [T-FrameUpdate]
q1 : Q[c,d,State]
```

Verification logic:

```text
Rule TeleportT:
  template = LogicalMeasurement / Teleportation
  VCs:
    VC-TEL-1  resource state a denotes the required teleportation state for logical T
    VC-TEL-2  logical Bell measurement implements teleportation up to known correction
    VC-TEL-3  correction function is total over all measurement outcomes
    VC-TEL-4  decoder maps syndrome history to a Pauli frame with failure <= eps_dec
    VC-TEL-5  branch-dependent correction is represented as a frame update, not as a hidden gate
    VC-TEL-6  a is consumed linearly
```

Formal verification explanation:

```text
P_tel =
  measureL BellBasisLogical (q,a);
  decode dec syndrome;
  frame_update q_out corr

erase(P_tel) =
  T q
```

The theorem explicitly quantifies over all classical branches:

```text
For every measurement outcome b and decoder output f:
  corr(b,f) composes with the measured teleportation branch
  to implement logical T up to Pauli frame.

Therefore:
  ValidCert(TeleportT)
  ----------------------------------------------------------
  [[lower(P_tel)]]_phys approx_{eps_a + eps_meas + eps_dec} T
```

Effect analysis:

```text
E_tel =
  E_measure_bell ;
  E_decode ;
  E_frame_update

err(E_tel)
  <= eps_a + eps_meas + eps_dec + eps_frame

cycles(E_tel)
  = cycles(measure_bell) + decoder_latency(dec) + cycles(frame_update)

decoder_latency(E_tel)
  = L_dec

measurements(E_tel)
  = M_bell + M_syndrome
```

This case highlights a key effect distinction:

```text
logical correction:
  cheap Pauli/S frame update in Omega

physical correction:
  optional realized gate in backend trace
```

The sidecar should record which one is used, because frame-only correction can reduce cycles while increasing dependence on later frame-aware lowering.

### 12.7 Backend E: measurement-free coherent code switching

This case targets an architecture where mid-circuit measurement or classical feedforward is slow. The planner chooses a measurement-free switch rather than the measurement-based `SwitchOneWay_7_15`.

Initial type:

```text
q   : Q[Steane3,3,State]
aux : AuxState[SwitchMF_7_15,eps_aux]
```

Rule library:

```text
CapMFSwitch(Steane3 -> Tetra15)
CapTrans(Tetra15,T)
CapMFSwitch(Tetra15 -> Steane3)
```

Compiler elaboration:

```text
q1 = switch_mf SwitchMF_7_15 q aux1
q2 = transv T q1
q3 = switch_mf SwitchMF_15_7 q2 aux2
return q3
```

Primitive expansion:

```text
switch_mf pi q aux =
  coherent_extract syndrome_register q aux
  coherent_feedback correction_unitary syndrome_register q
  reset syndrome_register
  reset / recycle aux when certified clean
```

Verification logic:

```text
Rule SwitchMF_7_15:
  template = MeasurementFree
  VCs:
    VC-MF-1  coherent syndrome extractor is equivalent to measuring the declared stabilizers
    VC-MF-2  feedback unitary implements the same correction relation as corr_7_15
    VC-MF-3  reset/disposal registers are disentangled from logical data before reset
    VC-MF-4  reset error contributes eps_reset and is not hidden inside eps_switch
    VC-MF-5  extra Toffoli/CCZ/control gates are counted in gates and qubit_rounds
    VC-MF-6  output mode is State
```

Formal verification explanation:

```text
erase(switch_mf pi q) = id(q)
erase(transv T q)     = T(q)

P_mf =
  switch_mf 7_15 ;
  transv T ;
  switch_mf 15_7

erase(P_mf) = T
```

The soundness statement has an extra reset/disposal side condition:

```text
ValidCert(SwitchMF_7_15)
and CleanReset(syndrome_registers)
and ValidCert(TransvT_Tetra15)
and ValidCert(SwitchMF_15_7)
----------------------------------------------------------
[[lower(P_mf)]]_phys approx_{E_mf.err} T
```

Effect analysis:

```text
E_mf_switch = {
  err: eps_extract + eps_feedback + eps_reset + eps_aux,
  fail: 0,
  accept: 1,
  measurements: 0,
  resets: R_mf,
  coherent_feedback_gates: G_fb,
  gates: {CNOT: n_cnot, Toffoli: n_toff, CCZ: n_ccz},
  decoder_latency: 0 or L_coherent_control,
  assumptions: {
    reset_fidelity >= r0,
    coherent_feedback_available = true,
    entropy_disposal_model = certified
  }
}
```

Comparison with measurement-based switching:

```text
measurement-based:
  lower coherent gate count
  higher measurement/feedforward latency
  explicit decoder call

measurement-free:
  no mid-circuit measurement latency
  higher coherent-control and reset cost
  stronger reset/disposal certificate requirement
```

This is a good POPL-style case because the difference is not just physical performance. The two implementations have different effects and different proof obligations, but they elaborate the same acquisition goal:

```text
acquire T q under {mid_circuit_measurement_allowed = false}
```

### 12.8 Backend F: parameterized dense non-Clifford region

A single `T` gate demonstrates local typing, but POPL evaluation should also show a parameterized family. Consider a region with `n_T` logical T gates and `n_CCZ` logical CCZ gates over a set of data qubits `R`.

Source:

```text
for i in 1..n_T:
  T q_i

for j in 1..n_CCZ:
  CCZ a_j b_j c_j
```

Candidate plan 1: magic-only.

```text
for each T:
  acquire T by TState factory + inject

for each CCZ:
  acquire CCZ by CCZState factory + inject/teleport
```

Candidate plan 2: region switch.

```text
switch all qubits in R from Surface/Steane to CodeU
run transv/native T and CCZ inside CodeU
switch all qubits in R back
```

Candidate plan 3: hybrid.

```text
switch dense subregion R_dense to CodeU
use magic injection for isolated gates outside R_dense
```

Parameterized typing statement:

```text
For all d >= d_min, n_T >= 0, n_CCZ >= 0:
  Omega;
  Gamma = R : Q[c,d,State]^r;
  Delta = available factories/resources
  |- elaborate(region(n_T,n_CCZ)) : Q[c,d,State]^r ! E(n_T,n_CCZ,d)
```

Verification logic:

```text
VC-PAR-1  loop elaboration preserves resource linearity for every iteration
VC-PAR-2  region switch preconditions hold for every qubit in R_dense
VC-PAR-3  all gates inside CodeU are supported by certified capabilities
VC-PAR-4  switch-back restores the original code/index context
VC-PAR-5  effect expression is symbolic in n_T, n_CCZ, d
VC-PAR-6  optimizer preserves erase(P) for every parameter instance
```

Formal optimization statement:

```text
P_magic(n_T,n_CCZ)
P_switch(n_T,n_CCZ)
P_hybrid(n_T,n_CCZ)

erase(P_magic)  = region(n_T,n_CCZ)
erase(P_switch) = region(n_T,n_CCZ)
erase(P_hybrid) = region(n_T,n_CCZ)
```

The planner is allowed to choose:

```text
argmin_P objective(E_P(n_T,n_CCZ,d))
```

only among plans whose certificates satisfy the requested trust policy.

Effect analysis:

```text
E_magic(n_T,n_CCZ)
  = n_T  * E_T_factory_inject
  + n_CCZ * E_CCZ_factory_inject

E_switch(n_T,n_CCZ)
  = E_switch_in(R)
  ; n_T  * E_transv_T
  ; n_CCZ * E_transv_CCZ
  ; E_switch_out(R)

E_hybrid
  = E_switch(n_T_dense,n_CCZ_dense)
  ; E_magic(n_T_sparse,n_CCZ_sparse)
```

Break-even analysis:

```text
switch better than magic when:
  cost(E_switch_in + E_switch_out)
  <
  n_T_dense  * (cost(E_T_factory_inject)    - cost(E_transv_T))
  +
  n_CCZ_dense * (cost(E_CCZ_factory_inject) - cost(E_transv_CCZ))
```

This is the case study that makes `Acquire[g]` visibly nontrivial. If the paper only compiles one isolated `T`, reviewers may read `Acquire` as syntactic sugar. A parameterized dense-region case shows that acquisition is an optimization problem over typed implementation families.

### 12.9 Negative case studies: rejected or conditional programs

POPL papers often earn trust by showing what the static system rules out. CiPR-FTQC should include small rejected examples.

#### Case N1: unsupported transversal gate

Program:

```text
q : Q[Steane3,3,State]
transv T q
```

Rejection:

```text
No rule CapTrans(Steane3,T)
```

The type checker suggests valid acquisitions:

```text
acquire T q under K
```

with candidates:

```text
CodeSwitchT
MagicInjectT
ZeroLevelThenInjectT
TeleportT
```

#### Case N2: double use of a magic state

Program:

```text
m : TState[Surface,d,eps]
q1 = inject T q m
q2 = inject T r m
```

Rejection:

```text
Linear resource m consumed by first inject
Second inject has no m in Delta
```

Formal explanation:

```text
Delta, m |- inject T q m : Q[Surface,d,State] ! E
--------------------------------------------------
Delta      after the rule conclusion
```

#### Case N3: observable-only output used as state resource

Program:

```text
q_obs : Q[Surface,d,Observable]
m     : TState[Surface,d,eps]
inject T q_obs m
```

Rejection:

```text
T-Inject requires q : Q[c,d,State]
Q[c,d,Observable] is not a subtype of Q[c,d,State]
```

This matters because algorithmic FT may guarantee only final measurement distributions. Treating such an intermediate object as a state-level input to magic injection would be unsound.

#### Case N4: assumed rule under strict trust policy

Program:

```text
acquire T q using HardwareTailoredT
```

Rule:

```text
HardwareTailoredT.certificate_level = Assumed
```

If the policy is:

```text
trust_policy = CheckedOrCertifiedOnly
```

the compiler rejects the plan. If the policy allows assumptions, the compiler emits:

```text
conditional_soundness:
  depends_on = {
    calibration_id,
    leakage_bound,
    drift_window,
    native_rotation_error_model
  }
```

This case explains the assumption boundary, which is often the difference between a PL theorem and an engineering resource-estimation note.

### 12.10 Planner comparison

A planner can choose among:

```text
CodeSwitchT:
  no magic factory
  requires Steane/Tetra code switching
  may require auxiliary logical states and fast measurements

ZeroLevelT:
  low qubit overhead
  output error ~= 100p^2
  probabilistic accept/restart

Surface15to1:
  consumes 15 raw T states
  output error ~= 35 eps^3 + circuit noise
  high resource demand but high accuracy
```

Selection examples:

```text
target = early FTQC, few physical qubits:
  choose ZeroLevelT

target = high T-count algorithm, very low logical error:
  choose ZeroLevelT + Surface15to1

target = neutral atom / ion trap with good transversal gates:
  choose CodeSwitchT

target = measurement-free architecture:
  choose SwitchMF instead of measurement-based switch
```

Hybrid region example for a slightly larger workload:

```text
source:
  H q;
  T q; T q; CCZ a b q; T q;     // dense non-Clifford region
  CliffordBlock;
  T r;                           // isolated T

plan:
  q_region = switch Steane3 -> CodeU
  transv T q_region
  transv T q_region
  transv CCZ a_region b_region q_region
  transv T q_region
  q_back = switch CodeU -> Steane3

  m = distill Surface15to1(raw_1,...,raw_15)
  r1 = inject T r m
```

Here `CodeU` denotes any certified intermediate code/backend context whose rule certificate provides the required transversal or native non-Clifford operations for that region.

Planner comparison for this workload:

```text
Magic-only:
  simple lowering to factory + injection
  high factory demand for dense T/CCZ region

Switch-only:
  avoids many magic resources
  may pay unnecessary switch overhead for isolated T

Hybrid:
  amortizes switch cost over dense non-Clifford region
  uses magic injection for isolated gates
  exposes a clear optimization frontier:
    switch_count vs factory_demand vs decoder_latency vs acceptance_loss
```

The calculus can type-check all three plans against the same logical erasure. The effect algebra then lets the compiler compare them quantitatively, while the certificate sidecar records which rules were checked, certified, or assumed.

### 12.11 Lowering artifacts

For the case study, prototype should emit:

```text
case_study/code_switch_T.json
case_study/code_switch_T.qasm

case_study/zero_level_T.json
case_study/zero_level_T.stim       // stabilizer fragments / syndrome checks
case_study/zero_level_T.qasm       // dynamic measurement/control

case_study/surface_15to1.json
case_study/surface_15to1.stim

case_study/hybrid_region_T_CCZ.json
case_study/hybrid_region_T_CCZ.qasm
case_study/hybrid_region_T_CCZ.stim
```

The JSON sidecar is essential because QASM/Stim alone cannot encode all proof/resource assumptions.

Minimal sidecar schema for every case:

```json
{
  "case_id": "code_switch_T",
  "logical_source": "T q",
  "erased_semantics": "T",
  "initial_context": {
    "Gamma": ["q : Q[Steane3,3,State]"],
    "Delta": ["b1 : Bell[Steane3,Tetra15,eps_b1]"]
  },
  "elaboration": [
    {"op": "switch", "rule": "SwitchOneWay_7_15"},
    {"op": "transv", "rule": "TransvT_Tetra15"},
    {"op": "switch", "rule": "SwitchOneWay_15_7"}
  ],
  "verification_conditions": [
    {"id": "VC-CS-1", "status": "checked"},
    {"id": "VC-CS-2", "status": "checked"},
    {"id": "VC-T-1", "status": "certified"}
  ],
  "effect": {
    "epsilon_L": "eps_7_15 + eps_T + eps_15_7",
    "space": "max(7 + aux_7_15, 15, 15 + aux_15_7)",
    "time": "tau_7_15 + 1 + tau_15_7"
  },
  "metadata": {
    "accept_lower_bound": "alpha_7_15 * alpha_15_7",
    "decoder": "lookup_table_v1",
    "measurement_mode": "mid_circuit_measurement"
  },
  "certificate_levels": {
    "SwitchOneWay_7_15": "Checked",
    "TransvT_Tetra15": "Certified",
    "SwitchOneWay_15_7": "Checked"
  },
  "assumptions": [
    "noise_model=distance3_circuit_level_depolarizing",
    "decoder=lookup_table_v1"
  ],
  "soundness_claim": {
    "mode": "State",
    "statement": "lower(elaboration) implements T within effect.epsilon_L"
  }
}
```

For parameterized cases, the sidecar should keep symbolic expressions rather than only evaluated numbers:

```json
{
  "case_id": "dense_region_T_CCZ",
  "parameters": ["d", "n_T", "n_CCZ", "factory_slots"],
  "effect_symbolic": {
    "magic_only": "n_T * E_T_factory + n_CCZ * E_CCZ_factory",
    "switch_region": "E_switch_in + n_T * E_transv_T + n_CCZ * E_transv_CCZ + E_switch_out",
    "hybrid": "E_switch_dense + E_magic_sparse"
  },
  "optimizer_witness": {
    "chosen_plan": "hybrid",
    "objective": "minimize <epsilon_L, space, time> subject to epsilon_L <= eps_budget",
    "proof": "erase(chosen_plan) = erase(source) and E(chosen_plan) is minimal among enumerated certified candidates"
  }
}
```

The paper can then report case-study evidence in a compact table:

```text
Case                 Primitive path              Static checks              Effect focus
CodeSwitchT          switch; transv; switch       code index, aux linearity  switch latency
ZeroLevelT           prepare; expand; inject      postselection, resource   retry cost
Surface15to1         distill; inject              15 linear inputs, decoder factory volume
TeleportT            measure; decode; frame       branch totality           decoder latency
SwitchMF_T           coherent feedback; reset     reset cleanliness         reset/control cost
DenseRegion          region switch + injection    parameterized typing      break-even frontier
Rejected cases       invalid fragments            type/effect rejection     soundness boundary
```

## 13. What the case study proves

This case study proves effectiveness along four axes.

### 13.1 Expressiveness

One calculus expresses:

- universal-resource acquisition goals；
- hybrid magic/code-switch planning；
- code switching；
- transversal gates；
- zero-level distillation；
- logical-level MSD；
- constant-time distillation；
- decoder assumptions；
- postselection；
- resource/error effects。

### 13.2 Static checking

The type checker rejects:

```text
T : Q[Steane3] -> Q[Steane3]
```

unless implemented via:

```text
switch to Tetra15
or consume TState
```

It also rejects:

```text
inject T q m
```

if:

- `m` is in the wrong code；
- `m` has insufficient fidelity bound；
- `m` has already been consumed；
- `q` only has `Observable` guarantee but injection requires `State`。

It also rejects or marks conditional:

```text
acquire T q using CandidateRule
```

if `CandidateRule` has no accepted certificate. With an `Assumed` certificate level, the compiler may continue only by emitting a conditional sidecar assumption.

### 13.3 Optimization

The planner can minimize:

```text
epsilon_L
space = physical qubits
time = FTQC cycles
```

under user constraints:

```text
epsilon_L <= 1e-10
space <= N
time <= T_max
backend = neutral_atom
measurements_slow = true
```

Acceptance loss、decoder latency、factory demand、switch count 和 certificate level 不作为主 effect 维度；它们进入 metadata，用来解释三元 effect 或作为 planner side constraints。

### 13.4 Correctness

For each compiled plan:

```text
typed derivation + certified rules
    => logical T semantics
    => resource/error bound
    => backend trace well-formedness
```

This is the POPL contribution: not a new T protocol, but a compositional typed framework for choosing, checking, and combining T implementations.

The detailed case studies instantiate the general theorem in several ways:

```text
CodeSwitchT:
  State soundness through code-indexed typestate transitions.

ZeroLevelT:
  conditional soundness under postselection, with retry cost separated
  from committed data error.

Surface15to1:
  resource-provider soundness for a linear 15-input factory,
  including decoder and circuit-noise assumptions.

TeleportT:
  branch-total soundness for every logical measurement outcome and
  frame correction.

SwitchMF_T:
  coherent-control soundness with explicit reset/disposal side condition.

DenseRegion:
  parameterized optimization soundness for all n_T, n_CCZ, and d in scope.

Negative cases:
  type/effect safety by rejection, not just by successful examples.
```

### 13.5 Artifact-level evidence

The case study should produce evidence at three levels:

```text
checker output:
  accepted/rejected typing derivations
  discharged verification conditions
  linear resource usage report

planner output:
  enumerated acquisition candidates
  selected plan and objective value
  Pareto frontier over epsilon_L, space, time
  metadata table for acceptance, decoder/reset assumptions, certificate level

lowering output:
  OpenQASM/Stim/QIR fragments
  JSON sidecar with effects, certificates, and assumptions
```

The important artifact is not just a runnable circuit. It is the pair:

```text
(backend trace, certificate/effect sidecar)
```

because the backend trace alone cannot explain why a rule is legal, what assumptions it depends on, or how its logical error and failure probability compose.

### 13.6 What reviewers should learn from the case study

The intended POPL-level message is:

```text
1. Acquire[g] is a typed planning problem, not syntactic sugar.
2. Code indices prevent illegal use of backend-specific capabilities.
3. Linear resources prevent unsound reuse of magic states and auxiliary states.
4. Effect algebra makes probabilistic failure, decoder latency, reset cost,
   and space-time volume visible to the optimizer.
5. Certificate levels separate checked theorems from conditional engineering assumptions.
6. Parameterized effects let the same rule family scale across distance,
   factory level, and non-Clifford region size.
```

This gives a clearer evaluation story than "we implemented several FTQC primitives": the case study demonstrates a programming-language interface for certified universal-resource acquisition.

## 14. Minimal implementation plan

### 14.1 Phase 1: rule checker

Implement:

- code signature format；
- capability rule format；
- certificate level tracking；
- type/effect checker；
- linear resource checker；
- proof-obligation generator for rule templates；
- simple acquisition planner。

No need for full OpenQASM parser initially.

### 14.2 Phase 2: backend profiles

Encode these rules:

```text
TransvH_Steane
TransvS_Steane
TransvCNOT_Steane
TransvT_Tetra
SwitchOneWay_7_15
SwitchOneWay_15_7
ZeroLevelT_Surface
Surface15to1
InjectT_Surface
AcquireT
RegionSwitchT
```

### 14.3 Phase 3: case study workloads

Start with:

```text
T
T;T;T
CCZ or Toffoli fragment
QFT rotation fragment
small arithmetic T-heavy fragment
```

For the first paper artifact, prioritize these workload/certificate pairs:

```text
T / CodeSwitchT:
  demonstrates code-indexed typestate and transversal capability checking

T / ZeroLevelThenInject:
  demonstrates probabilistic resource provider, retry semantics, and linear consumption

T / Surface15to1ThenInject:
  demonstrates multi-input linear factory and decoder assumptions

T / TeleportT:
  demonstrates branch-total verification for measurement and frame updates

T / SwitchMF_T:
  demonstrates coherent feedback, reset effects, and measurement-free assumptions

DenseRegion(n_T,n_CCZ,d):
  demonstrates parameterized effect expressions and hybrid planning

RejectedFragments:
  demonstrates unsupported capability, double resource use,
  Observable-vs-State misuse, and strict certificate policy
```

### 14.4 Phase 4: lowering

Lower stabilizer fragments to Stim:

- syndrome extraction；
- stabilizer measurement；
- detector/logical observable annotations；
- surface-code factory skeleton。

Lower dynamic circuits to OpenQASM 3:

- measurement；
- classical conditions；
- reset；
- gate/feedforward structure。

Keep resource/proof metadata in JSON.

## 15. How this differs from existing QEC verification

Existing works usually ask:

```text
Given this QEC gadget, is it fault-tolerant?
```

CiPR-FTQC asks:

```text
Given a library of certified FTQC gadgets,
how can a compiler safely compose them,
choose among them,
and preserve logical/resource/error guarantees?
```

This is why the calculus is useful even if Veri-QEC, symbolic execution, Stim, or manual proofs already verify individual gadgets.

They certify local rules. CiPR-FTQC gives the programming language and compiler layer that composes those rules.

The claim is intentionally not:

```text
automatically invent arbitrary new FTQC physics
```

The claim is:

```text
make universal-resource acquisition programmable,
generate/check proof obligations for known rule families,
and safely compose certified acquisition paths inside a compiler.
```

This is where the bottleneck is: today a programmer must manually decide whether a non-Clifford resource should come from a magic factory, code switch, teleportation gadget, or backend-specific operation, and the correctness/resource assumptions of that decision are scattered across papers and tools. CiPR-FTQC turns that decision into a typed rule-selection problem with explicit certificates and sidecar metadata.

## 16. Paper positioning

A possible paper thesis:

> Universal fault-tolerant quantum computation is no longer a single compilation target. It is a typed resource-planning problem over heterogeneous code capabilities, probabilistic magic resources, decoder-mediated effects, and backend-specific fault assumptions. CiPR-FTQC provides a small calculus and certified rule framework that makes these choices programmable, checkable, and optimizable.

Expected contributions:

1. A code-indexed probabilistic resource calculus for FTQC.
2. A universal-resource acquisition abstraction covering magic resources, code switching, teleportation, pieceable FT, and backend-specific operations.
3. A proof-atom hierarchy showing that protocol rules are certified macros, not a flat list of primitives.
4. A certified capability rule interface for importing FTQC protocols.
5. Proof-generating templates for major FTQC rule families.
6. Soundness theorems for logical semantics and resource/effect bounds.
7. A prototype compiler/rule checker that emits an auditable certificate/effect sidecar.
8. Case studies compiling logical non-Clifford operations via code switching, magic-state factories, logical teleportation, measurement-free switching, hybrid plans, and rejected invalid fragments.

## 17. Source papers and POPL references

Most directly used:

- Bravyi and Kitaev, *Universal quantum computation with ideal Clifford gates and noisy ancillas*, 2005.
- Litinski, *Magic State Distillation: Not as Costly as You Think*, 2019.
- Itogawa et al., *Efficient Magic State Distillation by Zero-Level Distillation*, PRX Quantum 2025.
- Wills, Hsieh, Yamasaki, *Constant-overhead magic state distillation*, Nature Physics 2025.
- Sales Rodriguez et al., *Experimental demonstration of logical magic state distillation*, Nature 2025.
- Wan, *Constant-time magic state distillation*, 2024.
- Butt et al., *Fault-Tolerant Code-Switching Protocols for Near-Term Quantum Processors*, PRX Quantum 2024.
- Heussen and Hilder, *Efficient fault-tolerant code switching via one-way transversal CNOT gates*, Quantum 2025.
- Butt et al., *Measurement-free, scalable, and fault-tolerant universal quantum computing*, Science Advances 2025.
- Zhou et al., *Low-Overhead Transversal Fault Tolerance for Universal Quantum Computation*, 2025.

Secondary influence:

- High-fidelity magic-state preparation with biased-noise architecture.
- Encoding a magic state with beyond break-even fidelity.
- Constant-overhead Bell-pair distillation using high-rate codes.
- 3D surface codes and transversal gates.
- Iterative transversal CNOT decoder.

POPL / PL writing and evidence references from local `POPL/pdfs/`:

- Molavi et al., *Generating Compilers for Qubit Mapping and Routing*, POPL 2026.
  - Writing lesson: define one compact abstraction for a heterogeneous backend family, then show multiple case studies and quality comparisons.
  - CiPR-FTQC use: treat acquisition implementations as a backend-independent planning interface over certified rules.
- Colledan and Dal Lago, *Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages*, POPL 2025.
  - Writing lesson: resource analysis should support multiple metric interpretations, not a single hard-coded cost.
  - CiPR-FTQC use: keep the core FTQC effect focused on `logical_error`, `space`, and `time`, with acceptance/decoder/certificate data as metadata.
- Abdulla et al., *Parameterized Verification of Quantum Circuits*, POPL 2026.
  - Writing lesson: show verification over parameterized families, not only fixed circuits.
  - CiPR-FTQC use: include dense-region workloads parameterized by `d`, `n_T`, `n_CCZ`, and factory level.
- Hirata and Heunen, *Qurts: Automatic Quantum Uncomputation by Affine Types with Lifetime*, POPL 2025.
  - Writing lesson: type systems are strongest when they reject subtle physically invalid resource use, not only when they annotate valid examples.
  - CiPR-FTQC use: include negative cases for linear magic reuse, Observable-vs-State misuse, and uncertified rule imports.

## 18. POPL framing risk and mitigation

The main risk is that the work looks like a catalog of FTQC primitives and rules. To make it read as a POPL paper, the novelty must be concentrated in three claims:

```text
1. Acquire[g] is not syntactic sugar.
   It unifies magic resources, code switching, teleportation,
   pieceable FT, and backend-specific operations as one typed
   universal-resource acquisition problem.

2. Rules are not configuration entries.
   They carry certificate levels, proof obligations, effect bounds,
   and a soundness interface.

3. The compiler is not just a resource estimator.
   It rejects illegal FTQC composition and preserves logical correctness,
   resource bounds, and assumption boundaries through lowering.
```

With the expanded case studies, the paper can argue:

```text
typed derivation
+ certified capability rules
+ explicit effect algebra
+ certificate/effect sidecar
------------------------------------------------
compositional universal FTQC compilation
```

This is a programming-language interface and proof architecture, not merely a list of physical protocol wrappers.
