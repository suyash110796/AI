from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from omega_runtime.core.proof_bundle import verify_proof_bundle


def _usage() -> str:
    return "usage: python scripts/verify_proof_bundle.py <proof-bundle.json> [--json]"


def _read_bundle_hash(bundle_path: str | Path) -> str | None:
    try:
        data = json.loads(Path(bundle_path).read_text(encoding="utf-8"))
    except Exception:
        return None

    bundle_hash = data.get("bundle_hash")
    if isinstance(bundle_hash, str) and bundle_hash:
        return bundle_hash

    return None


def _emit_json(
    *,
    accepted: bool,
    reason: str,
    path: str | None = None,
    bundle_hash: str | None = None,
) -> None:
    payload = {
        "accepted": accepted,
        "verified": accepted,
        "ok": accepted,
        "reason": reason,
        "bundle_hash": bundle_hash,
    }

    if path is not None:
        payload["path"] = path

    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    json_output = False
    if "--json" in args:
        json_output = True
        args.remove("--json")

    if len(args) != 1:
        reason = _usage()
        if json_output:
            _emit_json(
                accepted=False,
                reason=reason,
                bundle_hash=None,
            )
        else:
            print(reason)
        return 2

    bundle_path = args[0]
    verified, reason = verify_proof_bundle(bundle_path)
    bundle_hash = _read_bundle_hash(bundle_path)

    if json_output:
        _emit_json(
            accepted=verified,
            reason=reason,
            path=str(bundle_path),
            bundle_hash=bundle_hash,
        )
    else:
        print(reason)

    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
