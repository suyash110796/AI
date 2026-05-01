from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path.cwd().resolve()
SANDBOX_ROOT = (PROJECT_ROOT / "sandbox").resolve()

POLICY_SPEC: dict[str, Any] = {
    "policy_id": "omega-default-policy",
    "version": 1,
    "allowed_tools": [
        "sandbox.read_file",
        "sandbox.write_file",
    ],
    "sandbox_root": "sandbox",
    "invariants": [
        "I004_POLICY_HASH_BINDING",
        "I007_POLICY_ADMISSION",
        "I009_POLICY_MANIFEST_INTEGRITY",
    ],
    "rules": {
        "sandbox_paths_must_remain_inside_sandbox": True,
        "tool_must_be_allowlisted": True,
    },
}


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


POLICY_HASH = hashlib.sha256(_stable_json(POLICY_SPEC).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicyResult:
    allowed: bool
    reason: str

    @property
    def passed(self) -> bool:
        return self.allowed

    @property
    def accepted(self) -> bool:
        return self.allowed

    @property
    def ok(self) -> bool:
        return self.allowed

    def __bool__(self) -> bool:
        return self.allowed

    def __iter__(self):
        # Supports legacy code like: ok, reason = evaluate_action(action)
        yield self.allowed
        yield self.reason


def _get_action_tool(action: Any) -> str:
    return str(getattr(action, "tool", ""))


def _get_action_args(action: Any) -> dict[str, Any]:
    args = getattr(action, "args", {})
    if args is None:
        return {}
    if not isinstance(args, dict):
        return {}
    return args


def resolve_sandbox_path(path_value: str | Path) -> Path:
    """
    Resolve a user/tool path and enforce that it stays inside ./sandbox.

    Valid:
      sandbox/input.txt
      input.txt

    Invalid:
      ../secret.txt
      sandbox/../secret.txt
      absolute paths outside sandbox
    """
    raw = Path(path_value)

    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        parts = raw.parts
        if len(parts) > 0 and parts[0].lower() == "sandbox":
            candidate = (PROJECT_ROOT / raw).resolve()
        else:
            candidate = (SANDBOX_ROOT / raw).resolve()

    try:
        candidate.relative_to(SANDBOX_ROOT)
    except ValueError as exc:
        raise ValueError("path escapes sandbox") from exc

    return candidate


def evaluate_action(action: Any) -> PolicyResult:
    """
    Admission policy gate used by verifier/proxy.

    This intentionally uses duck typing so it does not import Action.
    That avoids circular imports and avoids depending on whether the file is
    named action.py or actions.py.
    """
    tool = _get_action_tool(action)
    args = _get_action_args(action)

    if tool not in POLICY_SPEC["allowed_tools"]:
        return PolicyResult(False, "tool not allowed")

    if tool in {"sandbox.read_file", "sandbox.write_file"}:
        path = args.get("path")
        if not path:
            return PolicyResult(False, "missing path")

        try:
            resolve_sandbox_path(path)
        except ValueError:
            return PolicyResult(False, "path escapes sandbox")

    return PolicyResult(True, "policy accept")


def is_action_allowed(action: Any) -> bool:
    return evaluate_action(action).allowed
