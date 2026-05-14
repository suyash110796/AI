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


# --- OMEGA_V040_DASHBOARD_ROUTE_ALIASES_START ---
#
# Dashboard compatibility routes.
#
# The dashboard UI calls one of these route names when the user presses
# "Verify system". These aliases intentionally all resolve to the same
# system-verification function so the UI cannot drift away from the API.
#
# Supported payload shapes:
#   {
#     "proof_bundle_path": "artifacts/proof_bundle_demo.json",
#     "trace_path": "traces/replay-verifier-demo.jsonl"
#   }
#
# Also accepted:
#   {
#     "proof_bundles": ["..."],
#     "traces": ["..."]
#   }

from typing import Any as _OmegaDashboardAny

from fastapi import Request as _OmegaDashboardRequest

from omega_runtime.core.system_verifier import (
    verify_runtime_system as _omega_dashboard_verify_runtime_system,
)


def _omega_dashboard_as_path_list(value: _OmegaDashboardAny) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = value.strip()
        return [value] if value else []

    if isinstance(value, (list, tuple)):
        paths: list[str] = []
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if text:
                paths.append(text)
        return paths

    text = str(value).strip()
    return [text] if text else []


def _omega_dashboard_extract_paths(
    payload: dict[str, _OmegaDashboardAny],
) -> tuple[list[str], list[str]]:
    proof_value = (
        payload.get("proof_bundles")
        or payload.get("proof_bundle_paths")
        or payload.get("proof_bundle_path")
        or payload.get("proof_bundle")
    )

    trace_value = (
        payload.get("traces")
        or payload.get("trace_paths")
        or payload.get("trace_path")
        or payload.get("trace")
    )

    return (
        _omega_dashboard_as_path_list(proof_value),
        _omega_dashboard_as_path_list(trace_value),
    )


async def _omega_dashboard_read_payload(
    request: _OmegaDashboardRequest,
) -> dict[str, _OmegaDashboardAny]:
    payload: dict[str, _OmegaDashboardAny] = {}

    try:
        body = await request.json()
        if isinstance(body, dict):
            payload.update(body)
    except Exception:
        pass

    for key, value in request.query_params.items():
        payload.setdefault(key, value)

    return payload


@app.post("/verify/system")
@app.post("/system/verify")
@app.post("/runtime/verify")
@app.post("/audit/system")
async def omega_dashboard_verify_system_alias(
    request: _OmegaDashboardRequest,
) -> dict[str, _OmegaDashboardAny]:
    payload = await _omega_dashboard_read_payload(request)
    proof_bundles, traces = _omega_dashboard_extract_paths(payload)

    report = _omega_dashboard_verify_runtime_system(
        proof_bundles=proof_bundles,
        traces=traces,
    )

    report.setdefault("route_alias", str(request.url.path))
    report.setdefault("requested_proof_bundles", proof_bundles)
    report.setdefault("requested_traces", traces)

    return report

# --- OMEGA_V040_DASHBOARD_ROUTE_ALIASES_END ---
# OMEGA_FAILURE_LAB_API_V1_BEGIN
from pathlib import Path as _OmegaFailureLabPath

from fastapi.responses import HTMLResponse as _OmegaFailureLabHTMLResponse
from pydantic import BaseModel as _OmegaFailureLabBaseModel

from omega_runtime.failure_lab import (
    FAILURE_LAB_TYPE as _OMEGA_FAILURE_LAB_TYPE,
    FAILURE_LAB_VERSION as _OMEGA_FAILURE_LAB_VERSION,
    failure_lab_dashboard_html as _omega_failure_lab_dashboard_html,
    run_failure_lab as _omega_run_failure_lab,
)


class _OmegaFailureLabRequest(_OmegaFailureLabBaseModel):
    output_dir: str = "artifacts/failure_lab"


@app.get("/failure-lab/status")
def omega_failure_lab_status() -> dict:
    return {
        "accepted": True,
        "failure_lab_type": _OMEGA_FAILURE_LAB_TYPE,
        "failure_lab_version": _OMEGA_FAILURE_LAB_VERSION,
        "reason": "failure lab route healthy",
    }


@app.post("/failure-lab/run")
def omega_failure_lab_run(request: _OmegaFailureLabRequest) -> dict:
    return _omega_run_failure_lab(_OmegaFailureLabPath(request.output_dir))


@app.get("/failure-lab", response_class=_OmegaFailureLabHTMLResponse)
def omega_failure_lab_page() -> str:
    return _omega_failure_lab_dashboard_html()
# OMEGA_FAILURE_LAB_API_V1_END

# OMEGA v0.6.0 failure lab dashboard route registration
try:
    from omega_runtime.failure_lab_dashboard import register_failure_lab_dashboard_routes

    register_failure_lab_dashboard_routes(app)
except Exception as exc:  # pragma: no cover - defensive startup fallback
    app.state.failure_lab_dashboard_registration_error = repr(exc)
