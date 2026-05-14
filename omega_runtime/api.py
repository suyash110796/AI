from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from omega_runtime.core.actions import Action
from omega_runtime.core.verifier import issue_certificate
from omega_runtime.core.proof_bundle import export_proof_bundle, verify_proof_bundle
from omega_runtime.core.proxy import OmegaProxy
from omega_runtime.core.replay_verifier import verify_replay_trace
from omega_runtime.core.system_verifier import verify_runtime_system


API_VERSION = "OMEGA_RUNTIME_API_V1"


def _jsonable(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]

    if is_dataclass(value):
        return _jsonable(asdict(value))

    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))

    return str(value)


def _verdict_payload(result: Any, default_success_reason: str) -> dict[str, Any]:
    if isinstance(result, tuple) and len(result) >= 2:
        return {
            "accepted": bool(result[0]),
            "reason": str(result[1]),
            "raw": _jsonable(result),
        }

    if isinstance(result, dict):
        payload = dict(result)

        if "accepted" not in payload:
            if "passed" in payload:
                payload["accepted"] = bool(payload["passed"])
            elif "valid" in payload:
                payload["accepted"] = bool(payload["valid"])
            else:
                payload["accepted"] = False

        payload.setdefault(
            "reason",
            default_success_reason if payload["accepted"] else "verification failed",
        )
        return _jsonable(payload)

    if hasattr(result, "passed"):
        return {
            "accepted": bool(getattr(result, "passed")),
            "passed": bool(getattr(result, "passed")),
            "reason": str(getattr(result, "reason", default_success_reason)),
            "entries_checked": getattr(result, "entries_checked", None),
            "final_entry_hash": getattr(result, "final_entry_hash", None),
            "violations": _jsonable(getattr(result, "violations", [])),
            "raw": _jsonable(result),
        }

    return {
        "accepted": False,
        "reason": f"unsupported verifier result type: {type(result).__name__}",
        "raw": _jsonable(result),
    }


class ExecuteRequest(BaseModel):
    run_id: str = Field(..., min_length=1)
    step_index: int = Field(..., ge=1)
    tool: str = Field(..., min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    nonce: str | None = None
    proof_bundle_path: str | None = None


class PathRequest(BaseModel):
    path: str = Field(..., min_length=1)


class SystemVerifyRequest(BaseModel):
    proof_bundles: list[str] = Field(default_factory=list)
    traces: list[str] = Field(default_factory=list)


from omega_runtime.ui_dashboard import register_dashboard_routes
app = FastAPI(

    title="OMEGA Runtime API",
    version="0.3.0",
    description=(
        "HTTP API for the OMEGA proof-carrying runtime. "
        "It exposes certified execution, proof bundle verification, "
        "trace replay verification, and system verification."
    ),
)

register_dashboard_routes(app)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "accepted": True,
        "api_version": API_VERSION,
        "runtime": "omega-runtime",
        "reason": "api online",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "accepted": True,
        "api_version": API_VERSION,
        "reason": "healthy",
    }


@app.post("/v1/execute")
def execute_action(request: ExecuteRequest) -> dict[str, Any]:
    action = Action(
        run_id=request.run_id,
        step_index=request.step_index,
        tool=request.tool,
        args=request.args,
        nonce=request.nonce or f"{request.run_id}-nonce-{request.step_index}",
    )

    ok, issue_reason, certificate = issue_certificate(action)

    if not ok or certificate is None:
        return {
            "accepted": False,
            "api_version": API_VERSION,
            "reason": issue_reason,
            "certificate_issued": False,
            "action": _jsonable(action),
        }

    proxy = OmegaProxy()
    result = proxy.execute(action, certificate)

    payload: dict[str, Any] = {
        "accepted": bool(result.accepted),
        "api_version": API_VERSION,
        "reason": str(result.reason),
        "certificate_issued": True,
        "action": _jsonable(action),
        "certificate": _jsonable(certificate),
        "receipt": _jsonable(result.receipt),
        "output": _jsonable(result.output),
        "counterexample": _jsonable(getattr(result, "counterexample", None)),
    }

    if result.accepted and result.receipt is not None:
        proof_path = (
            Path(request.proof_bundle_path)
            if request.proof_bundle_path
            else Path("artifacts") / f"api-proof-bundle-{request.run_id}-{request.step_index}.json"
        )
        proof_path.parent.mkdir(parents=True, exist_ok=True)

        export_proof_bundle(
            path=proof_path,
            action=action,
            certificate=certificate,
            receipt=result.receipt,
        )

        verified, verify_reason = verify_proof_bundle(proof_path)

        payload["proof_bundle_path"] = str(proof_path)
        payload["proof_bundle_verified"] = bool(verified)
        payload["proof_bundle_verify_reason"] = str(verify_reason)

    return payload


@app.post("/v1/verify/proof-bundle")
def verify_proof_bundle_endpoint(request: PathRequest) -> dict[str, Any]:
    payload = _verdict_payload(
        verify_proof_bundle(Path(request.path)),
        "proof bundle valid",
    )
    payload["api_version"] = API_VERSION
    payload["artifact_type"] = "proof_bundle"
    payload["path"] = request.path
    return payload


@app.post("/v1/verify/trace")
def verify_trace_endpoint(request: PathRequest) -> dict[str, Any]:
    payload = _verdict_payload(
        verify_replay_trace(Path(request.path)),
        "offline replay verification passed",
    )
    payload["api_version"] = API_VERSION
    payload["artifact_type"] = "trace"
    payload["path"] = request.path
    return payload


@app.post("/v1/system/verify")
def verify_system_endpoint(request: SystemVerifyRequest) -> dict[str, Any]:
    payload = verify_runtime_system(
        proof_bundles=request.proof_bundles,
        traces=request.traces,
    )
    payload["api_version"] = API_VERSION
    return _jsonable(payload)
