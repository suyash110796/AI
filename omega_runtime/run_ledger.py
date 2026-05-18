from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any


RUN_LEDGER_VERSION = "OMEGA_RUN_LEDGER_V1"
DEFAULT_RUNS_DIR = Path("artifacts") / "openai_live" / "runs"
DEFAULT_LEDGER_PATH = Path("artifacts") / "openai_live" / "openai_run_ledger.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def sanitize_token(value: Any, fallback: str = "value", max_length: int = 48) -> str:
    text = str(value or fallback).strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    if not text:
        text = fallback
    return text[:max_length]


def short_hash(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    return sanitize_token(text[:12], fallback=fallback, max_length=12)


def project_path(root: Path | str, relative: Path) -> Path:
    return Path(root).resolve() / relative


def ensure_run_ledger_dirs(root: Path | str = ".") -> dict[str, Path]:
    root_path = Path(root).resolve()
    runs_dir = project_path(root_path, DEFAULT_RUNS_DIR)
    ledger_path = project_path(root_path, DEFAULT_LEDGER_PATH)
    runs_dir.mkdir(parents=True, exist_ok=True)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    return {
        "root": root_path,
        "runs_dir": runs_dir,
        "ledger_path": ledger_path,
    }


def build_record_filename(report: dict[str, Any]) -> str:
    mode = sanitize_token(report.get("mode", "unknown-mode"), fallback="mode", max_length=24)
    model = sanitize_token(report.get("model", "unknown-model"), fallback="model", max_length=32)
    prompt = short_hash(report.get("prompt_hash"), fallback="no-prompt")
    response = short_hash(report.get("response_hash"), fallback="no-response")
    nonce = uuid.uuid4().hex[:12]
    return f"{utc_stamp()}_{mode}_{model}_{prompt}_{response}_{nonce}.json"


def normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(report)
    normalized.setdefault("accepted", False)
    normalized.setdefault("generated_at", utc_now())
    normalized.setdefault("mode", "unknown")
    normalized.setdefault("live", False)
    normalized.setdefault("model", "unknown")
    normalized.setdefault("prompt_hash", "")
    normalized.setdefault("response_hash", "")
    normalized.setdefault("response_text", "")
    return normalized


def write_run_record(
    report: dict[str, Any],
    *,
    root: Path | str = ".",
    source: str = "openai",
) -> dict[str, Any]:
    paths = ensure_run_ledger_dirs(root)
    normalized_report = normalize_report(report)

    record_id = uuid.uuid4().hex
    record = {
        "ledger_version": RUN_LEDGER_VERSION,
        "record_id": record_id,
        "recorded_at": utc_now(),
        "source": source,
        "accepted": bool(normalized_report.get("accepted")),
        "live": bool(normalized_report.get("live")),
        "mode": normalized_report.get("mode"),
        "model": normalized_report.get("model"),
        "prompt_hash": normalized_report.get("prompt_hash"),
        "response_hash": normalized_report.get("response_hash"),
        "aggregate_hash": normalized_report.get("aggregate_hash"),
        "report": normalized_report,
    }

    record["record_body_hash"] = sha256_text(canonical_json(record))

    filename = build_record_filename(normalized_report)
    record_path = paths["runs_dir"] / filename
    record_path.write_text(canonical_json(record) + "\n", encoding="utf-8")

    file_hash = sha256_file(record_path)
    index_entry = {
        "ledger_version": RUN_LEDGER_VERSION,
        "record_id": record_id,
        "recorded_at": record["recorded_at"],
        "source": source,
        "accepted": record["accepted"],
        "live": record["live"],
        "mode": record["mode"],
        "model": record["model"],
        "prompt_hash": record["prompt_hash"],
        "response_hash": record["response_hash"],
        "aggregate_hash": record["aggregate_hash"],
        "record_body_hash": record["record_body_hash"],
        "record_file_sha256": file_hash,
        "record_path": str(record_path.relative_to(paths["root"])),
    }

    with paths["ledger_path"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_entry, sort_keys=True, ensure_ascii=False) + "\n")

    return {
        "accepted": True,
        "ledger_version": RUN_LEDGER_VERSION,
        "reason": "run recorded",
        "record_id": record_id,
        "record_path": str(record_path.relative_to(paths["root"])),
        "record_file_sha256": file_hash,
        "ledger_path": str(paths["ledger_path"].relative_to(paths["root"])),
        "record": record,
        "index_entry": index_entry,
    }


def load_run_record(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def list_run_records(*, root: Path | str = ".", limit: int | None = None) -> list[dict[str, Any]]:
    paths = ensure_run_ledger_dirs(root)
    records: list[dict[str, Any]] = []

    for path in paths["runs_dir"].glob("*.json"):
        try:
            record = load_run_record(path)
            record["_path"] = str(path.relative_to(paths["root"]))
            records.append(record)
        except Exception as exc:
            records.append(
                {
                    "ledger_version": RUN_LEDGER_VERSION,
                    "accepted": False,
                    "reason": "failed to load run record",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "_path": str(path.relative_to(paths["root"])),
                }
            )

    records.sort(key=lambda item: (str(item.get("recorded_at", "")), str(item.get("_path", ""))), reverse=True)

    if limit is not None:
        return records[:limit]

    return records


def compare_reports(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    same_prompt = left.get("prompt_hash") == right.get("prompt_hash")
    same_system_prompt = left.get("system_prompt_hash") == right.get("system_prompt_hash")
    same_model = left.get("model") == right.get("model")
    same_mode = left.get("mode") == right.get("mode")
    same_live_flag = left.get("live") == right.get("live")
    same_response = left.get("response_hash") == right.get("response_hash")
    same_aggregate = left.get("aggregate_hash") == right.get("aggregate_hash")

    if same_prompt and same_system_prompt and same_model and same_mode and same_live_flag and not same_response:
        inference = "same request context produced a different model response"
    elif same_prompt and same_response:
        inference = "same request context produced the same response hash"
    elif not same_prompt:
        inference = "different prompt hash; this is not a same-request comparison"
    else:
        inference = "request context differs in one or more tracked dimensions"

    return {
        "accepted": True,
        "ledger_version": RUN_LEDGER_VERSION,
        "reason": "comparison completed",
        "same_prompt_hash": same_prompt,
        "same_system_prompt_hash": same_system_prompt,
        "same_model": same_model,
        "same_mode": same_mode,
        "same_live_flag": same_live_flag,
        "same_response_hash": same_response,
        "same_aggregate_hash": same_aggregate,
        "left": {
            "generated_at": left.get("generated_at"),
            "mode": left.get("mode"),
            "live": left.get("live"),
            "model": left.get("model"),
            "prompt_hash": left.get("prompt_hash"),
            "response_hash": left.get("response_hash"),
            "response_text": left.get("response_text"),
        },
        "right": {
            "generated_at": right.get("generated_at"),
            "mode": right.get("mode"),
            "live": right.get("live"),
            "model": right.get("model"),
            "prompt_hash": right.get("prompt_hash"),
            "response_hash": right.get("response_hash"),
            "response_text": right.get("response_text"),
        },
        "inference": inference,
    }


def compare_records(left_record: dict[str, Any], right_record: dict[str, Any]) -> dict[str, Any]:
    left_report = left_record.get("report", left_record)
    right_report = right_record.get("report", right_record)
    comparison = compare_reports(left_report, right_report)
    comparison["left_record_id"] = left_record.get("record_id")
    comparison["right_record_id"] = right_record.get("record_id")
    comparison["left_record_path"] = left_record.get("_path")
    comparison["right_record_path"] = right_record.get("_path")
    return comparison


def compare_last_two(*, root: Path | str = ".") -> dict[str, Any]:
    records = list_run_records(root=root, limit=2)
    if len(records) < 2:
        return {
            "accepted": False,
            "ledger_version": RUN_LEDGER_VERSION,
            "reason": "at least two run records are required for comparison",
            "records_found": len(records),
        }

    return compare_records(records[1], records[0])


def extract_json_object(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise ValueError("command produced no stdout")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


@dataclass(frozen=True)
class OpenAICliRunRequest:
    live: bool = False
    prompt: str | None = None
    model: str | None = None
    max_output_tokens: int = 300
    root: Path | str = "."


def run_openai_cli_and_record(request: OpenAICliRunRequest) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "omega_runtime.cli",
        "openai",
        "--json",
    ]

    if request.live:
        command.append("--live")
    else:
        command.append("--dry-run")

    if request.prompt:
        command.extend(["--prompt", request.prompt])

    if request.model:
        command.extend(["--model", request.model])

    command.extend(["--max-output-tokens", str(request.max_output_tokens)])

    completed = subprocess.run(
        command,
        cwd=Path(request.root),
        text=True,
        capture_output=True,
        check=False,
    )

    try:
        report = extract_json_object(completed.stdout)
    except Exception as exc:
        report = {
            "accepted": False,
            "adapter_version": "OMEGA_OPENAI_LIVE_V1",
            "generated_at": utc_now(),
            "live": request.live,
            "mode": "cli_error",
            "model": request.model or "unknown",
            "reason": "failed to parse OpenAI CLI output",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }

    record_result = write_run_record(report, root=request.root, source="openai_cli")

    return {
        "accepted": bool(report.get("accepted")) and completed.returncode == 0,
        "ledger_version": RUN_LEDGER_VERSION,
        "reason": "OpenAI CLI run recorded" if completed.returncode == 0 else "OpenAI CLI run failed and was recorded",
        "command": command,
        "returncode": completed.returncode,
        "stderr": completed.stderr,
        "report": report,
        "record_result": {
            "accepted": record_result["accepted"],
            "record_id": record_result["record_id"],
            "record_path": record_result["record_path"],
            "record_file_sha256": record_result["record_file_sha256"],
            "ledger_path": record_result["ledger_path"],
        },
    }


__all__ = [
    "RUN_LEDGER_VERSION",
    "OpenAICliRunRequest",
    "canonical_json",
    "compare_last_two",
    "compare_records",
    "compare_reports",
    "ensure_run_ledger_dirs",
    "list_run_records",
    "load_run_record",
    "run_openai_cli_and_record",
    "sha256_file",
    "sha256_text",
    "write_run_record",
]
# ---------------------------------------------------------------------
# OMEGA v1.3.0 live OpenAI CLI auto-record compatibility helper
# ---------------------------------------------------------------------

def record_openai_report(report, *, ledger_path=None):
    """
    Record one OpenAI adapter report into the OMEGA run ledger.

    This helper is intentionally self-contained so the CLI can record live
    OpenAI calls without depending on the demo script. It does not store the
    API key. It records the report, hashes, prompt preview, response hash,
    mode, model, and a unique per-run JSON file.
    """
    import json
    import re
    import secrets
    from datetime import datetime, timezone
    from hashlib import sha256
    from pathlib import Path

    ledger_version = "OMEGA_RUN_LEDGER_V1"

    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    def safe_json(value):
        return json.loads(json.dumps(value, default=str))

    def canonical_json(value) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    def pretty_json(value) -> str:
        return json.dumps(value, indent=2, sort_keys=True, default=str)

    def slug(value, default: str = "unknown") -> str:
        raw = str(value or default)
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip("-")
        return (cleaned or default)[:80]

    if isinstance(report, dict):
        report_copy = safe_json(report)
    else:
        report_copy = {
            "accepted": False,
            "reason": f"unsupported report type: {type(report).__name__}",
            "raw_report": str(report),
        }

    base_dir = Path("artifacts") / "openai_live"
    ledger_file = Path(ledger_path) if ledger_path is not None else base_dir / "openai_run_ledger.jsonl"
    runs_dir = ledger_file.parent / "runs"

    ledger_file.parent.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    report_sha256 = sha256(canonical_json(report_copy).encode("utf-8")).hexdigest()

    recorded_at = utc_now()
    record_id = sha256(
        f"{report_sha256}|{recorded_at}|{secrets.token_hex(16)}".encode("utf-8")
    ).hexdigest()[:32]

    generated_at = str(report_copy.get("generated_at") or recorded_at)
    stamp = re.sub(r"[^0-9A-Za-z]", "", generated_at)[:24]
    if not stamp:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    mode = str(report_copy.get("mode") or ("live" if report_copy.get("live") else "dry_run"))
    model = str(report_copy.get("model") or "unknown-model")
    prompt_hash = str(report_copy.get("prompt_hash") or "no_prompt_hash")
    response_hash = str(report_copy.get("response_hash") or "no_response_hash")

    record_filename = (
        f"{stamp}_"
        f"{slug(mode)}_"
        f"{slug(model)}_"
        f"{slug(prompt_hash[:12], 'prompt')}_"
        f"{slug(response_hash[:12], 'response')}_"
        f"{record_id[:12]}.json"
    )

    record_path = runs_dir / record_filename

    standard_fields = [
        "accepted",
        "adapter_version",
        "aggregate_hash",
        "api_key_stored",
        "cli_command",
        "cli_version",
        "generated_at",
        "live",
        "max_output_tokens",
        "mode",
        "model",
        "prompt_hash",
        "prompt_preview",
        "reason",
        "report_path",
        "response_hash",
        "response_text",
        "system_prompt_hash",
    ]

    record = {
        "ledger_version": ledger_version,
        "record_id": record_id,
        "record_type": "openai_report",
        "recorded_at": recorded_at,
        "record_path": str(record_path),
        "report_sha256": report_sha256,
        "report": report_copy,
    }

    for key in standard_fields:
        if key in report_copy:
            record[key] = report_copy[key]

    record_path.write_text(pretty_json(record) + "\n", encoding="utf-8")
    record_file_sha256 = sha256(record_path.read_bytes()).hexdigest()

    ledger_entry = {
        key: value
        for key, value in record.items()
        if key != "report"
    }
    ledger_entry["record_file_sha256"] = record_file_sha256

    with ledger_file.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(ledger_entry) + "\n")

    return {
        "accepted": True,
        "ledger_version": ledger_version,
        "reason": "OpenAI report recorded",
        "ledger_path": str(ledger_file),
        "record_path": str(record_path),
        "record_id": record_id,
        "record_file_sha256": record_file_sha256,
    }
