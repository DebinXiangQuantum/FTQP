from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from .ir import CertLevel, Effect
from .rules import BUTT2024, ITOGAWA2025, WAN2024, SourceRef
from .stabilizer import Pauli


ProofKind = Literal["machine_checked", "imported_theorem", "assumed"]


@dataclass(frozen=True)
class ImportedTheorem:
    name: str
    source: SourceRef
    locator: str
    claim: str

    def to_json(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source": self.source.to_json(),
            "locator": self.locator,
            "claim": self.claim,
        }


@dataclass(frozen=True)
class CodeSpec:
    name: str
    n: int
    k: int
    distance: int
    stabilizers: tuple[Pauli, ...]
    logical_x: Pauli
    logical_z: Pauli
    supported_topologies: frozenset[str]
    transversal_gates: frozenset[str] = frozenset()
    native_gates: frozenset[str] = frozenset()
    gauge_generators: tuple[Pauli, ...] = ()
    theorem: ImportedTheorem | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "n": self.n,
            "k": self.k,
            "distance": self.distance,
            "supported_topologies": sorted(self.supported_topologies),
            "transversal_gates": sorted(self.transversal_gates),
            "native_gates": sorted(self.native_gates),
            "stabilizer_count": len(self.stabilizers),
            "gauge_generator_count": len(self.gauge_generators),
            "logical_x": self.logical_x.to_json(),
            "logical_z": self.logical_z.to_json(),
            "theorem": None if self.theorem is None else self.theorem.to_json(),
        }


@dataclass(frozen=True)
class RuleSpec:
    name: str
    kind: str
    pre_codes: tuple[str, ...]
    post_codes: tuple[str, ...]
    effect: Effect
    cert_level: CertLevel
    proof_kind: ProofKind
    sources: tuple[SourceRef, ...] = ()
    produced_resources: tuple[str, ...] = ()
    consumed_resources: tuple[str, ...] = ()
    backend_topologies: frozenset[str] = frozenset({"grid2d", "long_range"})
    proof_obligations: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "pre_codes": list(self.pre_codes),
            "post_codes": list(self.post_codes),
            "effect": self.effect.to_json(),
            "cert_level": self.cert_level,
            "proof_kind": self.proof_kind,
            "sources": [source.to_json() for source in self.sources],
            "produced_resources": list(self.produced_resources),
            "consumed_resources": list(self.consumed_resources),
            "backend_topologies": sorted(self.backend_topologies),
            "proof_obligations": list(self.proof_obligations),
        }


@dataclass
class SpecVerification:
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


def verify_code_spec(spec: CodeSpec) -> SpecVerification:
    checked: list[str] = []
    failures: list[str] = []
    all_ops = list(spec.stabilizers) + list(spec.gauge_generators) + [spec.logical_x, spec.logical_z]
    for op in all_ops:
        if op.n != spec.n:
            failures.append(f"{op.name} has length {op.n}, expected {spec.n}")
    if not failures:
        checked.append("all_paulis_have_expected_length")

    for i, a in enumerate(spec.stabilizers):
        for b in spec.stabilizers[i + 1 :]:
            if not a.commutes(b):
                failures.append(f"noncommuting stabilizers {a.name}/{b.name}")
    if not any("noncommuting stabilizers" in failure for failure in failures):
        checked.append("stabilizers_commute")

    for stab in spec.stabilizers:
        if not stab.commutes(spec.logical_x) or not stab.commutes(spec.logical_z):
            failures.append(f"{stab.name} does not preserve logical operators")
    if not any("preserve logical" in failure for failure in failures):
        checked.append("stabilizers_preserve_logicals")

    if spec.logical_x.anticommutes(spec.logical_z):
        checked.append("logical_x_and_z_anticommute")
    else:
        failures.append("logical_x and logical_z must anticommute")

    if spec.theorem is not None:
        checked.append("external_code_theorem_recorded")

    return SpecVerification(
        name=f"CodeSpec:{spec.name}",
        ok=not failures,
        checked=checked,
        failures=failures,
        details=spec.to_json(),
    )


def steane7_code_spec() -> CodeSpec:
    n = 7
    # Hamming [7,4,3] parity-check columns are the nonzero 3-bit vectors.
    columns = [i + 1 for i in range(n)]
    x_rows = []
    z_rows = []
    for bit in range(3):
        support = [idx for idx, col in enumerate(columns) if (col >> bit) & 1]
        x_rows.append(Pauli.from_xz(f"Steane_X_check_{bit}", n, xs=support))
        z_rows.append(Pauli.from_xz(f"Steane_Z_check_{bit}", n, zs=support))
    return CodeSpec(
        name="Steane3",
        n=n,
        k=1,
        distance=3,
        stabilizers=tuple(x_rows + z_rows),
        logical_x=Pauli.from_xz("Steane_logical_X_all", n, xs=range(n)),
        logical_z=Pauli.from_xz("Steane_logical_Z_all", n, zs=range(n)),
        supported_topologies=frozenset({"grid2d", "long_range"}),
        transversal_gates=frozenset({"H", "S", "CNOT"}),
        theorem=ImportedTheorem(
            name="Steane [[7,1,3]] CSS code signature",
            source=BUTT2024,
            locator="pp. 020345-2--020345-4, Fig. 1--3",
            claim="The triangular 2D color-code/Steane instance supports transversal H, S, and CNOT in the cited code-switching setup.",
        ),
    )


def reed_muller_15_triorthogonal_rows() -> list[tuple[int, ...]]:
    columns = [i + 1 for i in range(15)]
    rows = [tuple(1 for _ in columns)]
    for bit in range(4):
        rows.append(tuple((col >> bit) & 1 for col in columns))
    return rows


def reed_muller_15_code_spec() -> CodeSpec:
    n = 15
    rows = reed_muller_15_triorthogonal_rows()
    # The even rows are a compact machine-checkable signature for the
    # 15-to-1 triorthogonal outer code used in Reed-Muller distillation.
    x_checks = [
        Pauli(tuple(row), tuple(0 for _ in row), name=f"RM15_even_X_row_{i}")
        for i, row in enumerate(rows[1:], start=1)
    ]
    return CodeSpec(
        name="RM15Triorthogonal",
        n=n,
        k=1,
        distance=3,
        stabilizers=tuple(x_checks),
        logical_x=Pauli.from_xz("RM15_logical_X_all", n, xs=range(n)),
        logical_z=Pauli.from_xz("RM15_logical_Z_all", n, zs=range(n)),
        supported_topologies=frozenset({"grid2d", "long_range"}),
        transversal_gates=frozenset({"T"}),
        theorem=ImportedTheorem(
            name="15-to-1 Reed-Muller magic distillation outer-code theorem",
            source=WAN2024,
            locator="pp. 1--2 and p. 7",
            claim="The 15-to-1 Reed-Muller magic-state distillation profile suppresses independent input error p to leading order 35 p^3 in the cited constant-time surface-code implementation.",
        ),
    )


def surface_d5_code_spec() -> CodeSpec:
    n = 25
    return CodeSpec(
        name="SurfaceD5",
        n=n,
        k=1,
        distance=5,
        stabilizers=(),
        logical_x=Pauli.from_xz("SurfaceD5_imported_logical_X", n, xs=range(5)),
        logical_z=Pauli.from_xz("SurfaceD5_imported_logical_Z", n, zs=range(0, n, 5)),
        supported_topologies=frozenset({"grid2d", "long_range"}),
        native_gates=frozenset({"H", "S"}),
        theorem=ImportedTheorem(
            name="Surface-code distance-5 imported code contract",
            source=ITOGAWA2025,
            locator="pp. 020356-7--020356-10",
            claim="The MVP treats SurfaceD5 as an imported rotated-surface logical patch with distance-5 resource profiles from the cited zero-level distillation setting.",
        ),
    )


def canonical_code_specs() -> list[CodeSpec]:
    return [surface_d5_code_spec(), steane7_code_spec(), reed_muller_15_code_spec()]


def canonical_rule_specs() -> list[RuleSpec]:
    return [
        RuleSpec(
            name="Switch_Steane3_to_Tetra15",
            kind="code_switch",
            pre_codes=("Steane3",),
            post_codes=("Tetra15",),
            effect=Effect(
                err=3.0e-2,
                fail=3.0e-2,
                accept=0.97,
                cycles=72,
                qubit_rounds=72,
                qubits_peak=17,
                switch_count=1,
                measurements=3,
                decoder_latency=1,
                two_qubit_gates=72,
            ),
            cert_level="Certified",
            proof_kind="imported_theorem",
            sources=(BUTT2024,),
            proof_obligations=(
                "algebraic_gauge_fixing_core",
                "flag_fault_tolerance_imported_theorem",
                "resource_table_match",
            ),
        ),
        RuleSpec(
            name="Surface15to1TThenInject_SurfaceD5",
            kind="magic_distillation_injection",
            pre_codes=("SurfaceD5",),
            post_codes=("SurfaceD5",),
            effect=Effect(
                err=3.5e-8,
                fail=0.015,
                accept=0.985,
                cycles=6,
                qubit_rounds=2775,
                qubits_peak=775,
                factory_count=1,
                measurements=15,
                decoder_latency=1,
                two_qubit_gates=60,
            ),
            cert_level="Certified",
            proof_kind="machine_checked",
            sources=(WAN2024,),
            produced_resources=("TState",),
            consumed_resources=("TState",),
            proof_obligations=(
                "triorthogonal_matrix_valid",
                "detects_all_weight_1_and_2_input_errors",
                "leading_weight_3_logical_error_count_is_35",
            ),
        ),
    ]

