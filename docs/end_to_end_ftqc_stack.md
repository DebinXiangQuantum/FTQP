# End-to-End FTQC Compiler Stack

整理日期：2026-06-02

本文说明当前仓库新增的端到端容错量子软件编译栈。目标是把编程语言、rule library、protocol certificate、decoder contract、patch geometry 和 Z3/Lean 证明连接成一条可运行验证路径。

## 1. 栈结构

```text
LogicalOp source program
  -> Compiler acquisition planner
  -> FTStep typed acquisition plan
  -> RuleSpec / CodeSpec legality checks
  -> protocol certificates
  -> decoder contracts
  -> patch geometry embedding
  -> Z3 resource/effect obligations
  -> Lean core safety proof
```

## 2. 新增模块

- `cipr/specs.py`
  - `CodeSpec`
  - `RuleSpec`
  - imported theorem metadata
  - Steane7 and Reed-Muller 15-to-1 machine-checkable signatures

- `cipr/protocols.py`
  - Butt 2024 Steane/Tetra code-switch certificate container
  - Reed-Muller 15-to-1 magic distillation checker

- `cipr/decoder.py`
  - Steane distance-3 syndrome-table decoder check
  - SurfaceD5 imported decoder contract

- `cipr/geometry.py`
  - rectangular patch embedding
  - backend capacity and workspace checks

- `experiments/verify_full_stack.py`
  - one command to verify the full stack and write `full_stack_report.json`

- `cipr/formal_toolchain.py`
  - unified formal toolchain runner
  - registry assembly
  - proof-obligation manifest
  - imported-theorem dependency tracking
  - artifact hashing
  - Lean/Z3/protocol/decoder/geometry report integration

## 3. Butt Code-Switch Certificate

The stack now treats Butt et al. 2024 as a full protocol certificate with two layers:

1. Machine-checked GF(2) algebraic gauge-fixing core.
2. Imported theorem for complete flag-circuit single-fault tolerance and Table-I resource counts.

This distinction is deliberate. The current repository does not contain a machine-readable list of every flag circuit and every component fault from the paper. The full-stack certificate therefore records the physical fault-tolerance proof as an imported theorem dependency with source locator, while still checking the algebraic code-switching core locally.

## 4. Real 15-to-1 Magic Distillation

The stack includes a machine-checked Reed-Muller / triorthogonal 15-to-1 certificate:

- one odd logical row and four even check rows;
- all pair overlaps are even;
- all triple overlaps are even;
- every weight-1 and weight-2 input `Z` error is detected;
- accepted weight-3 logical errors have count `35`, giving the leading term `35 p^3`.

The constant-time surface-code implementation profile, six code cycles, and `111 d^2` qubit-cycle cost remain an imported theorem from Wan 2024 because those are architecture-level implementation claims, not just outer-code matrix facts.

## 5. Decoder Correctness

Decoder support is split into:

- Steane3 syndrome-table decoder: machine checked for all single-qubit CSS `X` and `Z` errors, with `Y` decomposed into both syndromes.
- SurfaceD5 decoder contract: imported distance-5/MWPM-style contract with correction radius `t=2` and latency bound recorded in the rule library.

## 6. Patch Geometry

The geometry layer currently synthesizes conservative rectangular embeddings for final live patches and checks:

- all final patches fit in the fixed backend grid;
- rectangles do not overlap;
- embedding area covers reported live physical qubits;
- workspace reservations fit backend capacity.

This is stronger than footprint-only accounting, but it is still not a full nearest-neighbor routing or lattice-surgery boundary checker.

## 7. Run

```bash
uv run python experiments/run_mvp.py
uv run python experiments/run_complex_case_study.py
uv run python experiments/verify_protocols.py
uv run python experiments/verify_mvp.py
uv run python experiments/verify_full_stack.py
cd formal && lake build
```

Expected outputs:

```text
experiments/outputs/full_stack_report.json
experiments/outputs/verification_report.json
experiments/outputs/protocol_certificates.json
experiments/outputs/smt/*.smt2
```

`full_stack_report.json` is the canonical formal-toolchain artifact. It contains:

- `registry`: code, rule, and case-study registry;
- `obligations`: every machine-checked or imported proof obligation with stable ids;
- `sections`: raw reports from code specs, rule specs, protocols, decoders, compiler checker, Z3, geometry, and Lean;
- `artifacts`: SHA-256 hashes and byte sizes for generated sidecars and SMT files;
- `certificate_boundary`: the exact local-proof/imported-theorem boundary.

This replaces the earlier loose collection of independent scripts with a single auditable proof pipeline.

## 8. Current Boundary

The stack is now end-to-end at the software/compiler level. Remaining physical-detail gaps are represented as explicit imported theorem certificates rather than hidden assumptions:

- complete Butt flag-circuit fault enumeration;
- SurfaceD5 MWPM implementation internals;
- exact physical layout/routing for all code-switch circuits;
- circuit-level noise simulation for factory implementations.
