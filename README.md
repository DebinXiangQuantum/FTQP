# CiPR-FTQC MVP

This repository contains a small prototype for **Code-indexed Probabilistic Resource Calculus for FTQC**.

The prototype is not a physical FTQC simulator. It is a compiler/checker artifact for testing the paper idea:

```text
logical QEC program
  -> typed FTQC elaboration
  -> acquisition-plan selection
  -> effect/resource/certificate sidecar
  -> checker + SMT proof obligations
```

## What It Demonstrates

The current MVP checks that:

- ordinary logical gates such as `H`, `CNOT`, `T`, `CCZ`, logical measurement, QEC rounds, and classical control can be represented;
- a gate cannot be directly applied unless the current code has a matching capability rule;
- if the current code does not support a gate, the compiler must elaborate it through an acquisition path such as a resource-state injection or code switching;
- magic/resource states are linear: one produced resource cannot be consumed twice;
- each compiled plan carries concrete effect numbers such as `switch_count`, `factory_count`, `cycles`, `qubit_rounds`, and `two_qubit_gates`;
- every rule records whether it is `Checked`, `Certified`, or `Assumed`.

## Layout

```text
cipr/
  ir.py          # Logical IR, FT steps, quantum types, effects
  rules.py       # Paper-annotated rule library
  planner.py     # Logical-to-FT elaboration and acquisition planner
  checker.py     # Capability, certificate, and resource-linearity checker
  theorem.py     # Z3/SMT proof-obligation generation and checking

experiments/
  run_mvp.py     # QEC-flavored case study
  verify_mvp.py  # Z3 verifier for generated plans
  outputs/       # JSON sidecars and SMT-LIB files
```

## Paper-Annotated Profiles

The rule library in `cipr/rules.py` stores source metadata with Zotero keys, citation strings, page/figure/table locators, and notes.

Main paper-backed entries:

- `Steane3`: [[7,1,3]] Steane / 2D triangular color code with transversal `H`, `S`, `CNOT`.
  Source: Butt et al., PRX Quantum 5, 020345 (2024), pp. 020345-2--020345-4, Fig. 1--3.

- `Tetra15`: [[15,1,3]] tetrahedral / 3D color code with transversal `T` and `CNOT`.
  Source: Butt et al., PRX Quantum 5, 020345 (2024), Fig. 1--3; Heussen and Hilder, Quantum 9, 1846 (2025), pp. 1--4.

- `Switch_Steane3_to_Tetra15` and `Switch_Tetra15_to_Steane3`.
  Source: Butt et al., PRX Quantum 5, 020345 (2024), Table I.
  The prototype uses the table values `17` qubits and `72` / `18` CNOT gates as concrete resource counts.

- `ZeroLevelTThenInject_SurfaceD5`.
  Source: Itogawa et al., PRX Quantum 6, 020356 (2025), pp. 020356-1--020356-2 and pp. 020356-7--020356-10.
  The prototype instantiates the reported profile at `p=1e-3`: `p_L ~= 100 p^2 = 1e-4`, acceptance about `70%`, depth `25`.

- `Surface15to1TThenInject_SurfaceD5`.
  Source: Wan, arXiv:2410.17992 (2024), pp. 1--2 and p. 7.
  The prototype uses `35 p^3`, `6` code cycles, and `111 d^2` qubit-cycles; at `d=5`, this is `2775` qubit-cycles.

Some entries are deliberately marked `Assumed`, for example prototype bridges between `SurfaceD5` and `Tetra15`, and the placeholder `CCZFactoryThenInject_SurfaceD5`. These are compiler-integration placeholders, not physics claims.
现在验证的是编译器层面的结构正确性、资源线性、能力规则、效应上界/accept 下界，不是完整物理 FTQC correctness。
  SurfaceD5 -> Tetra15 bridge、Bell CNOT、CCZ factory 这类目前仍明确标成 Assumed
## Run the Case Study

```bash
python3 experiments/run_mvp.py
```

This writes detailed sidecars to `experiments/outputs/`.

Typical output:

```text
strategy       valid strict err         accept     cycles qr      switch factory 2q      assume
magic_only     True  False  ...
switch_only    True  False  ...
hybrid         True  False  ...
```

Key files:

```text
experiments/outputs/case_study_summary.json
experiments/outputs/case_study_magic_only.json
experiments/outputs/case_study_switch_only.json
experiments/outputs/case_study_hybrid.json
experiments/outputs/negative_tests.json
```

The negative tests include:

- direct `CNOT` on `SurfaceD5`, which is rejected because that code profile does not expose direct/native `CNOT`;
- duplicate consumption of the same resource, which is rejected by the linear resource checker.

## Run Z3 Verification

Z3 is installed outside the repository in `/tmp/ftqp_z3` for this workspace. Run:

```bash
PYTHONPATH=/tmp/ftqp_z3 python3 experiments/verify_mvp.py
```

The verifier checks:

- effect fields are nonnegative;
- direct gate steps have capability witnesses such as `NativeH_*` or `TransvT_*`;
- produced resources are consumed exactly once;
- reported total `err`, `accept`, `cycles`, `switch_count`, `factory_count`, and `two_qubit_gates` conservatively bound the composed plan;
- the same obligations are emitted as SMT-LIB files.

Outputs:

```text
experiments/outputs/verification_report.json
experiments/outputs/smt/*.smt2
```

The SMT-LIB files assert the negation of each bound. A solver answer of `unsat` means the corresponding conservative-bound theorem holds.

## Current Limitations

This MVP verifies the compiler-level structure, not full physical FTQC correctness.

What is checked now:

- capability discipline;
- rule certificate levels;
- linear resource usage;
- effect/resource accounting;
- plan-level proof obligations with Z3.

What is still future work:

- GF(2) stabilizer verification for code signatures and logical operator maps;
- certified extraction of code-switching verification conditions from stabilizer descriptions;
- mechanized preservation/progress/soundness theorem in Lean/Coq/Isabelle;
- replacing `Assumed` prototype bridge rules with literature-backed or mechanically verified rules.
