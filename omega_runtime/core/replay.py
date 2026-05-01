from __future__ import annotations

import json
import sys
from pathlib import Path

from omega_runtime.core.canonical import sha256_hex
from omega_runtime.core.types import ReplayResult


def replay_trace(path: str | Path) -> ReplayResult:
    p = Path(path)

    if not p.exists():
        return ReplayResult(False, "trace missing", 0, None)

    lines = [line for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    prev_hash = "GENESIS"
    final_hash = None

    for idx, line in enumerate(lines, start=1):
        try:
            entry = json.loads(line)
        except Exception as exc:
            return ReplayResult(False, f"trace unreadable at line {idx}: {exc}", idx - 1, final_hash)

        stored_hash = entry.get("entry_hash")
        body = dict(entry)
        body.pop("entry_hash", None)

        if body.get("prev_hash") != prev_hash:
            return ReplayResult(False, "trace prev_hash mismatch", idx - 1, final_hash)

        recomputed = sha256_hex(body)

        if stored_hash != recomputed:
            return ReplayResult(False, "entry_hash mismatch", idx - 1, final_hash)

        prev_hash = stored_hash
        final_hash = stored_hash

    return ReplayResult(True, "trace hash chain valid", len(lines), final_hash)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m omega_runtime.core.replay <trace.jsonl>")

    result = replay_trace(sys.argv[1])

    print(f"REPLAY: {'PASS' if result.passed else 'FAIL'}")
    print(f"REASON: {result.reason}")
    print(f"ENTRIES CHECKED: {result.entries_checked}")
    print(f"FINAL ENTRY HASH: {result.final_entry_hash}")

    if result.passed:
        print("FINAL: LAWFUL TRACE")
    else:
        print("FINAL: TRACE REJECTED")


if __name__ == "__main__":
    main()
