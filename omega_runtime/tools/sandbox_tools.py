from __future__ import annotations

from omega_runtime.core.policy import resolve_sandbox_path


def read_file(path: str) -> str:
    resolved = resolve_sandbox_path(path)
    return resolved.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    resolved = resolve_sandbox_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return "write ok"
