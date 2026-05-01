from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.system_verifier import write_runtime_system_report, verify_runtime_system


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Omega runtime artifacts as one system-level report."
    )
    parser.add_argument(
        "--proof-bundle",
        action="append",
        default=[],
        help="Path to a proof bundle JSON file. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--trace",
        action="append",
        default=[],
        help="Path to a replay trace JSONL file. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional output path for the system verification report JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )

    args = parser.parse_args()

    if args.out:
        report = write_runtime_system_report(
            path=args.out,
            proof_bundles=args.proof_bundle,
            traces=args.trace,
        )
    else:
        report = verify_runtime_system(
            proof_bundles=args.proof_bundle,
            traces=args.trace,
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        verdict = "PASS" if report["accepted"] else "FAIL"
        print(f"SYSTEM VERIFIER: {verdict}")
        print(f"REASON: {report['reason']}")
        print(f"ARTIFACTS: {report['artifact_count']}")
        print(f"AGGREGATE HASH: {report['aggregate_hash']}")
        if args.out:
            print(f"REPORT: {args.out}")

    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
