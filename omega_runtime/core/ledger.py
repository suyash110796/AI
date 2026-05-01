from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from omega_runtime.core.canonical import canonical_json, sha256_hex


def reset_ledger(path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("", encoding="utf-8")


def _read_last_hash(path: Path) -> str:
    if not path.exists():
        return "GENESIS"

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    if not lines:
        return "GENESIS"

    last = json.loads(lines[-1])
    return last["entry_hash"]


def record_decision(
    *,
    ledger_path: str | Path,
    run_id: str,
    step_index: int,
    action_hash: str,
    certificate_hash: str | None,
    receipt_hash: str | None,
    verdict: str,
    reason: str,
) -> dict[str, Any]:
    p = Path(ledger_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    prev_hash = _read_last_hash(p)

    entry_without_hash = {
        "run_id": run_id,
        "step_index": step_index,
        "action_hash": action_hash,
        "certificate_hash": certificate_hash,
        "receipt_hash": receipt_hash,
        "verdict": verdict,
        "reason": reason,
        "prev_hash": prev_hash,
    }

    entry_hash = sha256_hex(entry_without_hash)
    entry = {**entry_without_hash, "entry_hash": entry_hash}

    with p.open("a", encoding="utf-8") as f:
        f.write(canonical_json(entry) + "\n")

    return entry
