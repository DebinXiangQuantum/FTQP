# Code-Indexed Probabilistic Resource Calculus for Universal FTQC

检索与整理日期：2026-04-27

依据的 Zotero collections：

- `QEC/magic state distillation`
- `QEC/fault-tolerance operation`

本文给出一套可作为论文核心的 calculus 定义、规则组织方式、正确性叙事和一个 case study。目标不是取代物理协议，而是把已有 FTQC/QEC 协议包装成可组合、可检查、可优化的 typed capability rules。

最新设计补充：本文不把 magic-state distillation 和 code switching 看成两个孤立技巧，而把它们统一为 **non-Clifford / universal-resource acquisition** 问题。也就是说，一个逻辑 `T`、`CCZ` 或一般非 Clifford 能力，可以通过 magic resource injection、code switching/gauge fixing、logical teleportation、pieceable FT、hardware-tailored direct rotation、measurement-free coherent feedback 等不同路径获得。CiPR-FTQC 的核心价值是让这些路径作为带证书的 rule 被编译器组合、比较、选择和验证。

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

### 4.1 Effect fields

Effect 是一个 record：

```text
E = {
  err: epsilon,
  fail: phi,
  accept: alpha,
  qubits_peak: Q,
  cycles: T,
  qubit_rounds: QR,
  gates: GateCount,
  measurements: M,
  resets: R,
  decoder_latency: L_dec,
  assumptions: A,
  certs: CertSet
}
```

解释：

- `err`：logical error upper bound。
- `fail`：protocol failure / rejection probability upper bound。
- `accept`：acceptance probability lower bound。
- `qubits_peak`：peak physical qubits。
- `cycles`：logical / code cycles。
- `qubit_rounds`：space-time volume。
- `decoder_latency`：decoder/feedforward latency assumption。
- `assumptions`：noise model、connectivity、decoder assumptions。
- `certs`：rule certificates。

### 4.2 Sequential composition

如果：

```text
P ! E1
Q ! E2
```

则：

```text
P; Q ! E1 ; E2
```

其中：

```text
err(E1 ; E2)       = err(E1) + err(E2)          // union bound
fail(E1 ; E2)      = fail(E1) + fail(E2)        // conservative
accept(E1 ; E2)    = accept(E1) * accept(E2)
cycles(E1 ; E2)    = cycles(E1) + cycles(E2)
qubit_rounds       = qubit_rounds(E1) + qubit_rounds(E2)
qubits_peak        = max(qubits_peak(E1), qubits_peak(E2))
assumptions        = assumptions(E1) join assumptions(E2)
certs              = certs(E1) union certs(E2)
```

可以在实现中支持更精细的 dependence tracking，但论文第一版用保守组合即可。

### 4.3 Parallel composition

如果两个程序作用在 disjoint qubits/resources：

```text
P || Q
```

则：

```text
cycles = max(cycles(P), cycles(Q))
qubit_rounds = qubit_rounds(P) + qubit_rounds(Q)
qubits_peak = qubits_peak(P) + qubits_peak(Q)
err <= err(P) + err(Q)
accept >= accept(P) * accept(Q)
```

这对应 logical MSD experiment 中多个 logical qubits 并行 encoding / transversal gates，也对应 factory farm。

## 5. Syntax

### 5.1 Terms

核心命令：

```text
P ::= skip
    | let x = P in P
    | P ; P
    | P || P
    | acquire g q under K
    | transv g q
    | switch pi q
    | measureL O q
    | decode dec syndrome
    | frame_update q f
    | inject k q m
    | prepare rho using pi
    | distill D(m1,...,mk)
    | cultivate C()
    | postselect b then P else fail
    | reset r
    | lower backend P
```

### 5.2 Atomic operation classes

The calculus is small because every backend protocol is imported as one of these classes:

```text
Transversal gate:
  transv g q

Code transition:
  switch pi q

Magic-resource provider:
  distill D(...)
  cultivate C(...)
  prepare rho using pi

Resource consumption:
  inject k q m

Measurement and classical control:
  measureL O q
  decode dec syndrome
  frame_update q f

Measurement-free control:
  coherent_extract
  coherent_feedback
  reset

Universal-resource acquisition:
  acquire g q under K
```

`acquire g q under K` 是编译期形式，不是物理后端指令。它要求 planner 在约束 `K` 下选择一条已认证 implementation path，例如 `switch+transv+switch`、`distill+inject` 或 `logical teleportation`。Lowering 前必须消去所有 `acquire`。

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

`m` 在 rule conclusion 后从 `Delta` 中消失。

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

这条 rule 的意义不是引入新的物理 primitive，而是把 high-level non-Clifford demand elaborated into a certified plan。Elaboration 后程序中不再出现 `acquire`，只剩下 `switch`、`transv`、`distill`、`inject`、`measureL`、`decode`、`frame_update`、`reset` 等低层 command。

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

```text
ValidCert(R) =>
  lower_R implements postcondition from precondition
  with error/failure/resource bounded by E_R
```

This theorem is usually proved per rule family:

- stabilizer/transversal rules by symplectic tableau；
- code-switching rules by stabilizer/logical operator mapping + fault enumeration；
- magic distillation by protocol theorem / numerical certificate；
- decoder rules by decoder correctness or statistical certificate。

### 9.3 Program logical soundness

If:

```text
Omega; Gamma; Delta |- P : A ! E
```

and all capability certificates in `E.certs` are valid, then:

```text
lower(P) implements erase(P)
with logical error <= E.err
and failure probability <= E.fail
and acceptance probability >= E.accept
```

The exact relation is state-level or observable-level depending on output mode.

### 9.4 Resource soundness

For any physical trace `t` produced by `lower(P)`:

```text
cost(t) <= E.cost
```

where cost includes:

- peak physical qubits；
- qubit-rounds；
- code cycles；
- measurements；
- resets；
- decoder latency assumptions。

### 9.5 Optimization correctness

For an optimizer:

```text
opt(P) = P'
```

prove:

```text
erase(P') = erase(P)
E(P') <= E(P)          // for selected metric, or Pareto improvement
typing(P') preserved
```

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
  err <= epsilon_budget
  qubits_peak <= N
  backend in {surface, color, neutral_atom, ion_trap}
  measurements_slow = true/false
  mid_circuit_measurement_allowed = true/false
  factory_slots <= F

objective:
  minimize weighted_sum(
    logical_error,
    qubit_rounds,
    wall_clock_cycles,
    factory_demand,
    switch_count,
    decoder_latency,
    rejection_probability
  )
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

### 12.1 Goal

Show that the same logical operation:

```text
T q
```

can be compiled through multiple FTQC protocols under one calculus:

1. code-switching implementation；
2. zero-level magic resource implementation；
3. constant-time 15-to-1 factory implementation；
4. hybrid implementation that mixes region-level code switching and local magic injection。

The case study demonstrates:

- code-indexed typing；
- linear magic-resource consumption；
- probabilistic success/failure；
- rule selection；
- resource/effect comparison；
- hybrid acquisition planning；
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

### 12.6 Planner comparison

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

### 12.7 Lowering artifacts

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
err
qubit_rounds
cycles
acceptance loss
decoder latency
factory demand
switch count
certificate level preference
```

under user constraints:

```text
err <= 1e-10
qubits_peak <= N
backend = neutral_atom
measurements_slow = true
```

### 13.4 Correctness

For each compiled plan:

```text
typed derivation + certified rules
    => logical T semantics
    => resource/error bound
    => backend trace well-formedness
```

This is the POPL contribution: not a new T protocol, but a compositional typed framework for choosing, checking, and combining T implementations.

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
3. A certified capability rule interface for importing FTQC protocols.
4. Proof-generating templates for major FTQC rule families.
5. Soundness theorems for logical semantics and resource/effect bounds.
6. A prototype compiler/rule checker.
7. Case studies compiling logical non-Clifford operations via code switching, magic-state factories, and hybrid plans.

## 17. Source papers from the two Zotero collections

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

 对我们这个题目，危险点确实是“看起来只是定义一套原语和规则”。要让它像 POPL，需要把创新点压到三个地方：第一，Acquire[g] 不是语
  法糖，而是把 magic/code-switch/teleportation/backend operation 统一成 typed resource acquisition problem；第二，rule 不是手
  写配置，而是有 certificate level、proof obligations 和 soundness theorem；第三，compiler 不是普通 resource estimator，而是能
  拒绝非法 FTQC composition，并能保留 logical correctness + resource bound + assumption boundary。这样它就不是“列规则”，而是一
  个可证明的编程语言接口。