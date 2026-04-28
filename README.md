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
- the hardware model is fixed at compile time as a backend context, currently `Grid2D_SurfaceLike`;
- code-switch and factory rules carry topology/workspace constraints checked against the fixed backend and current layout state;
- magic/resource states are linear: one produced resource cannot be consumed twice;
- each compiled plan carries concrete effect numbers such as `switch_count`, `factory_count`, `cycles`, `qubit_rounds`, and `two_qubit_gates`;
- every rule records whether it is `Checked`, `Certified`, or `Assumed`.

## Layout

```text
cipr/
  ir.py          # Logical IR, FT steps, quantum types, effects
  layout.py      # Fixed backend model and mutable layout/footprint state
  rules.py       # Paper-annotated rule library
  planner.py     # Logical-to-FT elaboration and acquisition planner
  checker.py     # Capability, certificate, layout, and resource-linearity checker
  stabilizer.py  # GF(2)/Pauli symbolic protocol certificates
  theorem.py     # Z3/SMT proof-obligation generation and checking

experiments/
  run_mvp.py     # QEC-flavored case study
  verify_mvp.py  # Z3 verifier for generated plans
  verify_protocols.py # Gauge-switch and distillation certificate checks
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

The prototype also includes a negative-control `QLDPC12` profile. It is marked as requiring `long_range` topology, so a `SurfaceD5 -> QLDPC12` switch is rejected on the default `Grid2D_SurfaceLike` backend.

## Protocol Certificates

The implementation separates compiler-level rule use from protocol-level algebraic checks.

Run:

```bash
uv run python experiments/verify_protocols.py
```

This writes:

```text
experiments/outputs/protocol_certificates.json
```

The current certificate checker uses binary Pauli vectors over GF(2). It verifies:

- common logical `X/Z` operators anticommute;
- target stabilizers commute and preserve the common logicals;
- gauge corrections preserve the logical state;
- gauge corrections span the measured target-stabilizer syndrome space.

The Steane/tetrahedral certificate is based on Butt et al. 2024, Sec. IV, Eq. (14)--(16): the two stabilizer codes are treated as two gauge fixings of a common subsystem code. This is an ideal algebraic code-switching check. It does not yet enumerate all circuit-level single faults from the flag-qubit implementation in Sec. V.

The same module also contains a small magic-distillation skeleton checker: accepted low-weight Pauli input errors must not implement the declared output logical error. Real 15-to-1 or zero-level distillation certificates can be added by importing the exact check matrix/circuit from the target paper.

## Backend And Layout

The program language does not carry a hardware model in every quantum type. Logical qubits remain code-indexed:

```text
q : Q[SurfaceD5]
```

The hardware is a fixed compilation context:

```text
compile(program, backend = Grid2D_SurfaceLike)
```

The compiler maintains a `LayoutState` internally. Each prepare/switch/factory step emits a `layout_event` sidecar with:

- fixed backend and topology;
- free physical qubits before and after the step;
- code footprint changes;
- temporary workspace reservation;
- released qubits after shrinking switches, for example `Tetra15 -> Steane3`.

This keeps the core calculus small while still preventing backend-incompatible transitions. For example, the checker rejects `Switch_SurfaceD5_to_QLDPC12` on `Grid2D_SurfaceLike` because both the target code and switch rule require `long_range` topology.

## Run the Case Study

```bash
uv run python experiments/run_mvp.py
uv run python experiments/verify_protocols.py
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
- `SurfaceD5 -> QLDPC12` on `Grid2D_SurfaceLike`, which is rejected because the qLDPC-style profile requires long-range connectivity.

## Run Z3 Verification

The project declares `z3-solver` in `pyproject.toml`. Run:

```bash
uv run python experiments/verify_mvp.py
```

The verifier checks:

- effect fields are nonnegative;
- direct gate steps have capability witnesses such as `NativeH_*` or `TransvT_*`;
- produced resources are consumed exactly once;
- layout events preserve the fixed backend and maintain consistent free-qubit accounting;
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
- fixed-backend topology compatibility for code/switch rules;
- layout-event accounting for prepare, switch, and temporary factory workspace;
- effect/resource accounting;
- plan-level proof obligations with Z3.

What is still future work:

- GF(2) stabilizer verification for code signatures and logical operator maps;
- certified extraction of code-switching verification conditions from stabilizer descriptions;
- importing complete subsystem generators, exact appendix face labels, and flag-circuit fault sets for Butt et al. 2024;
- importing exact stabilizer checks/circuits for real magic distillation protocols instead of the current toy skeleton;
- real geometric embedding and routing, beyond the current footprint/workspace abstraction;
- mechanized preservation/progress/soundness theorem in Lean/Coq/Isabelle;
- replacing `Assumed` prototype bridge rules with literature-backed or mechanically verified rules.
