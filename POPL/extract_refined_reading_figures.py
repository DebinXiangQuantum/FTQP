from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import fitz


ROOT = Path(__file__).resolve().parent
PDF_DIR = ROOT / "pdfs"
OUT_DIR = ROOT / "reading_share_assets" / "figures_refined"


@dataclass(frozen=True)
class Crop:
    paper: str
    pdf: str
    name: str
    page: int
    rect: tuple[float, float, float, float]
    label: str


CROPS: tuple[Crop, ...] = (
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "overview_pipeline", 2, (38, 105, 448, 178), "Fig. 1 pipeline"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "case_table", 3, (70, 80, 395, 210), "Table 1 case studies"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "nisqmr_problem", 6, (45, 70, 442, 305), "Fig. 3 NISQMR"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "scmr_problem", 7, (45, 70, 442, 412), "Fig. 4 SCMR"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "amaro_nisqmr_code", 10, (45, 75, 442, 245), "Fig. 5 Amaro NISQMR"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "amaro_grammar", 13, (58, 68, 428, 292), "Fig. 6 grammar"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "amaro_semantics", 14, (45, 70, 442, 262), "Fig. 7 semantics"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "nisqmr_results", 22, (45, 82, 442, 240), "Fig. 9 results"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "scmr_raa_results", 24, (45, 100, 442, 218), "Fig. 12/13 results"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "ilq_tiqmr_results", 25, (45, 100, 442, 218), "Fig. 14/15 results"),
    Crop("molavi", "Molavi 等 - 2026 - Generating Compilers for Qubit Mapping and Routing.pdf", "ablation", 26, (78, 72, 405, 198), "Fig. 16 ablation"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "teleport_circuit", 4, (50, 72, 435, 175), "Fig. 1 teleportation"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "quipper_not", 5, (45, 76, 442, 180), "Fig. 2 Quipper negation"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "higher_order", 5, (45, 185, 442, 288), "Fig. 3 higher order"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "variable_input", 6, (45, 78, 442, 182), "Fig. 4 variable input"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "proto_quipper_syntax", 7, (56, 70, 430, 220), "Fig. 5 syntax"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "racs_bundle", 11, (55, 72, 432, 232), "Fig. 6 RACS"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "wire_routing", 11, (78, 232, 408, 314), "Fig. 7 wire routing"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "ra_syntax", 13, (55, 72, 432, 262), "Fig. 8 RA syntax"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "typing_rules", 16, (45, 80, 442, 602), "Fig. 9 typing rules"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "let_shape", 17, (48, 80, 438, 168), "Fig. 10 let shape"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "subtyping", 18, (58, 70, 428, 264), "Fig. 11 subtyping"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "semantics", 20, (45, 70, 442, 215), "Fig. 12 semantics"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "qft_example", 25, (45, 78, 442, 356), "Fig. 13 QFT"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "qura_outputs", 25, (45, 440, 442, 582), "Qura metric outputs"),
    Crop("colledan", "Colledan和Dal Lago - 2025 - Flexible Type-Based Resource Estimation in Quantum Circuit Description Languages.pdf", "grover_example", 26, (45, 78, 442, 522), "Fig. 14 Grover"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "state_representations", 4, (235, 88, 442, 438), "Fig. 1 representations"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "plain_tree_automaton", 5, (298, 105, 444, 286), "Fig. 2 PTA"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "lsta", 5, (248, 288, 444, 546), "Fig. 3 LSTA"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "swta_uniform", 6, (250, 110, 444, 304), "Fig. 5 SWTA"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "basic_transducers", 7, (286, 72, 444, 272), "Fig. 6 gates"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "cx_transducer", 7, (270, 292, 444, 486), "Fig. 7 CX"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "verification_framework", 11, (55, 284, 442, 468), "verification framework"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "bv_circuit", 11, (252, 492, 444, 650), "Fig. 9 BV"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "adder_qecc", 13, (78, 78, 444, 660), "Fig. 10/11 adder QECC"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "grover_circuits", 14, (45, 76, 442, 220), "Fig. 12 Grover"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "hamiltonian_table", 15, (45, 78, 445, 505), "Fig. 13 + Table 1"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "qft", 23, (95, 72, 390, 232), "Fig. 15 QFT"),
    Crop("abdulla", "Abdulla 等 - 2026 - Parameterized Verification of Quantum Circuits.pdf", "maj", 24, (280, 225, 430, 388), "Fig. 16 MAJ"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "language_table", 3, (70, 78, 402, 205), "Table 1 languages"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "pebble_game", 8, (80, 72, 410, 210), "Fig. 1 pebble game"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "grover_code", 9, (45, 78, 442, 208), "Fig. 2 Grover"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "syntax_types", 13, (45, 78, 442, 360), "Fig. 3/4 syntax types"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "typing_rules", 15, (45, 78, 442, 430), "Fig. 5 typing rules"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "drop_trait", 15, (168, 445, 322, 522), "Fig. 6 drop"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "pure_quantum", 16, (45, 70, 430, 208), "Fig. 7 pure quantum"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "block_function", 16, (45, 216, 442, 302), "Fig. 8 block/function"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "simulation_rules", 17, (45, 78, 442, 308), "Fig. 9 simulation"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "toy_eval", 18, (70, 78, 412, 272), "Fig. 10 toy eval"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "uncomp_semantics", 22, (55, 108, 432, 232), "Fig. 11 uncompute"),
    Crop("hirata", "Hirata和Heunen - 2025 - Qurts Automatic Quantum Uncomputation by Affine Types with Lifetime.pdf", "silq_compare", 24, (65, 78, 424, 276), "Fig. 12 Silq"),
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for crop in CROPS:
        doc = fitz.open(PDF_DIR / crop.pdf)
        page = doc[crop.page - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), clip=fitz.Rect(crop.rect), alpha=False)
        out = OUT_DIR / f"{crop.paper}_{crop.name}.png"
        pix.save(out)
        manifest.append(
            {
                "paper": crop.paper,
                "name": crop.name,
                "label": crop.label,
                "page": crop.page,
                "rect": crop.rect,
                "file": str(out.relative_to(ROOT.parent)),
                "size": [pix.width, pix.height],
            }
        )
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(manifest)} refined crops to {OUT_DIR}")


if __name__ == "__main__":
    main()
