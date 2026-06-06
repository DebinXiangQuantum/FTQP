from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cipr.formal_toolchain import FormalToolchain


OUT_DIR = Path(__file__).resolve().parent / "outputs"
SMT_DIR = OUT_DIR / "smt"


def _load_case_studies() -> list[tuple[str, dict[str, object]]]:
    cases = []
    for path in sorted(OUT_DIR.glob("case_study_*.json")):
        if path.name.endswith("_summary.json") or path.name == "case_study_summary.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "compile_result" in payload:
            cases.append((path.stem, payload))
    return cases


def main() -> None:
    toolchain = FormalToolchain(root=ROOT, out_dir=OUT_DIR, smt_dir=SMT_DIR)
    report = toolchain.run(run_lean=True).to_json()
    out_path = OUT_DIR / "full_stack_report.json"
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    ok = bool(report["ok"])
    status = "ok" if ok else "failed"
    print(f"full_stack: {status}")
    for key, value in report["summary"].items():
        print(f"  {key}: {value}")
    print(f"\nWrote full-stack report to {out_path}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
