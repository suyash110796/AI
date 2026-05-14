from __future__ import annotations

import argparse
import json
from pathlib import Path

from omega_runtime.failure_lab import run_failure_lab


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OMEGA failure demonstration lab.")
    parser.add_argument(
        "--out-dir",
        default="artifacts/failure_lab",
        help="Directory where failure lab artifacts and report will be written.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    args = parser.parse_args()

    report = run_failure_lab(Path(args.out_dir))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        print(f"FAILURE LAB ACCEPTED: {report['accepted']}")
        print(f"REASON: {report['reason']}")
        print(f"SCENARIOS: {report['scenarios_passed']}/{report['scenario_count']} passed")
        print(f"REPORT: {report['report_path']}")
        print()
        for scenario in report["scenarios"]:
            verdict = "PASS" if scenario["passed"] else "FAIL"
            actual = "ACCEPT" if scenario["actual_accept"] else "REJECT"
            expected = "ACCEPT" if scenario["expected_accept"] else "REJECT"
            print(f"[{verdict}] {scenario['name']}: actual={actual}, expected={expected}")
            print(f"       reason={scenario['reason']}")

    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
