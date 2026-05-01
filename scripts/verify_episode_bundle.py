from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omega_runtime.core.episode_bundle import verify_episode_bundle_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an Omega episode bundle.")
    parser.add_argument("path", help="Path to episode bundle JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    payload = verify_episode_bundle_json(args.path)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"accepted: {payload['accepted']}")
        print(f"reason: {payload['reason']}")
        print(f"bundle_hash: {payload.get('bundle_hash')}")

    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
