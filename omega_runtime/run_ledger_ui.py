from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


RUN_LEDGER_UI_VERSION = "OMEGA_RUN_LEDGER_UI_V1"
DEFAULT_LEDGER_PATH = Path("artifacts/openai_live/openai_run_ledger.jsonl")


def _safe_json_loads(line: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload

    return None


def _extract_report(record: dict[str, Any]) -> dict[str, Any]:
    report = record.get("report")
    if isinstance(report, dict):
        return report
    return record


def _extract_record_view(record: dict[str, Any]) -> dict[str, Any]:
    report = _extract_report(record)

    return {
        "record_id": record.get("record_id"),
        "record_path": record.get("record_path"),
        "generated_at": report.get("generated_at") or record.get("generated_at"),
        "accepted": report.get("accepted"),
        "mode": report.get("mode"),
        "live": report.get("live"),
        "model": report.get("model"),
        "prompt_preview": report.get("prompt_preview"),
        "prompt_hash": report.get("prompt_hash"),
        "response_hash": report.get("response_hash"),
        "aggregate_hash": report.get("aggregate_hash"),
        "response_text": report.get("response_text"),
        "reason": report.get("reason"),
        "report_path": report.get("report_path"),
        "api_key_stored": report.get("api_key_stored"),
    }


def load_run_ledger_records(
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []

    records: list[dict[str, Any]] = []

    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        payload = _safe_json_loads(line)
        if payload is not None:
            records.append(_extract_record_view(payload))

    return records[-limit:]


def summarize_run_ledger(
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    limit: int = 100,
) -> dict[str, Any]:
    records = load_run_ledger_records(ledger_path=ledger_path, limit=limit)

    prompt_groups: dict[str, dict[str, Any]] = {}

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        prompt_hash = record.get("prompt_hash") or "missing"
        grouped[prompt_hash].append(record)

    for prompt_hash, group in grouped.items():
        response_hashes = sorted(
            {
                str(item.get("response_hash"))
                for item in group
                if item.get("response_hash")
            }
        )

        prompt_groups[prompt_hash] = {
            "prompt_hash": prompt_hash,
            "runs": len(group),
            "distinct_response_hashes": len(response_hashes),
            "response_hashes": response_hashes,
            "prompt_preview": group[-1].get("prompt_preview"),
            "same_prompt_different_responses": len(response_hashes) > 1,
        }

    if len(records) < 2:
        latest_comparison = {
            "accepted": False,
            "reason": "at least two run records are required for comparison",
            "records_found": len(records),
        }
    else:
        previous = records[-2]
        latest = records[-1]

        same_prompt = previous.get("prompt_hash") == latest.get("prompt_hash")
        same_response = previous.get("response_hash") == latest.get("response_hash")

        latest_comparison = {
            "accepted": True,
            "reason": "latest two run records compared",
            "previous_record_id": previous.get("record_id"),
            "latest_record_id": latest.get("record_id"),
            "same_prompt_hash": same_prompt,
            "same_response_hash": same_response,
            "same_prompt_different_response": bool(same_prompt and not same_response),
            "previous_response_hash": previous.get("response_hash"),
            "latest_response_hash": latest.get("response_hash"),
        }

    return {
        "accepted": True,
        "ledger_ui_version": RUN_LEDGER_UI_VERSION,
        "ledger_path": str(ledger_path),
        "ledger_exists": ledger_path.exists(),
        "records_found": len(records),
        "records": list(reversed(records)),
        "prompt_groups": list(prompt_groups.values()),
        "latest_comparison": latest_comparison,
        "reason": "run ledger summary generated",
    }


def _run_openai_dry_run_and_record() -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/demo_openai_run_ledger.py",
        "--json",
        "--dry-run",
    ]

    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {
            "accepted": False,
            "reason": "command completed but did not return JSON",
            "stdout": completed.stdout,
        }

    payload["ui_command"] = "record-dry-run"
    payload["returncode"] = completed.returncode
    payload["stderr"] = completed.stderr

    if completed.returncode != 0:
        payload["accepted"] = False
        payload.setdefault("reason", "dry-run ledger command failed")

    return payload


_RUN_LEDGER_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OMEGA Run Ledger Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root {
      color-scheme: dark;
      --bg: #07111f;
      --panel: rgba(15, 23, 42, 0.92);
      --panel2: rgba(30, 41, 59, 0.74);
      --text: #e5eefc;
      --muted: #94a3b8;
      --good: #34d399;
      --bad: #fb7185;
      --warn: #fbbf24;
      --line: rgba(148, 163, 184, 0.22);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(45, 212, 191, 0.18), transparent 32rem),
        radial-gradient(circle at top right, rgba(96, 165, 250, 0.18), transparent 32rem),
        var(--bg);
      color: var(--text);
    }

    main {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 60px;
    }

    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(15,23,42,.95), rgba(30,41,59,.72));
      box-shadow: 0 24px 80px rgba(0,0,0,.35);
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(32px, 5vw, 58px);
      letter-spacing: -0.05em;
    }

    .subtitle {
      margin: 0;
      max-width: 860px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.6;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin: 22px 0;
    }

    .card {
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
    }

    .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .12em;
    }

    .value {
      margin-top: 8px;
      font-size: 24px;
      font-weight: 800;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 20px 0;
    }

    button, a.button {
      appearance: none;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 12px 16px;
      color: var(--text);
      background: rgba(15, 23, 42, .86);
      cursor: pointer;
      text-decoration: none;
      font-weight: 700;
    }

    button:hover, a.button:hover {
      border-color: rgba(45, 212, 191, .75);
    }

    .section {
      margin-top: 18px;
      padding: 22px;
      border: 1px solid var(--line);
      border-radius: 26px;
      background: var(--panel);
    }

    .record {
      margin-top: 14px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--panel2);
    }

    .record h3 {
      margin: 0 0 10px;
      font-size: 18px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 800;
      border: 1px solid var(--line);
    }

    .good { color: var(--good); }
    .bad { color: var(--bad); }
    .warn { color: var(--warn); }

    code {
      color: #bfdbfe;
      word-break: break-all;
    }

    pre {
      overflow: auto;
      padding: 14px;
      border-radius: 16px;
      background: rgba(2, 6, 23, .78);
      border: 1px solid var(--line);
      color: #dbeafe;
      white-space: pre-wrap;
    }

    @media (max-width: 860px) {
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 560px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="pill good">OMEGA_RUN_LEDGER_UI_V1</div>
      <h1>OMEGA Run Ledger Console</h1>
      <p class="subtitle">
        This screen turns raw OpenAI run evidence into something readable:
        what was asked, whether it was live or dry-run, what came back,
        and whether the same prompt produced a different result.
      </p>

      <div class="toolbar">
        <button onclick="loadSummary()">Refresh ledger</button>
        <button onclick="recordDryRun()">Record dry-run</button>
        <a class="button" href="/run-ledger/api/summary" target="_blank">Open JSON summary</a>
      </div>

      <p id="status" class="subtitle">Loading run ledger...</p>
    </section>

    <section class="grid">
      <div class="card">
        <div class="label">Records</div>
        <div id="recordsFound" class="value">—</div>
      </div>
      <div class="card">
        <div class="label">Ledger exists</div>
        <div id="ledgerExists" class="value">—</div>
      </div>
      <div class="card">
        <div class="label">Same prompt drift</div>
        <div id="driftCount" class="value">—</div>
      </div>
      <div class="card">
        <div class="label">Latest comparison</div>
        <div id="latestComparison" class="value">—</div>
      </div>
    </section>

    <section class="section">
      <h2>Latest runs</h2>
      <div id="records"></div>
    </section>

    <section class="section">
      <h2>Prompt groups</h2>
      <div id="groups"></div>
    </section>
  </main>

  <script>
    async function callJson(url, options) {
      const response = await fetch(url, options || {});
      const text = await response.text();

      try {
        return JSON.parse(text);
      } catch (error) {
        return {
          accepted: false,
          reason: "Response was not JSON",
          status: response.status,
          text
        };
      }
    }

    function yesNo(value) {
      return value ? "YES" : "NO";
    }

    function shortHash(value) {
      if (!value) return "missing";
      return String(value).slice(0, 12);
    }

    function renderSummary(payload) {
      document.getElementById("recordsFound").textContent = payload.records_found ?? 0;
      document.getElementById("ledgerExists").textContent = yesNo(payload.ledger_exists);

      const driftGroups = (payload.prompt_groups || []).filter(
        group => group.same_prompt_different_responses
      );

      document.getElementById("driftCount").textContent = driftGroups.length;

      const comparison = payload.latest_comparison || {};
      document.getElementById("latestComparison").textContent =
        comparison.same_prompt_different_response ? "DRIFT" :
        comparison.accepted ? "STABLE" : "N/A";

      const records = payload.records || [];
      const recordBox = document.getElementById("records");

      if (!records.length) {
        recordBox.innerHTML = "<p class='subtitle'>No run records yet. Click Record dry-run first.</p>";
      } else {
        recordBox.innerHTML = records.map(record => `
          <div class="record">
            <h3>${record.live ? "Live OpenAI call" : "Dry-run call"} · ${record.model || "unknown model"}</h3>
            <p><span class="pill ${record.accepted ? "good" : "bad"}">${record.accepted ? "ACCEPTED" : "REJECTED"}</span></p>
            <p><strong>Time:</strong> ${record.generated_at || "missing"}</p>
            <p><strong>Prompt:</strong> ${record.prompt_preview || "missing"}</p>
            <p><strong>Prompt hash:</strong> <code>${record.prompt_hash || "missing"}</code></p>
            <p><strong>Response hash:</strong> <code>${record.response_hash || "missing"}</code></p>
            <pre>${record.response_text || ""}</pre>
          </div>
        `).join("");
      }

      const groups = payload.prompt_groups || [];
      const groupBox = document.getElementById("groups");

      if (!groups.length) {
        groupBox.innerHTML = "<p class='subtitle'>No prompt groups yet.</p>";
      } else {
        groupBox.innerHTML = groups.map(group => `
          <div class="record">
            <h3>${group.same_prompt_different_responses ? "Same prompt, different results" : "Prompt group"}</h3>
            <p><span class="pill ${group.same_prompt_different_responses ? "warn" : "good"}">
              ${group.same_prompt_different_responses ? "DRIFT DETECTED" : "NO DRIFT"}
            </span></p>
            <p><strong>Prompt:</strong> ${group.prompt_preview || "missing"}</p>
            <p><strong>Runs:</strong> ${group.runs}</p>
            <p><strong>Distinct responses:</strong> ${group.distinct_response_hashes}</p>
            <p><strong>Prompt hash:</strong> <code>${group.prompt_hash}</code></p>
            <p><strong>Response hashes:</strong> <code>${(group.response_hashes || []).map(shortHash).join(", ")}</code></p>
          </div>
        `).join("");
      }
    }

    async function loadSummary() {
      document.getElementById("status").textContent = "Loading run ledger summary...";
      const payload = await callJson("/run-ledger/api/summary");
      renderSummary(payload);
      document.getElementById("status").textContent = payload.reason || "Loaded.";
    }

    async function recordDryRun() {
      document.getElementById("status").textContent = "Recording dry-run through OMEGA ledger...";
      const payload = await callJson("/run-ledger/api/record-dry-run", { method: "POST" });
      document.getElementById("status").textContent = payload.reason || "Dry-run completed.";
      await loadSummary();
    }

    loadSummary();
  </script>
</body>
</html>
"""


def run_ledger_page() -> HTMLResponse:
    return HTMLResponse(_RUN_LEDGER_HTML)


def latest_run_ledger_summary() -> dict[str, Any]:
    return summarize_run_ledger()


def record_dry_run_from_ui() -> dict[str, Any]:
    return _run_openai_dry_run_and_record()


def register_run_ledger_ui_routes(app: FastAPI) -> None:
    existing_paths = {getattr(route, "path", "") for route in app.routes}

    if "/run-ledger" not in existing_paths:
        app.add_api_route(
            "/run-ledger",
            run_ledger_page,
            methods=["GET"],
            response_class=HTMLResponse,
            include_in_schema=False,
            name="run_ledger_page",
        )

    if "/ui/run-ledger" not in existing_paths:
        app.add_api_route(
            "/ui/run-ledger",
            run_ledger_page,
            methods=["GET"],
            response_class=HTMLResponse,
            include_in_schema=False,
            name="run_ledger_page_alias",
        )

    if "/run-ledger/api/summary" not in existing_paths:
        app.add_api_route(
            "/run-ledger/api/summary",
            latest_run_ledger_summary,
            methods=["GET"],
            name="latest_run_ledger_summary",
        )

    if "/run-ledger/api/record-dry-run" not in existing_paths:
        app.add_api_route(
            "/run-ledger/api/record-dry-run",
            record_dry_run_from_ui,
            methods=["POST"],
            name="record_dry_run_from_ui",
        )
