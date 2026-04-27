from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Mode = Literal["State", "Observable"]
CertLevel = Literal["Checked", "Certified", "Assumed"]


@dataclass(frozen=True)
class QType:
    code: str
    distance: int
    mode: Mode = "State"

    def to_json(self) -> dict[str, Any]:
        return {"code": self.code, "distance": self.distance, "mode": self.mode}


@dataclass
class Effect:
    err: float = 0.0
    fail: float = 0.0
    accept: float = 1.0
    qubits_peak: int = 0
    cycles: int = 0
    qubit_rounds: int = 0
    switch_count: int = 0
    factory_count: int = 0
    measurements: int = 0
    resets: int = 0
    two_qubit_gates: int = 0
    three_qubit_gates: int = 0
    decoder_latency: int = 0
    certs: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    rules: list[str] = field(default_factory=list)

    def seq(self, other: Effect) -> Effect:
        return Effect(
            err=self.err + other.err,
            fail=min(1.0, self.fail + other.fail),
            accept=self.accept * other.accept,
            qubits_peak=max(self.qubits_peak, other.qubits_peak),
            cycles=self.cycles + other.cycles,
            qubit_rounds=self.qubit_rounds + other.qubit_rounds,
            switch_count=self.switch_count + other.switch_count,
            factory_count=self.factory_count + other.factory_count,
            measurements=self.measurements + other.measurements,
            resets=self.resets + other.resets,
            two_qubit_gates=self.two_qubit_gates + other.two_qubit_gates,
            three_qubit_gates=self.three_qubit_gates + other.three_qubit_gates,
            decoder_latency=self.decoder_latency + other.decoder_latency,
            certs=dedup(self.certs + other.certs),
            assumptions=dedup(self.assumptions + other.assumptions),
            rules=self.rules + other.rules,
        )

    def branch(self, other: Effect) -> Effect:
        return Effect(
            err=max(self.err, other.err),
            fail=max(self.fail, other.fail),
            accept=min(self.accept, other.accept),
            qubits_peak=max(self.qubits_peak, other.qubits_peak),
            cycles=max(self.cycles, other.cycles),
            qubit_rounds=max(self.qubit_rounds, other.qubit_rounds),
            switch_count=max(self.switch_count, other.switch_count),
            factory_count=max(self.factory_count, other.factory_count),
            measurements=max(self.measurements, other.measurements),
            resets=max(self.resets, other.resets),
            two_qubit_gates=max(self.two_qubit_gates, other.two_qubit_gates),
            three_qubit_gates=max(self.three_qubit_gates, other.three_qubit_gates),
            decoder_latency=max(self.decoder_latency, other.decoder_latency),
            certs=dedup(self.certs + other.certs),
            assumptions=dedup(self.assumptions + other.assumptions),
            rules=dedup(self.rules + other.rules),
        )

    def scaled_for_qubits(self, n: int, keep_switch_count: bool = True) -> Effect:
        switch_count = self.switch_count if keep_switch_count else self.switch_count * n
        return Effect(
            err=self.err * n,
            fail=min(1.0, self.fail * n),
            accept=self.accept**n,
            qubits_peak=self.qubits_peak * n,
            cycles=self.cycles,
            qubit_rounds=self.qubit_rounds * n,
            switch_count=switch_count,
            factory_count=self.factory_count * n,
            measurements=self.measurements * n,
            resets=self.resets * n,
            two_qubit_gates=self.two_qubit_gates * n,
            three_qubit_gates=self.three_qubit_gates * n,
            decoder_latency=self.decoder_latency,
            certs=list(self.certs),
            assumptions=list(self.assumptions),
            rules=list(self.rules),
        )

    def with_rule(self, rule_name: str, cert: str | None = None) -> Effect:
        out = self.copy()
        out.rules.append(rule_name)
        if cert:
            out.certs.append(cert)
        return out

    def copy(self) -> Effect:
        return Effect(
            err=self.err,
            fail=self.fail,
            accept=self.accept,
            qubits_peak=self.qubits_peak,
            cycles=self.cycles,
            qubit_rounds=self.qubit_rounds,
            switch_count=self.switch_count,
            factory_count=self.factory_count,
            measurements=self.measurements,
            resets=self.resets,
            two_qubit_gates=self.two_qubit_gates,
            three_qubit_gates=self.three_qubit_gates,
            decoder_latency=self.decoder_latency,
            certs=list(self.certs),
            assumptions=list(self.assumptions),
            rules=list(self.rules),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "err": self.err,
            "fail": self.fail,
            "accept": self.accept,
            "qubits_peak": self.qubits_peak,
            "cycles": self.cycles,
            "qubit_rounds": self.qubit_rounds,
            "switch_count": self.switch_count,
            "factory_count": self.factory_count,
            "measurements": self.measurements,
            "resets": self.resets,
            "two_qubit_gates": self.two_qubit_gates,
            "three_qubit_gates": self.three_qubit_gates,
            "decoder_latency": self.decoder_latency,
            "certs": dedup(self.certs),
            "assumptions": dedup(self.assumptions),
            "rules": self.rules,
        }


@dataclass(frozen=True)
class LogicalOp:
    kind: str
    qubits: tuple[str, ...] = ()
    gate: str | None = None
    state: str | None = None
    observable: str | None = None
    target: str | None = None
    decoder: str | None = None
    label: str | None = None
    then_ops: tuple[LogicalOp, ...] = ()
    else_ops: tuple[LogicalOp, ...] = ()

    @staticmethod
    def prepare(q: str, state: str = "0") -> LogicalOp:
        return LogicalOp(kind="prepare", qubits=(q,), state=state)

    @staticmethod
    def apply(gate: str, *qubits: str) -> LogicalOp:
        return LogicalOp(kind="gate", gate=gate, qubits=tuple(qubits))

    @staticmethod
    def ec(*qubits: str, decoder: str = "default") -> LogicalOp:
        return LogicalOp(kind="ec", qubits=tuple(qubits), decoder=decoder)

    @staticmethod
    def measure(target: str, observable: str, *qubits: str) -> LogicalOp:
        return LogicalOp(kind="measure", target=target, observable=observable, qubits=tuple(qubits))

    @staticmethod
    def branch(bit: str, then_ops: list[LogicalOp], else_ops: list[LogicalOp] | None = None) -> LogicalOp:
        return LogicalOp(
            kind="if",
            target=bit,
            then_ops=tuple(then_ops),
            else_ops=tuple(else_ops or []),
        )

    @staticmethod
    def barrier(label: str) -> LogicalOp:
        return LogicalOp(kind="barrier", label=label)

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind}
        if self.qubits:
            out["qubits"] = list(self.qubits)
        if self.gate:
            out["gate"] = self.gate
        if self.state:
            out["state"] = self.state
        if self.observable:
            out["observable"] = self.observable
        if self.target:
            out["target"] = self.target
        if self.decoder:
            out["decoder"] = self.decoder
        if self.label:
            out["label"] = self.label
        if self.then_ops:
            out["then_ops"] = [op.to_json() for op in self.then_ops]
        if self.else_ops:
            out["else_ops"] = [op.to_json() for op in self.else_ops]
        return out


@dataclass
class FTStep:
    op: str
    rule: str
    qubits: tuple[str, ...]
    input_codes: dict[str, str]
    output_codes: dict[str, str]
    effect: Effect
    cert_level: CertLevel
    details: dict[str, Any] = field(default_factory=dict)
    children: list[FTStep] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        out = {
            "op": self.op,
            "rule": self.rule,
            "qubits": list(self.qubits),
            "input_codes": self.input_codes,
            "output_codes": self.output_codes,
            "effect": self.effect.to_json(),
            "cert_level": self.cert_level,
            "details": self.details,
        }
        if self.children:
            out["children"] = [child.to_json() for child in self.children]
        return out


def dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
