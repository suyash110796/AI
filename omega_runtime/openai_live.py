"""OpenAI live-call adapter for OMEGA Runtime.

This module adds one deliberately small, auditable OpenAI integration.

Design rules:
- Dry-run by default, so tests never require network access or paid API calls.
- Live calls only happen when explicitly requested.
- The API key is read from OPENAI_API_KEY and is never stored or printed.
- Every run emits a machine-readable report for audit and replay.
- The OpenAI call is kept behind one narrow adapter boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OPENAI_LIVE_VERSION = "OMEGA_OPENAI_LIVE_V1"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_OUTPUT_DIR = Path("artifacts") / "openai_live"
DEFAULT_REPORT_PATH = DEFAULT_OUTPUT_DIR / "openai_live_report.json"

SYSTEM_PROMPT = (
    "You are being called through OMEGA Runtime. "
    "Return a useful answer, but stay inside the requested task. "
    "Do not claim that you executed external actions unless the prompt provides evidence. "
    "Keep the response concise and auditable."
)


@dataclass(frozen=True)
class OpenAILiveRequest:
    prompt: str
    model: str = DEFAULT_MODEL
    live: bool = False
    max_output_tokens: int = 300
    output_dir: Path = DEFAULT_OUTPUT_DIR
    store_prompt: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _preview(value: str, limit: int = 240) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _response_text_from_openai_response(response: Any) -> str:
    direct = getattr(response, "output_text", None)
    if isinstance(direct, str) and direct.strip():
        return direct

    try:
        output = getattr(response, "output", None) or []
        parts: list[str] = []

        for item in output:
            content = getattr(item, "content", None) or []
            for block in content:
                text = getattr(block, "text", None)
                if isinstance(text, str) and text:
                    parts.append(text)

        if parts:
            return "\n".join(parts)
    except Exception:
        pass

    return str(response)


def build_openai_report(
    request: OpenAILiveRequest,
    *,
    accepted: bool,
    reason: str,
    mode: str,
    response_text: str,
    error_type: str | None = None,
) -> dict[str, Any]:
    prompt_hash = _sha256_text(request.prompt)
    response_hash = _sha256_text(response_text) if response_text else None

    report: dict[str, Any] = {
        "accepted": accepted,
        "reason": reason,
        "adapter_version": OPENAI_LIVE_VERSION,
        "generated_at": _utc_now(),
        "mode": mode,
        "live": request.live,
        "model": request.model,
        "max_output_tokens": request.max_output_tokens,
        "prompt_hash": prompt_hash,
        "prompt_preview": _preview(request.prompt),
        "system_prompt_hash": _sha256_text(SYSTEM_PROMPT),
        "response_hash": response_hash,
        "response_text": response_text,
        "api_key_stored": False,
        "report_path": str(request.output_dir / "openai_live_report.json"),
    }

    if request.store_prompt:
        report["prompt"] = request.prompt

    if error_type:
        report["error_type"] = error_type

    report["aggregate_hash"] = _sha256_payload(
        {
            "adapter_version": report["adapter_version"],
            "mode": report["mode"],
            "model": report["model"],
            "prompt_hash": report["prompt_hash"],
            "system_prompt_hash": report["system_prompt_hash"],
            "response_hash": report["response_hash"],
            "accepted": report["accepted"],
            "reason": report["reason"],
        }
    )

    return report


def write_openai_report(report: dict[str, Any], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "openai_live_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def run_openai_live(request: OpenAILiveRequest) -> dict[str, Any]:
    if not request.prompt.strip():
        report = build_openai_report(
            request,
            accepted=False,
            reason="prompt is required",
            mode="validation_error",
            response_text="",
            error_type="ValueError",
        )
        write_openai_report(report, request.output_dir)
        return report

    if request.max_output_tokens < 1:
        report = build_openai_report(
            request,
            accepted=False,
            reason="max_output_tokens must be greater than zero",
            mode="validation_error",
            response_text="",
            error_type="ValueError",
        )
        write_openai_report(report, request.output_dir)
        return report

    if not request.live:
        response_text = (
            "DRY RUN: no network call was made. "
            "Set live=True and provide OPENAI_API_KEY to execute a real OpenAI call."
        )
        report = build_openai_report(
            request,
            accepted=True,
            reason="dry run completed",
            mode="dry_run",
            response_text=response_text,
        )
        write_openai_report(report, request.output_dir)
        return report

    if not os.environ.get("OPENAI_API_KEY"):
        report = build_openai_report(
            request,
            accepted=False,
            reason="OPENAI_API_KEY is required for live mode",
            mode="missing_api_key",
            response_text="",
            error_type="EnvironmentError",
        )
        write_openai_report(report, request.output_dir)
        return report

    try:
        from openai import OpenAI
    except Exception as exc:
        report = build_openai_report(
            request,
            accepted=False,
            reason="openai package is not installed",
            mode="missing_dependency",
            response_text=str(exc),
            error_type=exc.__class__.__name__,
        )
        write_openai_report(report, request.output_dir)
        return report

    try:
        client = OpenAI()
        response = client.responses.create(
            model=request.model,
            instructions=SYSTEM_PROMPT,
            input=request.prompt,
            max_output_tokens=request.max_output_tokens,
        )
        response_text = _response_text_from_openai_response(response)

        report = build_openai_report(
            request,
            accepted=True,
            reason="live OpenAI call completed",
            mode="live",
            response_text=response_text,
        )
        write_openai_report(report, request.output_dir)
        return report

    except Exception as exc:
        report = build_openai_report(
            request,
            accepted=False,
            reason="live OpenAI call failed",
            mode="live_error",
            response_text=str(exc),
            error_type=exc.__class__.__name__,
        )
        write_openai_report(report, request.output_dir)
        return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run OMEGA OpenAI live adapter.")
    parser.add_argument("--prompt", default="Explain OMEGA Runtime in one sentence.")
    parser.add_argument("--model", default=os.environ.get("OMEGA_OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--max-output-tokens", type=int, default=300)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--store-prompt", action="store_true")
    args = parser.parse_args(argv)

    request = OpenAILiveRequest(
        prompt=args.prompt,
        model=args.model,
        live=args.live,
        max_output_tokens=args.max_output_tokens,
        store_prompt=args.store_prompt,
    )

    report = run_openai_live(request)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(f"accepted: {report['accepted']}")
        print(f"reason: {report['reason']}")
        print(f"mode: {report['mode']}")
        print(f"model: {report['model']}")
        print(f"report_path: {report['report_path']}")

    return 0 if report["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
