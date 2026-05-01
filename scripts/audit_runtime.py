from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# IMPORTANT:
# When this file is executed as:
#   python scripts/audit_runtime.py
# Python puts scripts/ on sys.path, not the project root.
# Add the project root explicitly so omega_runtime imports work.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


AUDITOR_VERSION = "OMEGA_AUDITOR_V1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if hasattr(value, "__dict__"):
        return {str(k): _plain(v) for k, v in vars(value).items()}
    return value


def _normalize_verifier_result(raw: Any) -> tuple[bool, str, dict[str, Any]]:
    raw_plain = _plain(raw)

    if isinstance(raw, tuple):
        if len(raw) >= 2 and isinstance(raw[0], bool):
            return raw[0], str(raw[1]), {"raw": raw_plain}
        return False, "malformed verifier tuple", {"raw": raw_plain}

    if isinstance(raw_plain, dict):
        if "accepted" in raw_plain:
            accepted = bool(raw_plain["accepted"])
            reason = str(raw_plain.get("reason", "accepted" if accepted else "rejected"))
            return accepted, reason, raw_plain

        if "passed" in raw_plain:
            accepted = bool(raw_plain["passed"])
            reason = str(raw_plain.get("reason", "accepted" if accepted else "rejected"))
            return accepted, reason, raw_plain

        if "ok" in raw_plain:
            accepted = bool(raw_plain["ok"])
            reason = str(raw_plain.get("reason", "accepted" if accepted else "rejected"))
            return accepted, reason, raw_plain

    if isinstance(raw, bool):
        return raw, "accepted" if raw else "rejected", {"raw": raw_plain}

    return False, "malformed verifier result", {"raw": raw_plain}


def _candidate_functions(module: Any, preferred_names: list[str]) -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    seen: set[str] = set()

    for name in preferred_names:
        fn = getattr(module, name, None)
        if callable(fn):
            found.append((name, fn))
            seen.add(name)

    for name, fn in inspect.getmembers(module, inspect.isfunction):
        lowered = name.lower()
        if name in seen:
            continue
        if "verify" in lowered and not lowered.startswith("_"):
            found.append((name, fn))
            seen.add(name)

    return found


def _try_verify(
    *,
    module_name: str,
    preferred_names: list[str],
    path: Path,
) -> tuple[bool, str, dict[str, Any]]:
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        return False, f"verifier module import failed: {exc}", {
            "module": module_name,
            "error": repr(exc),
        }

    candidates = _candidate_functions(module, preferred_names)

    if not candidates:
        return False, "verifier not found", {
            "module": module_name,
            "candidate_names": preferred_names,
        }

    errors: list[dict[str, str]] = []

    for name, fn in candidates:
        try:
            raw = fn(path)
        except TypeError:
            try:
                raw = fn(str(path))
            except Exception as exc:
                errors.append({"function": name, "error": repr(exc)})
                continue
        except Exception as exc:
            errors.append({"function": name, "error": repr(exc)})
            continue

        accepted, reason, detail = _normalize_verifier_result(raw)
        detail.setdefault("verifier_function", name)
        detail.setdefault("verifier_module", module_name)
        return accepted, reason, detail

    return False, "no compatible verifier function accepted this artifact", {
        "module": module_name,
        "candidate_names": preferred_names,
        "errors": errors,
    }


def _audit_one(path: Path, artifact_type: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "artifact_type": artifact_type,
            "path": str(path),
            "artifact_hash": None,
            "accepted": False,
            "reason": "artifact not found",
            "detail": {},
        }

    artifact_hash = _file_hash(path)

    if artifact_type == "proof_bundle":
        accepted, reason, detail = _try_verify(
            module_name="omega_runtime.core.proof_bundle",
            preferred_names=[
                "verify_proof_bundle_json",
                "verify_proof_bundle",
                "verify_bundle_json",
                "verify_bundle",
            ],
            path=path,
        )

    elif artifact_type == "episode_bundle":
        accepted, reason, detail = _try_verify(
            module_name="omega_runtime.core.episode_bundle",
            preferred_names=[
                "verify_episode_bundle_json",
                "verify_episode_bundle",
            ],
            path=path,
        )

    elif artifact_type == "trace":
        accepted, reason, detail = _try_verify(
            module_name="omega_runtime.core.replay_verifier",
            preferred_names=[
                "verify_replay_json",
                "verify_replay_ledger_json",
                "verify_replay_verdict_json",
                "verify_replay_ledger",
                "verify_replay",
                "verify_trace",
                "verify_ledger",
                "verify_trace_json",
                "verify_trace_file",
                "verify_trace_file_json",
                "verify_replay_file",
                "verify_replay_file_json",
                "verify_jsonl_trace",
                "verify_jsonl_trace_json",
            ],
            path=path,
        )

    else:
        accepted = False
        reason = f"unknown artifact type: {artifact_type}"
        detail = {}

    return {
        "artifact_type": artifact_type,
        "path": str(path),
        "artifact_hash": artifact_hash,
        "accepted": accepted,
        "reason": reason,
        "detail": detail,
    }


def audit_runtime(
    *,
    proof_bundles: list[Path],
    episode_bundles: list[Path],
    traces: list[Path],
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    for path in proof_bundles:
        items.append(_audit_one(path, "proof_bundle"))

    for path in episode_bundles:
        items.append(_audit_one(path, "episode_bundle"))

    for path in traces:
        items.append(_audit_one(path, "trace"))

    if not items:
        accepted = False
        reason = "no artifacts supplied"
    else:
        accepted = all(item["accepted"] for item in items)
        reason = "runtime audit passed" if accepted else next(
            item["reason"] for item in items if not item["accepted"]
        )

    payload: dict[str, Any] = {
        "audit_type": AUDITOR_VERSION,
        "auditor_version": AUDITOR_VERSION,
        "generated_at": _utc_now_iso(),
        "artifact_count": len(items),
        "accepted": accepted,
        "reason": reason,
        "items": items,
    }

    payload["aggregate_hash"] = _json_hash({
        k: v for k, v in payload.items()
        if k not in {"aggregate_hash", "generated_at"}
    })

    return payload


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Omega Runtime proof artifacts.")
    parser.add_argument("--proof-bundle", action="append", default=[], help="Path to a proof bundle JSON file.")
    parser.add_argument("--episode-bundle", action="append", default=[], help="Path to an episode bundle JSON file.")
    parser.add_argument("--trace", action="append", default=[], help="Path to a replay trace JSONL file.")
    parser.add_argument("--out", help="Write the audit report JSON to this path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON to stdout.")

    args = parser.parse_args()

    payload = audit_runtime(
        proof_bundles=[Path(p) for p in args.proof_bundle],
        episode_bundles=[Path(p) for p in args.episode_bundle],
        traces=[Path(p) for p in args.trace],
    )

    if args.out:
        _write_report(Path(args.out), payload)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("OMEGA RUNTIME AUDIT")
        print(f"accepted: {payload['accepted']}")
        print(f"reason: {payload['reason']}")
        print(f"artifact_count: {payload['artifact_count']}")
        print(f"aggregate_hash: {payload['aggregate_hash']}")

        if args.out:
            print(f"report_path: {args.out}")

        for item in payload["items"]:
            print()
            print(f"- {item['artifact_type']}: {item['path']}")
            print(f"  accepted: {item['accepted']}")
            print(f"  reason: {item['reason']}")
            print(f"  artifact_hash: {item['artifact_hash']}")

    return 0 if payload["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
