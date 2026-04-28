from __future__ import annotations

from dataclasses import dataclass, field

from .ir import FTStep
from .layout import BackendSpec, LayoutState
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
    def __init__(self, rules: RuleLibrary | None = None, backend: BackendSpec | str | None = None) -> None:
        self.rules = rules or RuleLibrary()
        self.backend = LayoutState.empty(backend).backend

    def validate(self, result: CompileResult, allow_assumed: bool = True) -> CheckReport:
        previous_backend = self.backend
        self.backend = result.backend
        errors: list[str] = []
        warnings: list[str] = []
        produced: set[str] = set()
        consumed: set[str] = set()

        try:
            for step in self._flatten(result.steps):
                self._check_codes_on_backend(step, errors)
                self._check_layout_event(step, errors)

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
                    profile = None if source is None or target is None else self.rules.switch_rule(source, target)
                    if profile is None:
                        errors.append(f"unknown switch rule on step {step.rule}")
                    elif not self.rules.rule_supported_on_topology(profile, self.backend.topology):
                        errors.append(
                            f"{step.rule} is not supported on backend {self.backend.name} "
                            f"({self.backend.topology})"
                        )

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
        finally:
            self.backend = previous_backend

        return CheckReport(ok=not errors, errors=errors, warnings=warnings)

    def _check_codes_on_backend(self, step: FTStep, errors: list[str]) -> None:
        for code in set(step.input_codes.values()) | set(step.output_codes.values()):
            if code not in self.rules.codes:
                errors.append(f"unknown code {code} on step {step.rule}")
                continue
            if not self.rules.code_supported_on_topology(code, self.backend.topology):
                errors.append(
                    f"code {code} on step {step.rule} is not embeddable on backend "
                    f"{self.backend.name} ({self.backend.topology})"
                )

    def _check_layout_event(self, step: FTStep, errors: list[str]) -> None:
        event = step.details.get("layout_event")
        if event is None:
            return
        if event.get("backend") != self.backend.name:
            errors.append(
                f"layout event for {step.rule} targets backend {event.get('backend')}, "
                f"expected {self.backend.name}"
            )
        if event.get("topology") != self.backend.topology:
            errors.append(
                f"layout event for {step.rule} targets topology {event.get('topology')}, "
                f"expected {self.backend.topology}"
            )
        free_before = int(event.get("free_before", 0))
        free_after = int(event.get("free_after", 0))
        if free_before < 0 or free_after < 0:
            errors.append(f"layout event for {step.rule} has negative free qubits")
        if free_before > self.backend.capacity_qubits or free_after > self.backend.capacity_qubits:
            errors.append(f"layout event for {step.rule} exceeds backend capacity")
        if event.get("kind") == "prepare":
            allocated = int(event.get("allocated", 0))
            if free_after != free_before - allocated:
                errors.append(f"prepare layout event for {step.rule} has inconsistent free count")
        if event.get("kind") == "switch":
            old = int(event.get("old_footprint", 0))
            new = int(event.get("new_footprint", 0))
            if free_after != free_before + old - new:
                errors.append(f"switch layout event for {step.rule} has inconsistent free count")
            workspace = int(event.get("workspace_reserved", 0))
            if workspace > free_before:
                errors.append(f"switch layout event for {step.rule} reserves unavailable workspace")

    def _flatten(self, steps: list[FTStep]) -> list[FTStep]:
        out: list[FTStep] = []
        for step in steps:
            out.append(step)
            out.extend(self._flatten(step.children))
        return out
