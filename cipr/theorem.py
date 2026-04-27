from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any


try:
    import z3  # type: ignore
except Exception:  # pragma: no cover - exercised when z3 is unavailable
    z3 = None


@dataclass
class ProofReport:
    name: str
    solver: str
    ok: bool
    checked: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    smt_file: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "solver": self.solver,
            "ok": self.ok,
            "checked": self.checked,
            "failures": self.failures,
            "smt_file": self.smt_file,
        }


def verify_compile_result(name: str, payload: dict[str, Any], smt_dir: Path) -> ProofReport:
    result = payload["compile_result"]
    top_steps = result["steps"]
    steps = _flatten(top_steps)
    effect = result["effect"]
    smt_dir.mkdir(parents=True, exist_ok=True)
    smt_file = smt_dir / f"{name}.smt2"
    smt_file.write_text(_emit_smt2(name, top_steps, effect), encoding="utf-8")

    report = ProofReport(
        name=name,
        solver="z3" if z3 is not None else "smtlib-only",
        ok=True,
        smt_file=str(smt_file),
    )
    _check_nonnegative(report, steps, effect)
    _check_no_unsupported_direct_gate(report, steps)
    _check_resource_linearity(report, steps)
    _check_conservative_effect_bounds(report, top_steps, effect)
    if z3 is not None:
        _check_with_z3(report, top_steps, effect)
    report.ok = not report.failures
    return report


def _check_with_z3(report: ProofReport, steps: list[dict[str, Any]], effect: dict[str, Any]) -> None:
    solver = z3.Solver()
    err_terms = [_real(step["effect"]["err"]) for step in steps]
    cycles_terms = [z3.IntVal(int(step["effect"]["cycles"])) for step in steps]
    factory_terms = [z3.IntVal(int(step["effect"]["factory_count"])) for step in steps]
    switch_terms = [z3.IntVal(int(step["effect"]["switch_count"])) for step in steps]
    twoq_terms = [z3.IntVal(int(step["effect"].get("two_qubit_gates", 0))) for step in steps]
    accept_product = z3.RealVal("1")
    for step in steps:
        accept_product = accept_product * _real(step["effect"]["accept"])

    eps = z3.RealVal("1/1000000000000")
    obligations = {
        "err_bound_is_conservative": _real(effect["err"]) + eps >= z3.Sum(err_terms),
        "accept_lower_bound_is_conservative": _real(effect["accept"]) <= accept_product + eps,
        "cycles_bound_is_conservative": z3.IntVal(int(effect["cycles"])) >= z3.Sum(cycles_terms),
        "factory_count_is_conservative": z3.IntVal(int(effect["factory_count"])) >= z3.Sum(factory_terms),
        "switch_count_is_conservative": z3.IntVal(int(effect["switch_count"])) >= z3.Sum(switch_terms),
        "two_qubit_count_is_conservative": z3.IntVal(int(effect.get("two_qubit_gates", 0))) >= z3.Sum(twoq_terms),
    }
    for label, obligation in obligations.items():
        solver.push()
        solver.add(z3.Not(obligation))
        status = solver.check()
        solver.pop()
        if status == z3.unsat:
            report.checked.append(label)
        else:
            report.failures.append(f"{label}: expected unsat, got {status}")


def _check_nonnegative(report: ProofReport, steps: list[dict[str, Any]], effect: dict[str, Any]) -> None:
    fields = [
        "err",
        "fail",
        "accept",
        "qubits_peak",
        "cycles",
        "qubit_rounds",
        "switch_count",
        "factory_count",
        "measurements",
        "resets",
        "two_qubit_gates",
        "three_qubit_gates",
        "decoder_latency",
    ]
    for item_name, item in [("total", effect)] + [(step["rule"], step["effect"]) for step in steps]:
        for field in fields:
            if item.get(field, 0) < 0:
                report.failures.append(f"{item_name}.{field} is negative")
    if not any(f.endswith("is negative") for f in report.failures):
        report.checked.append("all_effect_fields_nonnegative")


def _check_no_unsupported_direct_gate(report: ProofReport, steps: list[dict[str, Any]]) -> None:
    bad: list[str] = []
    for step in steps:
        if step["op"] != "apply":
            continue
        reason = step.get("details", {}).get("reason")
        if reason in {"direct_capability", "hybrid_region"}:
            rule = step["rule"]
            gate = step.get("details", {}).get("gate")
            if gate and f"Transv{gate}" not in rule and f"Native{gate}" not in rule:
                bad.append(f"{rule} does not witness direct/hybrid {gate}")
    if bad:
        report.failures.extend(bad)
    else:
        report.checked.append("direct_gate_steps_have_capability_witnesses")


def _check_resource_linearity(report: ProofReport, steps: list[dict[str, Any]]) -> None:
    produced: dict[str, int] = {}
    consumed: dict[str, int] = {}
    for step in steps:
        details = step.get("details", {})
        if "produces" in details:
            produced[details["produces"]] = produced.get(details["produces"], 0) + 1
        if "consumes" in details:
            consumed[details["consumes"]] = consumed.get(details["consumes"], 0) + 1
    for resource, count in produced.items():
        if count != 1:
            report.failures.append(f"{resource} produced {count} times")
    for resource, count in consumed.items():
        if count != 1:
            report.failures.append(f"{resource} consumed {count} times")
        if resource not in produced:
            report.failures.append(f"{resource} consumed without production")
    if not any("produced" in f or "consumed" in f for f in report.failures):
        report.checked.append("linear_resources_produced_and_consumed_once")


def _check_conservative_effect_bounds(
    report: ProofReport, steps: list[dict[str, Any]], effect: dict[str, Any]
) -> None:
    failures_before = len(report.failures)
    additive = [
        "err",
        "cycles",
        "qubit_rounds",
        "switch_count",
        "factory_count",
        "measurements",
        "resets",
        "two_qubit_gates",
        "three_qubit_gates",
        "decoder_latency",
    ]
    for field in additive:
        total = _fraction(effect.get(field, 0))
        step_sum = sum((_fraction(step["effect"].get(field, 0)) for step in steps), Fraction(0))
        tolerance = Fraction(1, 1_000_000_000_000)
        if total + tolerance < step_sum:
            report.failures.append(f"{field} total {total} is below step sum {step_sum}")
    peak = max((step["effect"].get("qubits_peak", 0) for step in steps), default=0)
    if effect.get("qubits_peak", 0) < peak:
        report.failures.append("qubits_peak is below max child peak")
    accept_product = Fraction(1)
    for step in steps:
        accept_product *= _fraction(step["effect"].get("accept", 1))
    if _fraction(effect.get("accept", 1)) > accept_product + Fraction(1, 1_000_000_000_000):
        report.failures.append("accept lower bound is above product of child accepts")
    if len(report.failures) == failures_before:
        report.checked.append("reported_effect_is_conservative_over_flattened_steps")


def _emit_smt2(name: str, steps: list[dict[str, Any]], effect: dict[str, Any]) -> str:
    lines = [
        f"; CiPR-FTQC proof obligations for {name}",
        "; This file asserts the negation of conservative effect bounds.",
        "; A theorem prover/SMT solver should answer unsat.",
        "(set-logic ALL)",
    ]
    for field, sort in [
        ("err", "Real"),
        ("accept", "Real"),
        ("cycles", "Int"),
        ("factory_count", "Int"),
        ("switch_count", "Int"),
        ("two_qubit_gates", "Int"),
    ]:
        total = _smt_value(effect.get(field, 0), sort)
        if field == "accept":
            terms = " ".join(_smt_value(step["effect"].get(field, 1), sort) for step in steps)
        else:
            terms = " ".join(_smt_value(step["effect"].get(field, 0), sort) for step in steps)
        if not terms:
            terms = "1" if field == "accept" else "0"
        operator = "*" if field == "accept" else "+"
        relation = "<=" if field == "accept" else ">="
        lines.extend(
            [
                f"(define-fun total_{field} () {sort} {total})",
                f"(define-fun sum_{field} () {sort} ({operator} {terms}))",
                f"(assert (not ({relation} total_{field} sum_{field})))",
                "(check-sat)",
                "(reset-assertions)",
            ]
        )
    return "\n".join(lines) + "\n"


def _flatten(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        children = step.get("children", [])
        if children:
            out.extend(_flatten(children))
        else:
            out.append(step)
    return out


def _fraction(value: int | float) -> Fraction:
    return Fraction(str(value))


def _real(value: int | float):
    return z3.RealVal(str(value))


def _smt_value(value: int | float, sort: str) -> str:
    if sort == "Int":
        return str(int(value))
    return str(Fraction(str(value)))
