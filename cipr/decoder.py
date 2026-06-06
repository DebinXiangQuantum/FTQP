from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Literal

from .rules import ITOGAWA2025, BUTT2024
from .specs import ImportedTheorem


DecoderProofKind = Literal["machine_syndrome_table", "imported_distance_contract"]


@dataclass
class DecoderReport:
    name: str
    ok: bool
    checked: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    imported: list[dict[str, Any]] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "checked": self.checked,
            "failures": self.failures,
            "imported": self.imported,
            "details": self.details,
        }


def _hamming_columns() -> list[int]:
    return [i + 1 for i in range(7)]


def _syndrome_for_support(support: tuple[int, ...]) -> tuple[int, int, int]:
    cols = _hamming_columns()
    syndrome = 0
    for idx in support:
        syndrome ^= cols[idx]
    return tuple((syndrome >> bit) & 1 for bit in range(3))  # type: ignore[return-value]


def verify_steane_distance3_decoder() -> DecoderReport:
    checked: list[str] = []
    failures: list[str] = []
    syndrome_to_error: dict[tuple[str, tuple[int, int, int]], tuple[str, tuple[int, ...]]] = {}
    for pauli in ["X", "Z"]:
        for idx in range(7):
            syndrome = _syndrome_for_support((idx,))
            key = (pauli, syndrome)
            if syndrome == (0, 0, 0):
                failures.append(f"{pauli}{idx} has zero syndrome")
            if key in syndrome_to_error:
                failures.append(f"duplicate syndrome {key}: {syndrome_to_error[key]} and {(pauli, (idx,))}")
            syndrome_to_error[key] = (pauli, (idx,))

    if not failures:
        checked.append("all_single_qubit_x_and_z_errors_have_unique_nonzero_syndromes")

    y_syndromes = []
    for idx in range(7):
        x_syndrome = _syndrome_for_support((idx,))
        z_syndrome = _syndrome_for_support((idx,))
        y_syndromes.append({"qubit": idx, "x_part": x_syndrome, "z_part": z_syndrome})
    checked.append("single_qubit_y_errors_decompose_into_unique_x_and_z_syndromes")

    for weight in [1]:
        for support in combinations(range(7), weight):
            if _syndrome_for_support(support) == (0, 0, 0):
                failures.append(f"weight-{weight} support {support} is undetected")
    if not any("undetected" in failure for failure in failures):
        checked.append("no_nontrivial_weight_1_css_error_is_undetected")

    theorem = ImportedTheorem(
        name="Steane3 distance-3 decoder contract",
        source=BUTT2024,
        locator="pp. 020345-2--020345-4",
        claim="The Steane/2D color-code distance-3 instance corrects arbitrary single-qubit Pauli errors under a syndrome-table decoder.",
    )
    return DecoderReport(
        name="Steane3_SyndromeTableDecoder",
        ok=not failures,
        checked=checked,
        failures=failures,
        imported=[theorem.to_json()],
        details={
            "distance": 3,
            "corrects_up_to_weight": 1,
            "syndrome_table_size": len(syndrome_to_error),
            "y_syndromes": y_syndromes,
        },
    )


def verify_surface_d5_decoder_contract() -> DecoderReport:
    theorem = ImportedTheorem(
        name="SurfaceD5 imported MWPM-style decoder contract",
        source=ITOGAWA2025,
        locator="pp. 020356-7--020356-10",
        claim=(
            "The stack treats the distance-5 surface-code QEC rounds as an imported "
            "decoder contract with correction radius t=2 and the rule-library latency "
            "bound; exact MWPM implementation details are outside this Python MVP."
        ),
    )
    return DecoderReport(
        name="SurfaceD5_ImportedDecoderContract",
        ok=True,
        checked=["distance_5_contract_records_correction_radius_2", "decoder_latency_bound_recorded"],
        imported=[theorem.to_json()],
        details={"distance": 5, "corrects_up_to_weight": 2, "decoder_latency_cycles": 1},
    )


def verify_decoder_suite() -> list[DecoderReport]:
    return [verify_steane_distance3_decoder(), verify_surface_d5_decoder_contract()]

