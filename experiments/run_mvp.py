from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cipr.checker import Checker
from cipr.ir import Effect, FTStep, LogicalOp, QType
from cipr.planner import Compiler, CompileResult
from cipr.rules import RuleLibrary


OUT_DIR = Path(__file__).resolve().parent / "outputs"


def qec_kernel() -> list[LogicalOp]:
    """A compact logical program with ordinary circuit and QEC features.

    SurfaceD5 intentionally does not support transversal/native CNOT, T, or CCZ
    in the rule library. The compiler therefore has to acquire these
    capabilities through resource or switching rules.
    """

    return [
        LogicalOp.prepare("q0", "+"),
        LogicalOp.prepare("q1", "0"),
        LogicalOp.prepare("q2", "0"),
        LogicalOp.prepare("r", "0"),
        LogicalOp.ec("q0", "q1", "q2", "r", decoder="surface_mwpm"),
        LogicalOp.apply("H", "q0"),
        LogicalOp.barrier("dense_acquisition_region"),
        LogicalOp.apply("CNOT", "q0", "q1"),
        LogicalOp.apply("T", "q1"),
        LogicalOp.apply("CNOT", "q1", "q2"),
        LogicalOp.apply("T", "q2"),
        LogicalOp.ec("q0", "q1", "q2", decoder="surface_mwpm"),
        LogicalOp.barrier("isolated_resource_gate"),
        LogicalOp.apply("CCZ", "q0", "q1", "q2"),
        LogicalOp.apply("T", "r"),
        LogicalOp.measure("m0", "X", "q0"),
        LogicalOp.branch("m0", then_ops=[LogicalOp.apply("S", "q2")]),
        LogicalOp.measure("out", "Z", "q2"),
    ]


def summarize(result: CompileResult, valid: bool, warnings: list[str], strict_valid: bool) -> dict[str, object]:
    effect = result.effect
    return {
        "strategy": result.strategy,
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
        "three_qubit_gates": effect.three_qubit_gates,
        "decoder_latency": effect.decoder_latency,
        "cert_count": len(set(effect.certs)),
        "assumption_count": len(set(effect.assumptions)),
        "warnings": warnings,
    }


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def print_table(rows: list[dict[str, object]]) -> None:
    headers = [
        "strategy",
        "valid",
        "strict",
        "err",
        "accept",
        "cycles",
        "qr",
        "switch",
        "factory",
        "2q",
        "assume",
    ]
    print(
        f"{headers[0]:<14} {headers[1]:<5} {headers[2]:<6} "
        f"{headers[3]:<11} {headers[4]:<10} {headers[5]:<6} "
        f"{headers[6]:<7} {headers[7]:<6} {headers[8]:<7} {headers[9]:<7} {headers[10]:<6}"
    )
    for row in rows:
        print(
            f"{str(row['strategy']):<14} {str(row['valid']):<5} "
            f"{str(row['strict_without_assumptions']):<6} "
            f"{row['err_bound']:<11.3g} {row['accept_lower_bound']:<10.3g} "
            f"{row['cycles']:<6} {row['qubit_rounds']:<7} "
            f"{row['switch_count']:<6} {row['factory_count']:<7} "
            f"{row['two_qubit_gates']:<7} "
            f"{row['assumption_count']:<6}"
        )


def run_negative_tests(checker: Checker) -> list[dict[str, object]]:
    direct_bad = CompileResult(
        strategy="invalid_direct_cnot",
        source_program=[LogicalOp.apply("CNOT", "q0", "q1")],
        final_env={
            "q0": QType("SurfaceD5", 5),
            "q1": QType("SurfaceD5", 5),
        },
        effect=Effect(),
        steps=[
            FTStep(
                op="apply",
                rule="BadDirectCNOT_SurfaceD5",
                qubits=("q0", "q1"),
                input_codes={"q0": "SurfaceD5", "q1": "SurfaceD5"},
                output_codes={"q0": "SurfaceD5", "q1": "SurfaceD5"},
                effect=Effect(),
                cert_level="Checked",
                details={"gate": "CNOT"},
            )
        ],
    )

    duplicate_resource = CompileResult(
        strategy="invalid_duplicate_resource",
        source_program=[LogicalOp.apply("T", "q0"), LogicalOp.apply("T", "q1")],
        final_env={
            "q0": QType("SurfaceD5", 5),
            "q1": QType("SurfaceD5", 5),
        },
        effect=Effect(),
        steps=[
            FTStep(
                op="prepare_resource",
                rule="FakeTFactory",
                qubits=(),
                input_codes={},
                output_codes={},
                effect=Effect(factory_count=1),
                cert_level="Checked",
                details={"produces": "res_t_shared"},
            ),
            FTStep(
                op="consume_resource_gate",
                rule="FakeInjectT",
                qubits=("q0",),
                input_codes={"q0": "SurfaceD5"},
                output_codes={"q0": "SurfaceD5"},
                effect=Effect(),
                cert_level="Checked",
                details={"gate": "T", "consumes": "res_t_shared"},
            ),
            FTStep(
                op="consume_resource_gate",
                rule="FakeInjectT",
                qubits=("q1",),
                input_codes={"q1": "SurfaceD5"},
                output_codes={"q1": "SurfaceD5"},
                effect=Effect(),
                cert_level="Checked",
                details={"gate": "T", "consumes": "res_t_shared"},
            ),
        ],
    )

    cases = [direct_bad, duplicate_resource]
    results: list[dict[str, object]] = []
    for case in cases:
        report = checker.validate(case, allow_assumed=True)
        results.append(
            {
                "name": case.strategy,
                "expected_ok": False,
                "actual_ok": report.ok,
                "errors": report.errors,
                "warnings": report.warnings,
            }
        )
    return results


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rules = RuleLibrary()
    compiler = Compiler(rules=rules)
    checker = Checker(rules=rules)
    program = qec_kernel()

    runs: list[tuple[str, int]] = [
        ("magic_only", 0),
        ("switch_only", 0),
        ("hybrid", 0),
        ("best", 0),
        ("random", 7),
        ("random", 17),
    ]

    summaries: list[dict[str, object]] = []
    for strategy, seed in runs:
        result = compiler.compile(program, strategy=strategy, seed=seed, allow_assumed=True)
        report = checker.validate(result, allow_assumed=True)
        strict_report = checker.validate(result, allow_assumed=False)
        name = f"{strategy}_seed{seed}" if strategy == "random" else strategy
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

    negative_results = run_negative_tests(checker)
    write_json(OUT_DIR / "negative_tests.json", negative_results)
    write_json(OUT_DIR / "case_study_summary.json", summaries)
    print_table(summaries)
    print("\nnegative tests")
    for item in negative_results:
        print(f"{item['name']}: actual_ok={item['actual_ok']} errors={len(item['errors'])}")
    print(f"\nWrote {len(summaries)} detailed plans to {OUT_DIR}")


if __name__ == "__main__":
    main()
