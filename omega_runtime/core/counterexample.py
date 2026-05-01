from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Counterexample:
    counterexample_id: str
    failed_invariant: str
    expected: str
    observed: str
    decision: str = "REJECT"
