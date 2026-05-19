
from __future__ import annotations

import re

import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse


NON_ACTIONABLE_TOP_VIOLATION_SIGNALS = {"prompt_present"}


def _top_violation_signal_name(item: object) -> str:
    if isinstance(item, dict):
        return str(
            item.get("name")
            or item.get("signal")
            or item.get("check")
            or item.get("violation")
            or ""
        )
    if isinstance(item, (list, tuple)) and item:
        return str(item[0])
    return str(item)


def _filter_top_violation_signals(items: object) -> object:
    if not isinstance(items, list):
        return items
    return [
        item
        for item in items
        if _top_violation_signal_name(item) not in NON_ACTIONABLE_TOP_VIOLATION_SIGNALS
    ]


def _filter_gateway_summary(summary: object) -> object:
    if not isinstance(summary, dict):
        return _filter_gateway_summary(summary)

    for key in (
        "top_violation_signals",
        "top_violations",
        "violation_signals",
        "violation_counts",
    ):
        value = summary.get(key)
        if isinstance(value, list):
            summary[key] = _filter_top_violation_signals(value)

    return _filter_gateway_summary(summary)


def _strip_non_actionable_top_violation_rows(html_text: str) -> str:
    for signal in NON_ACTIONABLE_TOP_VIOLATION_SIGNALS:
        html_text = re.sub(
            rf'<div class="metric-line">\s*<span>{re.escape(signal)}</span>\s*<strong>[^<]*</strong>\s*</div>',
            "",
            html_text,
            flags=re.IGNORECASE,
        )
    return html_text



router = APIRouter()

GATEWAY_UI_VERSION = "OMEGA_ENFORCEMENT_GATEWAY_UI_V1"
LEDGER_PATH = Path("artifacts/openai_live/openai_run_ledger.jsonl")
MAX_SCAN_RECORDS = 250
MAX_RENDER_EVENTS = 60


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value)


def _short(value: Any, size: int = 12) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    return text[:size]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_ledger_records(limit: int = MAX_SCAN_RECORDS) -> list[dict[str, Any]]:
    if not LEDGER_PATH.exists():
        return []

    rows: list[dict[str, Any]] = []
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()

    for raw in reversed(lines[-limit:]):
        raw = raw.strip()
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            rows.append(parsed)

    return rows


def _record_body(record: dict[str, Any]) -> dict[str, Any]:
    record_path = record.get("record_path")
    if not record_path:
        return {}

    path = Path(str(record_path))
    if not path.exists():
        return {}

    return _read_json(path)


def _extract_payload(body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}

    payload = body.get("payload")
    if isinstance(payload, dict):
        return payload

    report = body.get("report")
    if isinstance(report, dict):
        return report

    return body


def _extract_gateway(payload: dict[str, Any], body: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        payload.get("enforcement_gateway") if isinstance(payload, dict) else None,
        body.get("enforcement_gateway") if isinstance(body, dict) else None,
        body.get("gateway") if isinstance(body, dict) else None,
        record.get("enforcement_gateway") if isinstance(record, dict) else None,
    ]

    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate

    return {}


def _extract_event(record: dict[str, Any]) -> dict[str, Any] | None:
    body = _record_body(record)
    payload = _extract_payload(body)
    gateway = _extract_gateway(payload, body, record)

    enforced = bool(payload.get("enforced")) or bool(gateway)
    mode = payload.get("mode", record.get("mode"))
    if mode == "blocked_by_enforcement_gateway":
        enforced = True

    if not enforced:
        return None

    checks = gateway.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    violations = gateway.get("violations", [])
    if not isinstance(violations, list):
        violations = []

    failed_checks = [
        check for check in checks
        if isinstance(check, dict) and check.get("passed") is False
    ]

    gateway_accepted = gateway.get("accepted")
    payload_accepted = payload.get("accepted", record.get("accepted"))

    blocked = (
        gateway_accepted is False
        or mode == "blocked_by_enforcement_gateway"
        or payload_accepted is False
    )

    openai_called = payload.get("openai_called")
    if openai_called is None:
        openai_called = bool(payload_accepted) and not blocked

    prompt_hash = payload.get("prompt_hash", record.get("prompt_hash", gateway.get("prompt_hash")))
    response_hash = payload.get("response_hash", record.get("response_hash"))
    decision_hash = gateway.get("decision_hash")
    prompt_preview = payload.get("prompt_preview", gateway.get("prompt_preview", ""))

    if blocked and "REDACTED" in _safe_text(prompt_preview).upper():
        prompt_preview = "[REDACTED BY ENFORCEMENT GATEWAY]"

    violation_names: list[str] = []
    for item in violations or failed_checks:
        if isinstance(item, dict):
            violation_names.append(_safe_text(item.get("name"), "unknown_violation"))

    return {
        "record_id": record.get("record_id"),
        "recorded_at": record.get("recorded_at"),
        "record_path": record.get("record_path"),
        "ledger_path": str(LEDGER_PATH),
        "source": record.get("source"),
        "accepted": bool(payload_accepted),
        "blocked": bool(blocked),
        "allowed": not bool(blocked),
        "openai_called": bool(openai_called),
        "mode": mode,
        "live": bool(payload.get("live", record.get("live", False))),
        "model": payload.get("model", record.get("model", gateway.get("model"))),
        "prompt_hash": prompt_hash,
        "prompt_hash_short": _short(prompt_hash),
        "response_hash": response_hash,
        "response_hash_short": _short(response_hash),
        "decision_hash": decision_hash,
        "decision_hash_short": _short(decision_hash),
        "prompt_preview": prompt_preview,
        "reason": payload.get("reason", gateway.get("reason", record.get("reason"))),
        "gateway_reason": gateway.get("reason"),
        "checks": checks,
        "checks_passed": sum(1 for check in checks if isinstance(check, dict) and check.get("passed") is True),
        "checks_failed": len(failed_checks),
        "violations": violations,
        "violation_names": violation_names,
        "policy": gateway.get("policy", {}),
        "gateway_version": gateway.get("gateway_version"),
    }


def load_gateway_events(limit: int = MAX_SCAN_RECORDS) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for record in _read_ledger_records(limit=limit):
        event = _extract_event(record)
        if event is not None:
            events.append(event)

    return events


def build_gateway_summary() -> dict[str, Any]:
    records = _read_ledger_records(limit=MAX_SCAN_RECORDS)
    events = load_gateway_events(limit=MAX_SCAN_RECORDS)

    violation_counter: Counter[str] = Counter()
    model_counter: Counter[str] = Counter()
    mode_counter: Counter[str] = Counter()

    for event in events:
        for name in event.get("violation_names", []):
            violation_counter[str(name)] += 1

        model = event.get("model")
        if model:
            model_counter[str(model)] += 1

        mode = event.get("mode")
        if mode:
            mode_counter[str(mode)] += 1

    blocked_events = [event for event in events if event.get("blocked")]
    allowed_events = [event for event in events if event.get("allowed")]
    openai_called_events = [event for event in events if event.get("openai_called")]
    openai_not_called_events = [event for event in events if not event.get("openai_called")]

    return {
        "accepted": True,
        "gateway_ui_version": GATEWAY_UI_VERSION,
        "generated_at": _utc_now(),
        "ledger_path": str(LEDGER_PATH),
        "ledger_exists": LEDGER_PATH.exists(),
        "records_scanned": len(records),
        "gateway_events_found": len(events),
        "allowed_events": len(allowed_events),
        "blocked_events": len(blocked_events),
        "openai_called_events": len(openai_called_events),
        "openai_not_called_events": len(openai_not_called_events),
        "top_violations": [
            {"name": name, "count": count}
            for name, count in violation_counter.most_common(10)
        ],
        "models": [
            {"model": name, "count": count}
            for name, count in model_counter.most_common(10)
        ],
        "modes": [
            {"mode": name, "count": count}
            for name, count in mode_counter.most_common(10)
        ],
        "events": events[:MAX_RENDER_EVENTS],
    }


def _escape(value: Any) -> str:
    return html.escape(_safe_text(value))


def _badge(label: str, kind: str) -> str:
    return f'<span class="badge {kind}">{_escape(label)}</span>'


def _render_check(check: dict[str, Any]) -> str:
    passed = check.get("passed") is True
    kind = "pass" if passed else "fail"
    status = "PASS" if passed else "FAIL"
    name = _escape(check.get("name", "unknown_check"))
    reason = _escape(check.get("reason", ""))

    return (
        '<div class="check-row">'
        f'<span class="check-status {kind}">{status}</span>'
        f'<span class="check-name">{name}</span>'
        f'<span class="check-reason">{reason}</span>'
        '</div>'
    )


def _render_event(event: dict[str, Any]) -> str:
    blocked = bool(event.get("blocked"))
    called = bool(event.get("openai_called"))
    live = bool(event.get("live"))

    outcome_badge = _badge("BLOCKED", "blocked") if blocked else _badge("ALLOWED", "allowed")
    call_badge = _badge("OPENAI NOT CALLED", "blocked") if not called else _badge("OPENAI CALLED", "called")
    mode_badge = _badge("LIVE", "live") if live else _badge("DRY RUN", "dry")

    checks = event.get("checks", [])
    rendered_checks = "".join(
        _render_check(check)
        for check in checks
        if isinstance(check, dict)
    )

    if not rendered_checks:
        rendered_checks = '<div class="muted">No gateway checks found in this record.</div>'

    violations = event.get("violation_names", [])
    if violations:
        violation_html = "".join(
            f'<span class="violation">{_escape(name)}</span>'
            for name in violations
        )
    else:
        violation_html = '<span class="muted">None</span>'

    return f"""
    <article class="event-card">
        <div class="event-top">
            <div>
                <div class="event-title">{outcome_badge} {call_badge} {mode_badge}</div>
                <div class="event-subtitle">{_escape(event.get("reason", ""))}</div>
            </div>
            <div class="record-id">record {_escape(event.get("record_id", ""))}</div>
        </div>

        <div class="grid">
            <div class="kv"><span>model</span><strong>{_escape(event.get("model", ""))}</strong></div>
            <div class="kv"><span>mode</span><strong>{_escape(event.get("mode", ""))}</strong></div>
            <div class="kv"><span>decision hash</span><strong>{_escape(event.get("decision_hash_short", ""))}</strong></div>
            <div class="kv"><span>prompt hash</span><strong>{_escape(event.get("prompt_hash_short", ""))}</strong></div>
            <div class="kv"><span>response hash</span><strong>{_escape(event.get("response_hash_short", ""))}</strong></div>
            <div class="kv"><span>recorded at</span><strong>{_escape(event.get("recorded_at", ""))}</strong></div>
        </div>

        <div class="prompt-preview">{_escape(event.get("prompt_preview", ""))}</div>

        <div class="section-title">Policy checks</div>
        <div class="checks">{rendered_checks}</div>

        <div class="section-title">Violations</div>
        <div class="violations">{violation_html}</div>

        <div class="path-row">
            <span>record path</span>
            <code>{_escape(event.get("record_path", ""))}</code>
        </div>
    </article>
    """


def render_gateway_page() -> str:
    summary = build_gateway_summary()
    events = summary["events"]

    if events:
        event_html = "\n".join(_render_event(event) for event in events)
    else:
        event_html = """
        <article class="event-card empty">
            <h2>No Enforcement Gateway records found yet.</h2>
            <p>Run an OpenAI CLI request through the gateway, then refresh this page.</p>
            <code>python -m omega_runtime.cli openai --json --dry-run --prompt "Gateway visibility test." --model "gpt-4.1-mini"</code>
        </article>
        """

    top_violations = summary.get("top_violations", [])
    if top_violations:
        violation_rows = "".join(
            f'<div class="metric-line"><span>{_escape(item["name"])}</span><strong>{item["count"]}</strong></div>'
            for item in top_violations
        )
    else:
        violation_rows = '<div class="metric-line"><span>No violations recorded</span><strong>0</strong></div>'

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>OMEGA Enforcement Gateway Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        :root {{
            color-scheme: dark;
            --bg: #07111f;
            --panel: #0e1b2f;
            --panel-2: #12243d;
            --text: #e7eefc;
            --muted: #8ea4c6;
            --line: rgba(148, 163, 184, 0.2);
            --green: #34d399;
            --red: #fb7185;
            --yellow: #facc15;
            --blue: #60a5fa;
            --cyan: #22d3ee;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(34, 211, 238, 0.16), transparent 28rem),
                radial-gradient(circle at top right, rgba(251, 113, 133, 0.12), transparent 26rem),
                var(--bg);
            color: var(--text);
        }}

        main {{
            width: min(1280px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 32px 0 60px;
        }}

        .hero {{
            border: 1px solid var(--line);
            background: linear-gradient(135deg, rgba(14, 27, 47, 0.96), rgba(18, 36, 61, 0.86));
            border-radius: 28px;
            padding: 28px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.26);
        }}

        .eyebrow {{
            color: var(--cyan);
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-size: 0.75rem;
        }}

        h1 {{
            margin: 10px 0 8px;
            font-size: clamp(2rem, 4vw, 4rem);
            line-height: 1;
        }}

        .hero p {{
            margin: 0;
            max-width: 900px;
            color: var(--muted);
            font-size: 1.05rem;
            line-height: 1.65;
        }}

        .toolbar {{
            margin-top: 22px;
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
        }}

        .button {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 10px 14px;
            color: var(--text);
            text-decoration: none;
            background: rgba(255, 255, 255, 0.05);
            font-weight: 700;
        }}

        .button:hover {{
            border-color: var(--cyan);
        }}

        .metrics {{
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 12px;
            margin-top: 18px;
        }}

        .metric {{
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 16px;
            background: rgba(255, 255, 255, 0.045);
        }}

        .metric span {{
            display: block;
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .metric strong {{
            display: block;
            margin-top: 8px;
            font-size: 1.65rem;
        }}

        .panel {{
            margin-top: 18px;
            border: 1px solid var(--line);
            background: rgba(14, 27, 47, 0.78);
            border-radius: 24px;
            padding: 20px;
        }}

        .panel h2 {{
            margin: 0 0 12px;
        }}

        .metric-line {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            padding: 10px 0;
            border-bottom: 1px solid var(--line);
            color: var(--muted);
        }}

        .metric-line:last-child {{
            border-bottom: 0;
        }}

        .metric-line strong {{
            color: var(--text);
        }}

        .events {{
            margin-top: 18px;
            display: grid;
            gap: 16px;
        }}

        .event-card {{
            border: 1px solid var(--line);
            background: rgba(14, 27, 47, 0.82);
            border-radius: 24px;
            padding: 20px;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.2);
        }}

        .event-top {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
        }}

        .event-title {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            align-items: center;
        }}

        .event-subtitle {{
            margin-top: 8px;
            color: var(--muted);
        }}

        .record-id {{
            color: var(--muted);
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            font-size: 0.8rem;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.75rem;
            font-weight: 900;
            letter-spacing: 0.06em;
        }}

        .badge.allowed {{
            background: rgba(52, 211, 153, 0.13);
            color: var(--green);
            border: 1px solid rgba(52, 211, 153, 0.35);
        }}

        .badge.blocked {{
            background: rgba(251, 113, 133, 0.13);
            color: var(--red);
            border: 1px solid rgba(251, 113, 133, 0.35);
        }}

        .badge.called {{
            background: rgba(96, 165, 250, 0.13);
            color: var(--blue);
            border: 1px solid rgba(96, 165, 250, 0.35);
        }}

        .badge.live {{
            background: rgba(250, 204, 21, 0.13);
            color: var(--yellow);
            border: 1px solid rgba(250, 204, 21, 0.35);
        }}

        .badge.dry {{
            background: rgba(148, 163, 184, 0.13);
            color: var(--muted);
            border: 1px solid rgba(148, 163, 184, 0.35);
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
            margin-top: 16px;
        }}

        .kv {{
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.04);
            min-width: 0;
        }}

        .kv span {{
            display: block;
            color: var(--muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .kv strong {{
            display: block;
            margin-top: 8px;
            overflow-wrap: anywhere;
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            font-size: 0.84rem;
        }}

        .prompt-preview {{
            margin-top: 16px;
            border-left: 3px solid var(--cyan);
            padding: 12px 14px;
            background: rgba(34, 211, 238, 0.06);
            border-radius: 12px;
            color: var(--text);
        }}

        .section-title {{
            margin-top: 18px;
            margin-bottom: 8px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.76rem;
            font-weight: 900;
        }}

        .checks {{
            display: grid;
            gap: 8px;
        }}

        .check-row {{
            display: grid;
            grid-template-columns: 74px minmax(180px, 0.7fr) 1fr;
            gap: 10px;
            align-items: start;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.035);
        }}

        .check-status {{
            font-weight: 900;
            font-size: 0.75rem;
        }}

        .check-status.pass {{
            color: var(--green);
        }}

        .check-status.fail {{
            color: var(--red);
        }}

        .check-name {{
            font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            overflow-wrap: anywhere;
        }}

        .check-reason {{
            color: var(--muted);
            overflow-wrap: anywhere;
        }}

        .violations {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .violation {{
            display: inline-flex;
            border: 1px solid rgba(251, 113, 133, 0.35);
            color: var(--red);
            background: rgba(251, 113, 133, 0.1);
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.8rem;
            font-weight: 800;
        }}

        .path-row {{
            margin-top: 16px;
            display: grid;
            gap: 6px;
        }}

        .path-row span {{
            color: var(--muted);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        code {{
            color: #bfdbfe;
            overflow-wrap: anywhere;
        }}

        .muted {{
            color: var(--muted);
        }}

        .empty h2 {{
            margin-top: 0;
        }}

        @media (max-width: 1050px) {{
            .metrics,
            .grid {{
                grid-template-columns: repeat(3, minmax(0, 1fr));
            }}

            .check-row {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 680px) {{
            .metrics,
            .grid {{
                grid-template-columns: 1fr;
            }}

            .event-top {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <main>
        <section class="hero">
            <div class="eyebrow">{GATEWAY_UI_VERSION}</div>
            <h1>OMEGA Enforcement Gateway Console</h1>
            <p>
                This is the firewall view. It shows whether a request was allowed or blocked before execution,
                whether OpenAI was actually called, which policy checks passed, and which violations stopped the call.
            </p>

            <div class="toolbar">
                <a class="button" href="/enforcement-gateway/api/summary">View JSON summary</a>
                <a class="button" href="/ui/run-ledger">Back to Run Ledger</a>
                <a class="button" href="/openapi.json">OpenAPI routes</a>
            </div>

            <div class="metrics">
                <div class="metric"><span>records scanned</span><strong>{summary["records_scanned"]}</strong></div>
                <div class="metric"><span>gateway events</span><strong>{summary["gateway_events_found"]}</strong></div>
                <div class="metric"><span>allowed</span><strong>{summary["allowed_events"]}</strong></div>
                <div class="metric"><span>blocked</span><strong>{summary["blocked_events"]}</strong></div>
                <div class="metric"><span>OpenAI called</span><strong>{summary["openai_called_events"]}</strong></div>
                <div class="metric"><span>OpenAI not called</span><strong>{summary["openai_not_called_events"]}</strong></div>
            </div>
        </section>

        <section class="panel">
            <h2>Top violation signals</h2>
            {violation_rows}
        </section>

        <section class="events">
            {event_html}
        </section>
    
        <section class="metric-clarity" data-ui-metric-clarity="OMEGA_UI_METRIC_CLARITY_V1">
            <h2>How to read these gateway metrics</h2>
            <p><strong>Important:</strong> These numbers are enforcement-decision counters, not model-quality scores.</p>
            <ul>
                <li><strong>Allowed</strong> means the request passed every configured gateway check before execution.</li>
                <li><strong>Blocked</strong> means the gateway rejected the request before the OpenAI call.</li>
                <li><strong>Top violation signals</strong> shows failed checks only. Non-actionable passed checks such as prompt_present are intentionally excluded.</li>
            </ul>
        </section>
</main>
</body>
</html>
"""


@router.get("/enforcement-gateway", response_class=HTMLResponse)
def enforcement_gateway_page() -> HTMLResponse:
    return HTMLResponse(_strip_non_actionable_top_violation_rows(render_gateway_page()))
@router.get("/ui/enforcement-gateway", response_class=HTMLResponse)
def enforcement_gateway_page_alias() -> HTMLResponse:
    return HTMLResponse(_strip_non_actionable_top_violation_rows(render_gateway_page()))
@router.get("/enforcement-gateway/api/summary")
def enforcement_gateway_summary() -> JSONResponse:
    return JSONResponse(build_gateway_summary())
