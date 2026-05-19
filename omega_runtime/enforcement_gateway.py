from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ENFORCEMENT_GATEWAY_VERSION = "OMEGA_ENFORCEMENT_GATEWAY_V1"

DECISION_ALLOW = "ALLOW"
DECISION_REJECT = "REJECT"
DECISION_NEEDS_HUMAN_APPROVAL = "NEEDS_HUMAN_APPROVAL"
DECISION_NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"

DEFAULT_RECEIPT_DIR = Path("artifacts") / "enforcement" / "receipts"

REQUIRED_ACTION_FIELDS = (
    "action_type",
    "operation",
    "target",
)

KNOWN_ACTION_TYPES = {
    "ai.openai.live_call",
    "ai.openai.dry_run",
    "tool.read_only",
    "tool.write_file",
    "tool.network_call",
    "email.send",
    "filesystem.delete",
    "deployment.release",
}

HIGH_RISK_ACTION_TYPES = {
    "email.send",
    "filesystem.delete",
    "deployment.release",
    "tool.network_call",
}

REQUIRED_AI_EVIDENCE_FIELDS = (
    "model",
    "prompt_hash",
    "response_hash",
    "aggregate_hash",
)

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[A-Za-z0-9_\-]{12,}"),
)


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    name: str
    passed: bool
    severity: str
    reason: str
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "reason": self.reason,
            "detail": self.detail,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _contains_secret(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, (dict, list, tuple)):
        text = canonical_json(value)
    else:
        text = str(value)

    return any(pattern.search(text) is not None for pattern in SECRET_PATTERNS)


def _policy_hash(policy: dict[str, Any] | None = None) -> str:
    effective_policy = policy or {
        "known_action_types": sorted(KNOWN_ACTION_TYPES),
        "high_risk_action_types": sorted(HIGH_RISK_ACTION_TYPES),
        "required_action_fields": list(REQUIRED_ACTION_FIELDS),
        "required_ai_evidence_fields": list(REQUIRED_AI_EVIDENCE_FIELDS),
        "secret_patterns": [pattern.pattern for pattern in SECRET_PATTERNS],
    }
    return sha256_json(effective_policy)


def evaluate_action(
    action_request: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluate whether an action is allowed to execute.

    This function does not execute the action.
    It only returns an enforcement decision and receipt-style evidence.
    """

    generated_at = utc_now_iso()
    rule_results: list[RuleResult] = []

    action_is_object = isinstance(action_request, dict)
    rule_results.append(
        RuleResult(
            rule_id="EG-001",
            name="action_request_must_be_object",
            passed=action_is_object,
            severity="critical",
            reason="action request is a JSON object" if action_is_object else "action request is not a JSON object",
            detail={"type": type(action_request).__name__},
        )
    )

    if not action_is_object:
        receipt = _build_receipt(
            action_request={},
            generated_at=generated_at,
            rule_results=rule_results,
            decision=DECISION_REJECT,
            reason="action request must be a JSON object",
            policy=policy,
        )
        return receipt

    action = dict(action_request)
    evidence = _safe_dict(action.get("evidence"))
    action_type = action.get("action_type")
    risk = str(action.get("risk", "low")).lower()

    missing_fields = [field for field in REQUIRED_ACTION_FIELDS if not action.get(field)]
    rule_results.append(
        RuleResult(
            rule_id="EG-002",
            name="required_action_fields_present",
            passed=not missing_fields,
            severity="critical",
            reason="required action fields are present" if not missing_fields else "required action fields are missing",
            detail={"missing_fields": missing_fields, "required_fields": list(REQUIRED_ACTION_FIELDS)},
        )
    )

    known_action = action_type in KNOWN_ACTION_TYPES
    rule_results.append(
        RuleResult(
            rule_id="EG-003",
            name="known_action_type",
            passed=known_action,
            severity="critical",
            reason="action type is known" if known_action else "action type is not registered in the gateway policy",
            detail={"action_type": action_type, "known_action_types": sorted(KNOWN_ACTION_TYPES)},
        )
    )

    secret_found = _contains_secret(action)
    rule_results.append(
        RuleResult(
            rule_id="EG-004",
            name="no_secret_material_in_action_request",
            passed=not secret_found,
            severity="critical",
            reason="no obvious secret material found" if not secret_found else "possible secret material found in action request",
            detail={"secret_detected": secret_found},
        )
    )

    if action_type == "ai.openai.live_call":
        live_ok = evidence.get("live") is True and evidence.get("mode") == "live"
        rule_results.append(
            RuleResult(
                rule_id="EG-005",
                name="live_ai_call_must_have_live_evidence",
                passed=live_ok,
                severity="critical",
                reason="live OpenAI evidence confirms live mode" if live_ok else "live OpenAI action lacks live evidence",
                detail={"evidence_live": evidence.get("live"), "evidence_mode": evidence.get("mode")},
            )
        )

    if action_type in {"ai.openai.live_call", "ai.openai.dry_run"}:
        missing_evidence = [field for field in REQUIRED_AI_EVIDENCE_FIELDS if not evidence.get(field)]
        rule_results.append(
            RuleResult(
                rule_id="EG-006",
                name="ai_action_requires_evidence_hashes",
                passed=not missing_evidence,
                severity="evidence",
                reason="AI action evidence hashes are present" if not missing_evidence else "AI action evidence is incomplete",
                detail={
                    "missing_evidence": missing_evidence,
                    "required_evidence": list(REQUIRED_AI_EVIDENCE_FIELDS),
                },
            )
        )

    high_risk = action_type in HIGH_RISK_ACTION_TYPES or risk in {"high", "critical", "destructive", "external"}
    human_approval = _safe_dict(evidence.get("human_approval"))
    human_approved = human_approval.get("accepted") is True or human_approval.get("approved") is True

    rule_results.append(
        RuleResult(
            rule_id="EG-007",
            name="high_risk_action_requires_human_approval",
            passed=(not high_risk) or human_approved,
            severity="approval",
            reason="human approval satisfied" if high_risk and human_approved else (
                "human approval not required" if not high_risk else "high-risk action requires human approval"
            ),
            detail={
                "high_risk": high_risk,
                "risk": risk,
                "action_type": action_type,
                "human_approved": human_approved,
            },
        )
    )

    failed_critical = [rule for rule in rule_results if not rule.passed and rule.severity == "critical"]
    failed_evidence = [rule for rule in rule_results if not rule.passed and rule.severity == "evidence"]
    failed_approval = [rule for rule in rule_results if not rule.passed and rule.severity == "approval"]

    if failed_critical:
        decision = DECISION_REJECT
        reason = "critical enforcement rule failed"
    elif failed_evidence:
        decision = DECISION_NEEDS_MORE_EVIDENCE
        reason = "required evidence is missing"
    elif failed_approval:
        decision = DECISION_NEEDS_HUMAN_APPROVAL
        reason = "human approval is required before execution"
    else:
        decision = DECISION_ALLOW
        reason = "all enforcement rules passed"

    return _build_receipt(
        action_request=action,
        generated_at=generated_at,
        rule_results=rule_results,
        decision=decision,
        reason=reason,
        policy=policy,
    )


def _build_receipt(
    *,
    action_request: dict[str, Any],
    generated_at: str,
    rule_results: list[RuleResult],
    decision: str,
    reason: str,
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    action_hash = sha256_json(action_request)
    rule_result_dicts = [rule.to_dict() for rule in rule_results]
    gateway_policy_hash = _policy_hash(policy)

    receipt_body = {
        "enforcement_gateway_version": ENFORCEMENT_GATEWAY_VERSION,
        "generated_at": generated_at,
        "decision": decision,
        "can_execute": decision == DECISION_ALLOW,
        "accepted": decision == DECISION_ALLOW,
        "reason": reason,
        "action_hash": action_hash,
        "policy_hash": gateway_policy_hash,
        "rule_results": rule_result_dicts,
    }

    receipt_hash = sha256_json(receipt_body)

    return {
        **receipt_body,
        "receipt_hash": receipt_hash,
        "rules_passed": sum(1 for rule in rule_results if rule.passed),
        "rules_failed": sum(1 for rule in rule_results if not rule.passed),
        "rules_total": len(rule_results),
    }


def write_enforcement_receipt(
    receipt: dict[str, Any],
    *,
    output_dir: Path | str = DEFAULT_RECEIPT_DIR,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    generated = receipt.get("generated_at") or utc_now_iso()
    safe_timestamp = (
        generated.replace("-", "")
        .replace(":", "")
        .replace("+00:00", "Z")
        .replace(".", "")
    )

    receipt_hash = str(receipt.get("receipt_hash") or sha256_json(receipt))
    decision = str(receipt.get("decision") or "UNKNOWN").lower()
    filename = f"{safe_timestamp}_{decision}_{receipt_hash[:16]}_{uuid.uuid4().hex[:12]}.json"
    receipt_path = output_path / filename

    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    file_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()

    return {
        "accepted": True,
        "reason": "enforcement receipt written",
        "receipt_path": str(receipt_path),
        "receipt_file_sha256": file_sha256,
        "receipt_hash": receipt_hash,
        "decision": receipt.get("decision"),
    }


def enforce_action(
    action_request: dict[str, Any],
    *,
    executor: Callable[[dict[str, Any]], Any] | None = None,
    write_receipt: bool = True,
    receipt_dir: Path | str = DEFAULT_RECEIPT_DIR,
) -> dict[str, Any]:
    """
    Evaluate an action and execute it only if the gateway allows it.

    If executor is None, the gateway only proves that the action would be allowed.
    """

    receipt = evaluate_action(action_request)

    receipt_write_result: dict[str, Any] | None = None
    if write_receipt:
        receipt_write_result = write_enforcement_receipt(receipt, output_dir=receipt_dir)

    execution_result: Any = None
    executed = False

    if receipt["decision"] == DECISION_ALLOW and executor is not None:
        execution_result = executor(action_request)
        executed = True

    if receipt["decision"] != DECISION_ALLOW:
        execution_reason = "execution blocked by enforcement gateway"
    elif executor is None:
        execution_reason = "execution allowed but no executor was provided"
    else:
        execution_reason = "execution completed"

    return {
        "accepted": receipt["decision"] == DECISION_ALLOW,
        "enforcement_gateway_version": ENFORCEMENT_GATEWAY_VERSION,
        "decision": receipt["decision"],
        "can_execute": receipt["can_execute"],
        "executed": executed,
        "reason": execution_reason,
        "receipt": receipt,
        "receipt_write": receipt_write_result,
        "execution_result": execution_result,
    }
