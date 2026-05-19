from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

RUN_LEDGER_UI_VERSION = "OMEGA_RUN_LEDGER_UI_V1"

DEFAULT_PROMPT = "Explain the value of verifiable AI execution in one sentence for a non-technical executive."
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 300

LEDGER_PATH = Path("artifacts/openai_live/openai_run_ledger.jsonl")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        if parsed <= 0:
            return default
        return parsed
    except Exception:
        return default


def _read_ledger_records(path: Path = LEDGER_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)

    records.sort(key=lambda item: str(item.get("recorded_at", "")), reverse=True)
    return records


def _prompt_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for record in records:
        prompt_hash = str(record.get("prompt_hash") or "UNKNOWN_PROMPT_HASH")
        response_hash = str(record.get("response_hash") or "UNKNOWN_RESPONSE_HASH")
        mode = str(record.get("mode") or "unknown")

        if prompt_hash not in grouped:
            grouped[prompt_hash] = {
                "prompt_hash": prompt_hash,
                "records": 0,
                "live_records": 0,
                "dry_run_records": 0,
                "response_hashes": set(),
                "latest_recorded_at": record.get("recorded_at"),
                "latest_record_id": record.get("record_id"),
            }

        group = grouped[prompt_hash]
        group["records"] += 1
        group["response_hashes"].add(response_hash)
        group["latest_recorded_at"] = group["latest_recorded_at"] or record.get("recorded_at")
        group["latest_record_id"] = group["latest_record_id"] or record.get("record_id")

        if mode == "live" or record.get("live") is True:
            group["live_records"] += 1
        elif mode == "dry_run" or record.get("live") is False:
            group["dry_run_records"] += 1

    result: list[dict[str, Any]] = []

    for group in grouped.values():
        response_hashes = sorted(group["response_hashes"])
        result.append(
            {
                "prompt_hash": group["prompt_hash"],
                "records": group["records"],
                "live_records": group["live_records"],
                "dry_run_records": group["dry_run_records"],
                "unique_response_hashes": len(response_hashes),
                "response_hashes": response_hashes,
                "same_prompt_different_responses": len(response_hashes) > 1,
                "latest_recorded_at": group["latest_recorded_at"],
                "latest_record_id": group["latest_record_id"],
            }
        )

    result.sort(key=lambda item: str(item.get("latest_recorded_at") or ""), reverse=True)
    return result


def _comparison(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) < 2:
        return {
            "accepted": False,
            "reason": "at least two run records are required for comparison",
            "records_found": len(records),
        }

    latest = records[0]
    previous = records[1]

    latest_prompt_hash = latest.get("prompt_hash")
    previous_prompt_hash = previous.get("prompt_hash")
    latest_response_hash = latest.get("response_hash")
    previous_response_hash = previous.get("response_hash")

    return {
        "accepted": True,
        "reason": "latest two records compared",
        "latest_record_id": latest.get("record_id"),
        "previous_record_id": previous.get("record_id"),
        "latest_mode": latest.get("mode"),
        "previous_mode": previous.get("mode"),
        "latest_live": latest.get("live"),
        "previous_live": previous.get("live"),
        "same_prompt_hash": latest_prompt_hash == previous_prompt_hash,
        "same_response_hash": latest_response_hash == previous_response_hash,
        "latest_prompt_hash": latest_prompt_hash,
        "previous_prompt_hash": previous_prompt_hash,
        "latest_response_hash": latest_response_hash,
        "previous_response_hash": previous_response_hash,
    }


def run_ledger_summary() -> dict[str, Any]:
    records = _read_ledger_records()
    prompt_groups = _prompt_groups(records)
    latest_records = records[:25]

    live_records = sum(1 for record in records if record.get("live") is True or record.get("mode") == "live")
    dry_run_records = sum(1 for record in records if record.get("live") is False or record.get("mode") == "dry_run")

    return {
        "accepted": True,
        "ledger_ui_version": RUN_LEDGER_UI_VERSION,
        "generated_at": _utc_now(),
        "ledger_path": str(LEDGER_PATH),
        "ledger_exists": LEDGER_PATH.exists(),
        "records_found": len(records),
        "live_records": live_records,
        "dry_run_records": dry_run_records,
        "records": latest_records,
        "latest_records": latest_records,
        "prompt_groups": prompt_groups,
        "comparison": _comparison(records),
    }


async def _form_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                return body
        except Exception:
            return {}

    try:
        form = await request.form()
        return dict(form)
    except Exception:
        return {}


async def _run_openai_and_record(request: Request, *, live: bool) -> dict[str, Any]:
    from omega_runtime.openai_live import OpenAILiveRequest, run_openai_live
    from omega_runtime.run_ledger import write_run_record

    form = await _form_payload(request)

    prompt = str(form.get("prompt") or DEFAULT_PROMPT).strip() or DEFAULT_PROMPT
    model = str(form.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    max_output_tokens = _safe_int(form.get("max_output_tokens"), DEFAULT_MAX_OUTPUT_TOKENS)

    openai_request = OpenAILiveRequest(
        prompt=prompt,
        model=model,
        live=live,
        max_output_tokens=max_output_tokens,
    )

    report = dict(run_openai_live(openai_request))
    report["ui_command"] = "run-ledger-live-openai" if live else "run-ledger-dry-run-openai"
    report["ledger_ui_version"] = RUN_LEDGER_UI_VERSION

    source = "ui.live_openai" if live else "ui.dry_run_openai"
    record_result = write_run_record(report, source=source)

    report["ledger_recorded"] = bool(record_result.get("accepted"))
    report["ledger_record"] = record_result
    report["summary"] = run_ledger_summary()

    if live:
        report["message"] = "Live OpenAI run recorded"
        report["reason"] = report.get("reason") or "Live OpenAI run recorded"
    else:
        report["message"] = "Dry-run OpenAI run recorded"
        report["reason"] = report.get("reason") or "Dry-run OpenAI run recorded"

    return report


def _json_pretty(payload: Any) -> str:
    return html.escape(json.dumps(payload, indent=2, sort_keys=True, default=str))


def _short(value: Any, length: int = 14) -> str:
    text = str(value or "")
    if len(text) <= length:
        return text
    return text[:length]


def _record_cards(records: list[dict[str, Any]]) -> str:
    if not records:
        return """
        <article class="card muted">
            <h3>No run records yet</h3>
            <p>Run a dry-run or LIVE OpenAI request from this console, or run the CLI with <code>python -m omega_runtime.cli openai --live</code>.</p>
        </article>
        """

    cards: list[str] = []

    for record in records[:25]:
        mode = html.escape(str(record.get("mode") or "unknown"))
        live = bool(record.get("live"))
        badge_class = "badge live" if live else "badge dry"
        accepted = html.escape(str(record.get("accepted")))
        record_id = html.escape(str(record.get("record_id") or ""))
        recorded_at = html.escape(str(record.get("recorded_at") or ""))
        model = html.escape(str(record.get("model") or ""))
        prompt_hash = html.escape(_short(record.get("prompt_hash"), 18))
        response_hash = html.escape(_short(record.get("response_hash"), 18))
        aggregate_hash = html.escape(_short(record.get("aggregate_hash"), 18))
        record_path = html.escape(str(record.get("record_path") or ""))

        cards.append(
            f"""
            <article class="card">
                <div class="card-head">
                    <span class="{badge_class}">{mode}</span>
                    <strong>{record_id}</strong>
                </div>
                <div class="grid">
                    <div><span>Accepted</span><b>{accepted}</b></div>
                    <div><span>Model</span><b>{model}</b></div>
                    <div><span>Recorded</span><b>{recorded_at}</b></div>
                    <div><span>Prompt hash</span><b>{prompt_hash}</b></div>
                    <div><span>Response hash</span><b>{response_hash}</b></div>
                    <div><span>Aggregate hash</span><b>{aggregate_hash}</b></div>
                </div>
                <p class="path">{record_path}</p>
            </article>
            """
        )

    return "\n".join(cards)


def _render_html(message: str | None = None) -> str:
    summary = run_ledger_summary()
    records = summary.get("records", [])
    comparison = summary.get("comparison", {})
    prompt_groups = summary.get("prompt_groups", [])

    escaped_message = html.escape(message or "")

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>OMEGA Run Ledger Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        :root {{
            color-scheme: dark;
            --bg: #08111f;
            --panel: #101c2f;
            --panel2: #13243d;
            --text: #e5eefc;
            --muted: #9fb0c8;
            --line: rgba(255,255,255,0.12);
            --good: #34d399;
            --warn: #fbbf24;
            --accent: #38bdf8;
            --danger: #fb7185;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            margin: 0;
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 34rem),
                radial-gradient(circle at top right, rgba(52, 211, 153, 0.12), transparent 30rem),
                var(--bg);
            color: var(--text);
        }}
        main {{
            width: min(1180px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 32px 0 56px;
        }}
        .hero {{
            padding: 28px;
            border: 1px solid var(--line);
            border-radius: 28px;
            background: rgba(16, 28, 47, 0.78);
            box-shadow: 0 24px 70px rgba(0,0,0,0.30);
        }}
        .hero h1 {{
            margin: 0 0 10px;
            font-size: clamp(30px, 5vw, 56px);
            letter-spacing: -0.05em;
        }}
        .hero p {{ color: var(--muted); max-width: 900px; line-height: 1.6; }}
        .version {{ color: var(--accent); font-weight: 800; }}
        .actions {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 22px;
        }}
        form {{
            border: 1px solid var(--line);
            background: rgba(19, 36, 61, 0.86);
            border-radius: 22px;
            padding: 18px;
        }}
        label {{
            display: block;
            color: var(--muted);
            font-size: 13px;
            margin: 10px 0 6px;
        }}
        textarea, input {{
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 11px 12px;
            background: rgba(8,17,31,0.9);
            color: var(--text);
            outline: none;
        }}
        textarea {{ min-height: 92px; resize: vertical; }}
        button {{
            margin-top: 14px;
            width: 100%;
            border: 0;
            border-radius: 16px;
            padding: 13px 16px;
            font-weight: 900;
            cursor: pointer;
            color: #04111f;
            background: var(--accent);
        }}
        .live-button {{
            background: linear-gradient(135deg, var(--good), var(--warn));
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
            margin: 18px 0;
        }}
        .stat, .card, .panel {{
            border: 1px solid var(--line);
            border-radius: 22px;
            background: rgba(16, 28, 47, 0.72);
            padding: 18px;
        }}
        .stat span, .grid span {{ color: var(--muted); font-size: 12px; display:block; }}
        .stat b {{ display:block; font-size: 28px; margin-top: 4px; }}
        .records {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 14px;
        }}
        .card-head {{
            display:flex;
            gap: 12px;
            align-items:center;
            justify-content:space-between;
            margin-bottom: 14px;
        }}
        .badge {{
            display:inline-flex;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 12px;
            font-weight: 900;
        }}
        .badge.live {{ background: rgba(52,211,153,0.16); color: var(--good); }}
        .badge.dry {{ background: rgba(251,191,36,0.16); color: var(--warn); }}
        .grid {{
            display:grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}
        .grid b {{ font-size: 13px; overflow-wrap:anywhere; }}
        .path {{
            color: var(--muted);
            font-size: 12px;
            overflow-wrap:anywhere;
        }}
        pre {{
            white-space: pre-wrap;
            overflow-wrap:anywhere;
            background: rgba(8,17,31,0.92);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 16px;
            color: #c7d2fe;
        }}
        .message {{
            margin: 18px 0;
            padding: 14px 16px;
            border-radius: 18px;
            border: 1px solid rgba(52,211,153,0.4);
            background: rgba(52,211,153,0.12);
            color: var(--good);
            font-weight: 800;
        }}
        .api-links {{
            color: var(--muted);
            font-size: 13px;
            margin-top: 10px;
        }}
        .api-links code {{ color: var(--text); }}
        @media (max-width: 820px) {{
            .actions, .stats, .grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <main>
        <section class="hero">
            <div class="version">{RUN_LEDGER_UI_VERSION}</div>
            <h1>OMEGA Run Ledger Console</h1>
            <p>
                Run OpenAI from the UI, record every result into the ledger, and compare whether the same prompt produced the same or different output.
                API: <code>/run-ledger/api/summary</code>. LIVE action: <code>/run-ledger/api/record-live-run</code>.
            </p>

            {f'<div class="message">{escaped_message}</div>' if escaped_message else ''}

            <div class="stats">
                <div class="stat"><span>Total records</span><b>{summary.get("records_found", 0)}</b></div>
                <div class="stat"><span>LIVE records</span><b>{summary.get("live_records", 0)}</b></div>
                <div class="stat"><span>Dry-run records</span><b>{summary.get("dry_run_records", 0)}</b></div>
                <div class="stat"><span>Prompt groups</span><b>{len(prompt_groups)}</b></div>
            </div>

            <div class="actions">
                <form method="post" action="/run-ledger/api/record-dry-run-ui">
                    <h2>Dry-run record</h2>
                    <p class="api-links">No API call. Records a simulated run.</p>
                    <label>Prompt</label>
                    <textarea name="prompt">{html.escape(DEFAULT_PROMPT)}</textarea>
                    <label>Model</label>
                    <input name="model" value="{html.escape(DEFAULT_MODEL)}" />
                    <label>Max output tokens</label>
                    <input name="max_output_tokens" value="{DEFAULT_MAX_OUTPUT_TOKENS}" />
                    <button type="submit">Run dry-run + Record</button>
                </form>

                <form method="post" action="/run-ledger/api/record-live-run">
                    <h2>LIVE OpenAI record</h2>
                    <p class="api-links">Uses <code>OPENAI_API_KEY</code>. This is an actual API call.</p>
                    <label>Prompt</label>
                    <textarea name="prompt">{html.escape(DEFAULT_PROMPT)}</textarea>
                    <label>Model</label>
                    <input name="model" value="{html.escape(DEFAULT_MODEL)}" />
                    <label>Max output tokens</label>
                    <input name="max_output_tokens" value="{DEFAULT_MAX_OUTPUT_TOKENS}" />
                    <button class="live-button" type="submit" title="Run LIVE OpenAI + record">Run LIVE OpenAI + Record</button>
                    <span style="display:none">Run LIVE OpenAI + record</span>
                </form>
            </div>
        </section>

        <section class="panel" style="margin-top:18px;">
            <h2>Latest comparison</h2>
            <pre>{_json_pretty(comparison)}</pre>
        </section>

        <section class="panel" style="margin-top:18px;">
            <h2>Latest run records</h2>
            <div class="records">
                {_record_cards(records)}
            </div>
        </section>

        <section class="panel" style="margin-top:18px;">
            <h2>Prompt groups</h2>
            <pre>{_json_pretty(prompt_groups[:12])}</pre>
        </section>
    </main>
</body>
</html>
"""


def register_run_ledger_routes(app: Any) -> None:
    @app.get("/run-ledger", response_class=HTMLResponse)
    def run_ledger_page(request: Request) -> HTMLResponse:
        message = request.query_params.get("message")
        return HTMLResponse(_render_html(message))

    @app.get("/ui/run-ledger", response_class=HTMLResponse)
    def run_ledger_page_alias(request: Request) -> HTMLResponse:
        message = request.query_params.get("message")
        return HTMLResponse(_render_html(message))

    @app.get("/run-ledger/api/summary")
    def run_ledger_summary_endpoint() -> JSONResponse:
        return JSONResponse(run_ledger_summary())

    @app.post("/run-ledger/api/record-dry-run")
    async def record_dry_run(request: Request) -> JSONResponse:
        payload = await _run_openai_and_record(request, live=False)
        payload["message"] = "Dry-run OpenAI run recorded"
        return JSONResponse(payload)

    @app.post("/run-ledger/api/record-dry-run-ui")
    async def record_dry_run_ui(request: Request) -> RedirectResponse:
        await _run_openai_and_record(request, live=False)
        return RedirectResponse(
            "/ui/run-ledger?message=Dry-run%20OpenAI%20run%20recorded",
            status_code=303,
        )

    @app.post("/run-ledger/api/record-live")
    async def record_live_run(request: Request) -> JSONResponse:
        payload = await _run_openai_and_record(request, live=True)
        payload["message"] = "Live OpenAI run recorded"
        return JSONResponse(payload)

    @app.post("/run-ledger/api/record-live-run")
    async def record_live_run_ui(request: Request) -> RedirectResponse:
        await _run_openai_and_record(request, live=True)
        return RedirectResponse(
            "/ui/run-ledger?message=Live%20OpenAI%20run%20recorded",
            status_code=303,
        )
