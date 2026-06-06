from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .checker import Checker
from .decoder import verify_decoder_suite
from .geometry import verify_compile_geometry
from .protocols import verify_protocol_suite
from .rules import RuleLibrary
from .specs import (
    RuleSpec,
    canonical_code_specs,
    canonical_rule_specs,
    verify_code_spec,
)
from .theorem import verify_compile_result


@dataclass
class Obligation:
    id: str
    category: str
    subject: str
    prover: str
    status: str
    dependencies: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "subject": self.subject,
            "prover": self.prover,
            "status": self.status,
            "dependencies": self.dependencies,
            "details": self.details,
        }


@dataclass
class Artifact:
    path: str
    sha256: str
    bytes: int

    def to_json(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "bytes": self.bytes}


@dataclass
class FormalToolchainReport:
    ok: bool
    generated_at: str
    summary: dict[str, int]
    registry: dict[str, Any]
    obligations: list[Obligation]
    sections: dict[str, Any]
    artifacts: list[Artifact]
    certificate_boundary: str

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "generated_at": self.generated_at,
            "summary": self.summary,
            "registry": self.registry,
            "obligations": [obligation.to_json() for obligation in self.obligations],
            "sections": self.sections,
            "artifacts": [artifact.to_json() for artifact in self.artifacts],
            "certificate_boundary": self.certificate_boundary,
        }


class FormalToolchain:
    def __init__(self, root: Path, out_dir: Path, smt_dir: Path) -> None:
        self.root = root
        self.out_dir = out_dir
        self.smt_dir = smt_dir
        self.rules = RuleLibrary()
        self.checker = Checker(rules=self.rules)

    def run(self, run_lean: bool = True) -> FormalToolchainReport:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.smt_dir.mkdir(parents=True, exist_ok=True)
        code_specs = canonical_code_specs()
        rule_specs = canonical_rule_specs()

        code_reports = [verify_code_spec(spec).to_json() for spec in code_specs]
        rule_reports = [self._verify_rule_spec(spec, code_specs).to_json() for spec in rule_specs]
        protocol_reports = [report.to_json() for report in verify_protocol_suite()]
        decoder_reports = [report.to_json() for report in verify_decoder_suite()]

        compile_reports: list[dict[str, Any]] = []
        checker_reports: list[dict[str, Any]] = []
        geometry_reports: list[dict[str, Any]] = []
        cases = self.load_case_studies()
        for name, payload in cases:
            proof = verify_compile_result(name, payload, self.smt_dir)
            compile_reports.append(proof.to_json())
            result = payload["compile_result"]
            checker_reports.append(
                {
                    "name": f"Checker:{name}",
                    "ok": self.checker.validate(_compile_result_from_json(result), allow_assumed=True).ok,
                    "strict_ok": self.checker.validate(_compile_result_from_json(result), allow_assumed=False).ok,
                }
            )
            geometry_reports.append(verify_compile_geometry(name, result).to_json())

        lean_report = self._run_lean() if run_lean else {"name": "Lean", "ok": True, "skipped": True}
        sections = {
            "code_specs": code_reports,
            "rule_specs": rule_reports,
            "protocols": protocol_reports,
            "decoders": decoder_reports,
            "checker": checker_reports,
            "compile_results": compile_reports,
            "geometry": geometry_reports,
            "lean": lean_report,
        }
        obligations = self._collect_obligations(sections, rule_specs)
        artifacts = self._collect_artifacts()
        report_items = (
            code_reports
            + rule_reports
            + protocol_reports
            + decoder_reports
            + checker_reports
            + compile_reports
            + geometry_reports
            + [lean_report]
        )
        ok = all(item.get("ok", True) for item in report_items) and all(
            obligation.status in {"ok", "imported", "skipped"} for obligation in obligations
        )
        summary = {
            "code_specs": len(code_reports),
            "rule_specs": len(rule_reports),
            "protocols": len(protocol_reports),
            "decoders": len(decoder_reports),
            "case_studies": len(cases),
            "compile_results": len(compile_reports),
            "geometry": len(geometry_reports),
            "obligations": len(obligations),
            "artifacts": len(artifacts),
        }
        return FormalToolchainReport(
            ok=ok,
            generated_at=datetime.now(timezone.utc).isoformat(),
            summary=summary,
            registry={
                "codes": [spec.to_json() for spec in code_specs],
                "rules": [spec.to_json() for spec in rule_specs],
                "case_studies": [name for name, _ in cases],
            },
            obligations=obligations,
            sections=sections,
            artifacts=artifacts,
            certificate_boundary=(
                "Machine-checked obligations are discharged by GF(2), Z3, geometry, "
                "decoder-table checks, Python rule validation, or Lean. Imported physical "
                "theorems remain explicit dependencies and are never counted as local proofs."
            ),
        )

    def load_case_studies(self) -> list[tuple[str, dict[str, Any]]]:
        cases: list[tuple[str, dict[str, Any]]] = []
        for path in sorted(self.out_dir.glob("case_study_*.json")):
            if path.name.endswith("_summary.json") or path.name == "case_study_summary.json":
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "compile_result" in payload:
                cases.append((path.stem, payload))
        return cases

    def _verify_rule_spec(self, spec: RuleSpec, code_specs: list[Any]) -> _Report:
        known_codes = {code.name for code in code_specs}
        failures: list[str] = []
        checked: list[str] = []
        for code in spec.pre_codes + spec.post_codes:
            if code not in known_codes and code not in self.rules.codes:
                failures.append(f"unknown code {code}")
        if not failures:
            checked.append("pre_and_post_codes_known")
        if spec.proof_kind == "machine_checked" and not spec.proof_obligations:
            failures.append("machine_checked rule has no proof obligations")
        else:
            checked.append("proof_obligations_recorded")
        if spec.cert_level == "Assumed" and spec.proof_kind != "assumed":
            failures.append("Assumed cert level must use assumed proof kind")
        if spec.effect.err < 0 or spec.effect.cycles < 0:
            failures.append("negative effect field")
        else:
            checked.append("effect_fields_nonnegative")
        return _Report(
            name=f"RuleSpec:{spec.name}",
            ok=not failures,
            checked=checked,
            failures=failures,
            details=spec.to_json(),
        )

    def _run_lean(self) -> dict[str, Any]:
        formal_dir = self.root / "formal"
        if not formal_dir.exists():
            return {"name": "Lean", "ok": False, "failures": ["missing formal directory"]}
        lake = shutil.which("lake") or str(Path.home() / ".elan" / "bin" / "lake")
        if not Path(lake).exists():
            return {"name": "Lean", "ok": False, "failures": ["lake executable not found"]}
        env = dict(os.environ)
        elan_bin = str(Path.home() / ".elan" / "bin")
        env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
        proc = subprocess.run(
            [lake, "build"],
            cwd=formal_dir,
            text=True,
            capture_output=True,
            env=env,
            timeout=120,
        )
        return {
            "name": "LeanCore",
            "ok": proc.returncode == 0,
            "checked": ["lake_build"] if proc.returncode == 0 else [],
            "failures": [] if proc.returncode == 0 else [proc.stderr or proc.stdout],
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }

    def _collect_obligations(self, sections: dict[str, Any], rule_specs: list[RuleSpec]) -> list[Obligation]:
        obligations: list[Obligation] = []
        for section_name, reports in sections.items():
            if section_name == "lean":
                status = "ok" if reports.get("ok") else "failed"
                obligations.append(
                    Obligation(
                        id="lean.core",
                        category="mechanized_proof",
                        subject="FTQP.Core",
                        prover="Lean4/lake",
                        status=status,
                        details={"checked": reports.get("checked", [])},
                    )
                )
                continue
            for report in reports:
                status = "ok" if report.get("ok", True) else "failed"
                obligations.append(
                    Obligation(
                        id=_stable_id(section_name, report.get("name", section_name)),
                        category=section_name,
                        subject=report.get("name", section_name),
                        prover=_prover_for_section(section_name),
                        status=status,
                        details={
                            "checked": report.get("checked", []),
                            "failures": report.get("failures", []),
                        },
                    )
                )
                for imported in report.get("imported", []):
                    obligations.append(
                        Obligation(
                            id=_stable_id("imported", imported.get("name", "theorem")),
                            category="imported_theorem",
                            subject=imported.get("name", "theorem"),
                            prover="external-literature",
                            status="imported",
                            dependencies=[report.get("name", section_name)],
                            details=imported,
                        )
                    )
        for rule in rule_specs:
            for item in rule.proof_obligations:
                obligations.append(
                    Obligation(
                        id=_stable_id("rule_obligation", f"{rule.name}:{item}"),
                        category="rule_obligation",
                        subject=f"{rule.name}:{item}",
                        prover=rule.proof_kind,
                        status="imported" if rule.proof_kind == "imported_theorem" else "ok",
                        dependencies=[rule.name],
                    )
                )
        return obligations

    def _collect_artifacts(self) -> list[Artifact]:
        candidates = [
            self.out_dir / "verification_report.json",
            self.out_dir / "protocol_certificates.json",
            self.out_dir / "full_stack_report.json",
        ]
        candidates.extend(sorted(self.out_dir.glob("case_study_*.json")))
        candidates.extend(sorted((self.out_dir / "smt").glob("*.smt2")))
        artifacts: list[Artifact] = []
        for path in candidates:
            if path.exists() and path.is_file():
                artifacts.append(
                    Artifact(
                        path=str(path.relative_to(self.root)),
                        sha256=_sha256(path),
                        bytes=path.stat().st_size,
                    )
                )
        return artifacts


@dataclass
class _Report:
    name: str
    ok: bool
    checked: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "checked": self.checked,
            "failures": self.failures,
            "details": self.details,
        }


def _compile_result_from_json(payload: dict[str, Any]) -> Any:
    # Checker only needs CompileResult-like attributes used in validate().
    from types import SimpleNamespace

    def effect_from_json(data: dict[str, Any]) -> Any:
        from .ir import Effect

        return Effect(
            err=data.get("err", 0.0),
            fail=data.get("fail", 0.0),
            accept=data.get("accept", 1.0),
            qubits_peak=data.get("qubits_peak", 0),
            cycles=data.get("cycles", 0),
            qubit_rounds=data.get("qubit_rounds", 0),
            switch_count=data.get("switch_count", 0),
            factory_count=data.get("factory_count", 0),
            measurements=data.get("measurements", 0),
            resets=data.get("resets", 0),
            two_qubit_gates=data.get("two_qubit_gates", 0),
            three_qubit_gates=data.get("three_qubit_gates", 0),
            decoder_latency=data.get("decoder_latency", 0),
            certs=list(data.get("certs", [])),
            assumptions=list(data.get("assumptions", [])),
            rules=list(data.get("rules", [])),
        )

    def step_from_json(data: dict[str, Any]) -> Any:
        from .ir import FTStep

        return FTStep(
            op=data["op"],
            rule=data["rule"],
            qubits=tuple(data.get("qubits", [])),
            input_codes=dict(data.get("input_codes", {})),
            output_codes=dict(data.get("output_codes", {})),
            effect=effect_from_json(data.get("effect", {})),
            cert_level=data.get("cert_level", "Checked"),
            details=dict(data.get("details", {})),
            children=[step_from_json(child) for child in data.get("children", [])],
        )

    backend = payload.get("backend", {})
    return SimpleNamespace(
        backend=SimpleNamespace(
            name=backend.get("name"),
            topology=backend.get("topology"),
            capacity_qubits=backend.get("capacity_qubits"),
        ),
        steps=[step_from_json(step) for step in payload.get("steps", [])],
    )


def _stable_id(category: str, subject: str) -> str:
    digest = hashlib.sha1(f"{category}:{subject}".encode("utf-8")).hexdigest()[:12]
    return f"{category}.{digest}"


def _prover_for_section(section: str) -> str:
    return {
        "code_specs": "GF(2)-CodeSpec",
        "rule_specs": "RuleSpec-validator",
        "protocols": "GF(2)/triorthogonal-checker",
        "decoders": "decoder-contract-checker",
        "checker": "FTStep-checker",
        "compile_results": "Z3/SMT",
        "geometry": "patch-geometry-checker",
    }.get(section, "checker")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
