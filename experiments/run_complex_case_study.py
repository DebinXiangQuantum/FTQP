from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cipr.checker import Checker
from cipr.ir import LogicalOp
from cipr.planner import Compiler, CompileResult
from cipr.rules import RuleLibrary


OUT_DIR = Path(__file__).resolve().parent / "outputs"


def phase_oracle_with_branch() -> list[LogicalOp]:
    """A denser logical workload for acquisition planning.

    The first non-Clifford region contains only CNOT/T gates, so the hybrid
    strategy can switch the involved qubits once into Tetra15, execute the
    region, and switch them back. Later branch and CCZ operations force the
    planner to combine resource acquisition, classical control, and direct
    Clifford corrections in the same program.
    """

    return [
        LogicalOp.prepare("q0", "+"),
        LogicalOp.prepare("q1", "+"),
        LogicalOp.prepare("q2", "0"),
        LogicalOp.prepare("q3", "0"),
        LogicalOp.prepare("q4", "0"),
        LogicalOp.prepare("anc", "0"),
        LogicalOp.prepare("flag", "0"),
        LogicalOp.ec("q0", "q1", "q2", "q3", "q4", "anc", "flag", decoder="surface_mwpm"),
        LogicalOp.apply("H", "q0"),
        LogicalOp.apply("H", "q1"),
        LogicalOp.barrier("phase_gradient_dense_region"),
        LogicalOp.apply("CNOT", "q0", "q2"),
        LogicalOp.apply("T", "q2"),
        LogicalOp.apply("CNOT", "q1", "q3"),
        LogicalOp.apply("T", "q3"),
        LogicalOp.apply("CNOT", "q2", "q4"),
        LogicalOp.apply("T", "q4"),
        LogicalOp.apply("CNOT", "q3", "anc"),
        LogicalOp.apply("T", "anc"),
        LogicalOp.ec("q0", "q1", "q2", "q3", "q4", "anc", decoder="surface_mwpm"),
        LogicalOp.measure("syndrome0", "X", "q0"),
        LogicalOp.branch(
            "syndrome0",
            then_ops=[
                LogicalOp.apply("T", "q1"),
                LogicalOp.apply("S", "q3"),
            ],
            else_ops=[
                LogicalOp.apply("S", "q1"),
                LogicalOp.apply("S", "q3"),
            ],
        ),
        LogicalOp.barrier("ccz_oracle_and_flag_cleanup"),
        LogicalOp.apply("CCZ", "q0", "q2", "q4"),
        LogicalOp.apply("CNOT", "flag", "anc"),
        LogicalOp.apply("T", "flag"),
        LogicalOp.measure("flag_out", "Z", "flag"),
        LogicalOp.branch(
            "flag_out",
            then_ops=[LogicalOp.apply("S", "anc")],
            else_ops=[LogicalOp.apply("H", "anc")],
        ),
        LogicalOp.measure("out0", "Z", "q4"),
        LogicalOp.measure("out1", "X", "anc"),
    ]


def summarize(result: CompileResult, valid: bool, warnings: list[str], strict_valid: bool) -> dict[str, object]:
    effect = result.effect
    assumption_count = len(set(effect.assumptions))
    return {
        "strategy": result.strategy,
        "backend": result.backend.name,
        "topology": result.backend.topology,
        "valid": valid,
        "strict_without_assumptions": strict_valid,
        "err_bound": effect.err,
        "accept_lower_bound": effect.accept,
        "fail_upper_bound": effect.fail,
        "cycles": effect.cycles,
        "qubit_rounds": effect.qubit_rounds,
        "qubits_peak": effect.qubits_peak,
        "switch_count": effect.switch_count,
        "factory_count": effect.factory_count,
        "measurements": effect.measurements,
        "two_qubit_gates": effect.two_qubit_gates,
        "decoder_latency": effect.decoder_latency,
        "physical_qubits_used": result.final_layout.used_qubits,
        "physical_qubits_free": result.final_layout.free_qubits,
        "cert_count": len(set(effect.certs)),
        "assumption_count": assumption_count,
        "warnings": warnings,
    }


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def print_table(rows: list[dict[str, object]]) -> None:
    print(
        f"{'strategy':<24} {'valid':<5} {'strict':<6} {'err':<11} "
        f"{'accept':<10} {'cycles':<6} {'qr':<7} {'switch':<6} "
        f"{'factory':<7} {'2q':<7} {'assume':<6}"
    )
    for row in rows:
        print(
            f"{str(row['strategy']):<24} {str(row['valid']):<5} "
            f"{str(row['strict_without_assumptions']):<6} "
            f"{row['err_bound']:<11.3g} {row['accept_lower_bound']:<10.3g} "
            f"{row['cycles']:<6} {row['qubit_rounds']:<7} "
            f"{row['switch_count']:<6} {row['factory_count']:<7} "
            f"{row['two_qubit_gates']:<7} {row['assumption_count']:<6}"
        )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rules = RuleLibrary()
    compiler = Compiler(rules=rules)
    checker = Checker(rules=rules)
    program = phase_oracle_with_branch()

    runs: list[tuple[str, int]] = [
        ("magic_only", 0),
        ("switch_only", 0),
        ("hybrid", 0),
        ("best", 0),
        ("random", 23),
    ]

    summaries: list[dict[str, object]] = []
    for strategy, seed in runs:
        result = compiler.compile(program, strategy=strategy, seed=seed, allow_assumed=True)
        report = checker.validate(result, allow_assumed=True)
        strict_report = checker.validate(result, allow_assumed=False)
        name = f"complex_{strategy}_seed{seed}" if strategy == "random" else f"complex_{strategy}"
        write_json(
            OUT_DIR / f"case_study_{name}.json",
            {
                "compile_result": result.to_json(),
                "check_report": report.to_json(),
                "strict_check_report": strict_report.to_json(),
            },
        )
        summaries.append(
            summarize(
                result,
                valid=report.ok,
                warnings=report.warnings,
                strict_valid=strict_report.ok,
            )
            | {"strategy": name}
        )

    write_json(OUT_DIR / "complex_case_study_summary.json", summaries)
    print_table(summaries)
    print(f"\nWrote {len(summaries)} complex plans to {OUT_DIR}")


if __name__ == "__main__":
    main()
