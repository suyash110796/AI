from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


FAILURE_LAB_DASHBOARD_VERSION = "OMEGA_FAILURE_LAB_DASHBOARD_V1"
DEFAULT_REPORT_PATH = Path("artifacts/failure_lab/failure_lab_report.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return str(value)


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()

    for index, char in enumerate(text):
        if char != "{":
            continue

        try:
            value, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    return None


def latest_failure_lab_report() -> dict[str, Any]:
    if not DEFAULT_REPORT_PATH.exists():
        return {
            "accepted": False,
            "reason": "failure lab report not generated yet",
            "dashboard_version": FAILURE_LAB_DASHBOARD_VERSION,
            "generated_at": _utc_now(),
            "report_path": str(DEFAULT_REPORT_PATH),
            "report_exists": False,
            "hint": "POST /failure-lab/run to generate the report.",
        }

    try:
        payload = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "accepted": False,
            "reason": f"failure lab report unreadable: {exc}",
            "dashboard_version": FAILURE_LAB_DASHBOARD_VERSION,
            "generated_at": _utc_now(),
            "report_path": str(DEFAULT_REPORT_PATH),
            "report_exists": True,
        }

    if not isinstance(payload, dict):
        return {
            "accepted": False,
            "reason": "failure lab report is not a JSON object",
            "dashboard_version": FAILURE_LAB_DASHBOARD_VERSION,
            "generated_at": _utc_now(),
            "report_path": str(DEFAULT_REPORT_PATH),
            "report_exists": True,
        }

    payload.setdefault("dashboard_version", FAILURE_LAB_DASHBOARD_VERSION)
    payload.setdefault("report_path", str(DEFAULT_REPORT_PATH))
    payload.setdefault("report_exists", True)
    return payload


def run_failure_lab_for_dashboard() -> dict[str, Any]:
    script = Path("scripts/demo_failure_lab.py")

    if not script.exists():
        return {
            "accepted": False,
            "reason": "scripts/demo_failure_lab.py not found",
            "dashboard_version": FAILURE_LAB_DASHBOARD_VERSION,
            "generated_at": _utc_now(),
            "report_path": str(DEFAULT_REPORT_PATH),
            "report_exists": DEFAULT_REPORT_PATH.exists(),
        }

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )

    parsed = _parse_first_json_object(completed.stdout)
    latest = latest_failure_lab_report()

    if parsed is not None:
        payload = parsed
    else:
        payload = latest

    payload.setdefault("dashboard_version", FAILURE_LAB_DASHBOARD_VERSION)
    payload.setdefault("generated_at", _utc_now())
    payload.setdefault("report_path", str(DEFAULT_REPORT_PATH))
    payload.setdefault("report_exists", DEFAULT_REPORT_PATH.exists())
    payload["runner"] = "scripts/demo_failure_lab.py"
    payload["subprocess_returncode"] = completed.returncode
    payload["stderr"] = completed.stderr

    if completed.returncode != 0:
        payload["accepted"] = False
        payload.setdefault("reason", "failure lab script failed")

    return payload


def _dashboard_html() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OMEGA Failure Lab Dashboard</title>
  <style>
    :root {
      --bg: #070b16;
      --panel: #101827;
      --panel2: #0c1220;
      --text: #eef4ff;
      --muted: #9aa8c7;
      --line: rgba(255,255,255,0.12);
      --good: #4ade80;
      --bad: #fb7185;
      --warn: #facc15;
      --blue: #60a5fa;
      --purple: #a78bfa;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(96,165,250,0.22), transparent 32%),
        radial-gradient(circle at top right, rgba(167,139,250,0.18), transparent 28%),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      max-width: 1180px;
      margin: 0 auto;
      padding: 36px 22px 60px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.35fr 0.65fr;
      gap: 22px;
      margin-bottom: 22px;
    }

    .card {
      background: linear-gradient(180deg, rgba(16,24,39,0.94), rgba(12,18,32,0.96));
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 20px 80px rgba(0,0,0,0.36);
      padding: 24px;
    }

    .eyebrow {
      color: var(--blue);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-weight: 900;
      margin-bottom: 12px;
    }

    h1 {
      margin: 0 0 12px;
      font-size: clamp(36px, 5vw, 62px);
      line-height: 0.95;
      letter-spacing: -0.055em;
    }

    .subtitle {
      color: var(--muted);
      max-width: 780px;
      line-height: 1.65;
      font-size: 16px;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }

    button, a.button {
      border: 0;
      border-radius: 14px;
      padding: 13px 16px;
      font-weight: 900;
      cursor: pointer;
      color: #05101f;
      background: linear-gradient(90deg, var(--good), var(--blue));
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    button.secondary, a.secondary {
      background: transparent;
      color: var(--text);
      border: 1px solid var(--line);
    }

    .metric {
      display: grid;
      gap: 8px;
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.035);
      margin-bottom: 14px;
    }

    .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 900;
    }

    .value {
      font-size: 28px;
      font-weight: 950;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 14px;
      margin: 22px 0;
    }

    .scenario {
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.035);
      padding: 16px;
      min-height: 160px;
    }

    .scenario h3 {
      margin: 0 0 10px;
      font-size: 15px;
      line-height: 1.25;
    }

    .scenario p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }

    .pill {
      display: inline-flex;
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 950;
      margin-bottom: 12px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.04);
    }

    .pass { color: var(--good); }
    .fail { color: var(--bad); }
    .warn { color: var(--warn); }

    .compare {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 22px;
    }

    pre {
      margin: 0;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      color: #d8e5ff;
      background: #050814;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      max-height: 520px;
      font-size: 12px;
      line-height: 1.5;
    }

    .status {
      margin-top: 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }

    .footer {
      margin-top: 26px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }

    @media (max-width: 960px) {
      .hero, .compare { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr 1fr; }
    }

    @media (max-width: 620px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="card">
        <div class="eyebrow">OMEGA Runtime ? Failure Demonstration Lab</div>
        <h1>OMEGA Failure Lab Dashboard</h1>
        <p class="subtitle">
          Show what the firewall catches. This page demonstrates the difference between
          ordinary agent logs and OMEGA proof-carrying execution: certificates, receipts,
          replay verification, tamper detection, missing-evidence rejection, and system audit.
        </p>

        <div class="actions">
          <button onclick="runFailureLab()">Run failure lab</button>
          <button class="secondary" onclick="loadLatestReport()">Load Latest Report</button>
          <a class="button secondary" href="/failure-lab/report" target="_blank">Open JSON Report</a>
          <a class="button secondary" href="/docs" target="_blank">Open API Docs</a>
        </div>

        <div id="status" class="status">
          Ready. Click <strong>Run failure lab</strong> to generate a fresh report.
        </div>
      </div>

      <div class="card">
        <div class="metric">
          <div class="label">System verdict</div>
          <div id="verdict" class="value warn">WAITING</div>
        </div>
        <div class="metric">
          <div class="label">Scenarios passed</div>
          <div id="passed" class="value">?</div>
        </div>
        <div class="metric">
          <div class="label">Scenarios failed</div>
          <div id="failed" class="value">?</div>
        </div>
      </div>
    </section>

    <section class="grid" id="scenarioGrid">
      <div class="scenario"><div class="pill warn">WAITING</div><h3>Valid system</h3><p>Untampered proof bundle plus untampered replay trace should pass.</p></div>
      <div class="scenario"><div class="pill warn">WAITING</div><h3>Tampered proof bundle</h3><p>A bundle changed after hashing/signing should be rejected.</p></div>
      <div class="scenario"><div class="pill warn">WAITING</div><h3>Tampered replay trace</h3><p>A changed trace should fail hash-chain replay verification.</p></div>
      <div class="scenario"><div class="pill warn">WAITING</div><h3>Missing proof bundle</h3><p>The system should reject unverifiable missing evidence.</p></div>
      <div class="scenario"><div class="pill warn">WAITING</div><h3>Missing replay trace</h3><p>The system should reject absent replay receipts.</p></div>
    </section>

    <section class="compare">
      <div class="card">
        <div class="eyebrow">Normal agent log</div>
        <pre>{
  "step": "tool_call",
  "status": "success",
  "message": "file read completed"
}

A normal log can say a step happened.

It usually does not prove:
- the step was allowed,
- the step was certificate-bound,
- the execution emitted receipts,
- the trace is replayable,
- the artifact was not tampered with later.</pre>
      </div>

      <div class="card">
        <div class="eyebrow">OMEGA verifier report</div>
        <pre id="jsonOutput">No report loaded yet.</pre>
        <div class="footer">
          OMEGA creates proof-carrying evidence: receipts, hashes, replay verification,
          bundle checks, system-level aggregation, and failure scenarios that demonstrate rejection.
        </div>
      </div>
    </section>
  </main>

  <script>
    const statusBox = document.getElementById("status");
    const output = document.getElementById("jsonOutput");
    const verdict = document.getElementById("verdict");
    const passed = document.getElementById("passed");
    const failed = document.getElementById("failed");
    const scenarioGrid = document.getElementById("scenarioGrid");

    function renderPayload(payload) {
      output.textContent = JSON.stringify(payload, null, 2);

      const accepted = Boolean(payload.accepted);
      verdict.textContent = accepted ? "ACCEPTED" : "REJECTED";
      verdict.className = accepted ? "value pass" : "value fail";

      passed.textContent = payload.scenarios_passed ?? "?";
      failed.textContent = payload.scenarios_failed ?? "?";

      const scenarios = payload.scenarios || [];
      if (scenarios.length > 0) {
        scenarioGrid.innerHTML = scenarios.map((s) => {
          const ok = Boolean(s.passed);
          const cls = ok ? "pass" : "fail";
          const label = ok ? "PASSED" : "FAILED";
          return `
            <div class="scenario">
              <div class="pill ${cls}">${label}</div>
              <h3>${s.title || s.name || "Scenario"}</h3>
              <p>${s.description || s.reason || ""}</p>
            </div>
          `;
        }).join("");
      }

      statusBox.innerHTML = `<strong>${payload.reason || "report loaded"}</strong>`;
    }

    async function runFailureLab() {
      statusBox.textContent = "Running failure lab...";
      output.textContent = "Running...";
      try {
        const response = await fetch("/failure-lab/run", { method: "POST" });
        const payload = await response.json();
        renderPayload(payload);
      } catch (error) {
        output.textContent = String(error);
        statusBox.textContent = "Failure lab request failed.";
      }
    }

    async function loadLatestReport() {
      statusBox.textContent = "Loading latest report...";
      try {
        const response = await fetch("/failure-lab/report");
        const payload = await response.json();
        renderPayload(payload);
      } catch (error) {
        output.textContent = String(error);
        statusBox.textContent = "Report load failed.";
      }
    }
  </script>
</body>
</html>
"""


def failure_lab_page() -> HTMLResponse:
    return HTMLResponse(_dashboard_html())


def _remove_existing_paths(app: FastAPI, paths: set[str]) -> None:
    app.router.routes = [
        route for route in app.router.routes
        if getattr(route, "path", "") not in paths
    ]


def register_failure_lab_dashboard_routes(app: FastAPI) -> None:
    dashboard_paths = {
        "/failure-lab",
        "/ui/failure-lab",
        "/failure-lab/run",
        "/failure-lab/report",
    }

    _remove_existing_paths(app, dashboard_paths)

    app.add_api_route(
        "/failure-lab",
        failure_lab_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="failure_lab_dashboard",
    )

    app.add_api_route(
        "/ui/failure-lab",
        failure_lab_page,
        methods=["GET"],
        response_class=HTMLResponse,
        include_in_schema=False,
        name="failure_lab_dashboard_alias",
    )

    app.add_api_route(
        "/failure-lab/run",
        run_failure_lab_for_dashboard,
        methods=["POST"],
        name="run_failure_lab_dashboard",
    )

    app.add_api_route(
        "/failure-lab/report",
        latest_failure_lab_report,
        methods=["GET"],
        name="latest_failure_lab_report",
    )
