# FTQP Lean Formalization

This directory contains a Lean 4 core for the FTQP / CiPR-FTQC formal story.

It proves a small but executable subset of the paper claims:

- unsupported direct gates are untypable;
- strict mode rejects `Assumed` bridge rules;
- produced resources are required before consumption;
- a resource cannot be consumed twice in sequence;
- sequential and branch effect composition conservatively bound child effects;
- a T-state production/injection plan is typable in strict mode.

Run from this directory:

```bash
lake build
```

The formalization is intentionally small. Full FTQC logical soundness is represented in
`docs/formal_calculus.md` as a rule-contract theorem and should be added incrementally.
