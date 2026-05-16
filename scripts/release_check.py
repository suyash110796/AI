from __future__ import annotations

import argparse
import json
from pathlib import Path

from omega_runtime.release_check import run_release_check, write_release_report

def main() -> int:
    parser = argparse.ArgumentParser(description="Run OMEGA release hardening checks.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    parser.add_argument(
        "--out",
        default="artifacts/release/release_check_report.json",
        help="Where to write the release check report.",
    )
    args = parser.parse_args()

    report = write_release_report(Path(args.out))

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        verdict = "ACCEPTED" if report["accepted"] else "REJECTED"
        print(f"RELEASE CHECK: {verdict}")
        print(f"REASON: {report['reason']}")
        print(f"VERSION: {report['release_version']}")
        print(f"CHECKS: {report['checks_passed']}/{report['checks_total']} passed")
        print(f"AGGREGATE HASH: {report['aggregate_hash']}")
        print(f"REPORT: {report['report_path']}")

    return 0 if report["accepted"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
