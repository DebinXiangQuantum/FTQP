from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable


@dataclass(frozen=True)
class Pauli:
    x: tuple[int, ...]
    z: tuple[int, ...]
    name: str = ""

    @staticmethod
    def from_xz(name: str, n: int, xs: Iterable[int] = (), zs: Iterable[int] = ()) -> Pauli:
        x = [0] * n
        z = [0] * n
        for i in xs:
            x[i] ^= 1
        for i in zs:
            z[i] ^= 1
        return Pauli(tuple(x), tuple(z), name=name)

    @property
    def n(self) -> int:
        return len(self.x)

    @property
    def weight(self) -> int:
        return sum(1 for a, b in zip(self.x, self.z, strict=True) if a or b)

    def symplectic(self, other: Pauli) -> int:
        self._check_same_n(other)
        left = sum(a & b for a, b in zip(self.x, other.z, strict=True))
        right = sum(a & b for a, b in zip(self.z, other.x, strict=True))
        return (left + right) % 2

    def commutes(self, other: Pauli) -> bool:
        return self.symplectic(other) == 0

    def anticommutes(self, other: Pauli) -> bool:
        return self.symplectic(other) == 1

    def syndrome_against(self, checks: list[Pauli]) -> tuple[int, ...]:
        return tuple(self.symplectic(check) for check in checks)

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "n": self.n,
            "x_support": [i for i, bit in enumerate(self.x) if bit],
            "z_support": [i for i, bit in enumerate(self.z) if bit],
            "weight": self.weight,
        }

    def _check_same_n(self, other: Pauli) -> None:
        if self.n != other.n:
            raise ValueError(f"Paulis have different lengths: {self.n} != {other.n}")


@dataclass
class VerificationResult:
    name: str
    ok: bool
    checked: list[str]
    failures: list[str]
    details: dict[str, object]

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ok": self.ok,
            "checked": self.checked,
            "failures": self.failures,
            "details": self.details,
        }


@dataclass(frozen=True)
class GaugeSwitchSpec:
    name: str
    n: int
    subsystem_stabilizers: tuple[Pauli, ...]
    target_stabilizers: tuple[Pauli, ...]
    gauge_corrections: tuple[Pauli, ...]
    logical_x: Pauli
    logical_z: Pauli
    source: str
    target: str
    source_ref: str


def verify_gauge_switch(spec: GaugeSwitchSpec) -> VerificationResult:
    checked: list[str] = []
    failures: list[str] = []

    all_ops = (
        list(spec.subsystem_stabilizers)
        + list(spec.target_stabilizers)
        + list(spec.gauge_corrections)
        + [spec.logical_x, spec.logical_z]
    )
    for op in all_ops:
        if op.n != spec.n:
            failures.append(f"{op.name} has length {op.n}, expected {spec.n}")
    if not failures:
        checked.append("all_paulis_have_expected_length")

    if spec.logical_x.anticommutes(spec.logical_z):
        checked.append("logical_x_and_z_anticommute")
    else:
        failures.append("logical_x and logical_z must anticommute")

    for group_name, group in [
        ("subsystem_stabilizers", spec.subsystem_stabilizers),
        ("target_stabilizers", spec.target_stabilizers),
    ]:
        bad = _noncommuting_pairs(list(group))
        if bad:
            failures.extend(f"{group_name} noncommuting pair {a}/{b}" for a, b in bad)
        else:
            checked.append(f"{group_name}_commute")

    for op in list(spec.subsystem_stabilizers) + list(spec.target_stabilizers):
        if not op.commutes(spec.logical_x) or not op.commutes(spec.logical_z):
            failures.append(f"{op.name} does not preserve common logical operators")
    if not any("preserve common logical" in f for f in failures):
        checked.append("stabilizers_preserve_common_logicals")

    syndrome_rows: list[tuple[int, ...]] = []
    for corr in spec.gauge_corrections:
        if not corr.commutes(spec.logical_x) or not corr.commutes(spec.logical_z):
            failures.append(f"{corr.name} changes the encoded logical state")
        syndrome_rows.append(corr.syndrome_against(list(spec.target_stabilizers)))
    if not any("encoded logical" in f for f in failures):
        checked.append("gauge_corrections_preserve_logicals")

    rank = _gf2_rank(syndrome_rows)
    if rank == len(spec.target_stabilizers):
        checked.append("gauge_corrections_span_target_syndromes")
    else:
        failures.append(
            f"gauge corrections span rank {rank}, expected {len(spec.target_stabilizers)}"
        )

    return VerificationResult(
        name=spec.name,
        ok=not failures,
        checked=checked,
        failures=failures,
        details={
            "source": spec.source,
            "target": spec.target,
            "source_ref": spec.source_ref,
            "logical_x": spec.logical_x.to_json(),
            "logical_z": spec.logical_z.to_json(),
            "target_stabilizers": [op.to_json() for op in spec.target_stabilizers],
            "gauge_corrections": [op.to_json() for op in spec.gauge_corrections],
            "correction_syndrome_matrix": [list(row) for row in syndrome_rows],
        },
    )


@dataclass(frozen=True)
class MagicDistillationSpec:
    name: str
    n_inputs: int
    checks: tuple[Pauli, ...]
    logical_error: Pauli
    detect_up_to_weight: int
    source_ref: str


def verify_magic_distillation_skeleton(spec: MagicDistillationSpec) -> VerificationResult:
    checked: list[str] = []
    failures: list[str] = []
    if spec.logical_error.n != spec.n_inputs:
        failures.append("logical error length does not match input count")

    bad_checks = _noncommuting_pairs(list(spec.checks))
    if bad_checks:
        failures.extend(f"noncommuting distillation checks {a}/{b}" for a, b in bad_checks)
    else:
        checked.append("distillation_checks_commute")

    undetected: list[dict[str, object]] = []
    indices = range(spec.n_inputs)
    for weight in range(1, spec.detect_up_to_weight + 1):
        for support in combinations(indices, weight):
            err = Pauli.from_xz(f"Z_error_{support}", spec.n_inputs, zs=support)
            syndrome = err.syndrome_against(list(spec.checks))
            if any(syndrome):
                continue
            if err.anticommutes(spec.logical_error):
                undetected.append({"support": list(support), "syndrome": list(syndrome)})

    if undetected:
        failures.append(
            f"{len(undetected)} accepted low-weight errors can flip the declared logical output"
        )
    else:
        checked.append(f"no_accepted_logical_errors_up_to_weight_{spec.detect_up_to_weight}")

    return VerificationResult(
        name=spec.name,
        ok=not failures,
        checked=checked,
        failures=failures,
        details={
            "n_inputs": spec.n_inputs,
            "source_ref": spec.source_ref,
            "checks": [check.to_json() for check in spec.checks],
            "logical_error": spec.logical_error.to_json(),
            "detect_up_to_weight": spec.detect_up_to_weight,
            "undetected_logical_errors": undetected[:20],
        },
    )


def _noncommuting_pairs(ops: list[Pauli]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for a, b in combinations(ops, 2):
        if not a.commutes(b):
            out.append((a.name, b.name))
    return out


def _gf2_rank(rows: list[tuple[int, ...]]) -> int:
    if not rows:
        return 0
    matrix = [list(row) for row in rows]
    rank = 0
    col_count = len(matrix[0])
    for col in range(col_count):
        pivot = None
        for r in range(rank, len(matrix)):
            if matrix[r][col]:
                pivot = r
                break
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        for r in range(len(matrix)):
            if r != rank and matrix[r][col]:
                matrix[r] = [a ^ b for a, b in zip(matrix[r], matrix[rank], strict=True)]
        rank += 1
    return rank
