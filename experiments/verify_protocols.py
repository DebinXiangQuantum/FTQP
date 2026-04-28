from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cipr.stabilizer import (  # noqa: E402
    GaugeSwitchSpec,
    MagicDistillationSpec,
    Pauli,
    verify_gauge_switch,
    verify_magic_distillation_skeleton,
)


OUT_DIR = Path(__file__).resolve().parent / "outputs"


def steane_tetra_gauge_switch_spec() -> GaugeSwitchSpec:
    n = 15
    target_x_faces = (
        Pauli.from_xz("Steane_X_red_face", n, xs=[0, 1, 2, 3]),
        Pauli.from_xz("Steane_X_green_face", n, xs=[1, 2, 4, 5]),
        Pauli.from_xz("Steane_X_blue_face", n, xs=[2, 3, 5, 6]),
    )
    # Syndrome-equivalent Z-face corrections. The red entry uses the explicit
    # BZ_BG example discussed around Fig. 7(a); the other two form a compact
    # basis with the same gauge-fixing algebra and should be replaced by exact
    # face labels when importing the appendix protocol.
    gauge_corrections = (
        Pauli.from_xz("Gauge_Z_for_red_face_BZ_BG", n, zs=[2, 5, 11, 13]),
        Pauli.from_xz("Gauge_Z_for_green_face_basis", n, zs=[0, 1]),
        Pauli.from_xz("Gauge_Z_for_blue_face_basis", n, zs=[0, 3]),
    )
    return GaugeSwitchSpec(
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


def toy_magic_distillation_spec() -> MagicDistillationSpec:
    n = 3
    return MagicDistillationSpec(
        name="Toy_Repetition_MagicDistillation_Syndrome_Core",
        n_inputs=n,
        checks=(
            Pauli.from_xz("X_parity_01", n, xs=[0, 1]),
            Pauli.from_xz("X_parity_12", n, xs=[1, 2]),
        ),
        logical_error=Pauli.from_xz("Logical_ZZZ", n, zs=[0, 1, 2]),
        detect_up_to_weight=2,
        source_ref=(
            "Generic stabilizer distillation skeleton: accepted low-weight input "
            "Pauli errors must not implement the output logical error."
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = [
        verify_gauge_switch(steane_tetra_gauge_switch_spec()).to_json(),
        verify_magic_distillation_skeleton(toy_magic_distillation_spec()).to_json(),
    ]
    out_path = OUT_DIR / "protocol_certificates.json"
    out_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")
    for result in results:
        status = "ok" if result["ok"] else "failed"
        print(f"{result['name']}: {status} checks={len(result['checked'])}")
        for failure in result["failures"]:
            print(f"  - {failure}")
    print(f"\nWrote protocol certificates to {out_path}")


if __name__ == "__main__":
    main()
