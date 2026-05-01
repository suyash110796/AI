from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.final_verifier_report import verify_final_verifier_report_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify an Omega final verifier report."
    )
    parser.add_argument("path", help="Path to final verifier report JSON")
    parser.add_argument("--json", action="store_true", help="Emit machine JSON")
    args = parser.parse_args()

    payload = verify_final_verifier_report_json(args.path)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        verdict = "ACCEPT" if payload["accepted"] else "REJECT"
        print(f"FINAL REPORT VERIFIER: {verdict}")
        print(f"REASON: {payload['reason']}")
        print(f"REPORT HASH: {payload.get('report_hash')}")

    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
