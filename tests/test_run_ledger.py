from __future__ import annotations

from pathlib import Path

from omega_runtime.run_ledger import (
    RUN_LEDGER_VERSION,
    compare_last_two,
    compare_reports,
    list_run_records,
    write_run_record,
)


def _report(response_hash: str, response_text: str) -> dict:
    return {
        "accepted": True,
        "adapter_version": "OMEGA_OPENAI_LIVE_V1",
        "aggregate_hash": response_hash[::-1],
        "api_key_stored": False,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "live": True,
        "max_output_tokens": 300,
        "mode": "live",
        "model": "gpt-4.1-mini",
        "prompt_hash": "e4441d6c3d9b6adac1759e5f4321209d3749e7a3f3878838aa9bcbf518e4c4f9",
        "prompt_preview": "Explain the value of verifiable AI execution in one sentence for a non-technical executive.",
        "reason": "live OpenAI call completed",
        "report_path": "artifacts/openai_live/openai_live_report.json",
        "response_hash": response_hash,
        "response_text": response_text,
        "system_prompt_hash": "6191a4d8dd58844a478a82619db32a4b7bcfd26e5b1c83e9c4140b340d2c29b0",
    }


def test_run_ledger_writes_unique_records(tmp_path: Path):
    first = write_run_record(_report("a" * 64, "first answer"), root=tmp_path)
    second = write_run_record(_report("b" * 64, "second answer"), root=tmp_path)

    assert first["accepted"] is True
    assert second["accepted"] is True
    assert first["ledger_version"] == RUN_LEDGER_VERSION
    assert first["record_path"] != second["record_path"]

    assert (tmp_path / first["record_path"]).exists()
    assert (tmp_path / second["record_path"]).exists()
    assert (tmp_path / first["ledger_path"]).exists()

    records = list_run_records(root=tmp_path)
    assert len(records) == 2
    assert {record["report"]["response_text"] for record in records} == {
        "first answer",
        "second answer",
    }


def test_compare_reports_detects_same_prompt_different_response():
    left = _report("a" * 64, "first answer")
    right = _report("b" * 64, "second answer")

    comparison = compare_reports(left, right)

    assert comparison["accepted"] is True
    assert comparison["same_prompt_hash"] is True
    assert comparison["same_system_prompt_hash"] is True
    assert comparison["same_model"] is True
    assert comparison["same_response_hash"] is False
    assert comparison["inference"] == "same request context produced a different model response"


def test_compare_last_two_requires_two_records(tmp_path: Path):
    comparison = compare_last_two(root=tmp_path)

    assert comparison["accepted"] is False
    assert comparison["records_found"] == 0


def test_compare_last_two_works_after_two_records(tmp_path: Path):
    write_run_record(_report("a" * 64, "first answer"), root=tmp_path)
    write_run_record(_report("b" * 64, "second answer"), root=tmp_path)

    comparison = compare_last_two(root=tmp_path)

    assert comparison["accepted"] is True
    assert comparison["same_prompt_hash"] is True
    assert comparison["same_response_hash"] is False
