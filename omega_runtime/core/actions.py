from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Action:
    """
    Canonical tool-action object.

    This is the object that gets:
      1. policy-admitted,
      2. certificate-bound,
      3. hash-bound,
      4. replay-protected,
      5. executed by OmegaProxy.

    Required invariant:
      certificate.payload.action_hash == sha256_hex(current Action)
    """

    run_id: str
    step_index: int
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    nonce: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_index": self.step_index,
            "tool": self.tool,
            "args": self.args,
            "nonce": self.nonce,
        }
