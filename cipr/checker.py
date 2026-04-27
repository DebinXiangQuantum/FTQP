from __future__ import annotations

from dataclasses import dataclass, field

from .ir import FTStep
from .planner import CompileResult
from .rules import RuleLibrary


@dataclass
class CheckReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, object]:
        return {"ok": self.ok, "errors": self.errors, "warnings": self.warnings}


class Checker:
    def __init__(self, rules: RuleLibrary | None = None) -> None:
        self.rules = rules or RuleLibrary()

    def validate(self, result: CompileResult, allow_assumed: bool = True) -> CheckReport:
        errors: list[str] = []
        warnings: list[str] = []
        produced: set[str] = set()
        consumed: set[str] = set()

        for step in self._flatten(result.steps):
            if step.cert_level == "Assumed":
                message = f"{step.rule} is Assumed"
                if allow_assumed:
                    warnings.append(message)
                else:
                    errors.append(message)

            if step.op == "apply":
                gate = step.details.get("gate")
                for q, code in step.input_codes.items():
                    if gate and not self.rules.supports_gate(code, gate):
                        errors.append(f"direct apply {gate} on {q}:{code} is not supported")

            if step.op == "switch":
                source = step.details.get("from")
                target = step.details.get("to")
                if source is None or target is None or self.rules.switch_rule(source, target) is None:
                    errors.append(f"unknown switch rule on step {step.rule}")

            if "produces" in step.details:
                resource = step.details["produces"]
                if resource in produced:
                    errors.append(f"resource {resource} produced twice")
                produced.add(resource)

            if "consumes" in step.details:
                resource = step.details["consumes"]
                if resource in consumed:
                    errors.append(f"resource {resource} consumed twice")
                consumed.add(resource)
                if resource not in produced:
                    errors.append(f"resource {resource} consumed before production")

        unused = produced - consumed
        for resource in sorted(unused):
            warnings.append(f"resource {resource} produced but not consumed")

        return CheckReport(ok=not errors, errors=errors, warnings=warnings)

    def _flatten(self, steps: list[FTStep]) -> list[FTStep]:
        out: list[FTStep] = []
        for step in steps:
            out.append(step)
            out.extend(self._flatten(step.children))
        return out
