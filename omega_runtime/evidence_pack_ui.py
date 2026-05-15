from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


EVIDENCE_PACK_UI_VERSION = "OMEGA_EVIDENCE_PACK_UI_V1"
DEFAULT_REPORT_PATH = Path("artifacts/evidence_pack/evidence_pack_report.json")


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


def latest_evidence_pack_report() -> dict[str, Any]:
    if not DEFAULT_REPORT_PATH.exists():
        return {
            "accepted": False,
            "reason": "evidence pack report not generated yet",
            "evidence_pack_ui_version": EVIDENCE_PACK_UI_VERSION,
            "generated_at": _utc_now(),
            "report_exists": False,
            "report_path": str(DEFAULT_REPORT_PATH),
            "hint": "POST /evidence-pack/run to generate the evidence pack.",
        }

    try:
        payload = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "accepted": False,
            "reason": f"evidence pack report unreadable: {exc}",
            "evidence_pack_ui_version": EVIDENCE_PACK_UI_VERSION,
            "generated_at": _utc_now(),
            "report_exists": True,
            "report_path": str(DEFAULT_REPORT_PATH),
        }

    if not isinstance(payload, dict):
        return {
            "accepted": False,
            "reason": "evidence pack report is not a JSON object",
            "evidence_pack_ui_version": EVIDENCE_PACK_UI_VERSION,
            "generated_at": _utc_now(),
            "report_exists": True,
            "report_path": str(DEFAULT_REPORT_PATH),
        }

    payload.setdefault("accepted", False)
    payload.setdefault("reason", "evidence pack report loaded")
    payload.setdefault("evidence_pack_ui_version", EVIDENCE_PACK_UI_VERSION)
    payload.setdefault("generated_at", _utc_now())
    payload.setdefault("report_exists", True)
    payload.setdefault("report_path", str(DEFAULT_REPORT_PATH))

    return payload


def run_evidence_pack_for_ui() -> dict[str, Any]:
    script = Path("scripts/demo_evidence_pack.py")

    if not script.exists():
        return {
            "accepted": False,
            "reason": "scripts/demo_evidence_pack.py not found",
            "evidence_pack_ui_version": EVIDENCE_PACK_UI_VERSION,
            "generated_at": _utc_now(),
            "report_exists": DEFAULT_REPORT_PATH.exists(),
            "report_path": str(DEFAULT_REPORT_PATH),
        }

    commands = [
        [sys.executable, str(script), "--json"],
        [sys.executable, str(script)],
    ]

    last_completed: subprocess.CompletedProcess[str] | None = None

    for command in commands:
        completed = subprocess.run(
            command,
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
        )
        last_completed = completed

        parsed = _parse_first_json_object(completed.stdout)

        if parsed is not None:
            parsed.setdefault("accepted", completed.returncode == 0)
            parsed.setdefault("reason", "evidence pack generated")
            parsed["evidence_pack_ui_version"] = EVIDENCE_PACK_UI_VERSION
            parsed["runner"] = "scripts/demo_evidence_pack.py"
            parsed["command"] = command
            parsed["subprocess_returncode"] = completed.returncode
            parsed["stderr"] = completed.stderr
            parsed["report_exists"] = DEFAULT_REPORT_PATH.exists()
            parsed["report_path"] = str(DEFAULT_REPORT_PATH)

            if completed.returncode != 0:
                parsed["accepted"] = False
                parsed["reason"] = parsed.get("reason") or "evidence pack script failed"

            return parsed

        if completed.returncode == 0:
            report = latest_evidence_pack_report()
            report["runner"] = "scripts/demo_evidence_pack.py"
            report["command"] = command
            report["subprocess_returncode"] = completed.returncode
            report["stderr"] = completed.stderr
            return report

    report = latest_evidence_pack_report()

    if last_completed is not None:
        report["accepted"] = False
        report["reason"] = "evidence pack script failed"
        report["runner"] = "scripts/demo_evidence_pack.py"
        report["subprocess_returncode"] = last_completed.returncode
        report["stdout"] = last_completed.stdout
        report["stderr"] = last_completed.stderr

    return report


def _evidence_pack_html() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OMEGA Evidence Pack UI</title>
  <style>
    :root {
      --bg: #070b16;
      --panel: #111a2e;
      --panel2: #0d1324;
      --text: #eef4ff;
      --muted: #94a3b8;
      --line: rgba(255,255,255,0.12);
      --blue: #6ea8ff;
      --green: #4ade80;
      --red: #fb7185;
      --yellow: #facc15;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(110,168,255,0.18), transparent 35%),
        radial-gradient(circle at top right, rgba(74,222,128,0.12), transparent 30%),
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
      grid-template-columns: 1.25fr 0.75fr;
      gap: 20px;
      margin-bottom: 22px;
    }

    .card {
      background: linear-gradient(180deg, rgba(17,26,46,0.94), rgba(13,19,36,0.98));
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 90px rgba(0,0,0,0.35);
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
      margin: 0 0 14px;
      font-size: clamp(34px, 5vw, 58px);
      line-height: 0.96;
      letter-spacing: -0.05em;
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
      color: #06101f;
      background: linear-gradient(90deg, var(--green), var(--blue));
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
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.04);
      margin-bottom: 12px;
    }

    .metric .label {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 900;
    }

    .metric .value {
      font-size: 28px;
      font-weight: 950;
    }

    .good { color: var(--green); }
    .bad { color: var(--red); }
    .warn { color: var(--yellow); }

    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin: 22px 0;
    }

    .mini {
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.035);
      padding: 18px;
      min-height: 150px;
    }

    .mini h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }

    .mini p {
      color: var(--muted);
      line-height: 1.5;
      margin: 0;
      font-size: 13px;
    }

    .compare {
      display: grid;
      grid-template-columns: 0.85fr 1.15fr;
      gap: 18px;
      margin-top: 20px;
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
      max-height: 560px;
      font-size: 12px;
      line-height: 1.5;
    }

    .status {
      margin-top: 18px;
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }

    @media (max-width: 920px) {
      .hero, .compare { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="card">
        <div class="eyebrow">OMEGA Runtime · Evidence Pack</div>
        <h1>Export proof, trace, and failure evidence in one package.</h1>
        <div class="subtitle">
          The evidence pack is the demo artifact you can hand to someone else.
          It gathers the proof bundle, replay trace, failure lab report, hashes,
          and a ZIP archive so the run can be inspected after the fact.
        </div>

        <div class="actions">
          <button onclick="runEvidencePack()">Run evidence pack</button>
          <button class="secondary" onclick="loadReport()">Load latest report</button>
          <a class="button secondary" href="/evidence-pack/report" target="_blank">Open JSON report</a>
          <a class="button secondary" href="/docs" target="_blank">Open API docs</a>
        </div>

        <div id="status" class="status">
          Ready. Click <strong>Run evidence pack</strong> to generate a fresh export.
        </div>
      </div>

      <div class="card">
        <div class="metric">
          <div class="label">Verdict</div>
          <div id="verdict" class="value warn">WAITING</div>
        </div>
        <div class="metric">
          <div class="label">Artifacts found</div>
          <div id="found" class="value">—</div>
        </div>
        <div class="metric">
          <div class="label">ZIP archive</div>
          <div id="zip" class="value">—</div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="mini">
        <h3>1. Proof bundle</h3>
        <p>Shows the certified action evidence and policy-bound execution result.</p>
      </div>
      <div class="mini">
        <h3>2. Replay trace</h3>
        <p>Shows the hash-linked run receipt that can be replay-verified offline.</p>
      </div>
      <div class="mini">
        <h3>3. Failure lab report</h3>
        <p>Shows what the firewall catches: tampering, missing artifacts, and replay failure.</p>
      </div>
    </section>

    <section class="compare">
      <div class="card">
        <div class="eyebrow">Why this exists</div>
        <pre>A normal agent log is usually just a story.

OMEGA Evidence Pack is meant to be portable evidence.

It gives the reader:
- proof bundle path
- replay trace path
- failure lab report path
- SHA-256 hashes
- ZIP archive hash
- machine-readable report

This is the artifact you can send to someone who asks:
"Can I inspect what happened after the run?"</pre>
      </div>

      <div class="card">
        <div class="eyebrow">Machine report</div>
        <pre id="jsonOutput">No evidence pack report loaded yet.</pre>
      </div>
    </section>
  </main>

  <script>
    const output = document.getElementById("jsonOutput");
    const statusBox = document.getElementById("status");
    const verdict = document.getElementById("verdict");
    const found = document.getElementById("found");
    const zip = document.getElementById("zip");

    function renderReport(data) {
      output.textContent = JSON.stringify(data, null, 2);

      const accepted = Boolean(data.accepted);
      verdict.textContent = accepted ? "ACCEPT" : "REJECT";
      verdict.className = "value " + (accepted ? "good" : "bad");

      found.textContent = data.artifacts_found ?? data.artifact_count ?? "—";

      const archive = data.archive || {};
      zip.textContent = archive.zip_exists ? "CREATED" : "MISSING";
      zip.className = "value " + (archive.zip_exists ? "good" : "warn");

      statusBox.textContent = data.reason || "Report loaded.";
    }

    async function runEvidencePack() {
      statusBox.textContent = "Running evidence pack. This may take a few seconds...";
      output.textContent = "Running...";

      try {
        const response = await fetch("/evidence-pack/run", { method: "POST" });
        const data = await response.json();
        renderReport(data);
      } catch (error) {
        output.textContent = String(error);
        statusBox.textContent = "Evidence pack run failed.";
      }
    }

    async function loadReport() {
      statusBox.textContent = "Loading latest evidence pack report...";

      try {
        const response = await fetch("/evidence-pack/report");
        const data = await response.json();
        renderReport(data);
      } catch (error) {
        output.textContent = String(error);
        statusBox.textContent = "Report load failed.";
      }
    }
  </script>
</body>
</html>
"""


def evidence_pack_page() -> HTMLResponse:
    return HTMLResponse(_evidence_pack_html())


def register_evidence_pack_ui_routes(app: FastAPI) -> None:
    existing_paths = {getattr(route, "path", "") for route in app.routes}

    if "/evidence-pack" not in existing_paths:
        app.add_api_route(
            "/evidence-pack",
            evidence_pack_page,
            methods=["GET"],
            response_class=HTMLResponse,
            include_in_schema=False,
            name="evidence_pack_ui",
        )

    if "/ui/evidence-pack" not in existing_paths:
        app.add_api_route(
            "/ui/evidence-pack",
            evidence_pack_page,
            methods=["GET"],
            response_class=HTMLResponse,
            include_in_schema=False,
            name="evidence_pack_ui_alias",
        )

    if "/evidence-pack/run" not in existing_paths:
        app.add_api_route(
            "/evidence-pack/run",
            run_evidence_pack_for_ui,
            methods=["POST"],
            name="run_evidence_pack_ui",
        )

    if "/evidence-pack/report" not in existing_paths:
        app.add_api_route(
            "/evidence-pack/report",
            latest_evidence_pack_report,
            methods=["GET"],
            name="latest_evidence_pack_report",
        )
