from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .ir import Effect, FTStep, LogicalOp, QType
from .layout import BackendSpec, LayoutState
from .rules import RuleLibrary, RuleProfile


@dataclass
class PlanCandidate:
    name: str
    steps: list[FTStep]
    effect: Effect
    final_env: dict[str, QType]
    final_layout: LayoutState
    kind: str


@dataclass
class CompileResult:
    strategy: str
    source_program: list[LogicalOp]
    backend: BackendSpec
    steps: list[FTStep]
    final_env: dict[str, QType]
    final_layout: LayoutState
    effect: Effect
    diagnostics: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "source_program": [op.to_json() for op in self.source_program],
            "backend": self.backend.to_json(),
            "final_env": {name: qtype.to_json() for name, qtype in self.final_env.items()},
            "final_layout": self.final_layout.to_json(),
            "effect": self.effect.to_json(),
            "diagnostics": self.diagnostics,
            "steps": [step.to_json() for step in self.steps],
        }


class Compiler:
    def __init__(
        self,
        rules: RuleLibrary | None = None,
        base_code: str = "SurfaceD5",
        backend: BackendSpec | str | None = None,
    ) -> None:
        self.rules = rules or RuleLibrary()
        self.base_code = base_code
        self.backend = LayoutState.empty(backend).backend
        self.resource_counter = 0
        self.rng = random.Random(0)

    def compile(
        self,
        program: list[LogicalOp],
        strategy: str = "hybrid",
        seed: int = 0,
        allow_assumed: bool = True,
    ) -> CompileResult:
        self.resource_counter = 0
        self.rng = random.Random(seed)
        env: dict[str, QType] = {}
        bits: set[str] = set()
        layout = LayoutState.empty(self.backend)
        steps, effect, final_env, final_layout = self._compile_ops(
            program,
            env,
            layout,
            bits,
            strategy=strategy,
            allow_assumed=allow_assumed,
        )
        return CompileResult(strategy, program, self.backend, steps, final_env, final_layout, effect)

    def _compile_ops(
        self,
        ops: list[LogicalOp] | tuple[LogicalOp, ...],
        env: dict[str, QType],
        layout: LayoutState,
        bits: set[str],
        strategy: str,
        allow_assumed: bool,
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        out_steps: list[FTStep] = []
        total = Effect()
        i = 0
        while i < len(ops):
            op = ops[i]
            if strategy == "hybrid" and op.kind == "gate":
                j = i
                block: list[LogicalOp] = []
                while j < len(ops) and ops[j].kind == "gate":
                    block.append(ops[j])
                    j += 1
                block_steps, block_effect, env, layout = self._compile_gate_block(
                    block,
                    env,
                    layout,
                    strategy=strategy,
                    allow_assumed=allow_assumed,
                )
                out_steps.extend(block_steps)
                total = total.seq(block_effect)
                i = j
                continue

            step_list, effect, env, layout = self._compile_one(op, env, layout, bits, strategy, allow_assumed)
            out_steps.extend(step_list)
            total = total.seq(effect)
            i += 1
        return out_steps, total, env, layout

    def _compile_one(
        self,
        op: LogicalOp,
        env: dict[str, QType],
        layout: LayoutState,
        bits: set[str],
        strategy: str,
        allow_assumed: bool,
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        if op.kind == "prepare":
            return self._compile_prepare(op, env, layout)
        if op.kind == "ec":
            return self._compile_ec(op, env, layout)
        if op.kind == "measure":
            return self._compile_measure(op, env, layout, bits)
        if op.kind == "if":
            return self._compile_if(op, env, layout, bits, strategy, allow_assumed)
        if op.kind == "barrier":
            step = FTStep(
                op="barrier",
                rule="Barrier",
                qubits=(),
                input_codes={},
                output_codes={},
                effect=Effect(),
                cert_level="Checked",
                details={"label": op.label},
            )
            return [step], Effect(), env, layout
        if op.kind == "gate":
            return self._compile_gate(op, env, layout, strategy, allow_assumed)
        raise ValueError(f"unsupported logical op kind: {op.kind}")

    def _compile_prepare(
        self, op: LogicalOp, env: dict[str, QType], layout: LayoutState
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        q = op.qubits[0]
        if q in env:
            raise ValueError(f"qubit {q} is already prepared")
        code = self.base_code
        layout, layout_event = layout.prepare(q, self.rules.codes[code], self.rules.prepare.name)
        qtype = QType(code=code, distance=self.rules.codes[code].distance)
        new_env = dict(env)
        new_env[q] = qtype
        effect = self.rules.prepare.instantiated_effect()
        step = FTStep(
            op="prepareL",
            rule=self.rules.prepare.name,
            qubits=(q,),
            input_codes={},
            output_codes={q: code},
            effect=effect,
            cert_level=self.rules.prepare.cert_level,
            details={
                "state": op.state,
                "sources": self.rules.prepare.sources_json(),
                "layout_event": layout_event,
            },
        )
        return [step], effect, new_env, layout

    def _compile_ec(
        self, op: LogicalOp, env: dict[str, QType], layout: LayoutState
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        self._require_qubits(op.qubits, env)
        by_code: dict[str, list[str]] = {}
        for q in op.qubits:
            by_code.setdefault(env[q].code, []).append(q)

        steps: list[FTStep] = []
        total = Effect()
        for code, qubits in by_code.items():
            profile = self.rules.ec[code]
            effect = profile.instantiated_effect().scaled_for_qubits(len(qubits))
            step = FTStep(
                op="ec",
                rule=profile.name,
                qubits=tuple(qubits),
                input_codes={q: code for q in qubits},
                output_codes={q: code for q in qubits},
                effect=effect,
                cert_level=profile.cert_level,
                details={"decoder": op.decoder, "sources": profile.sources_json()},
            )
            steps.append(step)
            total = total.seq(effect)
        return steps, total, env, layout

    def _compile_measure(
        self, op: LogicalOp, env: dict[str, QType], layout: LayoutState, bits: set[str]
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        self._require_qubits(op.qubits, env)
        if len({env[q].code for q in op.qubits}) != 1:
            raise ValueError("logical measurement currently requires all qubits in the same code")
        code = env[op.qubits[0]].code
        profile = self.rules.measure[code]
        effect = profile.instantiated_effect().scaled_for_qubits(len(op.qubits))
        if op.target:
            bits.add(op.target)
        step = FTStep(
            op="measureL",
            rule=profile.name,
            qubits=op.qubits,
            input_codes={q: code for q in op.qubits},
            output_codes={q: code for q in op.qubits},
            effect=effect,
            cert_level=profile.cert_level,
            details={"observable": op.observable, "target": op.target, "sources": profile.sources_json()},
        )
        return [step], effect, env, layout

    def _compile_if(
        self,
        op: LogicalOp,
        env: dict[str, QType],
        layout: LayoutState,
        bits: set[str],
        strategy: str,
        allow_assumed: bool,
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        if op.target not in bits:
            raise ValueError(f"branch condition {op.target} is not a known classical bit")

        then_steps, then_effect, then_env, then_layout = self._compile_ops(
            op.then_ops,
            dict(env),
            layout.copy(),
            set(bits),
            strategy=strategy,
            allow_assumed=allow_assumed,
        )
        else_steps, else_effect, else_env, else_layout = self._compile_ops(
            op.else_ops,
            dict(env),
            layout.copy(),
            set(bits),
            strategy=strategy,
            allow_assumed=allow_assumed,
        )
        if then_env != else_env:
            raise ValueError("if branches must return the same quantum context")
        if not then_layout.equivalent(else_layout):
            raise ValueError("if branches must return the same layout context")
        effect = then_effect.branch(else_effect)
        step = FTStep(
            op="if",
            rule="ClassicalControl",
            qubits=tuple(sorted(then_env)),
            input_codes={q: env[q].code for q in env},
            output_codes={q: then_env[q].code for q in then_env},
            effect=effect,
            cert_level="Checked",
            details={"condition": op.target},
            children=then_steps + else_steps,
        )
        return [step], effect, then_env, then_layout

    def _compile_gate_block(
        self,
        block: list[LogicalOp],
        env: dict[str, QType],
        layout: LayoutState,
        strategy: str,
        allow_assumed: bool,
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        acquire_ops = [op for op in block if self._gate_needs_acquisition(op, env)]
        if len(acquire_ops) < 2:
            steps: list[FTStep] = []
            total = Effect()
            for op in block:
                op_steps, op_effect, env, layout = self._compile_gate(op, env, layout, strategy, allow_assumed)
                steps.extend(op_steps)
                total = total.seq(op_effect)
            return steps, total, env, layout

        involved = self._qubits_in_order(block)
        codes = {env[q].code for q in involved}
        if len(codes) != 1:
            raise ValueError("hybrid region planning currently requires a single input code")
        source_code = next(iter(codes))
        target_code = "Tetra15"
        if not self._can_region_switch(source_code, target_code, block, allow_assumed):
            steps: list[FTStep] = []
            total = Effect()
            for op in block:
                op_steps, op_effect, env, layout = self._compile_gate(op, env, layout, strategy, allow_assumed)
                steps.extend(op_steps)
                total = total.seq(op_effect)
            return steps, total, env, layout

        before_env = dict(env)
        children: list[FTStep] = []
        total = Effect()

        switch_in, switch_in_effect, layout = self._make_switch_step(involved, source_code, target_code, layout)
        children.append(switch_in)
        total = total.seq(switch_in_effect)
        for q in involved:
            env[q] = QType(target_code, self.rules.codes[target_code].distance)

        for gate_op in block:
            step, effect = self._make_direct_gate_step(gate_op, env, reason="hybrid_region")
            children.append(step)
            total = total.seq(effect)

        switch_out, switch_out_effect, layout = self._make_switch_step(involved, target_code, source_code, layout)
        children.append(switch_out)
        total = total.seq(switch_out_effect)
        for q in involved:
            env[q] = QType(source_code, self.rules.codes[source_code].distance)

        region_step = FTStep(
            op="acquire_region",
            rule="HybridRegionAcquire_Tetra15",
            qubits=tuple(involved),
            input_codes={q: before_env[q].code for q in involved},
            output_codes={q: env[q].code for q in involved},
            effect=total,
            cert_level="Assumed" if not allow_assumed else "Assumed",
            details={
                "strategy": "hybrid",
                "target_code": target_code,
                "source_gates": [op.gate for op in block],
                "note": "switch once, run the dense gate region, switch back",
            },
            children=children,
        )
        return [region_step], total, env, layout

    def _compile_gate(
        self,
        op: LogicalOp,
        env: dict[str, QType],
        layout: LayoutState,
        strategy: str,
        allow_assumed: bool,
    ) -> tuple[list[FTStep], Effect, dict[str, QType], LayoutState]:
        self._require_qubits(op.qubits, env)
        if len({env[q].code for q in op.qubits}) != 1:
            raise ValueError(f"gate {op.gate} currently requires all operands in the same code")
        code = env[op.qubits[0]].code
        assert op.gate is not None

        if self.rules.supports_gate(code, op.gate):
            step, effect = self._make_direct_gate_step(op, env, reason="direct_capability")
            return [step], effect, env, layout

        candidates = self._gate_candidates(op, env, layout, strategy, allow_assumed)
        candidate = self._choose_candidate(candidates, strategy)
        return [
            FTStep(
                op="acquire_gate",
                rule=candidate.name,
                qubits=op.qubits,
                input_codes={q: env[q].code for q in op.qubits},
                output_codes={q: candidate.final_env[q].code for q in op.qubits},
                effect=candidate.effect,
                cert_level=self._candidate_cert_level(candidate),
                details={
                    "gate": op.gate,
                    "candidate_kind": candidate.kind,
                    "strategy": strategy,
                },
                children=candidate.steps,
            )
        ], candidate.effect, candidate.final_env, candidate.final_layout

    def _gate_candidates(
        self,
        op: LogicalOp,
        env: dict[str, QType],
        layout: LayoutState,
        strategy: str,
        allow_assumed: bool,
    ) -> list[PlanCandidate]:
        assert op.gate is not None
        code = env[op.qubits[0]].code
        candidates: list[PlanCandidate] = []

        for target_code in self.rules.codes_supporting(op.gate):
            if target_code == code:
                continue
            if not self._switch_allowed(code, target_code, allow_assumed):
                continue
            if not self._switch_allowed(target_code, code, allow_assumed):
                continue

            candidate_layout = layout.copy()
            switch_in, e1, candidate_layout = self._make_switch_step(
                list(op.qubits), code, target_code, candidate_layout
            )
            temp_env = dict(env)
            for q in op.qubits:
                temp_env[q] = QType(target_code, self.rules.codes[target_code].distance)
            gate_step, e2 = self._make_direct_gate_step(op, temp_env, reason=f"switch_via_{target_code}")
            switch_out, e3, candidate_layout = self._make_switch_step(
                list(op.qubits), target_code, code, candidate_layout
            )
            final_env = dict(env)
            effect = e1.seq(e2).seq(e3)
            candidates.append(
                PlanCandidate(
                    name=f"SwitchVia{target_code}_{op.gate}",
                    steps=[switch_in, gate_step, switch_out],
                    effect=effect,
                    final_env=final_env,
                    final_layout=candidate_layout,
                    kind="switch",
                )
            )

        resource_profiles: list[RuleProfile] = []
        direct_resource = self.rules.resource_rule(code, op.gate)
        if direct_resource:
            resource_profiles.append(direct_resource)
        high_fidelity = self.rules.resource_rule(code, op.gate, high_fidelity=True)
        if high_fidelity:
            resource_profiles.append(high_fidelity)

        for profile in resource_profiles:
            steps, effect, final_layout = self._make_resource_steps(op, env, layout.copy(), profile)
            candidates.append(
                PlanCandidate(
                    name=profile.name,
                    steps=steps,
                    effect=effect,
                    final_env=dict(env),
                    final_layout=final_layout,
                    kind="resource",
                )
            )

        if not candidates:
            raise ValueError(f"no certified acquisition plan for {op.gate} in code {code}")
        return candidates

    def _choose_candidate(self, candidates: list[PlanCandidate], strategy: str) -> PlanCandidate:
        if strategy == "random":
            return self.rng.choice(candidates)
        if strategy == "switch_only":
            switch_candidates = [c for c in candidates if c.kind == "switch"]
            if switch_candidates:
                return min(switch_candidates, key=self._score)
        if strategy in {"magic_only", "hybrid"}:
            resource_candidates = [c for c in candidates if c.kind == "resource"]
            if resource_candidates:
                return min(resource_candidates, key=self._score)
        return min(candidates, key=self._score)

    def _score(self, candidate: PlanCandidate) -> float:
        e = candidate.effect
        return (
            e.cycles
            + 0.01 * e.qubit_rounds
            + 25.0 * e.switch_count
            + 35.0 * e.factory_count
            + 1.0e6 * e.err
            + 20.0 * e.fail
        )

    def _make_direct_gate_step(
        self, op: LogicalOp, env: dict[str, QType], reason: str
    ) -> tuple[FTStep, Effect]:
        assert op.gate is not None
        code = env[op.qubits[0]].code
        profile = self.rules.gate_rule(code, op.gate)
        effect = profile.instantiated_effect()
        step = FTStep(
            op="apply",
            rule=profile.name,
            qubits=op.qubits,
            input_codes={q: code for q in op.qubits},
            output_codes={q: code for q in op.qubits},
            effect=effect,
            cert_level=profile.cert_level,
            details={"gate": op.gate, "reason": reason, "sources": profile.sources_json()},
        )
        return step, effect

    def _make_switch_step(
        self, qubits: list[str], source_code: str, target_code: str, layout: LayoutState
    ) -> tuple[FTStep, Effect, LayoutState]:
        profile = self.rules.switch_rule(source_code, target_code)
        if profile is None:
            raise ValueError(f"no switch rule {source_code} -> {target_code}")
        layout, layout_event = layout.switch(
            qubits,
            self.rules.codes[source_code],
            self.rules.codes[target_code],
            profile,
        )
        effect = profile.instantiated_effect().scaled_for_qubits(len(qubits), keep_switch_count=True)
        step = FTStep(
            op="switch",
            rule=profile.name,
            qubits=tuple(qubits),
            input_codes={q: source_code for q in qubits},
            output_codes={q: target_code for q in qubits},
            effect=effect,
            cert_level=profile.cert_level,
            details={
                "from": source_code,
                "to": target_code,
                "sources": profile.sources_json(),
                "layout_note": profile.layout_note,
                "layout_event": layout_event,
            },
        )
        return step, effect, layout

    def _make_resource_steps(
        self, op: LogicalOp, env: dict[str, QType], layout: LayoutState, profile: RuleProfile
    ) -> tuple[list[FTStep], Effect, LayoutState]:
        assert op.gate is not None
        code = env[op.qubits[0]].code
        resource_id = self._fresh_resource_id(op.gate)
        full = profile.instantiated_effect()
        layout_event = layout.reserve_workspace(full.qubits_peak, profile.name)
        factory_cycles = max(1, full.cycles - 4)
        factory_qr = max(1, full.qubit_rounds - 500)
        factory_meas = max(0, full.measurements - 1)
        factory_effect = Effect(
            err=full.err * 0.8,
            fail=full.fail,
            accept=full.accept,
            qubits_peak=full.qubits_peak,
            cycles=factory_cycles,
            qubit_rounds=factory_qr,
            factory_count=full.factory_count,
            measurements=factory_meas,
            decoder_latency=full.decoder_latency,
            two_qubit_gates=full.two_qubit_gates,
            three_qubit_gates=full.three_qubit_gates,
            certs=list(full.certs),
            assumptions=list(full.assumptions),
            rules=[f"{profile.name}:produce"],
        )
        consume_effect = Effect(
            err=full.err * 0.2,
            qubits_peak=max(30, 10 * len(op.qubits)),
            cycles=4,
            qubit_rounds=500,
            measurements=1,
            certs=list(full.certs),
            assumptions=list(full.assumptions),
            rules=[f"{profile.name}:consume"],
        )
        factory_step = FTStep(
            op="prepare_resource",
            rule=f"{profile.name}:produce",
            qubits=(),
            input_codes={},
            output_codes={},
            effect=factory_effect,
            cert_level=profile.cert_level,
            details={
                "resource": resource_id,
                "resource_kind": self._resource_kind(op.gate),
                "for_gate": op.gate,
                "produces": resource_id,
                "sources": profile.sources_json(),
                "layout_event": layout_event,
            },
        )
        consume_step = FTStep(
            op="consume_resource_gate",
            rule=f"{profile.name}:consume",
            qubits=op.qubits,
            input_codes={q: code for q in op.qubits},
            output_codes={q: code for q in op.qubits},
            effect=consume_effect,
            cert_level=profile.cert_level,
            details={
                "gate": op.gate,
                "resource": resource_id,
                "consumes": resource_id,
                "sources": profile.sources_json(),
            },
        )
        return [factory_step, consume_step], factory_effect.seq(consume_effect), layout

    def _candidate_cert_level(self, candidate: PlanCandidate) -> str:
        levels = {step.cert_level for step in self._flatten_steps(candidate.steps)}
        if "Assumed" in levels:
            return "Assumed"
        if "Certified" in levels:
            return "Certified"
        return "Checked"

    def _flatten_steps(self, steps: list[FTStep]) -> list[FTStep]:
        out: list[FTStep] = []
        for step in steps:
            out.append(step)
            out.extend(self._flatten_steps(step.children))
        return out

    def _gate_needs_acquisition(self, op: LogicalOp, env: dict[str, QType]) -> bool:
        if op.kind != "gate" or op.gate is None:
            return False
        self._require_qubits(op.qubits, env)
        if len({env[q].code for q in op.qubits}) != 1:
            return True
        code = env[op.qubits[0]].code
        return not self.rules.supports_gate(code, op.gate)

    def _can_region_switch(
        self,
        source_code: str,
        target_code: str,
        block: list[LogicalOp],
        allow_assumed: bool,
    ) -> bool:
        if not self._switch_allowed(source_code, target_code, allow_assumed):
            return False
        if not self._switch_allowed(target_code, source_code, allow_assumed):
            return False
        return all(op.gate is not None and self.rules.supports_gate(target_code, op.gate) for op in block)

    def _switch_allowed(self, source_code: str, target_code: str, allow_assumed: bool) -> bool:
        profile = self.rules.switch_rule(source_code, target_code)
        if profile is None:
            return False
        if not self.rules.code_supported_on_topology(source_code, self.backend.topology):
            return False
        if not self.rules.code_supported_on_topology(target_code, self.backend.topology):
            return False
        if not self.rules.rule_supported_on_topology(profile, self.backend.topology):
            return False
        return allow_assumed or profile.cert_level != "Assumed"

    def _qubits_in_order(self, ops: list[LogicalOp]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for op in ops:
            for q in op.qubits:
                if q not in seen:
                    seen.add(q)
                    out.append(q)
        return out

    def _require_qubits(self, qubits: tuple[str, ...], env: dict[str, QType]) -> None:
        for q in qubits:
            if q not in env:
                raise ValueError(f"qubit {q} is not prepared")

    def _fresh_resource_id(self, gate: str) -> str:
        self.resource_counter += 1
        return f"res_{gate.lower()}_{self.resource_counter}"

    def _resource_kind(self, gate: str) -> str:
        if gate == "T":
            return "TState"
        if gate == "CCZ":
            return "CCZState"
        if gate == "CNOT":
            return "BellPair"
        return f"{gate}Resource"
