from pathlib import Path

from omega_runtime.enforcement_gateway import (
    DECISION_ALLOW,
    DECISION_NEEDS_HUMAN_APPROVAL,
    DECISION_NEEDS_MORE_EVIDENCE,
    DECISION_REJECT,
    ENFORCEMENT_GATEWAY_VERSION,
    enforce_action,
    evaluate_action,
    write_enforcement_receipt,
)


def valid_live_ai_action():
    return {
        "action_type": "ai.openai.live_call",
        "operation": "model_call",
        "target": "openai:gpt-4.1-mini",
        "risk": "low",
        "evidence": {
            "live": True,
            "mode": "live",
            "model": "gpt-4.1-mini",
            "prompt_hash": "a" * 64,
            "response_hash": "b" * 64,
            "aggregate_hash": "c" * 64,
        },
    }


def test_enforcement_gateway_allows_valid_live_ai_action():
    receipt = evaluate_action(valid_live_ai_action())

    assert receipt["accepted"] is True
    assert receipt["can_execute"] is True
    assert receipt["decision"] == DECISION_ALLOW
    assert receipt["enforcement_gateway_version"] == ENFORCEMENT_GATEWAY_VERSION
    assert receipt["rules_failed"] == 0
    assert receipt["receipt_hash"]


def test_enforcement_gateway_rejects_missing_required_action_field():
    action = valid_live_ai_action()
    del action["target"]

    receipt = evaluate_action(action)

    assert receipt["accepted"] is False
    assert receipt["can_execute"] is False
    assert receipt["decision"] == DECISION_REJECT
    assert receipt["rules_failed"] >= 1


def test_enforcement_gateway_needs_more_evidence_for_incomplete_ai_action():
    action = valid_live_ai_action()
    del action["evidence"]["response_hash"]

    receipt = evaluate_action(action)

    assert receipt["accepted"] is False
    assert receipt["can_execute"] is False
    assert receipt["decision"] == DECISION_NEEDS_MORE_EVIDENCE


def test_enforcement_gateway_blocks_live_action_without_live_evidence():
    action = valid_live_ai_action()
    action["evidence"]["live"] = False
    action["evidence"]["mode"] = "dry_run"

    receipt = evaluate_action(action)

    assert receipt["accepted"] is False
    assert receipt["can_execute"] is False
    assert receipt["decision"] == DECISION_REJECT


def test_enforcement_gateway_requires_human_approval_for_high_risk_action():
    action = {
        "action_type": "email.send",
        "operation": "send_email",
        "target": "customer@example.com",
        "risk": "high",
        "evidence": {},
    }

    receipt = evaluate_action(action)

    assert receipt["accepted"] is False
    assert receipt["can_execute"] is False
    assert receipt["decision"] == DECISION_NEEDS_HUMAN_APPROVAL


def test_enforcement_gateway_allows_high_risk_action_with_human_approval():
    action = {
        "action_type": "email.send",
        "operation": "send_email",
        "target": "customer@example.com",
        "risk": "high",
        "evidence": {
            "human_approval": {
                "accepted": True,
                "approved_by": "manual-review",
            }
        },
    }

    receipt = evaluate_action(action)

    assert receipt["accepted"] is True
    assert receipt["can_execute"] is True
    assert receipt["decision"] == DECISION_ALLOW


def test_enforcement_gateway_rejects_secret_material():
    action = valid_live_ai_action()
    action["evidence"]["debug_note"] = "api_key=sk-thisShouldNeverBeInEvidence123456789"

    receipt = evaluate_action(action)

    assert receipt["accepted"] is False
    assert receipt["decision"] == DECISION_REJECT


def test_enforce_action_does_not_execute_when_blocked():
    called = {"value": False}

    def executor(_action):
        called["value"] = True
        return {"executed": True}

    action = valid_live_ai_action()
    del action["target"]

    result = enforce_action(action, executor=executor, write_receipt=False)

    assert result["accepted"] is False
    assert result["executed"] is False
    assert called["value"] is False
    assert result["decision"] == DECISION_REJECT


def test_enforce_action_executes_only_when_allowed():
    called = {"value": False}

    def executor(action):
        called["value"] = True
        return {"target": action["target"], "executed": True}

    result = enforce_action(valid_live_ai_action(), executor=executor, write_receipt=False)

    assert result["accepted"] is True
    assert result["executed"] is True
    assert called["value"] is True
    assert result["execution_result"]["executed"] is True


def test_enforcement_receipt_writer_creates_unique_file(tmp_path):
    receipt = evaluate_action(valid_live_ai_action())

    first = write_enforcement_receipt(receipt, output_dir=tmp_path)
    second = write_enforcement_receipt(receipt, output_dir=tmp_path)

    assert first["accepted"] is True
    assert second["accepted"] is True
    assert Path(first["receipt_path"]).exists()
    assert Path(second["receipt_path"]).exists()
    assert first["receipt_path"] != second["receipt_path"]
    assert first["receipt_file_sha256"]
    assert second["receipt_file_sha256"]



def test_openai_cli_gateway_accepts_safe_request():
    from omega_runtime.enforcement_gateway import evaluate_openai_cli_request

    decision = evaluate_openai_cli_request(
        prompt="Explain verifiable AI execution in one sentence.",
        model="gpt-4.1-mini",
        live=True,
        max_output_tokens=64,
    )

    assert decision["accepted"] is True
    assert decision["operation"] == "openai_model_call"
    assert decision["mode"] == "live"
    assert decision["decision_hash"]


def test_openai_cli_gateway_rejects_blank_prompt():
    from omega_runtime.enforcement_gateway import evaluate_openai_cli_request

    decision = evaluate_openai_cli_request(
        prompt="",
        model="gpt-4.1-mini",
        live=True,
        max_output_tokens=64,
    )

    assert decision["accepted"] is False
    assert decision["violations"]
    assert decision["reason"] == "enforcement gateway rejected request before OpenAI call"


def test_openai_cli_gateway_rejects_secret_like_prompt():
    from omega_runtime.enforcement_gateway import evaluate_openai_cli_request

    decision = evaluate_openai_cli_request(
        prompt="Use this API key: sk-svcacct-example-secret-material-1234567890",
        model="gpt-4.1-mini",
        live=True,
        max_output_tokens=64,
    )

    assert decision["accepted"] is False
    assert decision["prompt_preview"] == "[REDACTED: prompt contains secret-like material]"
