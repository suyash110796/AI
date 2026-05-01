from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class ReplayViolation:
    code: str
    message: str
    step_index: int | None = None


@dataclass(frozen=True)
class ReplayVerificationResult:
    passed: bool
    reason: str
    entries_checked: int = 0
    final_entry_hash: str | None = None
    violations: list[ReplayViolation] = field(default_factory=list)


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)

    if not trace_path.exists():
        raise FileNotFoundError(f"trace file not found: {trace_path}")

    entries: list[dict[str, Any]] = []

    for line_number, raw_line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc

        if not isinstance(value, dict):
            raise ValueError(f"trace line {line_number} is not a JSON object")

        entries.append(value)

    return entries


def _get_step_index(entry: dict[str, Any]) -> int | None:
    value = entry.get("step_index")
    if isinstance(value, int):
        return value

    try:
        return int(value)
    except Exception:
        return None


def _get_final_entry_hash_from_replay_result(result: Any) -> str | None:
    return getattr(result, "final_entry_hash", None)


def _get_entries_checked_from_replay_result(result: Any) -> int:
    value = getattr(result, "entries_checked", 0)
    try:
        return int(value)
    except Exception:
        return 0


def _get_passed_from_replay_result(result: Any) -> bool:
    return bool(getattr(result, "passed", False))


def _get_reason_from_replay_result(result: Any) -> str:
    return str(getattr(result, "reason", "unknown replay result"))


def _run_existing_hash_chain_replay(trace_path: Path) -> ReplayVerificationResult:
    """
    Delegates hash-chain verification to omega_runtime.core.replay.replay_trace.

    This is intentional: core.replay already owns the canonical ledger hash-chain
    semantics. This module adds offline replay-verifier orchestration and
    semantic trace-shape checks without duplicating the hash-chain algorithm.
    """
    try:
        from omega_runtime.core.replay import replay_trace
    except Exception as exc:
        return ReplayVerificationResult(
            passed=False,
            reason=f"replay engine unavailable: {exc}",
            violations=[
                ReplayViolation(
                    code="REPLAY_ENGINE_UNAVAILABLE",
                    message=str(exc),
                )
            ],
        )

    try:
        replay_result = replay_trace(trace_path)
    except Exception as exc:
        return ReplayVerificationResult(
            passed=False,
            reason=f"replay engine error: {exc}",
            violations=[
                ReplayViolation(
                    code="REPLAY_ENGINE_ERROR",
                    message=str(exc),
                )
            ],
        )

    if not _get_passed_from_replay_result(replay_result):
        return ReplayVerificationResult(
            passed=False,
            reason=_get_reason_from_replay_result(replay_result),
            entries_checked=_get_entries_checked_from_replay_result(replay_result),
            final_entry_hash=_get_final_entry_hash_from_replay_result(replay_result),
            violations=[
                ReplayViolation(
                    code="TRACE_HASH_CHAIN_REJECTED",
                    message=_get_reason_from_replay_result(replay_result),
                )
            ],
        )

    return ReplayVerificationResult(
        passed=True,
        reason=_get_reason_from_replay_result(replay_result),
        entries_checked=_get_entries_checked_from_replay_result(replay_result),
        final_entry_hash=_get_final_entry_hash_from_replay_result(replay_result),
        violations=[],
    )


def _semantic_trace_checks(entries: list[dict[str, Any]]) -> list[ReplayViolation]:
    violations: list[ReplayViolation] = []

    if not entries:
        violations.append(
            ReplayViolation(
                code="EMPTY_TRACE",
                message="trace contains no entries",
            )
        )
        return violations

    last_step: int | None = None

    for position, entry in enumerate(entries, start=1):
        step_index = _get_step_index(entry)

        if step_index is None:
            violations.append(
                ReplayViolation(
                    code="MISSING_STEP_INDEX",
                    message=f"entry {position} has no integer step_index",
                    step_index=None,
                )
            )
            continue

        if last_step is not None and step_index < last_step:
            violations.append(
                ReplayViolation(
                    code="STEP_ORDER_REGRESSION",
                    message=f"step_index regressed from {last_step} to {step_index}",
                    step_index=step_index,
                )
            )

        last_step = step_index

        run_id = entry.get("run_id")
        if not isinstance(run_id, str) or not run_id.strip():
            violations.append(
                ReplayViolation(
                    code="MISSING_RUN_ID",
                    message=f"entry {position} has no run_id",
                    step_index=step_index,
                )
            )

        action_hash = entry.get("action_hash")
        if not isinstance(action_hash, str) or len(action_hash) < 32:
            violations.append(
                ReplayViolation(
                    code="MISSING_ACTION_HASH",
                    message=f"entry {position} has no action_hash",
                    step_index=step_index,
                )
            )

        verdict = entry.get("verdict")
        if verdict not in {"ACCEPT", "REJECT"}:
            violations.append(
                ReplayViolation(
                    code="INVALID_VERDICT",
                    message=f"entry {position} verdict must be ACCEPT or REJECT",
                    step_index=step_index,
                )
            )

    return violations


def verify_replay_trace(path: str | Path) -> ReplayVerificationResult:
    """
    Offline replay verifier.

    Gate order:
      1. Load JSONL trace.
      2. Run canonical hash-chain replay.
      3. Run semantic trace-shape checks.
      4. Return machine-readable replay verdict.

    This verifier does not execute tools again. It verifies that the stored
    execution history remains intact, ordered, hash-chain valid, and shaped
    like a lawful Omega runtime trace.
    """
    trace_path = Path(path)

    try:
        entries = _load_jsonl(trace_path)
    except Exception as exc:
        return ReplayVerificationResult(
            passed=False,
            reason=str(exc),
            violations=[
                ReplayViolation(
                    code="TRACE_LOAD_FAILED",
                    message=str(exc),
                )
            ],
        )

    hash_result = _run_existing_hash_chain_replay(trace_path)
    if not hash_result.passed:
        return hash_result

    semantic_violations = _semantic_trace_checks(entries)
    if semantic_violations:
        return ReplayVerificationResult(
            passed=False,
            reason=semantic_violations[0].message,
            entries_checked=len(entries),
            final_entry_hash=hash_result.final_entry_hash,
            violations=semantic_violations,
        )

    return ReplayVerificationResult(
        passed=True,
        reason="offline replay verification passed",
        entries_checked=len(entries),
        final_entry_hash=hash_result.final_entry_hash,
        violations=[],
    )


def result_to_dict(result: ReplayVerificationResult) -> dict[str, Any]:
    return {
        "accepted": result.passed,
        "passed": result.passed,
        "reason": result.reason,
        "entries_checked": result.entries_checked,
        "final_entry_hash": result.final_entry_hash,
        "violations": [
            {
                "code": violation.code,
                "message": violation.message,
                "step_index": violation.step_index,
            }
            for violation in result.violations
        ],
    }
