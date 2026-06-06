# FTQP POPL Draft Writing Brief

This draft should read as a PL paper about a fault-tolerant quantum programming interface, not as a protocol paper and not as a feature list.

Running example:

- A logical program starts in `SurfaceD5`.
- The program asks for `H`, `CNOT`, `T`, `CCZ`, QEC rounds, measurement, and branches.
- `H` is direct in the surface profile, but `CNOT`, `T`, and `CCZ` require acquisition.
- `T` can be acquired by producing and consuming a `TState`, or by switching to a code with transversal `T`.
- Dense regions motivate a hybrid plan: switch once, execute several gates, switch back.
- The checker must retain evidence for capability, resource linearity, backend layout, and certificate level.

Formula policy:

- Keep only formulas that advance the story.
- Explain `Q[C,d,mu]` as the state carried by the running example.
- Explain `K; Gamma; Delta |- t : Gamma'; Delta' ! E` as the checker's audit contract.
- Explain `produce`/`consume` as the reason a magic state cannot be reused.
- Explain effect composition with concrete case-study quantities.
- Explain certificate policy as the distinction between exploratory compilation and strict theorem mode.

Code policy:

- Do not paste long code listings.
- Mention `LogicalOp`, `QType`, `Effect`, and `FTStep` as the representation backbone.
- Mention planner candidate construction for resource plans, switch plans, and hybrid regions.
- Mention checker flattening, capability checks, layout checks, and produced/consumed resource sets.

Proof boundary:

- Local: Python checker invariants, GF(2) protocol checks, decoder-table checks, geometry checks, Z3 obligations, and Lean core theorems.
- Imported: complete flag-circuit single-fault tolerance, surface decoder internals, architecture-level factory profiles.
- Assumed: prototype bridge rules and placeholder resource rules. These are accepted only in exploratory mode and rejected in strict mode.

Chapter responsibilities:

- Introduction: broad motivation, exact PL problem, contribution arc.
- Overview: explain the running example and pipeline.
- Core Language: introduce only constructs needed by the example.
- Typing/Metatheory: explain the judgment, key rules, and current theorem boundary.
- Implementation: show how the ideas appear in the codebase.
- Case Study: walk through the actual SurfaceD5 workload and planner choices.
- Evaluation: summarize evidence, negative tests, and full-stack report.
- Related Work: compare mechanisms and proof boundaries.
- Limitations: honest POPL reviewer-facing risks.
- Conclusion: concise takeaway.
