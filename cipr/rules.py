from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ir import CertLevel, Effect


GateKind = Literal["native", "transversal"]


@dataclass(frozen=True)
class SourceRef:
    key: str
    citation: str
    locator: str
    note: str
    url: str

    def to_json(self) -> dict[str, str]:
        return {
            "key": self.key,
            "citation": self.citation,
            "locator": self.locator,
            "note": self.note,
            "url": self.url,
        }


@dataclass(frozen=True)
class CodeProfile:
    name: str
    distance: int
    gates: frozenset[str]
    gate_kind: GateKind
    sources: tuple[SourceRef, ...] = ()


@dataclass(frozen=True)
class RuleProfile:
    name: str
    kind: str
    cert_level: CertLevel
    effect: Effect
    assumptions: tuple[str, ...] = ()
    sources: tuple[SourceRef, ...] = ()

    def instantiated_effect(self) -> Effect:
        effect = self.effect.copy()
        effect.rules.append(self.name)
        effect.certs.append(f"cert:{self.name}:{self.cert_level}")
        effect.assumptions.extend(self.assumptions)
        return effect

    def sources_json(self) -> list[dict[str, str]]:
        return [source.to_json() for source in self.sources]


BUTT2024 = SourceRef(
    key="8QS8EFNR",
    citation="Butt et al., Fault-Tolerant Code-Switching Protocols for Near-Term Quantum Processors, PRX Quantum 5, 020345 (2024)",
    locator="pp. 020345-2--020345-4, Fig. 1--3; p. 020345-4, Table I",
    note="2D triangular/Steane code has transversal H,S,CNOT; tetrahedral [[15,1,3]] has transversal T,CNOT; Table I reports switch building-block qubits/CNOT counts.",
    url="https://doi.org/10.1103/PRXQuantum.5.020345",
)

HEUSSEN2025 = SourceRef(
    key="D9ABXAEH",
    citation="Heussen and Hilder, Efficient fault-tolerant code switching via one-way transversal CNOT gates, Quantum 9, 1846 (2025)",
    locator="pp. 1--4, Fig. 1--4; p. 7 for distance-3 T-gate resource discussion",
    note="One-way transversal CNOT code switching implements a logical T gate by switching 2D -> 3D -> 2D; reports 83 CNOT gates for the d=3 scheme and about 95% auxiliary-state acceptance under the stated ion-trap noise model.",
    url="https://doi.org/10.22331/q-2025-09-03-1846",
)

ITOGAWA2025 = SourceRef(
    key="ITFGJ4YN",
    citation="Itogawa et al., Efficient Magic State Distillation by Zero-Level Distillation, PRX Quantum 6, 020356 (2025)",
    locator="pp. 020356-1--020356-2 abstract/introduction; p. 020356-5; pp. 020356-7--020356-10, Fig. 11--16",
    note="Zero-level distillation uses Steane-code verification and teleportation/conversion to surface code; reports p_L approximately 100 p^2, physical depth 25 for rotated-surface teleportation, and success about 70% at p=1e-3 / 95% at p=1e-4.",
    url="https://doi.org/10.1103/thxx-njr6",
)

WAN2024 = SourceRef(
    key="WV8K4EP7",
    citation="Wan, Constant-time magic state distillation, arXiv:2410.17992 (2024)",
    locator="pp. 1--2 for O(1) code cycles and 35p^3/7p^3; p. 7 for 111 d^2 and 47 d^2 qubit-cycle costs",
    note="15-to-1 surface-code MSD has leading-order 35 p^3 suppression, O(1) code cycles, 6 code cycles, and 111 d^2 qubit-cycles excluding physical ancilla/injection cost.",
    url="https://arxiv.org/abs/2410.17992",
)

BUTT2025_MF = SourceRef(
    key="2LGTLTNX",
    citation="Butt et al., Measurement-free, scalable, and fault-tolerant universal quantum computing, Science Advances 11, eadv2590 (2025)",
    locator="pp. 1--4, Fig. 1--5; pp. 7--10, Eq. 7--10 and Fig. 9--10",
    note="Measurement-free code switching replaces mid-circuit measurement/feed-forward with coherent syndrome extraction, quantum feedback, resets, and auxiliary code states.",
    url="https://doi.org/10.1126/sciadv.adv2590",
)

BRAVYI_KITAEV2005 = SourceRef(
    key="7IERWW53",
    citation="Bravyi and Kitaev, Universal quantum computation with ideal Clifford gates and noisy ancillas, Phys. Rev. A 71, 022316 (2005)",
    locator="general magic-state injection/distillation foundation",
    note="Clifford operations plus noisy magic ancillas can enable universal quantum computation through magic-state distillation/injection.",
    url="https://doi.org/10.1103/PhysRevA.71.022316",
)

PROTOTYPE_ASSUMPTION = SourceRef(
    key="CIPR-PROTOTYPE",
    citation="CiPR-FTQC prototype assumption",
    locator="not a literature claim",
    note="Used only to connect otherwise paper-backed rules inside a compact compiler case study. Treat as Assumed, not as a physics result.",
    url="",
)


class RuleLibrary:
    """A small certified FTQC rule library with concrete resource numbers.

    The values are deliberately coarse. They are experimental profiles for the
    language prototype, not claims about a particular hardware implementation.
    """

    def __init__(self) -> None:
        self.codes = {
            "SurfaceD5": CodeProfile(
                name="SurfaceD5",
                distance=5,
                gates=frozenset({"H", "S"}),
                gate_kind="native",
                sources=(WAN2024, ITOGAWA2025),
            ),
            "Steane3": CodeProfile(
                name="Steane3",
                distance=3,
                gates=frozenset({"H", "S", "CNOT"}),
                gate_kind="transversal",
                sources=(BUTT2024, ITOGAWA2025),
            ),
            "Tetra15": CodeProfile(
                name="Tetra15",
                distance=3,
                gates=frozenset({"CNOT", "T"}),
                gate_kind="transversal",
                sources=(BUTT2024, HEUSSEN2025),
            ),
        }

        self.prepare = RuleProfile(
            "PrepareL_SurfaceD5",
            "prepare",
            "Checked",
            Effect(err=1.0e-5, cycles=2, qubit_rounds=400, qubits_peak=25),
            sources=(ITOGAWA2025,),
        )
        self.ec = {
            "SurfaceD5": RuleProfile(
                "EC_SurfaceD5",
                "ec",
                "Checked",
                Effect(
                    err=2.0e-5,
                    cycles=3,
                    qubit_rounds=600,
                    qubits_peak=25,
                    measurements=4,
                    decoder_latency=1,
                ),
                sources=(ITOGAWA2025,),
            ),
            "Steane3": RuleProfile(
                "EC_Steane3",
                "ec",
                "Checked",
                Effect(
                    err=1.2e-5,
                    cycles=2,
                    qubit_rounds=220,
                    qubits_peak=7,
                    measurements=2,
                    decoder_latency=1,
                ),
                sources=(BUTT2024,),
            ),
            "Tetra15": RuleProfile(
                "EC_Tetra15",
                "ec",
                "Certified",
                Effect(
                    err=8.0e-6,
                    cycles=2,
                    qubit_rounds=30,
                    qubits_peak=15,
                    measurements=3,
                    decoder_latency=1,
                ),
                sources=(BUTT2024,),
            ),
        }
        self.measure = {
            "SurfaceD5": RuleProfile(
                "MeasureL_SurfaceD5",
                "measure",
                "Checked",
                Effect(err=8.0e-6, cycles=2, qubit_rounds=300, qubits_peak=25, measurements=1),
                sources=(ITOGAWA2025,),
            ),
            "Steane3": RuleProfile(
                "MeasureL_Steane3",
                "measure",
                "Checked",
                Effect(err=5.0e-6, cycles=1, qubit_rounds=120, qubits_peak=7, measurements=1),
                sources=(BUTT2024,),
            ),
            "Tetra15": RuleProfile(
                "MeasureL_Tetra15",
                "measure",
                "Certified",
                Effect(err=5.0e-6, cycles=1, qubit_rounds=15, qubits_peak=15, measurements=1),
                sources=(BUTT2024,),
            ),
        }

        self.gate_effects = {
            ("SurfaceD5", "H"): RuleProfile(
                "NativeH_SurfaceD5",
                "gate",
                "Checked",
                Effect(err=5.0e-6, cycles=1, qubit_rounds=120, qubits_peak=25),
                sources=(PROTOTYPE_ASSUMPTION,),
            ),
            ("SurfaceD5", "S"): RuleProfile(
                "NativeS_SurfaceD5",
                "gate",
                "Checked",
                Effect(err=5.0e-6, cycles=1, qubit_rounds=120, qubits_peak=25),
                sources=(PROTOTYPE_ASSUMPTION,),
            ),
            ("Steane3", "H"): RuleProfile(
                "TransvH_Steane3",
                "gate",
                "Checked",
                Effect(err=3.0e-6, cycles=1, qubit_rounds=7, qubits_peak=7),
                sources=(BUTT2024,),
            ),
            ("Steane3", "S"): RuleProfile(
                "TransvS_Steane3",
                "gate",
                "Checked",
                Effect(err=3.0e-6, cycles=1, qubit_rounds=7, qubits_peak=7),
                sources=(BUTT2024,),
            ),
            ("Steane3", "CNOT"): RuleProfile(
                "TransvCNOT_Steane3",
                "gate",
                "Checked",
                Effect(err=4.0e-6, cycles=1, qubit_rounds=14, qubits_peak=14, two_qubit_gates=7),
                sources=(BUTT2024,),
            ),
            ("Tetra15", "CNOT"): RuleProfile(
                "TransvCNOT_Tetra15",
                "gate",
                "Certified",
                Effect(err=1.5e-6, cycles=1, qubit_rounds=30, qubits_peak=30, two_qubit_gates=15),
                sources=(BUTT2024, HEUSSEN2025),
            ),
            ("Tetra15", "T"): RuleProfile(
                "TransvT_Tetra15",
                "gate",
                "Certified",
                Effect(err=1.0e-6, cycles=1, qubit_rounds=15, qubits_peak=15),
                sources=(BUTT2024, HEUSSEN2025),
            ),
        }

        self.switches = {
            ("SurfaceD5", "Steane3"): RuleProfile(
                "Switch_SurfaceD5_to_Steane3",
                "switch",
                "Assumed",
                Effect(
                    err=7.0e-6,
                    fail=0.005,
                    accept=0.995,
                    cycles=4,
                    qubit_rounds=800,
                    qubits_peak=32,
                    switch_count=1,
                    measurements=2,
                    decoder_latency=1,
                ),
                ("prototype bridge: surface-to-Steane data switch not directly reported by cited code-switching papers",),
                (PROTOTYPE_ASSUMPTION, ITOGAWA2025),
            ),
            ("Steane3", "SurfaceD5"): RuleProfile(
                "Switch_Steane3_to_SurfaceD5",
                "switch",
                "Assumed",
                Effect(
                    err=7.0e-6,
                    fail=0.005,
                    accept=0.995,
                    cycles=4,
                    qubit_rounds=800,
                    qubits_peak=32,
                    switch_count=1,
                    measurements=2,
                    decoder_latency=1,
                ),
                ("prototype bridge: Steane-to-surface data switch not directly reported by cited code-switching papers",),
                (PROTOTYPE_ASSUMPTION, ITOGAWA2025),
            ),
            ("Steane3", "Tetra15"): RuleProfile(
                "Switch_Steane3_to_Tetra15",
                "switch",
                "Certified",
                Effect(
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
                ("PRX Quantum 2024 Table I reports [[7,1,3]] -> [[15,1,3]] with 17 qubits and 72 CNOT gates; 3% logical failure is the deterministic logical-gate estimate in the abstract.",),
                (BUTT2024,),
            ),
            ("Tetra15", "Steane3"): RuleProfile(
                "Switch_Tetra15_to_Steane3",
                "switch",
                "Certified",
                Effect(
                    err=3.0e-2,
                    fail=3.0e-2,
                    accept=0.97,
                    cycles=18,
                    qubit_rounds=18,
                    qubits_peak=17,
                    switch_count=1,
                    measurements=3,
                    decoder_latency=1,
                    two_qubit_gates=18,
                ),
                ("PRX Quantum 2024 Table I reports [[15,1,3]] -> [[7,1,3]] with 17 qubits and 18 CNOT gates; 3% logical failure is the deterministic logical-gate estimate in the abstract.",),
                (BUTT2024,),
            ),
            ("SurfaceD5", "Tetra15"): RuleProfile(
                "Switch_SurfaceD5_to_Tetra15",
                "switch",
                "Assumed",
                Effect(
                    err=1.0e-5,
                    fail=0.01,
                    accept=0.99,
                    cycles=6,
                    qubit_rounds=1500,
                    qubits_peak=56,
                    switch_count=1,
                    measurements=3,
                    decoder_latency=2,
                    two_qubit_gates=90,
                ),
                ("prototype bridge for hybrid case study; not directly reported as a surface-to-tetrahedral switch",),
                (PROTOTYPE_ASSUMPTION,),
            ),
            ("Tetra15", "SurfaceD5"): RuleProfile(
                "Switch_Tetra15_to_SurfaceD5",
                "switch",
                "Assumed",
                Effect(
                    err=1.0e-5,
                    fail=0.01,
                    accept=0.99,
                    cycles=6,
                    qubit_rounds=1500,
                    qubits_peak=56,
                    switch_count=1,
                    measurements=3,
                    decoder_latency=2,
                    two_qubit_gates=90,
                ),
                ("prototype bridge for hybrid case study; not directly reported as a tetrahedral-to-surface switch",),
                (PROTOTYPE_ASSUMPTION,),
            ),
        }

        self.resource_plans = {
            ("SurfaceD5", "CNOT"): RuleProfile(
                "BellTeleportCNOT_SurfaceD5",
                "resource_gate",
                "Assumed",
                Effect(
                    err=2.5e-5,
                    fail=0.002,
                    accept=0.998,
                    cycles=9,
                    qubit_rounds=1700,
                    qubits_peak=80,
                    factory_count=1,
                    measurements=2,
                    decoder_latency=1,
                    two_qubit_gates=16,
                ),
                ("prototype Bell-resource CNOT path; exact surface-code CNOT resource profile is not imported from a specific paper yet",),
                (PROTOTYPE_ASSUMPTION, BRAVYI_KITAEV2005),
            ),
            ("SurfaceD5", "T"): RuleProfile(
                "ZeroLevelTThenInject_SurfaceD5",
                "resource_gate",
                "Certified",
                Effect(
                    err=1.0e-4,
                    fail=0.30,
                    accept=0.70,
                    cycles=25,
                    qubit_rounds=1000,
                    qubits_peak=40,
                    factory_count=1,
                    measurements=3,
                    decoder_latency=1,
                    two_qubit_gates=25,
                ),
                ("paper profile instantiated at p=1e-3: p_L ~= 100 p^2 = 1e-4; accept ~= 70%; rotated-surface teleportation depth 25",),
                (ITOGAWA2025,),
            ),
            ("SurfaceD5", "T.high_fidelity"): RuleProfile(
                "Surface15to1TThenInject_SurfaceD5",
                "resource_gate",
                "Certified",
                Effect(
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
                ("paper profile instantiated at d=5, p_in=1e-3: eps_out ~= 35 p^3; cost = 111 d^2 = 2775 qubit-cycles; 6 code cycles; accept approximated by 1-15p",),
                (WAN2024,),
            ),
            ("SurfaceD5", "CCZ"): RuleProfile(
                "CCZFactoryThenInject_SurfaceD5",
                "resource_gate",
                "Assumed",
                Effect(
                    err=2.0e-8,
                    fail=0.12,
                    accept=0.88,
                    cycles=34,
                    qubit_rounds=5200,
                    qubits_peak=240,
                    factory_count=1,
                    measurements=6,
                    decoder_latency=1,
                    two_qubit_gates=96,
                ),
                ("placeholder CCZ-state factory used to keep the case study multi-qubit; replace with a specific CCZ factory paper before making physics claims",),
                (PROTOTYPE_ASSUMPTION,),
            ),
        }

    def supports_gate(self, code: str, gate: str) -> bool:
        return gate in self.codes[code].gates

    def gate_rule(self, code: str, gate: str) -> RuleProfile:
        return self.gate_effects[(code, gate)]

    def switch_rule(self, source: str, target: str) -> RuleProfile | None:
        return self.switches.get((source, target))

    def resource_rule(self, code: str, gate: str, high_fidelity: bool = False) -> RuleProfile | None:
        if high_fidelity and gate == "T":
            return self.resource_plans.get((code, "T.high_fidelity"))
        return self.resource_plans.get((code, gate))

    def codes_supporting(self, gate: str) -> list[str]:
        return [code for code, profile in self.codes.items() if gate in profile.gates]
