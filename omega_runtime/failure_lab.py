from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FAILURE_LAB_TYPE = "OMEGA_FAILURE_LAB_V1"
FAILURE_LAB_VERSION = "OMEGA_FAILURE_LAB_V1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _project_root() -> Path:
    return Path.cwd()


def _run_command(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=_project_root(),
        text=True,
        capture_output=True,
    )

    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def _parse_json_stdout(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return {"raw_stdout": stdout}

    return {"raw_stdout": stdout}


def _accepted_from_payload(payload: dict[str, Any], returncode: int) -> bool:
    if isinstance(payload.get("accepted"), bool):
        return bool(payload["accepted"])
    if isinstance(payload.get("passed"), bool):
        return bool(payload["passed"])
    if isinstance(payload.get("valid"), bool):
        return bool(payload["valid"])
    return returncode == 0


def _reason_from_payload(payload: dict[str, Any], fallback: str) -> str:
    reason = payload.get("reason")
    if reason is None:
        return fallback
    return str(reason)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _ensure_demo_artifacts() -> dict[str, Any]:
    proof_demo = _run_command([sys.executable, "scripts/demo_proof_bundle.py"])
    trace_demo = _run_command([sys.executable, "scripts/demo_replay_verifier.py"])

    proof_path = Path("artifacts/proof_bundle_demo.json")
    trace_path = Path("traces/replay-verifier-demo.jsonl")

    return {
        "proof_demo": proof_demo,
        "trace_demo": trace_demo,
        "proof_path": str(proof_path),
        "trace_path": str(trace_path),
        "proof_exists": proof_path.exists(),
        "trace_exists": trace_path.exists(),
        "accepted": proof_demo["passed"] and trace_demo["passed"] and proof_path.exists() and trace_path.exists(),
    }


def _verify_system(proof_bundle: Path, trace: Path) -> dict[str, Any]:
    result = _run_command(
        [
            sys.executable,
            "scripts/verify_runtime_system.py",
            "--proof-bundle",
            str(proof_bundle),
            "--trace",
            str(trace),
            "--json",
        ]
    )

    payload = _parse_json_stdout(result["stdout"])
    actual_accept = _accepted_from_payload(payload, result["returncode"])

    return {
        "command_result": result,
        "payload": payload,
        "actual_accept": actual_accept,
        "reason": _reason_from_payload(payload, "system verification command completed"),
    }


def _tamper_json_file(source: Path, target: Path) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))

    data["_failure_lab_tamper"] = {
        "tampered_at": _utc_now(),
        "tamper_type": "added unauthorized top-level field",
        "expected_effect": "hash/signature verification should reject this artifact",
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _tamper_jsonl_trace(source: Path, target: Path) -> None:
    lines = source.read_text(encoding="utf-8").splitlines()
    output_lines: list[str] = []
    tampered = False

    for line in lines:
        if not line.strip():
            continue

        if not tampered:
            try:
                entry = json.loads(line)
                entry["_failure_lab_tamper"] = {
                    "tampered_at": _utc_now(),
                    "tamper_type": "added unauthorized field to replay entry",
                    "expected_effect": "trace hash chain or replay verifier should reject this trace",
                }
                output_lines.append(json.dumps(entry, sort_keys=True))
                tampered = True
                continue
            except json.JSONDecodeError:
                output_lines.append(line + " FAILURE_LAB_TAMPER")
                tampered = True
                continue

        output_lines.append(line)

    if not output_lines:
        output_lines.append(
            json.dumps(
                {
                    "_failure_lab_tamper": {
                        "tampered_at": _utc_now(),
                        "tamper_type": "empty trace replaced by tamper marker",
                    }
                },
                sort_keys=True,
            )
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


def _scenario(
    *,
    name: str,
    title: str,
    expected_accept: bool,
    proof_bundle: Path,
    trace: Path,
    description: str,
) -> dict[str, Any]:
    verification = _verify_system(proof_bundle, trace)
    actual_accept = bool(verification["actual_accept"])
    passed = actual_accept is expected_accept

    return {
        "name": name,
        "title": title,
        "description": description,
        "expected_accept": expected_accept,
        "actual_accept": actual_accept,
        "passed": passed,
        "reason": verification["reason"],
        "proof_bundle_path": str(proof_bundle),
        "trace_path": str(trace),
        "proof_bundle_hash": _sha256_file(proof_bundle),
        "trace_hash": _sha256_file(trace),
        "verifier_payload": verification["payload"],
        "command": verification["command_result"]["command"],
        "returncode": verification["command_result"]["returncode"],
        "stderr": verification["command_result"]["stderr"],
    }


def run_failure_lab(output_dir: str | Path = "artifacts/failure_lab") -> dict[str, Any]:
    """
    Build a small failure demonstration suite.

    The lab creates fresh valid demo artifacts, then creates intentionally broken
    variants. Each scenario is passed through the same system verifier used by
    the runtime. The lab passes only if valid artifacts are accepted and broken
    artifacts are rejected.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    setup = _ensure_demo_artifacts()

    valid_proof = Path(setup["proof_path"])
    valid_trace = Path(setup["trace_path"])

    tampered_proof = output_dir / "tampered_proof_bundle.json"
    tampered_trace = output_dir / "tampered_replay_trace.jsonl"
    missing_proof = output_dir / "missing_proof_bundle.json"
    missing_trace = output_dir / "missing_trace.jsonl"

    if not setup["accepted"]:
        report: dict[str, Any] = {
            "lab_type": FAILURE_LAB_TYPE,
            "failure_lab_version": FAILURE_LAB_VERSION,
            "generated_at": _utc_now(),
            "accepted": False,
            "reason": "failed to generate baseline demo artifacts",
            "output_dir": str(output_dir),
            "setup": setup,
            "scenario_count": 0,
            "scenarios": [],
        }
        report["aggregate_hash"] = _sha256_bytes(
            json.dumps(report, sort_keys=True, default=str).encode("utf-8")
        )
        report_path = output_dir / "failure_lab_report.json"
        report["report_path"] = str(report_path)
        _write_json(report_path, report)
        return report

    _tamper_json_file(valid_proof, tampered_proof)
    _tamper_jsonl_trace(valid_trace, tampered_trace)

    scenarios = [
        _scenario(
            name="valid_system",
            title="Valid proof bundle + valid replay trace",
            expected_accept=True,
            proof_bundle=valid_proof,
            trace=valid_trace,
            description="The baseline system should accept an untampered proof bundle and replay trace.",
        ),
        _scenario(
            name="tampered_proof_bundle",
            title="Tampered proof bundle",
            expected_accept=False,
            proof_bundle=tampered_proof,
            trace=valid_trace,
            description="The system should reject a proof bundle changed after signing/hashing.",
        ),
        _scenario(
            name="tampered_trace",
            title="Tampered replay trace",
            expected_accept=False,
            proof_bundle=valid_proof,
            trace=tampered_trace,
            description="The system should reject a replay trace changed after generation.",
        ),
        _scenario(
            name="missing_proof_bundle",
            title="Missing proof bundle",
            expected_accept=False,
            proof_bundle=missing_proof,
            trace=valid_trace,
            description="The system should reject when the proof bundle artifact is missing.",
        ),
        _scenario(
            name="missing_trace",
            title="Missing replay trace",
            expected_accept=False,
            proof_bundle=valid_proof,
            trace=missing_trace,
            description="The system should reject when the replay trace artifact is missing.",
        ),
    ]

    accepted = all(bool(item["passed"]) for item in scenarios)

    report = {
        "lab_type": FAILURE_LAB_TYPE,
        "failure_lab_version": FAILURE_LAB_VERSION,
        "generated_at": _utc_now(),
        "accepted": accepted,
        "reason": "failure lab passed" if accepted else "failure lab failed",
        "output_dir": str(output_dir),
        "setup": setup,
        "scenario_count": len(scenarios),
        "scenarios_passed": sum(1 for item in scenarios if item["passed"]),
        "scenarios_failed": sum(1 for item in scenarios if not item["passed"]),
        "scenarios": scenarios,
    }

    report["aggregate_hash"] = _sha256_bytes(
        json.dumps(report, sort_keys=True, default=str).encode("utf-8")
    )

    report_path = output_dir / "failure_lab_report.json"
    report["report_path"] = str(report_path)
    _write_json(report_path, report)

    return report


def failure_lab_dashboard_html() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OMEGA Failure Demonstration Lab</title>
  <style>
    :root {
      --bg: #080b14;
      --panel: #121727;
      --panel2: #171c2e;
      --text: #eef3ff;
      --muted: #aeb8d4;
      --green: #8be6a7;
      --red: #ff7d88;
      --yellow: #ffe082;
      --blue: #94a8ff;
      --border: rgba(255,255,255,.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
      background:
        radial-gradient(circle at 20% 0%, rgba(88, 112, 255, .24), transparent 30%),
        radial-gradient(circle at 80% 20%, rgba(139, 230, 167, .12), transparent 25%),
        var(--bg);
      color: var(--text);
    }
    main {
      width: min(1180px, calc(100% - 40px));
      margin: 0 auto;
      padding: 44px 0 80px;
    }
    .hero {
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 34px;
      background: linear-gradient(135deg, rgba(18,23,39,.94), rgba(23,28,46,.78));
      box-shadow: 0 24px 100px rgba(0,0,0,.35);
    }
    .eyebrow {
      color: var(--green);
      letter-spacing: .22em;
      font-weight: 800;
      font-size: 13px;
      text-transform: uppercase;
    }
    h1 {
      font-size: clamp(42px, 6vw, 78px);
      line-height: .94;
      margin: 18px 0;
      max-width: 900px;
    }
    p {
      color: var(--muted);
      font-size: 18px;
      line-height: 1.65;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
      margin-top: 28px;
    }
    .card {
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 20px;
      background: rgba(18,23,39,.86);
    }
    .card h3 { margin: 0 0 10px; }
    .card p { font-size: 15px; margin: 0; }
    .valid { color: var(--green); }
    .bad { color: var(--red); }
    .audit { color: var(--yellow); }
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 28px 0 18px;
      align-items: center;
    }
    input {
      flex: 1;
      min-width: 280px;
      background: var(--panel2);
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 14px;
      padding: 14px 16px;
      font-size: 15px;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 14px 18px;
      font-weight: 900;
      cursor: pointer;
      background: var(--green);
      color: #06100a;
      font-size: 15px;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      min-height: 320px;
      border: 1px solid var(--border);
      background: #050713;
      border-radius: 22px;
      padding: 20px;
      color: #dfe7ff;
      overflow: auto;
    }
    .scenario {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 14px 0;
      border-bottom: 1px solid var(--border);
    }
    .pill {
      border-radius: 999px;
      padding: 7px 12px;
      font-weight: 900;
      align-self: start;
    }
    .pass { background: rgba(139,230,167,.16); color: var(--green); }
    .fail { background: rgba(255,125,136,.16); color: var(--red); }
    @media (max-width: 900px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="eyebrow">OMEGA Runtime ? v0.5.0</div>
      <h1>Failure Demonstration Lab.</h1>
      <p>
        This page shows the real firewall story: not just that valid execution is accepted,
        but that tampered proof bundles, tampered traces, missing artifacts, and broken evidence
        are rejected with machine-readable reasons.
      </p>

      <div class="grid">
        <div class="card"><h3 class="valid">Valid run</h3><p>Proof bundle + replay trace should accept.</p></div>
        <div class="card"><h3 class="bad">Tampered proof</h3><p>Post-signing mutation should reject.</p></div>
        <div class="card"><h3 class="bad">Tampered trace</h3><p>Replay evidence mutation should reject.</p></div>
        <div class="card"><h3 class="bad">Missing artifact</h3><p>Absent evidence should reject.</p></div>
        <div class="card"><h3 class="audit">Auditable report</h3><p>Every scenario leaves JSON output.</p></div>
      </div>

      <div class="controls">
        <input id="out" value="artifacts/failure_lab" />
        <button onclick="runLab()">Run failure lab</button>
        <button onclick="clearOutput()" style="background:#252b3d;color:#eef3ff;">Clear</button>
      </div>

      <div id="summary"></div>
      <pre id="output">Click "Run failure lab" to generate valid and intentionally broken artifacts.</pre>
    </section>
  </main>

  <script>
    const output = document.getElementById("output");
    const summary = document.getElementById("summary");

    function clearOutput() {
      output.textContent = "";
      summary.innerHTML = "";
    }

    function renderSummary(data) {
      if (!data.scenarios) {
        summary.innerHTML = "";
        return;
      }

      summary.innerHTML = data.scenarios.map(item => {
        const klass = item.passed ? "pass" : "fail";
        const label = item.passed ? "PASS" : "FAIL";
        return `
          <div class="scenario">
            <div>
              <strong>${item.title}</strong><br/>
              <span style="color: var(--muted);">${item.reason}</span>
            </div>
            <div class="pill ${klass}">${label}</div>
          </div>
        `;
      }).join("");
    }

    async function runLab() {
      output.textContent = "Running failure lab...";
      summary.innerHTML = "";

      try {
        const response = await fetch("/failure-lab/run", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({output_dir: document.getElementById("out").value})
        });

        const data = await response.json();
        renderSummary(data);
        output.textContent = JSON.stringify(data, null, 2);
      } catch (error) {
        output.textContent = String(error);
      }
    }
  </script>
</body>
</html>
"""


__all__ = [
    "FAILURE_LAB_TYPE",
    "FAILURE_LAB_VERSION",
    "failure_lab_dashboard_html",
    "run_failure_lab",
]
