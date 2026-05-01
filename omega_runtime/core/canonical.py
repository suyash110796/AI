from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any


def to_plain_data(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return to_plain_data(dataclasses.asdict(value))

    if isinstance(value, dict):
        return {str(k): to_plain_data(v) for k, v in value.items()}

    if isinstance(value, list):
        return [to_plain_data(v) for v in value]

    if isinstance(value, tuple):
        return [to_plain_data(v) for v in value]

    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        to_plain_data(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
