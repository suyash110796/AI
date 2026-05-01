from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return str(value)


def _print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))
        return

    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, indent=2, sort_keys=True, default=_json_default)}")
        else:
            print(f"{key}: {value}")


def _tuple_verdict_to_payload(result: Any, valid_reason: str = "valid") -> dict[str, Any]:
    if isinstance(result, tuple) and len(result) >= 2:
        accepted = bool(result[0])
        reason = str(result[1])
        return {
            "accepted": accepted,
            "reason": reason,
        }

    if isinstance(result, dict):
        if "accepted" not in result:
            if "passed" in result:
                result["accepted"] = bool(result["passed"])
            elif "valid" in result:
                result["accepted"] = bool(result["valid"])
        if "reason" not in result:
            result["reason"] = valid_reason if result.get("accepted") else "verification failed"
        return result

    if hasattr(result, "passed"):
        return {
            "accepted": bool(getattr(result, "passed")),
            "passed": bool(getattr(result, "passed")),
            "reason": str(getattr(result, "reason", valid_reason)),
            "entries_checked": getattr(result, "entries_checked", None),
            "final_entry_hash": getattr(result, "final_entry_hash", None),
            "violations": getattr(result, "violations", []),
        }

    return {
        "accepted": False,
        "reason": f"unsupported verifier result type: {type(result).__name__}",
        "raw": str(result),
    }


def verify_proof_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omega-verify-proof",
        description="Verify an OMEGA proof bundle."
    )
    parser.add_argument("path", help="Path to proof bundle JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    from omega_runtime.core.proof_bundle import verify_proof_bundle

    payload = _tuple_verdict_to_payload(verify_proof_bundle(Path(args.path)), "proof bundle valid")
    payload.setdefault("artifact_type", "proof_bundle")
    payload.setdefault("path", str(Path(args.path)))

    _print_payload(payload, args.json)
    return 0 if payload["accepted"] else 1


def verify_trace_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omega-verify-trace",
        description="Verify an OMEGA replay trace."
    )
    parser.add_argument("path", help="Path to replay trace JSONL file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    from omega_runtime.core.replay_verifier import verify_replay_trace

    payload = _tuple_verdict_to_payload(verify_replay_trace(Path(args.path)), "offline replay verification passed")
    payload.setdefault("artifact_type", "trace")
    payload.setdefault("path", str(Path(args.path)))

    _print_payload(payload, args.json)
    return 0 if payload["accepted"] else 1


def verify_episode_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omega-verify-episode",
        description="Verify an OMEGA episode bundle."
    )
    parser.add_argument("path", help="Path to episode bundle JSON file.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    from omega_runtime.core.episode_bundle import verify_episode_bundle_json

    payload = verify_episode_bundle_json(Path(args.path))
    payload.setdefault("artifact_type", "episode_bundle")
    payload.setdefault("path", str(Path(args.path)))

    _print_payload(payload, args.json)
    return 0 if payload["accepted"] else 1


def system_verify_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="omega-system-verify",
        description="Verify proof bundles and traces as one runtime system."
    )
    parser.add_argument("--proof-bundle", action="append", default=[], help="Proof bundle path. Can be repeated.")
    parser.add_argument("--trace", action="append", default=[], help="Replay trace path. Can be repeated.")
    parser.add_argument("--out", help="Optional output JSON report path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    from omega_runtime.core.system_verifier import verify_runtime_system

    payload = verify_runtime_system(
        proof_bundles=args.proof_bundle,
        traces=args.trace,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )

    _print_payload(payload, args.json)
    return 0 if payload["accepted"] else 1


def audit_main(argv: list[str] | None = None) -> int:
    """
    CLI compatibility wrapper.

    The canonical auditor already exists as scripts/audit_runtime.py and is
    covered by tests. This entry point delegates to that script when running
    from the project root, preserving exact existing behavior.
    """
    script = Path("scripts/audit_runtime.py")

    if script.exists():
        completed = subprocess.run(
            [sys.executable, str(script), *(argv if argv is not None else sys.argv[1:])],
            text=True,
        )
        return int(completed.returncode)

    parser = argparse.ArgumentParser(
        prog="omega-audit",
        description="Run the OMEGA runtime auditor."
    )
    parser.add_argument("--proof-bundle", action="append", default=[])
    parser.add_argument("--trace", action="append", default=[])
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from omega_runtime.core.system_verifier import verify_runtime_system

    payload = verify_runtime_system(
        proof_bundles=args.proof_bundle,
        traces=args.trace,
    )
    payload["audit_type"] = "OMEGA_AUDITOR_V1"
    payload["auditor_version"] = "OMEGA_AUDITOR_V1"
    if payload.get("accepted"):
        payload["reason"] = "runtime audit passed"

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
            encoding="utf-8",
        )

    _print_payload(payload, args.json)
    return 0 if payload["accepted"] else 1


__all__ = [
    "verify_proof_main",
    "verify_trace_main",
    "verify_episode_main",
    "audit_main",
    "system_verify_main",
]
