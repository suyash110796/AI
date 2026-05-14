from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>OMEGA Runtime Dashboard</title>
  <style>
    :root {
      --bg: #070a12;
      --panel: #0d1220;
      --panel-2: #121a2e;
      --text: #e8eefc;
      --muted: #95a3bd;
      --line: rgba(255, 255, 255, 0.1);
      --green: #5ee7a4;
      --red: #ff6b7a;
      --yellow: #ffd166;
      --blue: #7aa2ff;
      --purple: #b48cff;
      --shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(122, 162, 255, 0.18), transparent 30%),
        radial-gradient(circle at top right, rgba(180, 140, 255, 0.12), transparent 32%),
        linear-gradient(180deg, #070a12 0%, #0a0f1d 100%);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      width: min(1320px, calc(100% - 40px));
      margin: 0 auto;
      padding: 32px 0 56px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.4fr 0.9fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 24px;
    }

    .card {
      background: rgba(13, 18, 32, 0.86);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }

    .hero-main {
      padding: 34px;
      position: relative;
      overflow: hidden;
    }

    .hero-main::after {
      content: "";
      position: absolute;
      width: 240px;
      height: 240px;
      border-radius: 999px;
      right: -80px;
      top: -80px;
      background: rgba(122, 162, 255, 0.16);
      filter: blur(4px);
    }

    .eyebrow {
      color: var(--green);
      font-size: 13px;
      letter-spacing: 0.14em;
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 14px;
    }

    h1 {
      margin: 0;
      max-width: 820px;
      font-size: clamp(36px, 5vw, 72px);
      line-height: 0.94;
      letter-spacing: -0.06em;
    }

    .hero-copy {
      color: var(--muted);
      max-width: 760px;
      font-size: 18px;
      line-height: 1.65;
      margin: 22px 0 0;
    }

    .status-panel {
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(94, 231, 164, 0.12);
      border: 1px solid rgba(94, 231, 164, 0.26);
      color: var(--green);
      font-weight: 800;
      width: fit-content;
    }

    .pulse {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: var(--green);
      box-shadow: 0 0 0 8px rgba(94, 231, 164, 0.12);
    }

    .status-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .metric {
      background: rgba(255, 255, 255, 0.035);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
    }

    .metric strong {
      display: block;
      font-size: 26px;
      margin-bottom: 4px;
    }

    .metric span {
      color: var(--muted);
      font-size: 13px;
    }

    .section-title {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 16px;
      margin: 30px 0 14px;
    }

    .section-title h2 {
      margin: 0;
      font-size: 24px;
      letter-spacing: -0.03em;
    }

    .section-title p {
      margin: 0;
      color: var(--muted);
    }

    .flow {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
    }

    .flow-step {
      padding: 18px;
      min-height: 160px;
      background: rgba(18, 26, 46, 0.78);
      border: 1px solid var(--line);
      border-radius: 22px;
      position: relative;
      overflow: hidden;
    }

    .flow-step::before {
      content: attr(data-step);
      display: inline-grid;
      place-items: center;
      width: 34px;
      height: 34px;
      border-radius: 12px;
      background: rgba(122, 162, 255, 0.16);
      color: var(--blue);
      font-weight: 900;
      margin-bottom: 18px;
    }

    .flow-step h3 {
      margin: 0 0 8px;
      font-size: 17px;
    }

    .flow-step p {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
      font-size: 14px;
    }

    .workspace {
      display: grid;
      grid-template-columns: 0.95fr 1.05fr;
      gap: 18px;
      margin-top: 14px;
    }

    .panel {
      padding: 22px;
    }

    .panel h2 {
      margin: 0 0 8px;
      letter-spacing: -0.03em;
    }

    .panel p {
      color: var(--muted);
      line-height: 1.55;
      margin: 0 0 18px;
    }

    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
    }

    button {
      border: 0;
      border-radius: 14px;
      padding: 12px 15px;
      color: #071018;
      background: var(--green);
      font-weight: 900;
      cursor: pointer;
    }

    button.secondary {
      color: var(--text);
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--line);
    }

    button.blue {
      background: var(--blue);
    }

    button.purple {
      background: var(--purple);
    }

    .input-grid {
      display: grid;
      gap: 10px;
    }

    label {
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }

    input {
      width: 100%;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.045);
      color: var(--text);
      border-radius: 14px;
      padding: 13px 14px;
      outline: none;
      font-size: 14px;
    }

    input:focus {
      border-color: rgba(122, 162, 255, 0.75);
      box-shadow: 0 0 0 4px rgba(122, 162, 255, 0.12);
    }

    pre {
      margin: 0;
      min-height: 420px;
      max-height: 620px;
      overflow: auto;
      background: #050814;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      color: #dce6ff;
      line-height: 1.55;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .verdict {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
      margin-top: 14px;
    }

    .verdict-card {
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.035);
    }

    .verdict-card strong {
      display: block;
      font-size: 18px;
      margin-bottom: 8px;
    }

    .verdict-card span {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    .ok {
      color: var(--green);
    }

    .warn {
      color: var(--yellow);
    }

    .bad {
      color: var(--red);
    }

    footer {
      color: var(--muted);
      text-align: center;
      padding-top: 34px;
      font-size: 13px;
    }

    @media (max-width: 980px) {
      .hero,
      .workspace {
        grid-template-columns: 1fr;
      }

      .flow {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 620px) {
      .shell {
        width: min(100% - 22px, 1320px);
      }

      .flow,
      .verdict,
      .status-grid {
        grid-template-columns: 1fr;
      }

      .hero-main {
        padding: 24px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="card hero-main">
        <div class="eyebrow">OMEGA Runtime Dashboard</div>
        <h1>Proof-carrying execution for AI agent actions.</h1>
        <p class="hero-copy">
          This dashboard shows the runtime story visually: an action is checked,
          certified, executed, receipted, replayed, bundled, and audited. The point
          is not only that an agent acted. The point is that the action can prove
          why it was allowed.
        </p>
      </div>

      <aside class="card status-panel">
        <div>
          <div class="status-pill"><span class="pulse"></span><span id="health-text">Checking API...</span></div>
        </div>

        <div class="status-grid">
          <div class="metric">
            <strong id="api-version">?</strong>
            <span>API version</span>
          </div>
          <div class="metric">
            <strong>v0.4.0</strong>
            <span>UI milestone</span>
          </div>
          <div class="metric">
            <strong>56+</strong>
            <span>test-backed checks</span>
          </div>
          <div class="metric">
            <strong>Replay</strong>
            <span>offline verification</span>
          </div>
        </div>
      </aside>
    </section>

    <section>
      <div class="section-title">
        <div>
          <h2>Execution lifecycle</h2>
          <p>What the UI must help people understand in under two minutes.</p>
        </div>
      </div>

      <div class="flow">
        <div class="flow-step" data-step="01">
          <h3>Request</h3>
          <p>The agent asks to perform a concrete tool action with arguments, nonce, run id, and step index.</p>
        </div>

        <div class="flow-step" data-step="02">
          <h3>Policy decision</h3>
          <p>The runtime checks whether the requested action is inside the allowed policy boundary.</p>
        </div>

        <div class="flow-step" data-step="03">
          <h3>Certificate</h3>
          <p>If allowed, a certificate binds the action hash, policy manifest, key id, payload hash, and signature.</p>
        </div>

        <div class="flow-step" data-step="04">
          <h3>Execution</h3>
          <p>The proxy executes only certified actions and rejects missing, wrong-key, or tampered certificates.</p>
        </div>

        <div class="flow-step" data-step="05">
          <h3>Receipt</h3>
          <p>The executed step leaves a machine-readable receipt showing what happened and what was bound.</p>
        </div>

        <div class="flow-step" data-step="06">
          <h3>Trace</h3>
          <p>Each step becomes part of a replayable trace chain so later verification does not rely on trust.</p>
        </div>

        <div class="flow-step" data-step="07">
          <h3>Bundle</h3>
          <p>Proof bundles and episode bundles package the evidence into verifiable artifacts.</p>
        </div>

        <div class="flow-step" data-step="08">
          <h3>Audit</h3>
          <p>The auditor checks artifacts and returns a final accepted/rejected system verdict.</p>
        </div>
      </div>
    </section>

    <section class="workspace">
      <div class="card panel">
        <h2>Live checks</h2>
        <p>
          Use these buttons after generating demo artifacts. They call the API and show the
          machine-readable verdicts directly in the dashboard.
        </p>

        <div class="button-row">
          <button onclick="checkHealth()">Health</button>
          <button class="blue" onclick="verifySystem()">Verify system</button>
          <button class="purple" onclick="loadOpenApi()">OpenAPI</button>
          <button class="secondary" onclick="clearOutput()">Clear</button>
        </div>

        <div class="input-grid">
          <label>
            Proof bundle path
            <input id="proof-path" value="artifacts/proof_bundle_demo.json" />
          </label>

          <label>
            Trace path
            <input id="trace-path" value="traces/replay-verifier-demo.jsonl" />
          </label>
        </div>

        <div class="verdict">
          <div class="verdict-card">
            <strong class="ok">Allowed</strong>
            <span>Actions that satisfy policy, certificate, signature, receipt, and replay checks.</span>
          </div>

          <div class="verdict-card">
            <strong class="bad">Blocked</strong>
            <span>Missing certificates, wrong keys, tampered payloads, replay failures, and path escapes.</span>
          </div>

          <div class="verdict-card">
            <strong class="warn">Auditable</strong>
            <span>The final value is post-run verification: proof, receipt, trace, and report.</span>
          </div>
        </div>
      </div>

      <div class="card panel">
        <h2>Machine output</h2>
        <p>The UI must never hide the verdict. Raw JSON stays visible.</p>
        <pre id="output">Click Health to confirm the API is running.</pre>
      </div>
    </section>

    <footer>
      OMEGA Runtime ? proof-carrying agent firewall ? local research prototype
    </footer>
  </main>

  <script>
    const output = document.getElementById("output");

    function show(value) {
      output.textContent = typeof value === "string"
        ? value
        : JSON.stringify(value, null, 2);
    }

    function clearOutput() {
      output.textContent = "";
    }

    async function requestJson(url, options = {}) {
      const response = await fetch(url, options);
      const text = await response.text();

      let payload;
      try {
        payload = JSON.parse(text);
      } catch {
        payload = { raw: text };
      }

      if (!response.ok) {
        return {
          accepted: false,
          status: response.status,
          reason: "HTTP request failed",
          detail: payload
        };
      }

      return payload;
    }

    async function checkHealth() {
      const payload = await requestJson("/health");
      document.getElementById("health-text").textContent = payload.accepted ? "API healthy" : "API error";
      document.getElementById("api-version").textContent = payload.api_version || "unknown";
      show(payload);
    }

    async function loadOpenApi() {
      const payload = await requestJson("/openapi.json");
      show(payload);
    }

    async function verifySystem() {
      const proofPath = document.getElementById("proof-path").value;
      const tracePath = document.getElementById("trace-path").value;

      const candidateBodies = [
        {
          proof_bundles: [proofPath],
          traces: [tracePath]
        },
        {
          proof_bundle_paths: [proofPath],
          trace_paths: [tracePath]
        },
        {
          proof_bundle: proofPath,
          trace: tracePath
        }
      ];

      const candidateUrls = [
        "/verify/system",
        "/system/verify",
        "/runtime/verify",
        "/audit/system"
      ];

      for (const url of candidateUrls) {
        for (const body of candidateBodies) {
          try {
            const payload = await requestJson(url, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body)
            });

            if (payload && payload.reason !== "HTTP request failed") {
              show({
                endpoint_used: url,
                request_body: body,
                response: payload
              });
              return;
            }
          } catch (error) {
            // Try the next route shape.
          }
        }
      }

      show({
        accepted: false,
        reason: "No compatible system verification endpoint found from the dashboard.",
        next_step: "Use /docs to inspect the exact API route names, then wire this button to that route.",
        proof_bundle: proofPath,
        trace: tracePath
      });
    }

    checkHealth().catch(error => {
      document.getElementById("health-text").textContent = "API unreachable";
      show({
        accepted: false,
        reason: "API health check failed",
        error: String(error)
      });
    });
  </script>
</body>
</html>
"""


def register_dashboard_routes(app: FastAPI) -> None:
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard_root() -> HTMLResponse:
        return HTMLResponse(DASHBOARD_HTML)

    @app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
    def dashboard_ui() -> HTMLResponse:
        return HTMLResponse(DASHBOARD_HTML)
