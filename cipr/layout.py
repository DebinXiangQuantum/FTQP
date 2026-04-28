from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BackendSpec:
    name: str
    topology: str
    capacity_qubits: int
    notes: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "topology": self.topology,
            "capacity_qubits": self.capacity_qubits,
            "notes": self.notes,
        }


GRID2D_SURFACE_BACKEND = BackendSpec(
    name="Grid2D_SurfaceLike",
    topology="grid2d",
    capacity_qubits=4096,
    notes="Fixed 2D nearest-neighbor grid backend used by the MVP case study.",
)

LONG_RANGE_BACKEND = BackendSpec(
    name="LongRange_Modular",
    topology="long_range",
    capacity_qubits=4096,
    notes="Toy backend with nonlocal connectivity for qLDPC-style experiments.",
)

BACKENDS = {
    GRID2D_SURFACE_BACKEND.name: GRID2D_SURFACE_BACKEND,
    LONG_RANGE_BACKEND.name: LONG_RANGE_BACKEND,
}


@dataclass(frozen=True)
class Region:
    owner: str
    code: str
    size: int

    def to_json(self) -> dict[str, Any]:
        return {"owner": self.owner, "code": self.code, "size": self.size}


@dataclass
class LayoutState:
    backend: BackendSpec
    live: dict[str, Region] = field(default_factory=dict)

    @staticmethod
    def empty(backend: BackendSpec | str | None = None) -> LayoutState:
        if backend is None:
            spec = GRID2D_SURFACE_BACKEND
        elif isinstance(backend, str):
            spec = BACKENDS[backend]
        else:
            spec = backend
        return LayoutState(backend=spec)

    @property
    def used_qubits(self) -> int:
        return sum(region.size for region in self.live.values())

    @property
    def free_qubits(self) -> int:
        return self.backend.capacity_qubits - self.used_qubits

    def copy(self) -> LayoutState:
        return LayoutState(backend=self.backend, live=dict(self.live))

    def equivalent(self, other: LayoutState) -> bool:
        return self.backend == other.backend and self.live == other.live

    def prepare(self, q: str, code_profile: Any, rule: str) -> tuple[LayoutState, dict[str, Any]]:
        self._require_code_supported(code_profile.name, code_profile.supported_topologies)
        footprint = code_profile.footprint_qubits
        self._require_free(footprint, rule)
        before = self.free_qubits
        out = self.copy()
        out.live[q] = Region(owner=q, code=code_profile.name, size=footprint)
        return out, {
            "kind": "prepare",
            "backend": self.backend.name,
            "topology": self.backend.topology,
            "allocated": footprint,
            "free_before": before,
            "free_after": out.free_qubits,
            "region": out.live[q].to_json(),
        }

    def reserve_workspace(self, peak_qubits: int, rule: str) -> dict[str, Any]:
        self._require_free(peak_qubits, rule)
        return {
            "kind": "workspace",
            "backend": self.backend.name,
            "topology": self.backend.topology,
            "workspace_reserved": peak_qubits,
            "free_before": self.free_qubits,
            "free_after": self.free_qubits,
        }

    def switch(
        self,
        qubits: list[str],
        source_profile: Any,
        target_profile: Any,
        rule_profile: Any,
    ) -> tuple[LayoutState, dict[str, Any]]:
        if not qubits:
            raise ValueError("switch requires at least one logical qubit")
        self._require_code_supported(source_profile.name, source_profile.supported_topologies)
        self._require_code_supported(target_profile.name, target_profile.supported_topologies)
        self._require_rule_supported(rule_profile.name, rule_profile.supported_topologies)

        old_total = 0
        for q in qubits:
            region = self.live.get(q)
            if region is None:
                raise ValueError(f"layout has no region for {q}")
            if region.code != source_profile.name:
                raise ValueError(f"layout region for {q} is {region.code}, expected {source_profile.name}")
            old_total += region.size

        new_total = target_profile.footprint_qubits * len(qubits)
        workspace = rule_profile.workspace_qubits * len(qubits)
        additional_target = max(0, new_total - old_total)
        required_free = max(workspace, additional_target)
        self._require_free(required_free, rule_profile.name)

        before = self.free_qubits
        out = self.copy()
        for q in qubits:
            out.live[q] = Region(owner=q, code=target_profile.name, size=target_profile.footprint_qubits)

        freed = max(0, old_total - new_total)
        allocated_extra = max(0, new_total - old_total)
        return out, {
            "kind": "switch",
            "backend": self.backend.name,
            "topology": self.backend.topology,
            "from": source_profile.name,
            "to": target_profile.name,
            "old_footprint": old_total,
            "new_footprint": new_total,
            "workspace_reserved": workspace,
            "allocated_extra": allocated_extra,
            "freed_qubits": freed,
            "freed_regions": self._freed_region_names(qubits, source_profile.name, target_profile.name, freed),
            "free_before": before,
            "free_after": out.free_qubits,
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "backend": self.backend.to_json(),
            "used_qubits": self.used_qubits,
            "free_qubits": self.free_qubits,
            "live": {q: region.to_json() for q, region in sorted(self.live.items())},
        }

    def _freed_region_names(
        self, qubits: list[str], source_code: str, target_code: str, freed: int
    ) -> list[str]:
        if freed <= 0:
            return []
        per_qubit = freed // len(qubits)
        remainder = freed % len(qubits)
        names = []
        for i, q in enumerate(qubits):
            size = per_qubit + (1 if i < remainder else 0)
            if size > 0:
                names.append(f"{q}:{source_code}->idle_after_{target_code}:{size}")
        return names

    def _require_code_supported(self, code: str, supported_topologies: frozenset[str]) -> None:
        if self.backend.topology not in supported_topologies:
            raise ValueError(
                f"code {code} is not embeddable on backend {self.backend.name} "
                f"({self.backend.topology})"
            )

    def _require_rule_supported(self, rule: str, supported_topologies: frozenset[str]) -> None:
        if self.backend.topology not in supported_topologies:
            raise ValueError(
                f"rule {rule} is not embeddable on backend {self.backend.name} "
                f"({self.backend.topology})"
            )

    def _require_free(self, amount: int, rule: str) -> None:
        if amount > self.free_qubits:
            raise ValueError(
                f"insufficient free physical qubits for {rule}: need {amount}, "
                f"have {self.free_qubits} on {self.backend.name}"
            )
