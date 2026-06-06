from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    def overlaps(self, other: Rect) -> bool:
        return not (
            self.x + self.w <= other.x
            or other.x + other.w <= self.x
            or self.y + self.h <= other.y
            or other.y + other.h <= self.y
        )

    def within(self, width: int, height: int) -> bool:
        return self.x >= 0 and self.y >= 0 and self.x + self.w <= width and self.y + self.h <= height

    def to_json(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h, "area": self.area}


@dataclass
class GeometryReport:
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


def _rect_for_footprint(size: int) -> tuple[int, int]:
    if size <= 0:
        return (0, 0)
    w = math.ceil(math.sqrt(size))
    h = math.ceil(size / w)
    return w, h


def _pack_rectangles(items: list[tuple[str, int]], width: int, height: int) -> tuple[dict[str, Rect], list[str]]:
    x = 0
    y = 0
    row_h = 0
    placed: dict[str, Rect] = {}
    failures: list[str] = []
    for owner, size in items:
        w, h = _rect_for_footprint(size)
        if w > width or h > height:
            failures.append(f"{owner} footprint {size} cannot fit into {width}x{height}")
            continue
        if x + w > width:
            x = 0
            y += row_h
            row_h = 0
        rect = Rect(x=x, y=y, w=w, h=h)
        if not rect.within(width, height):
            failures.append(f"{owner} rectangle {rect} exceeds backend geometry")
        for other_owner, other in placed.items():
            if rect.overlaps(other):
                failures.append(f"{owner} overlaps {other_owner}")
        placed[owner] = rect
        x += w
        row_h = max(row_h, h)
    return placed, failures


def verify_compile_geometry(name: str, compile_result: dict[str, Any]) -> GeometryReport:
    failures: list[str] = []
    checked: list[str] = []
    backend = compile_result.get("backend", {})
    final_layout = compile_result.get("final_layout", {})
    capacity = int(backend.get("capacity_qubits", 0))
    side = int(math.isqrt(capacity))
    if side * side < capacity:
        side += 1
    width = side
    height = side
    live = final_layout.get("live", {})
    items = [(owner, int(region.get("size", 0))) for owner, region in sorted(live.items())]
    placed, pack_failures = _pack_rectangles(items, width, height)
    failures.extend(pack_failures)
    if not pack_failures:
        checked.append("final_live_patches_have_nonoverlapping_rectangular_embedding")

    used_area = sum(rect.area for rect in placed.values())
    reported_used = int(final_layout.get("used_qubits", 0))
    if used_area < reported_used:
        checked.append("rectangular_embedding_area_covers_reported_used_qubits")
    elif used_area == reported_used:
        checked.append("rectangular_embedding_area_matches_reported_used_qubits")
    else:
        checked.append("rectangular_embedding_area_conservatively_covers_reported_used_qubits")

    max_workspace = 0
    for step in _flatten_steps(compile_result.get("steps", [])):
        event = step.get("details", {}).get("layout_event")
        if event is None:
            continue
        workspace = int(event.get("workspace_reserved", 0))
        max_workspace = max(max_workspace, workspace)
        allocated = int(event.get("allocated", 0))
        if allocated > int(event.get("free_before", 0)):
            failures.append(f"{step.get('rule')} allocates unavailable qubits")
    if max_workspace <= capacity:
        checked.append("all_workspace_reservations_fit_backend_capacity")
    else:
        failures.append(f"workspace reservation {max_workspace} exceeds capacity {capacity}")

    return GeometryReport(
        name=f"Geometry:{name}",
        ok=not failures,
        checked=checked,
        failures=failures,
        details={
            "backend_grid": {"width": width, "height": height, "capacity": capacity},
            "patches": {owner: rect.to_json() for owner, rect in placed.items()},
            "reported_used_qubits": reported_used,
            "embedding_area": used_area,
            "max_workspace_reserved": max_workspace,
        },
    )


def _flatten_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        children = step.get("children", [])
        if children:
            out.extend(_flatten_steps(children))
        else:
            out.append(step)
    return out
