from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from omega_runtime.openai_live import OpenAILiveRequest, run_openai_live
from omega_runtime.run_ledger import write_run_record

RUN_LEDGER_UI_VERSION = "OMEGA_RUN_LEDGER_UI_V1"
DEFAULT_PROMPT = "Explain the value of verifiable AI execution in one sentence for a non-technical executive."
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 300
LEDGER_PATH = Path("artifacts/openai_live/openai_run_ledger.jsonl")

router = APIRouter()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_hash(value: Any, size: int = 12) -> str:
    text = str(value or "")
    if len(text) <= size:
        return text
    return text[:size]


def _safe_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        if parsed <= 0:
            return default
        return parsed
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "json"}


def _load_records(limit: int | None = None) -> list[dict[str, Any]]:
    if not LEDGER_PATH.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)

    records.sort(key=lambda record: str(record.get("recorded_at", "")), reverse=True)
    if limit is not None:
        return records[:limit]
    return records


def _group_by_prompt(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("prompt_hash") or "unknown")].append(record)

    groups: list[dict[str, Any]] = []
    for prompt_hash, group_records in grouped.items():
        response_hashes = sorted({str(item.get("response_hash") or "") for item in group_records if item.get("response_hash")})
        modes = Counter(str(item.get("mode") or "unknown") for item in group_records)
        live_count = sum(1 for item in group_records if bool(item.get("live")))
        latest = max(group_records, key=lambda item: str(item.get("recorded_at", "")))
        groups.append(
            {
                "prompt_hash": prompt_hash,
                "prompt_hash_short": _short_hash(prompt_hash),
                "records": len(group_records),
                "response_variants": len(response_hashes),
                "response_hashes": response_hashes,
                "live_records": live_count,
                "dry_run_records": len(group_records) - live_count,
                "modes": dict(modes),
                "latest_record_id": latest.get("record_id"),
                "latest_recorded_at": latest.get("recorded_at"),
                "latest_mode": latest.get("mode"),
                "latest_response_hash": latest.get("response_hash"),
            }
        )

    groups.sort(key=lambda group: (group["records"], group.get("latest_recorded_at") or ""), reverse=True)
    return groups


def _compare_latest(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) < 2:
        return {
            "accepted": False,
            "reason": "at least two run records are required for comparison",
            "records_found": len(records),
        }

    latest, previous = records[0], records[1]
    same_prompt = latest.get("prompt_hash") == previous.get("prompt_hash")
    same_response = latest.get("response_hash") == previous.get("response_hash")
    same_mode = latest.get("mode") == previous.get("mode")
    same_model = latest.get("model") == previous.get("model")

    return {
        "accepted": True,
        "reason": "latest two runs compared",
        "latest_record_id": latest.get("record_id"),
        "previous_record_id": previous.get("record_id"),
        "latest_mode": latest.get("mode"),
        "previous_mode": previous.get("mode"),
        "latest_live": bool(latest.get("live")),
        "previous_live": bool(previous.get("live")),
        "same_prompt_hash": same_prompt,
        "same_response_hash": same_response,
        "same_mode": same_mode,
        "same_model": same_model,
        "interpretation": (
            "same request produced a different result"
            if same_prompt and not same_response
            else "same request produced the same result"
            if same_prompt and same_response
            else "different requests were compared"
        ),
    }


def build_run_ledger_summary(limit: int = 50) -> dict[str, Any]:
    all_records = _load_records()
    latest_records = all_records[:limit]
    prompt_groups = _group_by_prompt(all_records)
    live_records = sum(1 for item in all_records if bool(item.get("live")))
    dry_run_records = len(all_records) - live_records
    response_variants = len({str(item.get("response_hash") or "") for item in all_records if item.get("response_hash")})
    prompt_variants = len({str(item.get("prompt_hash") or "") for item in all_records if item.get("prompt_hash")})

    return {
        "accepted": True,
        "ledger_ui_version": RUN_LEDGER_UI_VERSION,
        "generated_at": _utc_now(),
        "ledger_path": str(LEDGER_PATH),
        "ledger_exists": LEDGER_PATH.exists(),
        "records_found": len(all_records),
        "records_returned": len(latest_records),
        "records": latest_records,
        "latest_records": latest_records,
        "live_records": live_records,
        "dry_run_records": dry_run_records,
        "prompt_variants": prompt_variants,
        "response_variants": response_variants,
        "prompt_groups": prompt_groups,
        "comparison": _compare_latest(all_records),
    }


async def _request_payload(request: Request) -> dict[str, Any]:
    body = await request.body()
    if not body:
        return {}

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            payload = json.loads(body.decode("utf-8"))
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

    # Avoid FastAPI Form(...) so the app does not require python-multipart.
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _html_escape(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _json_pretty(value: Any) -> str:
    return _html_escape(json.dumps(value, indent=2, sort_keys=True, default=str))


def _run_cards(records: list[dict[str, Any]]) -> str:
    if not records:
        return '<article class="empty-card">No runs recorded yet. Use one of the buttons above.</article>'

    cards: list[str] = []
    for record in records[:12]:
        live = bool(record.get("live"))
        mode = _html_escape(record.get("mode") or "unknown")
        badge = "LIVE" if live else "DRY RUN"
        record_id = _html_escape(record.get("record_id") or "unknown")
        prompt_hash = _html_escape(_short_hash(record.get("prompt_hash")))
        response_hash = _html_escape(_short_hash(record.get("response_hash")))
        aggregate_hash = _html_escape(_short_hash(record.get("aggregate_hash")))
        record_path = _html_escape(record.get("record_path") or "")
        recorded_at = _html_escape(record.get("recorded_at") or "")
        source = _html_escape(record.get("source") or "unknown")
        model = _html_escape(record.get("model") or "unknown")
        cards.append(
            f'''
            <article class="run-card {'live' if live else 'dry'}">
                <div class="run-card-top">
                    <span class="badge {'badge-live' if live else 'badge-dry'}">{badge}</span>
                    <span class="muted">{recorded_at}</span>
                </div>
                <h3>{record_id}</h3>
                <div class="grid-mini">
                    <div><span>Mode</span><strong>{mode}</strong></div>
                    <div><span>Model</span><strong>{model}</strong></div>
                    <div><span>Prompt</span><code>{prompt_hash}</code></div>
                    <div><span>Response</span><code>{response_hash}</code></div>
                    <div><span>Aggregate</span><code>{aggregate_hash}</code></div>
                    <div><span>Source</span><strong>{source}</strong></div>
                </div>
                <p class="path">{record_path}</p>
            </article>
            '''
        )
    return "\n".join(cards)


def _prompt_group_rows(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return '<tr><td colspan="6">No prompt groups yet.</td></tr>'

    rows: list[str] = []
    for group in groups[:10]:
        changed = "YES" if group.get("response_variants", 0) > 1 else "NO"
        rows.append(
            "<tr>"
            f"<td><code>{_html_escape(group.get('prompt_hash_short'))}</code></td>"
            f"<td>{_html_escape(group.get('records'))}</td>"
            f"<td>{_html_escape(group.get('live_records'))}</td>"
            f"<td>{_html_escape(group.get('dry_run_records'))}</td>"
            f"<td>{_html_escape(group.get('response_variants'))}</td>"
            f"<td><strong>{changed}</strong></td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_run_ledger_page(notice: str | None = None) -> str:
    summary = build_run_ledger_summary(limit=50)
    records = summary["latest_records"]
    comparison = summary["comparison"]

    css = """
    :root { color-scheme: dark; }
    body { margin: 0; font-family: Inter, Segoe UI, Arial, sans-serif; background: #07111f; color: #e8f3ff; }
    main { max-width: 1220px; margin: 0 auto; padding: 32px; }
    .hero { padding: 28px; border-radius: 28px; background: linear-gradient(135deg, rgba(45,212,191,.16), rgba(96,165,250,.12)); border: 1px solid rgba(148,163,184,.24); }
    .eyebrow { color: #5eead4; font-weight: 800; letter-spacing: .08em; font-size: 12px; text-transform: uppercase; }
    h1 { margin: 8px 0 8px; font-size: 42px; line-height: 1.05; }
    h2 { margin-top: 0; }
    p { color: #b8c7d9; }
    a { color: #93c5fd; }
    .cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 22px 0; }
    .metric, .panel, .run-card, .empty-card { border: 1px solid rgba(148,163,184,.22); border-radius: 22px; background: rgba(15,23,42,.82); box-shadow: 0 20px 70px rgba(0,0,0,.22); }
    .metric { padding: 18px; }
    .metric span { display:block; color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .metric strong { display:block; font-size: 30px; margin-top: 8px; }
    .panel { padding: 22px; margin-top: 18px; }
    .actions { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    form { display: grid; gap: 10px; }
    input { width: 100%; box-sizing: border-box; border: 1px solid rgba(148,163,184,.3); border-radius: 14px; padding: 12px 14px; background: #0b1220; color: #e2e8f0; }
    button { border: 0; border-radius: 14px; padding: 12px 16px; font-weight: 800; cursor: pointer; color: #06111f; }
    .dry-button { background: #93c5fd; }
    .live-button { background: #5eead4; }
    .warning { padding: 12px 14px; border-radius: 14px; background: rgba(251,191,36,.12); border: 1px solid rgba(251,191,36,.32); color: #fde68a; }
    .run-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
    .run-card { padding: 16px; }
    .run-card.live { border-color: rgba(94,234,212,.44); }
    .run-card.dry { border-color: rgba(147,197,253,.34); }
    .run-card-top { display:flex; justify-content:space-between; gap:10px; align-items:center; }
    .badge { border-radius: 999px; padding: 6px 10px; font-size: 11px; font-weight: 900; letter-spacing:.05em; }
    .badge-live { background: rgba(94,234,212,.16); color: #99f6e4; }
    .badge-dry { background: rgba(147,197,253,.14); color: #bfdbfe; }
    .muted { color: #94a3b8; font-size: 12px; }
    .grid-mini { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px; }
    .grid-mini div { padding: 10px; border-radius: 14px; background: rgba(2,6,23,.46); }
    .grid-mini span { display:block; color:#94a3b8; font-size: 11px; text-transform:uppercase; }
    code { color: #c4b5fd; word-break: break-all; }
    .path { font-size: 12px; word-break: break-all; }
    table { width: 100%; border-collapse: collapse; overflow: hidden; border-radius: 18px; }
    th, td { text-align: left; padding: 12px; border-bottom: 1px solid rgba(148,163,184,.16); }
    th { color:#93c5fd; font-size: 12px; text-transform: uppercase; letter-spacing:.08em; }
    pre { white-space: pre-wrap; word-break: break-word; padding: 16px; border-radius: 18px; background: #020617; border: 1px solid rgba(148,163,184,.16); }
    @media (max-width: 900px) { .cards, .actions, .run-grid { grid-template-columns: 1fr; } h1 { font-size: 32px; } main { padding: 18px; } }
    """

    notice_html = f'<section class="panel warning"><strong>{_html_escape(notice)}</strong></section>' if notice else ""

    return f'''<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <title>OMEGA Run Ledger Console</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>{css}</style>
</head>
<body>
<main>
    <section class="hero">
        <div class="eyebrow">{RUN_LEDGER_UI_VERSION}</div>
        <h1>OMEGA Run Ledger Console</h1>
        <p>Visible evidence for AI execution: what was asked, whether it was live or simulated, what came back, and whether the same request produced the same or different result.</p>
        <p>Machine summary endpoint: <a href="/run-ledger/api/summary">/run-ledger/api/summary</a></p>
    </section>

    {notice_html}

    <section class="cards">
        <div class="metric"><span>Total records</span><strong>{summary['records_found']}</strong></div>
        <div class="metric"><span>Live API runs</span><strong>{summary['live_records']}</strong></div>
        <div class="metric"><span>Dry runs</span><strong>{summary['dry_run_records']}</strong></div>
        <div class="metric"><span>Response variants</span><strong>{summary['response_variants']}</strong></div>
    </section>

    <section class="panel actions">
        <div>
            <h2>Run dry-run + record</h2>
            <p>No network call. Useful for proving the ledger path and UI flow.</p>
            <form method="post" action="/run-ledger/api/record-dry-run">
                <input name="prompt" value="{_html_escape(DEFAULT_PROMPT)}" />
                <input name="model" value="{_html_escape(DEFAULT_MODEL)}" />
                <input name="max_output_tokens" value="{DEFAULT_MAX_OUTPUT_TOKENS}" />
                <button class="dry-button" type="submit">Run dry-run + record</button>
            </form>
        </div>
        <div>
            <h2>Run LIVE OpenAI + Record</h2>
            <p>Uses OPENAI_API_KEY from your shell. The key is not stored in the ledger.</p>
            <p class="warning">This can spend API credits. Use small token limits while testing.</p>
            <form method="post" action="/run-ledger/api/record-live-run">
                <input name="prompt" value="{_html_escape(DEFAULT_PROMPT)}" />
                <input name="model" value="{_html_escape(DEFAULT_MODEL)}" />
                <input name="max_output_tokens" value="64" />
                <button class="live-button" type="submit">Run LIVE OpenAI + record</button>
            </form>
        </div>
    </section>

    <section class="panel">
        <h2>Outside-the-box insight: same prompt, response drift</h2>
        <p>This table groups runs by prompt_hash. If response variants are greater than 1, the same request produced different AI outputs.</p>
        <table>
            <thead><tr><th>Prompt hash</th><th>Runs</th><th>Live</th><th>Dry</th><th>Response variants</th><th>Changed?</th></tr></thead>
            <tbody>{_prompt_group_rows(summary['prompt_groups'])}</tbody>
        </table>
    </section>

    <section class="panel">
        <h2>Latest two-run comparison</h2>
        <pre>{_json_pretty(comparison)}</pre>
    </section>

    <section class="panel">
        <h2>Latest recorded runs</h2>
        <div class="run-grid">{_run_cards(records)}</div>
    </section>
</main>
</body>
</html>'''


async def _record_openai_run(request: Request, *, live: bool) -> Response:
    payload = await _request_payload(request)
    prompt = str(payload.get("prompt") or DEFAULT_PROMPT)
    model = str(payload.get("model") or DEFAULT_MODEL)
    max_output_tokens = _safe_int(payload.get("max_output_tokens"), DEFAULT_MAX_OUTPUT_TOKENS)

    report = run_openai_live(
        OpenAILiveRequest(
            prompt=prompt,
            model=model,
            live=live,
            max_output_tokens=max_output_tokens,
        )
    )
    report["ui_action"] = "record_live_run" if live else "record_dry_run"
    report["ledger_ui_version"] = RUN_LEDGER_UI_VERSION

    record_result = write_run_record(report, source="run_ledger_ui.live" if live else "run_ledger_ui.dry_run")
    report["ledger_recorded"] = bool(record_result.get("accepted"))
    report["ledger_record"] = record_result
    report["summary"] = build_run_ledger_summary(limit=20)

    wants_json = _safe_bool(payload.get("json")) or "application/json" in request.headers.get("accept", "").lower()
    if wants_json:
        return JSONResponse(report)

    target = "/ui/run-ledger?notice=" + ("Live+OpenAI+run+recorded" if live else "Dry-run+recorded")
    return RedirectResponse(target, status_code=303)


@router.get("/run-ledger", response_class=HTMLResponse)
async def run_ledger_page(request: Request) -> HTMLResponse:
    return HTMLResponse(render_run_ledger_page(request.query_params.get("notice")))


@router.get("/ui/run-ledger", response_class=HTMLResponse)
async def run_ledger_page_alias(request: Request) -> HTMLResponse:
    return HTMLResponse(render_run_ledger_page(request.query_params.get("notice")))


@router.get("/run-ledger/api/summary")
async def run_ledger_summary() -> JSONResponse:
    return JSONResponse(build_run_ledger_summary(limit=50))


@router.post("/run-ledger/api/record-dry-run", response_model=None)
async def record_dry_run(request: Request) -> Response:
    return await _record_openai_run(request, live=False)


@router.post("/run-ledger/api/record-live", response_model=None)
async def record_live(request: Request) -> Response:
    return await _record_openai_run(request, live=True)


@router.post("/run-ledger/api/record-live-run", response_model=None)
async def record_live_run(request: Request) -> Response:
    return await _record_openai_run(request, live=True)
