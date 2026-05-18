from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from omega_runtime import openai_live


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value

    if is_dataclass(value):
        return asdict(value)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped

    if hasattr(value, "__dict__"):
        return dict(value.__dict__)

    raise TypeError(f"Unsupported report type: {type(value).__name__}")


def _runner():
    runner = getattr(openai_live, "run_openai_live_call", None)
    if runner is not None:
        return runner

    runner = getattr(openai_live, "run_openai_live", None)
    if runner is not None:
        return runner

    raise AssertionError("OpenAI live adapter runner is missing")


def test_openai_live_dry_run_accepts_without_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = openai_live.OpenAILiveRequest(
        prompt="Explain OMEGA Runtime in one short sentence.",
        live=False,
        max_output_tokens=64,
        output_dir=tmp_path,
    )

    report = _to_dict(_runner()(request))

    assert report["accepted"] is True
    assert report["live"] is False
    assert report["mode"] == "dry_run"
    assert report["api_key_stored"] is False
    assert report["reason"] == "dry run completed"

    assert report["adapter_version"] == "OMEGA_OPENAI_LIVE_V1"
    assert report["model"]
    assert report["prompt_preview"] == "Explain OMEGA Runtime in one short sentence."

    assert len(report["prompt_hash"]) == 64
    assert len(report["system_prompt_hash"]) == 64
    assert len(report["response_hash"]) == 64
    assert len(report["aggregate_hash"]) == 64

    assert "DRY RUN" in report["response_text"]

    report_path = Path(report["report_path"])
    assert report_path.exists()

    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["accepted"] is True
    assert saved["api_key_stored"] is False


def test_openai_live_dry_run_hash_changes_with_prompt(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    first = openai_live.OpenAILiveRequest(
        prompt="Prompt one",
        live=False,
        output_dir=tmp_path / "one",
    )
    second = openai_live.OpenAILiveRequest(
        prompt="Prompt two",
        live=False,
        output_dir=tmp_path / "two",
    )

    first_report = _to_dict(_runner()(first))
    second_report = _to_dict(_runner()(second))

    assert first_report["accepted"] is True
    assert second_report["accepted"] is True
    assert first_report["prompt_hash"] != second_report["prompt_hash"]


def test_openai_live_live_mode_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    request = openai_live.OpenAILiveRequest(
        prompt="This should not call the network without a key.",
        live=True,
        output_dir=tmp_path,
    )

    report = _to_dict(_runner()(request))

    assert report["accepted"] is False
    assert report["live"] is True
    assert report["api_key_stored"] is False
    assert "OPENAI_API_KEY" in report["reason"]


def test_demo_openai_live_call_script_json_dry_run(tmp_path):
    out_path = tmp_path / "openai_live_report.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/demo_openai_live_call.py",
            "--json",
            "--prompt",
            "Explain OMEGA Runtime in five words.",
            "--out",
            str(out_path),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    payload = json.loads(completed.stdout)

    assert payload["accepted"] is True
    assert payload["live"] is False
    assert payload["mode"] == "dry_run"
    assert payload["api_key_stored"] is False
    assert out_path.exists()
