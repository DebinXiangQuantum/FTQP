from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

Z3_TARGET = Path("/tmp/ftqp_z3")
if Z3_TARGET.exists() and str(Z3_TARGET) not in sys.path:
    sys.path.insert(0, str(Z3_TARGET))

from cipr.theorem import verify_compile_result


OUT_DIR = Path(__file__).resolve().parent / "outputs"
SMT_DIR = OUT_DIR / "smt"


def main() -> None:
    reports = []
    for path in sorted(OUT_DIR.glob("case_study_*.json")):
        if path.name == "case_study_summary.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = verify_compile_result(path.stem, payload, SMT_DIR)
        reports.append(report.to_json())

    out_path = OUT_DIR / "verification_report.json"
    out_path.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")
    for report in reports:
        status = "ok" if report["ok"] else "failed"
        print(f"{report['name']}: {status} via {report['solver']} checks={len(report['checked'])}")
        for failure in report["failures"]:
            print(f"  - {failure}")
    print(f"\nWrote verification report to {out_path}")
    print(f"Wrote SMT-LIB obligations to {SMT_DIR}")


if __name__ == "__main__":
    main()
