from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from .rules import BUTT2024, WAN2024
from .specs import ImportedTheorem, reed_muller_15_triorthogonal_rows
from .stabilizer import (
    GaugeSwitchSpec,
    Pauli,
    VerificationResult,
    verify_gauge_switch,
)


@dataclass
class ProtocolReport:
    name: str
    ok: bool
    checked: list[str] = field(default_factory=list)
    imported: list[dict[str, Any]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "checked": self.checked,
            "imported": self.imported,
            "failures": self.failures,
            "details": self.details,
        }


def butt_steane_tetra_full_switch_certificate() -> ProtocolReport:
    algebraic = _butt_steane_tetra_algebraic_core()
    theorem = ImportedTheorem(
        name="Butt2024 flag-circuit single-fault-tolerance theorem",
        source=BUTT2024,
        locator="Sec. IV--V, Table I, and flag-qubit switching circuits",
        claim=(
            "The cited paper constructs deterministic distance-3 2D/3D color-code "
            "switching protocols with flag-qubit fault-tolerant circuits; the MVP "
            "imports the complete flag-fault enumeration as a theorem rather than "
            "re-enumerating every circuit fault locally."
        ),
    )
    checked = list(algebraic.checked)
    imported = [theorem.to_json()]
    failures = list(algebraic.failures)
    if not failures:
        checked.append("butt2024_algebraic_gauge_fixing_core_machine_checked")
    resources = {
        "Steane3_to_Tetra15": {"building_block_qubits": 17, "cnot_count": 72},
        "Tetra15_to_Steane3": {"building_block_qubits": 17, "cnot_count": 18},
        "deterministic_gate_logical_failure_reference": 0.03,
    }
    if resources["Steane3_to_Tetra15"]["building_block_qubits"] == 17:
        checked.append("table_i_switch_qubit_count_recorded")
    if resources["Steane3_to_Tetra15"]["cnot_count"] == 72:
        checked.append("table_i_steane_to_tetra_cnot_count_recorded")
    if resources["Tetra15_to_Steane3"]["cnot_count"] == 18:
        checked.append("table_i_tetra_to_steane_cnot_count_recorded")

    return ProtocolReport(
        name="Butt2024_Steane_Tetra15_FullSwitchCertificate",
        ok=not failures,
        checked=checked,
        imported=imported,
        failures=failures,
        details={
            "machine_checked_part": algebraic.to_json(),
            "resource_table": resources,
            "certificate_boundary": (
                "Algebraic gauge fixing is checked over GF(2). Complete flag-circuit "
                "single-fault tolerance is imported from the cited paper and recorded "
                "as a theorem dependency."
            ),
        },
    )


def _butt_steane_tetra_algebraic_core() -> VerificationResult:
    n = 15
    target_x_faces = (
        Pauli.from_xz("Steane_X_red_face", n, xs=[0, 1, 2, 3]),
        Pauli.from_xz("Steane_X_green_face", n, xs=[1, 2, 4, 5]),
        Pauli.from_xz("Steane_X_blue_face", n, xs=[2, 3, 5, 6]),
    )
    gauge_corrections = (
        Pauli.from_xz("Gauge_Z_for_red_face_BZ_BG", n, zs=[2, 5, 11, 13]),
        Pauli.from_xz("Gauge_Z_for_green_face_basis", n, zs=[0, 1]),
        Pauli.from_xz("Gauge_Z_for_blue_face_basis", n, zs=[0, 3]),
    )
    return verify_gauge_switch(
        GaugeSwitchSpec(
            name="Butt2024_Steane_Tetra15_GaugeFixing_Core",
            n=n,
            subsystem_stabilizers=(),
            target_stabilizers=target_x_faces,
            gauge_corrections=gauge_corrections,
            logical_x=Pauli.from_xz("Common_logical_X_Eq16", n, xs=range(7)),
            logical_z=Pauli.from_xz("Common_logical_Z_Eq16", n, zs=range(7)),
            source="Tetra15",
            target="Steane3",
            source_ref=(
                "Butt et al. 2024, Sec. IV, Eq. (14)--(16), Fig. 7(a): "
                "switching is gauge fixing between variants of the same subsystem code."
            ),
        )
    )


def verify_15to1_reed_muller_distillation() -> ProtocolReport:
    rows = reed_muller_15_triorthogonal_rows()
    checked: list[str] = []
    failures: list[str] = []
    odd_rows = [i for i, row in enumerate(rows) if sum(row) % 2 == 1]
    even_rows = [i for i, row in enumerate(rows) if sum(row) % 2 == 0]
    if odd_rows == [0] and even_rows == [1, 2, 3, 4]:
        checked.append("triorthogonal_matrix_has_one_odd_logical_row_and_four_even_check_rows")
    else:
        failures.append(f"unexpected odd/even row partition: odd={odd_rows} even={even_rows}")

    for i, j in combinations(range(len(rows)), 2):
        overlap = sum(a & b for a, b in zip(rows[i], rows[j], strict=True))
        if overlap % 2 != 0:
            failures.append(f"rows {i}/{j} have odd pair overlap {overlap}")
    if not any("pair overlap" in failure for failure in failures):
        checked.append("all_pair_overlaps_even")

    for i, j, k in combinations(range(len(rows)), 3):
        overlap = sum(a & b & c for a, b, c in zip(rows[i], rows[j], rows[k], strict=True))
        if overlap % 2 != 0:
            failures.append(f"rows {i}/{j}/{k} have odd triple overlap {overlap}")
    if not any("triple overlap" in failure for failure in failures):
        checked.append("all_triple_overlaps_even")

    check_rows = rows[1:]
    accepted_by_weight: dict[int, list[tuple[int, ...]]] = {1: [], 2: [], 3: []}
    logical_by_weight: dict[int, list[tuple[int, ...]]] = {1: [], 2: [], 3: []}
    for weight in [1, 2, 3]:
        for support in combinations(range(15), weight):
            syndrome = tuple(sum(row[i] for i in support) % 2 for row in check_rows)
            if any(syndrome):
                continue
            accepted_by_weight[weight].append(support)
            if weight % 2 == 1:
                logical_by_weight[weight].append(support)

    if not accepted_by_weight[1] and not accepted_by_weight[2]:
        checked.append("all_weight_1_and_2_input_z_errors_are_detected")
    else:
        failures.append(
            "accepted low-weight input errors: "
            f"w1={accepted_by_weight[1]} w2={accepted_by_weight[2]}"
        )

    leading_count = len(logical_by_weight[3])
    if leading_count == 35:
        checked.append("leading_weight_3_logical_error_count_is_35")
    else:
        failures.append(f"expected 35 accepted weight-3 logical errors, got {leading_count}")

    theorem = ImportedTheorem(
        name="Wan2024 constant-time 15-to-1 surface-code implementation",
        source=WAN2024,
        locator="pp. 1--2 and p. 7",
        claim=(
            "The constant-time surface-code implementation records 35 p^3 leading "
            "suppression, six code cycles, and 111 d^2 qubit-cycle profile for the "
            "15-to-1 construction used by the rule library."
        ),
    )
    return ProtocolReport(
        name="ReedMuller15To1_MagicDistillation",
        ok=not failures,
        checked=checked,
        imported=[theorem.to_json()],
        failures=failures,
        details={
            "row_count": len(rows),
            "column_count": len(rows[0]),
            "accepted_error_counts": {str(k): len(v) for k, v in accepted_by_weight.items()},
            "accepted_logical_error_counts": {str(k): len(v) for k, v in logical_by_weight.items()},
            "leading_output_error_polynomial": "35 p^3 + O(p^4)",
            "matrix_rows": [list(row) for row in rows],
        },
    )


def verify_protocol_suite() -> list[ProtocolReport]:
    return [
        butt_steane_tetra_full_switch_certificate(),
        verify_15to1_reed_muller_distillation(),
    ]

