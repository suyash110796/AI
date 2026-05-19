from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from omega_runtime.openai_live import OpenAILiveRequest, run_openai_live
from omega_runtime.run_ledger import write_run_record

router = APIRouter()

LEDGER_UI_VERSION = "OMEGA_RUN_LEDGER_UI_V1"
DEFAULT_PROMPT = "Explain the value of verifiable AI execution in one sentence for a non-technical executive."
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 300
LEDGER_PATH = Path("artifacts/openai_live/openai_run_ledger.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _short(value: Any, length: int = 12) -> str:
    text = "" if value is None else str(value)
    return text[:length] if text else "missing"


def _read_records(limit: int | None = None) -> list[dict[str, Any]]:
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

    records.sort(key=lambda r: str(r.get("recorded_at", "")), reverse=True)

    if limit is not None:
        return records[:limit]
    return records


def _group_by_prompt(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}

    for record in records:
        prompt_hash = str(record.get("prompt_hash") or "missing")
        response_hash = str(record.get("response_hash") or "missing")
        mode = str(record.get("mode") or "unknown").lower()
        live = bool(record.get("live")) or mode == "live"

        group = groups.setdefault(
            prompt_hash,
            {
                "prompt_hash": prompt_hash,
                "runs": 0,
                "live": 0,
                "dry": 0,
                "response_hashes": set(),
                "latest_recorded_at": "",
            },
        )

        group["runs"] += 1
        if live:
            group["live"] += 1
        else:
            group["dry"] += 1
        group["response_hashes"].add(response_hash)

        recorded_at = str(record.get("recorded_at") or "")
        if recorded_at > group["latest_recorded_at"]:
            group["latest_recorded_at"] = recorded_at

    result: list[dict[str, Any]] = []
    for group in groups.values():
        response_hashes = sorted(group["response_hashes"])
        result.append(
            {
                "prompt_hash": group["prompt_hash"],
                "runs": group["runs"],
                "live": group["live"],
                "dry": group["dry"],
                "response_variants": len(response_hashes),
                "response_hashes": response_hashes,
                "changed": len(response_hashes) > 1,
                "latest_recorded_at": group["latest_recorded_at"],
            }
        )

    result.sort(key=lambda g: (g["changed"], g["runs"], g["latest_recorded_at"]), reverse=True)
    return result


def _compare_latest(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) < 2:
        return {
            "accepted": False,
            "reason": "at least two run records are required for comparison",
            "records_found": len(records),
        }

    latest = records[0]
    previous = records[1]

    same_prompt_hash = latest.get("prompt_hash") == previous.get("prompt_hash")
    same_response_hash = latest.get("response_hash") == previous.get("response_hash")
    same_model = latest.get("model") == previous.get("model")
    same_mode = latest.get("mode") == previous.get("mode")

    if same_prompt_hash and not same_response_hash:
        interpretation = "same request produced a different result"
    elif same_prompt_hash and same_response_hash:
        interpretation = "same request produced the same result"
    else:
        interpretation = "different request compared"

    return {
        "accepted": True,
        "reason": "latest two runs compared",
        "interpretation": interpretation,
        "latest_record_id": latest.get("record_id"),
        "previous_record_id": previous.get("record_id"),
        "latest_mode": latest.get("mode"),
        "previous_mode": previous.get("mode"),
        "latest_live": bool(latest.get("live")),
        "previous_live": bool(previous.get("live")),
        "same_prompt_hash": same_prompt_hash,
        "same_response_hash": same_response_hash,
        "same_model": same_model,
        "same_mode": same_mode,
        "latest_prompt_hash": latest.get("prompt_hash"),
        "previous_prompt_hash": previous.get("prompt_hash"),
        "latest_response_hash": latest.get("response_hash"),
        "previous_response_hash": previous.get("response_hash"),
    }


def _summary_payload() -> dict[str, Any]:
    records = _read_records()
    latest_records = records[:8]
    prompt_groups = _group_by_prompt(records)

    live_records = [
        r for r in records
        if bool(r.get("live")) or str(r.get("mode", "")).lower() == "live"
    ]
    dry_run_records = [
        r for r in records
        if not (bool(r.get("live")) or str(r.get("mode", "")).lower() == "live")
    ]

    response_variants = len(
        {
            str(r.get("response_hash"))
            for r in records
            if r.get("response_hash")
        }
    )

    drift_groups = [g for g in prompt_groups if g.get("changed")]

    return {
        "accepted": True,
        "ledger_ui_version": LEDGER_UI_VERSION,
        "generated_at": _now(),
        "ledger_path": str(LEDGER_PATH),
        "ledger_exists": LEDGER_PATH.exists(),
        "records_found": len(records),
        "records": latest_records,
        "latest_records": latest_records,
        "prompt_groups": prompt_groups,
        "live_records": len(live_records),
        "dry_run_records": len(dry_run_records),
        "response_variants": response_variants,
        "drift_groups": len(drift_groups),
        "comparison": _compare_latest(records),
        "insights": {
            "ledger_has_live_api_evidence": len(live_records) > 0,
            "ledger_has_dry_run_evidence": len(dry_run_records) > 0,
            "same_prompt_drift_detected": len(drift_groups) > 0,
            "most_repeated_prompt_hash": prompt_groups[0]["prompt_hash"] if prompt_groups else None,
            "top_prompt_response_variants": prompt_groups[0]["response_variants"] if prompt_groups else 0,
        },
    }


async def _body_params(request: Request) -> dict[str, str]:
    raw = await request.body()
    parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def _run_and_record(
    *,
    prompt: str,
    model: str,
    max_output_tokens: int,
    live: bool,
    source: str,
) -> dict[str, Any]:
    request = OpenAILiveRequest(
        prompt=prompt,
        model=model,
        live=live,
        max_output_tokens=max_output_tokens,
    )

    payload = run_openai_live(request)
    payload["ui_version"] = LEDGER_UI_VERSION
    payload["ui_command"] = "record-live-run" if live else "record-dry-run"

    record_result = write_run_record(payload, source=source)

    payload["ledger_recorded"] = bool(record_result.get("accepted"))
    payload["ledger_record"] = {
        "accepted": record_result.get("accepted"),
        "reason": record_result.get("reason"),
        "record_id": record_result.get("record_id"),
        "record_path": record_result.get("record_path"),
        "ledger_path": record_result.get("ledger_path"),
        "record_file_sha256": record_result.get("record_file_sha256"),
    }

    payload["summary_after_record"] = _summary_payload()
    return payload


def _redirect_with_status(message: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"/ui/run-ledger?message={html.escape(message, quote=True)}",
        status_code=303,
    )


@router.get("/run-ledger/api/summary")
def run_ledger_summary() -> JSONResponse:
    return JSONResponse(_summary_payload())


@router.post("/run-ledger/api/record-dry-run", response_model=None)
async def record_dry_run(request: Request):
    params = await _body_params(request)

    prompt = params.get("prompt") or DEFAULT_PROMPT
    model = params.get("model") or DEFAULT_MODEL

    try:
        max_output_tokens = int(params.get("max_output_tokens") or DEFAULT_MAX_OUTPUT_TOKENS)
    except ValueError:
        max_output_tokens = DEFAULT_MAX_OUTPUT_TOKENS

    _run_and_record(
        prompt=prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        live=False,
        source="run_ledger_ui.dry_run",
    )

    return _redirect_with_status("Dry-run recorded")


@router.post("/run-ledger/api/record-live", response_model=None)
@router.post("/run-ledger/api/record-live-run", response_model=None)
async def record_live_run(request: Request):
    params = await _body_params(request)

    prompt = params.get("prompt") or DEFAULT_PROMPT
    model = params.get("model") or DEFAULT_MODEL

    try:
        max_output_tokens = int(params.get("max_output_tokens") or 64)
    except ValueError:
        max_output_tokens = 64

    _run_and_record(
        prompt=prompt,
        model=model,
        max_output_tokens=max_output_tokens,
        live=True,
        source="run_ledger_ui.live",
    )

    return _redirect_with_status("Live OpenAI run recorded")


def _render_prompt_groups(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return "<p>No prompt groups yet.</p>"

    rows = []
    for group in groups[:12]:
        changed = "YES" if group.get("changed") else "NO"
        badge_class = "danger" if group.get("changed") else "ok"
        rows.append(
            "<tr>"
            f"<td><code>{_esc(_short(group.get('prompt_hash'), 12))}</code></td>"
            f"<td>{_esc(group.get('runs'))}</td>"
            f"<td>{_esc(group.get('live'))}</td>"
            f"<td>{_esc(group.get('dry'))}</td>"
            f"<td>{_esc(group.get('response_variants'))}</td>"
            f"<td><span class='pill {badge_class}'>{changed}</span></td>"
            "</tr>"
        )

    return (
        "<table>"
        "<thead>"
        "<tr>"
        "<th>Prompt hash</th><th>Runs</th><th>Live</th><th>Dry</th>"
        "<th>Response variants</th><th>Changed?</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _render_latest_records(records: list[dict[str, Any]]) -> str:
    if not records:
        return "<p>No run records yet.</p>"

    cards = []
    for record in records[:8]:
        live = bool(record.get("live")) or str(record.get("mode", "")).lower() == "live"
        mode_label = "LIVE" if live else "DRY RUN"
        mode_class = "live" if live else "dry"
        title = _short(record.get("record_id"), 32)

        cards.append(
            "<article class='run-card'>"
            "<div class='run-card-top'>"
            f"<span class='pill {mode_class}'>{mode_label}</span>"
            f"<span>{_esc(record.get('recorded_at', 'missing'))}</span>"
            "</div>"
            f"<h3>{_esc(title)}</h3>"
            "<div class='kv-grid'>"
            f"<div><span>Mode</span><strong>{_esc(record.get('mode', 'missing'))}</strong></div>"
            f"<div><span>Model</span><strong>{_esc(record.get('model', 'missing'))}</strong></div>"
            f"<div><span>Prompt</span><strong>{_esc(_short(record.get('prompt_hash')))}</strong></div>"
            f"<div><span>Response</span><strong>{_esc(_short(record.get('response_hash')))}</strong></div>"
            f"<div><span>Aggregate</span><strong>{_esc(_short(record.get('aggregate_hash')))}</strong></div>"
            f"<div><span>Source</span><strong>{_esc(record.get('source', 'missing'))}</strong></div>"
            "</div>"
            f"<p class='path'>{_esc(record.get('record_path', 'missing'))}</p>"
            "</article>"
        )

    return "<div class='run-grid'>" + "".join(cards) + "</div>"


def _render_html(message: str | None = None) -> str:
    summary = _summary_payload()
    comparison_json = json.dumps(summary.get("comparison", {}), indent=2, sort_keys=True)
    insights_json = json.dumps(summary.get("insights", {}), indent=2, sort_keys=True)

    status = ""
    if message:
        status = f"<section class='notice'>{_esc(message)}</section>"

    prompt_groups_html = _render_prompt_groups(summary["prompt_groups"])
    latest_records_html = _render_latest_records(summary["latest_records"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>OMEGA Run Ledger Console</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root {{
  --bg: #07101f;
  --panel: #101827;
  --panel2: #172235;
  --text: #eef5ff;
  --muted: #abc4e8;
  --line: #26344d;
  --blue: #8fc5ff;
  --green: #8be8c9;
  --yellow: #f5dd68;
  --red: #ff9c9c;
  --purple: #c7a6ff;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at top left, rgba(64, 224, 208, .12), transparent 32rem),
    radial-gradient(circle at top right, rgba(143, 197, 255, .10), transparent 34rem),
    var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
}}
main {{
  width: min(1800px, calc(100vw - 72px));
  margin: 48px auto;
}}
.hero, section {{
  border: 1px solid var(--line);
  border-radius: 34px;
  background: linear-gradient(135deg, rgba(23, 34, 53, .96), rgba(15, 23, 42, .96));
  padding: 32px;
  margin-bottom: 28px;
  box-shadow: 0 24px 80px rgba(0,0,0,.26);
}}
.hero h1 {{
  font-size: clamp(44px, 6vw, 76px);
  line-height: .95;
  margin: 14px 0 20px;
}}
.version {{
  color: var(--green);
  font-weight: 900;
  letter-spacing: .12em;
}}
.lead {{
  font-size: 24px;
  color: var(--muted);
  max-width: 1650px;
}}
.notice {{
  color: var(--yellow);
  border-color: rgba(245,221,104,.35);
  background: rgba(245,221,104,.11);
  font-size: 24px;
  font-weight: 900;
}}
.metrics {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 22px;
  margin-bottom: 28px;
}}
.metric {{
  border: 1px solid var(--line);
  border-radius: 28px;
  padding: 26px;
  background: rgba(15,23,42,.8);
}}
.metric span {{
  display: block;
  color: var(--muted);
  letter-spacing: .12em;
  text-transform: uppercase;
}}
.metric strong {{
  display: block;
  font-size: 44px;
  margin-top: 12px;
}}
.forms {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 28px;
}}
form {{
  border: 1px solid var(--line);
  border-radius: 28px;
  padding: 28px;
  background: var(--panel2);
}}
form h2, section h2 {{
  font-size: 34px;
  margin: 0 0 18px;
}}
input, textarea {{
  width: 100%;
  margin: 8px 0;
  padding: 18px 20px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: #070c1a;
  color: var(--text);
  font: inherit;
  font-weight: 700;
}}
textarea {{ min-height: 110px; }}
button {{
  width: 100%;
  margin-top: 14px;
  border: 0;
  border-radius: 20px;
  padding: 20px;
  font-size: 20px;
  font-weight: 950;
  cursor: pointer;
}}
.dry-button {{ background: var(--blue); color: #020817; }}
.live-button {{ background: var(--green); color: #020817; }}
.warning {{
  color: var(--yellow);
  border: 1px solid rgba(245,221,104,.35);
  border-radius: 18px;
  padding: 14px 18px;
  background: rgba(245,221,104,.10);
}}
table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 18px;
}}
th {{
  text-align: left;
  color: var(--blue);
  text-transform: uppercase;
  letter-spacing: .11em;
}}
td, th {{
  padding: 18px;
  border-bottom: 1px solid rgba(171,196,232,.12);
}}
code {{
  color: var(--purple);
  font-weight: 900;
}}
.pill {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  border-radius: 999px;
  font-weight: 950;
  letter-spacing: .05em;
}}
.pill.ok, .pill.live {{ background: rgba(139,232,201,.18); color: var(--green); }}
.pill.danger {{ background: rgba(255,156,156,.16); color: var(--red); }}
.pill.dry {{ background: rgba(143,197,255,.18); color: var(--blue); }}
pre {{
  overflow: auto;
  background: #030615;
  border: 1px solid var(--line);
  border-radius: 24px;
  padding: 24px;
  color: #dbeafe;
  font-size: 18px;
}}
.run-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 22px;
}}
.run-card {{
  border: 1px solid rgba(139,232,201,.35);
  border-radius: 28px;
  padding: 24px;
  background: rgba(15,23,42,.82);
}}
.run-card-top {{
  display: flex;
  justify-content: space-between;
  gap: 20px;
  color: var(--muted);
}}
.run-card h3 {{
  font-size: 26px;
  overflow-wrap: anywhere;
}}
.kv-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}}
.kv-grid div {{
  background: #070c1a;
  border-radius: 18px;
  padding: 14px;
}}
.kv-grid span {{
  display: block;
  color: var(--muted);
  text-transform: uppercase;
}}
.kv-grid strong {{
  display: block;
  font-size: 22px;
  overflow-wrap: anywhere;
}}
.path {{
  color: var(--muted);
  overflow-wrap: anywhere;
}}
a {{ color: var(--blue); }}
@media (max-width: 1100px) {{
  .metrics, .forms, .run-grid {{
    grid-template-columns: 1fr;
  }}
  main {{
    width: min(100vw - 28px, 1800px);
  }}
}}
</style>
</head>
<body>
<main>
  <section class="hero">
    <div class="version">{LEDGER_UI_VERSION}</div>
    <h1>OMEGA Run Ledger Console</h1>
    <p class="lead">
      Evidence Inspector for AI execution: what was asked, whether it was live or simulated,
      what came back, whether the same prompt drifted, and where the audit record lives.
    </p>
    <p class="lead">
      Machine summary endpoint:
      <a href="/run-ledger/api/summary">/run-ledger/api/summary</a>.
      LIVE action:
      <code>/run-ledger/api/record-live-run</code>.
    </p>
  </section>

  {status}

  <div class="metrics">
    <div class="metric"><span>Total records</span><strong>{summary["records_found"]}</strong></div>
    <div class="metric"><span>Live API runs</span><strong>{summary["live_records"]}</strong></div>
    <div class="metric"><span>Dry runs</span><strong>{summary["dry_run_records"]}</strong></div>
    <div class="metric"><span>Response variants</span><strong>{summary["response_variants"]}</strong></div>
  </div>

  <section>
    <div class="forms">
      <form method="post" action="/run-ledger/api/record-dry-run">
        <h2>Run dry-run + record</h2>
        <p>No network call. Useful for proving the ledger path and UI flow.</p>
        <textarea name="prompt">{_esc(DEFAULT_PROMPT)}</textarea>
        <input name="model" value="{_esc(DEFAULT_MODEL)}" />
        <input name="max_output_tokens" value="{DEFAULT_MAX_OUTPUT_TOKENS}" />
        <button class="dry-button" type="submit">Run dry-run + record</button>
      </form>

      <form method="post" action="/run-ledger/api/record-live-run">
        <h2>Run LIVE OpenAI + Record</h2>
        <p>Uses <code>OPENAI_API_KEY</code> from your shell. The key is not stored in the ledger.</p>
        <p class="warning">This can spend API credits. Use small token limits while testing.</p>
        <textarea name="prompt">{_esc(DEFAULT_PROMPT)}</textarea>
        <input name="model" value="{_esc(DEFAULT_MODEL)}" />
        <input name="max_output_tokens" value="64" />
        <button class="live-button" type="submit">Run LIVE OpenAI + record</button>
      </form>
    </div>
  </section>

  <section>
    <h2>Outside-the-box insight: same prompt, response drift</h2>
    <p>
      This table groups runs by <code>prompt_hash</code>. If response variants are greater than 1,
      the same request produced different AI outputs.
    </p>
    {prompt_groups_html}
  </section>

  <section>
    <h2>Latest two-run comparison</h2>
    <pre>{_esc(comparison_json)}</pre>
  </section>

  <section>
    <h2>Machine-readable insight receipt</h2>
    <pre>{_esc(insights_json)}</pre>
  </section>

  <section>
    <h2>Latest recorded runs</h2>
    {latest_records_html}
  </section>
</main>
</body>
</html>"""


@router.get("/run-ledger", response_class=HTMLResponse)
@router.get("/ui/run-ledger", response_class=HTMLResponse)
def run_ledger_page(request: Request) -> HTMLResponse:
    message = request.query_params.get("message")
    return HTMLResponse(_render_html(message))
