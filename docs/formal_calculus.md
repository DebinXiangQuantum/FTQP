# FTQP Core Calculus and Formal Analysis

整理日期：2026-06-02

本文给出 FTQP / CiPR-FTQC 的论文级形式化核心。目标不是把完整物理噪声模型、decoder 实现和 patch routing 一次性纳入定理证明，而是定义一个足够小、可证明、可实现检查的中间层：

```text
logical program
  -> typed fault-tolerant acquisition program
  -> certificate/effect/layout sidecar
```

本层回答的问题是：

> 如果编译器选择了一组 certified FTQC capability rules，那么生成的 acquisition plan 是否只使用合法 code capability、是否线性消费资源、是否保守组合 logical-error/resource effect，并且是否在 accepted runs 上实现 source logical program？

当前仓库中的 Python 原型负责执行 planning 和生成 sidecar；`formal/FTQP/Core.lean` 则机械化证明一个小核心：capability legality、strict certificate policy、linear resource consumption 和 effect-bound composition。

## 1. 形式化边界

### 1.1 本 calculus 覆盖什么

FTQP core calculus 覆盖以下对象：

- encoded logical data: `q : Q[C, d, mu]`；
- code capability: native/transversal gates, code switch, logical measurement；
- linear probabilistic resources: `TState`, `CCZState`, `BellPair`；
- acquisition plans: switch path, resource production/injection, hybrid region；
- certificate level: `Checked`, `Certified`, `Assumed`；
- fixed backend side conditions: topology, workspace, capacity；
- conservative effect algebra: logical error, failure, acceptance, space, time；
- compiler legality: unsupported direct gates rejected, resources not duplicated, assumptions visible。

### 1.2 本 calculus 暂不覆盖什么

以下内容作为 rule certificate 的外部契约或后续扩展，而不是当前 small core 的 primitive theorem：

- physical circuit-level threshold proof；
- full decoder algorithm correctness；
- exact geometric patch routing；
- parallel factory scheduling optimality；
- arbitrary stabilizer-code distance proof；
- complete extraction from arbitrary FTQC papers。

这一区分很重要。POPL 主张应是：

```text
certified local FTQC rules
  -> safe composition and planning layer
```

而不是：

```text
automatic proof of every physical FTQC protocol from first principles
```

## 2. Static Domains

### 2.1 Codes

Code family:

```text
C ::= SurfaceD5 | Steane3 | Tetra15 | QLDPC12 | ...
```

论文中的一般 code signature 应写为：

```text
CodeSpec C = {
  n, k, d,
  stabilizer_generators,
  gauge_generators,
  logical_operators,
  transversal_actions,
  measurement_capabilities,
  supported_topologies,
  decoder_contract
}
```

当前 MVP 中的实例：

```text
SurfaceD5:
  native = {H, S}
  topology = {grid2d, long_range}

Steane3:
  transversal = {H, S, CNOT}
  topology = {grid2d, long_range}

Tetra15:
  transversal = {CNOT, T}
  topology = {grid2d, long_range}

QLDPC12:
  transversal = {H, S, CNOT, T}
  topology = {long_range}
  role = negative-control profile
```

`QLDPC12` 当前只是 checker negative control，不是物理论文主张。

### 2.2 Gates

Logical gates:

```text
g ::= H | S | CNOT | T | CCZ | Rz(theta) | ...
```

一个 direct gate 只有在 capability context 中有证据时才合法：

```text
Cap(C, g)
```

否则 source gate 必须被 elaborated 成 acquisition plan，例如：

```text
Acquire[T, q]
  => produce r:TState; consume r for T q

Acquire[T, q]
  => switch q SurfaceD5 Tetra15; transv T q; switch q Tetra15 SurfaceD5
```

### 2.3 Correctness Mode

Encoded quantum type:

```text
Q[C, d, mu]
```

其中：

```text
mu ::= State | Observable
```

- `State`: accepted target channel approximates the ideal logical state/channel；
- `Observable`: accepted final measurement distribution is correct, but intermediate state may not be close to a code state。

Typing 必须阻止：

```text
Q[C, d, Observable]
```

被传入一个要求 state-level magic injection 或 state-level code switch 的 rule。

当前 Python `QType` 已有 `mode` 字段，但 planner/checker 还没有充分使用；这是下一步实现必须补齐的点。

### 2.4 Resource Kinds

Linear resources:

```text
R ::= TState[eps] | CCZState[eps] | BellPair[eps] | AuxState[C, eps]
```

Resource context:

```text
Delta ::= empty | Delta, r : R
```

线性规则：

```text
r : R in Delta
-------------------------------
consume r removes r from Delta
```

同一 resource 不能被消费两次，也不能在未生产时消费。这个性质已在 Lean 小核心中机械化。

## 3. Source Language

Source language 表达用户希望执行的 logical program：

```text
e ::= prepare q state
    | gate g qs
    | ec qs decoder
    | measure target O qs
    | if b then e1 else e2
    | e1 ; e2
```

Source language 不要求用户指定每个 `T` 或 `CCZ` 如何实现。它只表达 logical intent。

当前 Python 对应：

```text
LogicalOp.prepare
LogicalOp.apply
LogicalOp.ec
LogicalOp.measure
LogicalOp.branch
LogicalOp.barrier
```

## 4. Target Acquisition Language

Target language 是编译器生成、checker 验证的 FTQC acquisition program。

### 4.1 Primitive Atoms

核心 primitive atoms：

```text
a ::= alloc q C
    | native g q
    | transv g q
    | switch q C1 C2
    | produce r R
    | consume r R for g q
    | measureL target O q
    | decode syndrome
    | frame_update q P
    | postselect predicate
    | reset_clean a
```

这些 atoms 必须足够小，不能允许一个 opaque primitive 隐藏所有证明。

明确禁止的过强 primitive：

```text
apply U
```

如果 calculus 允许 `apply U`，那么任何 FTQC protocol 都可以被塞进 `U` 中，checker 无法验证 capability、resource 和 certificate boundary。

### 4.2 Composite Programs

```text
t ::= a
    | t1 ; t2
    | if b then t1 else t2
    | macro m(args)
```

其中 macro 只是 derived form，必须展开成 atoms 或携带 rule certificate。

常见 derived forms：

```text
SwitchVia[Ctarget, g, q]:
  switch q Csource Ctarget;
  transv/native g q;
  switch q Ctarget Csource

InjectT[q]:
  produce r:TState[eps];
  consume r for T q

HybridRegion[Ctarget, block]:
  switch all involved qubits to Ctarget;
  run every gate in block directly;
  switch all involved qubits back
```

当前 Python 对应：

```text
FTStep(op="apply")
FTStep(op="switch")
FTStep(op="prepare_resource")
FTStep(op="consume_resource_gate")
FTStep(op="acquire_gate")
FTStep(op="acquire_region")
FTStep(op="measureL")
FTStep(op="ec")
```

## 5. Contexts

Quantum context:

```text
Gamma ::= q1 : Q[C1, d1, mu1], ..., qn : Q[Cn, dn, mun]
```

Resource context:

```text
Delta ::= r1 : R1, ..., rk : Rk
```

Capability context:

```text
K ::= {
  codes,
  rule_library,
  backend,
  certificate_policy
}
```

Certificate policy:

```text
pi ::= exploratory | strict
```

- `exploratory`: allow `Assumed` rules but record them；
- `strict`: reject `Assumed` rules。

当前 Lean 小核心证明了一个代表性结论：

```text
strict policy rejects SurfaceD5 -> Tetra15 assumed bridge
```

这与 Python strict checker 的行为一致：现有 case studies 在 ordinary validation 下通过，但 `strict_without_assumptions = False`。

## 6. Typing and Effect Judgment

核心 judgment：

```text
K ; Gamma ; Delta |- t : Gamma' ; Delta' ! E
```

含义：

- 在 capability context `K` 下；
- target program `t` 从 quantum context `Gamma` 和 resource context `Delta` 出发；
- 产生新的 quantum context `Gamma'` 和 resource context `Delta'`；
- 同时产生 conservative effect bound `E`。

### 6.1 Direct Gate

```text
Gamma(q) = Q[C, d, State]
Cap(C, g)
CertAllowed(pi, RuleCert(C, g))
-----------------------------------------
K ; Gamma ; Delta |- direct g q
  : Gamma ; Delta ! E_direct(C, g)
```

如果 `Cap(C, g)` 不成立，则 direct gate 不可类型化。Lean 中对应 theorem：

```text
unsupported_direct_rejected
```

### 6.2 Code Switch

```text
Gamma(q) = Q[C1, d1, mu]
Switch(C1, C2)
ModeOK(mu, Switch(C1, C2))
BackendOK(K.backend, Switch(C1, C2))
CertAllowed(pi, RuleCert(C1, C2))
-------------------------------------------------
K ; Gamma ; Delta |- switch q C1 C2
  : Gamma[q -> Q[C2, d2, mu]] ; Delta ! E_switch
```

在 strict policy 下，`Assumed` switch rule 不可类型化。

### 6.3 Produce Resource

```text
r notin Delta
Factory(R)
CertAllowed(pi, RuleCert(Factory(R)))
------------------------------------------------
K ; Gamma ; Delta |- produce r:R
  : Gamma ; Delta, r:R ! E_factory
```

### 6.4 Consume Resource

```text
r : R in Delta
Injection(R, g, C)
Gamma(q) = Q[C, d, State]
------------------------------------------------
K ; Gamma ; Delta |- consume r for g q
  : Gamma ; Delta - r ! E_consume
```

Lean 中机械化了：

```text
no_double_consume_same_resource
bad_double_consume_second_step_rejected
```

也就是说，一次成功消费后，同一个 resource 在后继 context 中不可再次消费。

### 6.5 Sequencing

```text
K ; Gamma ; Delta  |- t1 : Gamma1 ; Delta1 ! E1
K ; Gamma1 ; Delta1 |- t2 : Gamma2 ; Delta2 ! E2
------------------------------------------------
K ; Gamma ; Delta |- t1 ; t2
  : Gamma2 ; Delta2 ! E1 ; E2
```

### 6.6 Branch

```text
K ; Gamma ; Delta |- t1 : Gamma' ; Delta' ! E1
K ; Gamma ; Delta |- t2 : Gamma' ; Delta' ! E2
------------------------------------------------
K ; Gamma ; Delta |- if b then t1 else t2
  : Gamma' ; Delta' ! branch(E1, E2)
```

Branch 两侧必须返回同样的 quantum/resource context。当前 Python checker 已要求 branch 两侧返回同样 `env` 和 `layout`。

## 7. Effect Algebra

论文主 effect 建议采用五元组：

```text
E = <epsilon, fail, accept, space, time>
```

当前实现 sidecar 还记录更多工程字段：

```text
qubit_rounds, switch_count, factory_count,
measurements, resets, two_qubit_gates,
decoder_latency, certs, assumptions, rules
```

形式化时可把这些视为附加 monoidal counters。

### 7.1 Sequential Composition

Conservative sequential composition：

```text
E1 ; E2 =
  epsilon = E1.epsilon + E2.epsilon
  fail    = min(1, E1.fail + E2.fail)
  accept  = E1.accept * E2.accept
  space   = max(E1.space, E2.space)
  time    = E1.time + E2.time
```

解释：

- error 使用 union-bound 风格上界；
- failure 使用 capped union bound；
- acceptance 使用 accepted-run lower bound；
- space 使用峰值；
- time 当前采用 serial schedule 上界。

Lean 小核心中用自然数抽象了 `epsilon/fail/space/time/factory/switch`，证明：

```text
seq_left_bound
seq_right_bound
```

即 `E1` 和 `E2` 都被 `E1 ; E2` 保守覆盖。

### 7.2 Branch Composition

```text
branch(E1, E2) =
  epsilon = max(E1.epsilon, E2.epsilon)
  fail    = max(E1.fail, E2.fail)
  accept  = min(E1.accept, E2.accept)
  space   = max(E1.space, E2.space)
  time    = max(E1.time, E2.time)
```

当前 Lean 小核心证明：

```text
branch_left_bound
branch_right_bound
```

### 7.3 Effect Preorder

定义 conservative preorder：

```text
E1 <= E2
```

当且仅当 `E2` 的 error/failure/space/time/counter 都不小于 `E1`，并且 acceptance lower bound 不大于或等于相应 conservative requirement。

为了让 Lean 核心简洁，当前 Lean 文件先证明自然数上界字段；acceptance 的乘法 lower bound 仍由 Python/Z3 sidecar 检查。

## 8. Rule Contracts

每条 rule 都应被解释为一个 local soundness contract：

```text
RuleContract R:
  precondition(Gamma, Delta, backend)
  postcondition(Gamma', Delta')
  effect E
  certificate Cert
  semantic_soundness:
    if certificate is valid and precondition holds,
    then accepted physical execution refines ideal logical operation
    within E.epsilon
```

对于不同 rule：

```text
Transversal gate:
  prove or import logical operator action.

Code switch:
  prove source and target are compatible gauge fixings
  and measured syndrome/correction preserves logical state.

Magic injection:
  prove resource state quality plus injection circuit implements g.

Logical measurement:
  prove measured physical observable maps to intended logical observable.

Decoder/frame:
  prove decoder contract and frame update are reflected in sidecar.
```

## 9. Soundness Theorems

### 9.1 Type Preservation

Statement:

```text
If K ; Gamma ; Delta |- t : Gamma' ; Delta' ! E
and t takes one target step to t1,
then there exist Gamma1, Delta1, E1 such that
K ; Gamma1 ; Delta1 |- t1 : Gamma' ; Delta' ! E1
and E1 <= E.
```

在当前 compiler/checker 版本中，这个 theorem 的程序对应物是：

- every emitted child step is checked against rule library；
- direct unsupported gates are rejected；
- branch contexts must match；
- layout events preserve fixed backend。

### 9.2 Resource Linearity

Statement:

```text
If K ; Gamma ; Delta |- t : Gamma' ; Delta' ! E,
then no resource is consumed more than once,
and every consume step consumes a resource present in the current Delta.
```

Lean 小核心已证明同一 resource 连续第二次消费不可类型化。

### 9.3 Strict Certificate Soundness Boundary

Statement:

```text
If K.strict ; Gamma ; Delta |- t : Gamma' ; Delta' ! E,
then t contains no Assumed rule.
```

Lean 小核心机械化了一个代表性 strict rejection；完整版本应对 all rules 做 induction。

### 9.4 Logical Soundness

Statement:

```text
If K ; Gamma ; empty |- t : Gamma' ; empty ! E
and every rule certificate used by t is valid,
then the accepted-run target semantics refines the source logical semantics
within logical error E.epsilon.
```

这里的 `refines` 可以按 modality 区分：

```text
StateSound:
  target channel is epsilon-close to source logical channel.

ObservableSound:
  target final measurement distribution is epsilon-close.
```

### 9.5 Resource Soundness

Statement:

```text
If K ; Gamma ; Delta |- t : Gamma' ; Delta' ! E,
then the sidecar-reported resource counters conservatively bound
the flattened target plan.
```

当前 `cipr/theorem.py` 和 Z3 obligations 已经检查该性质的实现版本：

- all effect fields nonnegative；
- direct gate steps have capability witnesses；
- produced resources are consumed exactly once；
- layout events preserve fixed backend and free-qubit accounting；
- reported total effect bounds flattened steps。

## 10. Lean Mechanization

Lean source:

```text
formal/FTQP/Core.lean
```

它目前机械化以下内容：

- codes, gates, resources, certificate policy；
- strict vs exploratory certificate admission；
- direct gate capability legality；
- switch legality and assumed-rule rejection；
- resource context as `Nat -> Bool`；
- produce/consume state transition；
- no-double-consume theorem；
- effect sequential/branch conservative bounds；
- typed program construction for a T-state injection plan；
- rejection of a bad double-consume plan。

这不是完整 FTQC soundness 证明，但它已经把论文中最容易被质疑的 compiler-safety claims 从 prose 变成了 proof assistant objects。

下一步 Lean 扩展应包括：

- quantum context `Gamma`；
- mode preservation；
- branch context equality；
- induction theorem for no `Assumed` rules under strict policy；
- induction theorem for resource linearity over arbitrary typed programs；
- extracted correspondence between Python `FTStep` and Lean `Prim`。

## 11. Complex Case Study

新增脚本：

```text
experiments/run_complex_case_study.py
```

该 case study 比 MVP kernel 更复杂，包含：

- 7 个 logical qubits；
- initial EC；
- dense CNOT/T phase-gradient region；
- hybrid strategy 可一次性切换 dense region；
- mid-circuit logical measurement；
- branch 中一侧执行 non-Clifford acquisition，另一侧执行 Clifford correction；
- CCZ resource acquisition；
- final measurement。

它用于验证：

- acquisition planner 在更复杂 block 上仍能生成 sidecar；
- branch effect 使用 max/min conservative composition；
- strict checker 会暴露 `Assumed` rule boundary；
- Z3 obligations 仍能验证 effect/resource/layout consistency。

推荐命令：

```bash
uv run python experiments/run_complex_case_study.py
uv run python experiments/verify_mvp.py
```

输出：

```text
experiments/outputs/case_study_complex_magic_only.json
experiments/outputs/case_study_complex_switch_only.json
experiments/outputs/case_study_complex_hybrid.json
experiments/outputs/case_study_complex_best.json
experiments/outputs/complex_case_study_summary.json
```

## 12. Mapping Table

| Formal object | Python implementation | Current status |
|---|---|---|
| `Q[C,d,mu]` | `cipr.ir.QType` | code/distance/mode present; mode rules incomplete |
| `Effect` | `cipr.ir.Effect` | implemented; Lean proves Nat abstraction |
| `Cap(C,g)` | `RuleLibrary.supports_gate` | implemented |
| `Switch(C1,C2)` | `RuleLibrary.switch_rule` | implemented with cert levels |
| `produce r:R` | `FTStep(op="prepare_resource")` | implemented |
| `consume r` | `FTStep(op="consume_resource_gate")` | implemented |
| resource linearity | `Checker.validate`, `theorem.py` | implemented and Z3-checked |
| strict policy | `Checker.validate(... allow_assumed=False)` | implemented |
| proof atoms | `stabilizer.py` partial | gauge core and magic skeleton |
| resource soundness | `verify_mvp.py` | implemented for generated sidecars |
| logical soundness | paper theorem / future Lean | not fully mechanized |

## 13. Immediate Gaps

The next implementation pass should focus on:

1. using `QType.mode` in the checker；
2. replacing ad hoc rule profiles with machine-readable `CodeSpec` / `RuleSpec`；
3. turning checker output into explicit typing derivation trees；
4. completing one real protocol certificate beyond toy skeleton；
5. extending Lean from step-level safety to induction over arbitrary typed programs；
6. adding a strict-certified-only benchmark that can pass without `Assumed` rules。

## 14. End-to-End Stack Extension

后续实现已经把第 13 节中的部分内容接入工程栈：

```text
cipr/specs.py
  CodeSpec / RuleSpec / ImportedTheorem

cipr/protocols.py
  Butt2024 full switch certificate container
  Reed-Muller 15-to-1 magic distillation checker

cipr/decoder.py
  Steane syndrome-table decoder
  SurfaceD5 imported decoder contract

cipr/geometry.py
  rectangular patch embedding checker

experiments/verify_full_stack.py
  full-stack verification report
```

完整栈采用两层证书策略：

1. `machine_checked`: 当前仓库内通过 GF(2)、矩阵枚举、Z3、Lean 或 geometry checker 自动验证；
2. `imported_theorem`: 来自物理论文的完整 protocol/architecture theorem，带 source locator 和 claim 进入 sidecar。

这使端到端软件编译栈可以运行，同时避免把没有机器可读 fault table 的物理证明误标为本地机械证明。

当前已机器检查：

- Steane `CodeSpec` 的 stabilizer commutation 和 logical anti-commutation；
- Reed-Muller / triorthogonal 15-to-1 matrix；
- 15-to-1 detects all weight-1/2 input `Z` errors；
- accepted weight-3 logical-error count equals `35`；
- Butt code-switch algebraic gauge-fixing core；
- Steane distance-3 syndrome-table decoder for single-qubit CSS errors；
- generated acquisition plans' Z3 resource/effect obligations；
- final patch rectangular embedding and workspace-capacity checks；
- Lean core safety theorem fragments。

Lean 目前还覆盖程序级性质，而不只是单步例子：

- `typed_all_certs_allowed`: every typed program has all certificates allowed by the policy；
- `injectTPlan_all_certs_allowed`: the strict T-injection plan contains no disallowed certificate；
- `injectTPlan_linear_resources`: producing then consuming a T state is linear；
- `badDoubleConsumePlan_not_linear_after_single_resource`: consuming the same resource twice is rejected by the linear-resource checker；
- direct CNOT on SurfaceD5 remains untypable in strict mode。

当前 imported theorem：

- Butt 2024 complete flag-circuit single-fault-tolerance enumeration；
- Wan 2024 constant-time surface-code implementation profile；
- SurfaceD5 MWPM-style decoder internals and distance-5 physical contract。

The resulting end-to-end theorem statement becomes:

```text
If
  the source program elaborates to a plan,
  all machine-checkable obligations in full_stack_report.json pass,
  and every imported theorem dependency is accepted,
then
  the generated acquisition plan is legal in the FTQP stack,
  consumes resources linearly,
  respects backend geometry/capacity constraints,
  and reports conservative effect/resource bounds.
```

This is an end-to-end compiler-stack guarantee, parameterized by explicit physical theorem dependencies.

These are the pieces needed to make the POPL submission claim precise and defensible.
