# OMEGA Runtime v1.0.0

**Proof-carrying runtime for controlled, replayable, and auditable agent execution.**

OMEGA Runtime is a verification framework for tool-using AI agents. It is designed around one simple rule:

> An agent should not merely say that it performed an allowed action.  
> It should produce evidence that the action was authorized, certificate-bound, executed through a controlled gateway, recorded with receipts, replayable later, and auditable as a complete artifact.

The current stable release is:

```text
v1.0.0
```

The final release checkpoint includes:

```text
83 tests passing
release check passing
main pushed
v1.0.0 tag created
working tree clean
```

---

## 1. Thirty-Second Explanation

A normal agent log might say:

```json
{
  "step": "tool_call",
  "status": "success",
  "message": "file read completed"
}
```

That is not enough.

It does not prove:

- the tool call was allowed,
- the input was not changed after approval,
- the policy was the same policy that approved the action,
- the certificate was valid,
- the runtime emitted a receipt,
- the trace was not tampered with,
- the run can be audited later.

OMEGA Runtime adds that missing evidence layer.

For every controlled action, OMEGA can answer:

1. **Was the action allowed?**
2. **Which policy allowed it?**
3. **Was it bound to a certificate?**
4. **Was the certificate signed by the expected key?**
5. **Was the action modified after approval?**
6. **Did execution happen through the proxy?**
7. **Was a receipt emitted?**
8. **Was the trace hash-linked?**
9. **Can the trace be replayed offline?**
10. **Can the evidence pack be exported and checked later?**

In short:

> OMEGA Runtime turns agent execution from “trust me” into “verify this evidence.”

---

## 2. What This Project Is

OMEGA Runtime is a runtime control and verification framework for advanced tool-using agents.

Its goal is to ensure that every tool execution is:

1. authorized by policy,
2. bound to a signed certificate,
3. tied to a specific action payload,
4. checked against runtime invariants,
5. executed only through a controlled proxy,
6. recorded in a replayable trace,
7. packaged into portable evidence,
8. verifiable offline,
9. auditable as a complete system artifact.

In simple terms:

> An agent is not allowed to simply call tools.  
> It must present proof that the requested action is lawful.  
> The runtime verifies that proof before execution.  
> Every result is recorded so the execution can be checked again later.

---

## 3. Why This Exists

Tool-using AI agents can perform real actions:

- read files,
- write files,
- call APIs,
- invoke tools,
- chain multiple steps,
- create final reports,
- generate persistent artifacts,
- trigger external workflows.

Without a verification layer, an agent can:

- call a forbidden tool,
- modify action arguments after approval,
- reuse an old certificate,
- drift from the original task,
- bypass policy checks,
- tamper with execution traces,
- forge final reports,
- hide invalid transitions,
- produce outputs that cannot be audited.

OMEGA Runtime prevents those failures by requiring **proof-carrying execution**.

The runtime does not merely ask:

> Did the agent succeed?

It asks:

> Can the agent prove that this success was authorized, bound, recorded, replayable, and auditable?

---

## 4. The Real-Life Problem It Solves

Modern AI agents are moving from chat into action.

They are increasingly expected to:

- summarize files,
- modify code,
- access internal documents,
- call SaaS APIs,
- operate workflows,
- make decisions,
- produce reports,
- coordinate multi-step tasks.

This creates a serious governance problem.

A company may need to know:

- Why did the agent take this action?
- Was the action allowed by policy?
- What exact input was approved?
- Did the input change after approval?
- Which tool actually ran?
- What did the tool return?
- Was the output tampered with?
- Can this execution be replayed later?
- Can an auditor independently verify the evidence?

Ordinary logs do not answer these questions strongly enough.

OMEGA Runtime addresses this by creating a runtime evidence chain:

```text
Action
  -> action hash
  -> policy decision
  -> policy manifest hash
  -> certificate
  -> proxy execution
  -> receipt
  -> trace entry
  -> replay verification
  -> proof bundle
  -> evidence pack
  -> release/system audit
```

This makes the execution explainable, reproducible, and auditable.

---

## 5. How OMEGA Is Different From Ordinary Agent Logs

### Ordinary Agent Log

An ordinary log can say:

```text
The agent read a file.
```

But it usually does not prove:

- the file read was allowed,
- the action was certified,
- the certificate matched the exact action,
- the policy was not changed,
- the trace was not tampered with,
- the final report was derived from valid evidence.

### OMEGA Runtime

OMEGA can produce a machine-verifiable evidence set showing:

- the action hash,
- the policy hash,
- the certificate binding,
- the receipt,
- the trace entry,
- the replay verification result,
- the proof bundle,
- the evidence pack archive hash,
- the release check output.

The key difference:

> OMEGA does not only log what happened.  
> OMEGA verifies why it was allowed and preserves evidence that can be checked later.

---

## 6. What OMEGA Is Not

OMEGA Runtime is not a claim of magical AI safety.

It is not:

- a model-weight modification system,
- a hidden memory system,
- an AGI containment system,
- a replacement for operating-system sandboxing,
- a replacement for cloud IAM,
- a replacement for secrets management,
- a replacement for human review in high-risk environments.

It is a concrete engineering framework for:

- controlled tool execution,
- proof-bound authorization,
- tamper detection,
- trace replay,
- artifact verification,
- audit-friendly evidence packaging.

---

## 7. Core Design Principle

OMEGA follows this rule:

> No action executes unless the runtime can verify that the action, policy, certificate, trace, and result are mutually consistent.

This is enforced through:

- canonical hashing,
- certificate signing,
- policy manifest binding,
- invariant checking,
- controlled proxy execution,
- structured rejection reasons,
- counterexample generation,
- append-only trace chains,
- offline replay verification,
- proof bundles,
- episode bundles,
- evidence packs,
- browser dashboards,
- final release checks.

---

## 8. Current Stable Milestone

The current stable release is:

```text
v1.0.0
```

Latest final-release validation showed:

```text
83 passed
release check passed
v1.0.0 tag pushed
main clean
```

The project history includes these milestone tags:

```text
v0.1.0-stable
v0.2.0-cli-packaging
v0.3.0-api
v0.4.0-ui-dashboard-complete
v0.5.0-failure-lab
v0.6.0-failure-lab-dashboard
v0.7.0-agent-action-playground
v0.8.0-evidence-pack
v0.9.0-evidence-pack-ui
v1.0.0-rc1-release-hardening
v1.0.0
```

---

## 9. Repository Structure

```text
omega_runtime/
  api.py
  action_playground.py
  evidence_pack_ui.py
  failure_lab_dashboard.py
  release_check.py

omega_runtime/core/
  actions.py
  auditor.py
  canonical.py
  certificates.py
  counterexample.py
  counterexamples.py
  crypto_ed25519.py
  decision_firewall.py
  episode_bundle.py
  final_verifier_report.py
  gates.py
  invariants.py
  ledger.py
  policy.py
  policy_manifest.py
  proof_bundle.py
  proxy.py
  replay.py
  replay_verifier.py
  run_context.py
  state.py
  stateful_proxy.py
  system_verifier.py
  trace_chain.py
  transitions.py
  types.py
  verifier.py

omega_runtime/tools/
  sandbox_tools.py

scripts/
  audit_runtime.py
  demo_decision_firewall.py
  demo_episode_bundle.py
  demo_evidence_pack.py
  demo_failure_lab.py
  demo_final_verifier_report.py
  demo_proof_bundle.py
  demo_replay_verifier.py
  demo_trace_chain.py
  release_check.py
  run_api.py
  verify_episode_bundle.py
  verify_final_report.py
  verify_proof_bundle.py
  verify_runtime_system.py

tests/
  test_action_playground.py
  test_action_tamper_rejected.py
  test_api.py
  test_auditor.py
  test_certificate_binds_policy_manifest.py
  test_counterexample_on_path_escape.py
  test_counterexample_on_tamper.py
  test_decision_firewall.py
  test_episode_bundle.py
  test_evidence_pack_ui.py
  test_failure_lab.py
  test_failure_lab_dashboard.py
  test_final_verifier_report.py
  test_gate_order_rejected.py
  test_illegal_transition_rejected.py
  test_no_certificate_rejected.py
  test_no_counterexample_on_accept.py
  test_packaging_cli.py
  test_path_escape_rejected.py
  test_policy_manifest_signature_tamper_rejected.py
  test_policy_manifest_tamper_rejected.py
  test_policy_manifest_valid.py
  test_proof_bundle_cli.py
  test_proof_bundle_export.py
  test_release_hardening.py
  test_replay_rejected.py
  test_replay_verifier.py
  test_signature_tamper_rejected.py
  test_system_verifier.py
  test_terminal_reentry_rejected.py
  test_trace_chain.py
  test_trace_tamper_detected.py
  test_ui_dashboard.py
  test_ui_dashboard_routes.py
  test_valid_certified_trace.py
  test_valid_transition_sequence.py
  test_wrong_key_rejected.py

policies/
  default_policy.json

specs/
  certificate_schema_v1.json
  invariants.md
  policy.v1.json
  threat_model.md

examples/
  demo_certified_file_summary.py
  demo_policy_tamper_rejected.py
  demo_replay_rejected.py
  demo_signature_tamper_rejected.py
  demo_stateful_runtime.py
  demo_tamper_rejected.py
  demo_wrong_key_rejected.py

artifacts/
  generated proof bundles, reports, evidence packs, and release reports

traces/
  replayable trace files

sandbox/
  safe demo input/output area
```

---

## 10. Installation

From project root:

```powershell
python -m pip install -e .
```

Run the full test suite:

```powershell
python -m pytest
```

Expected result for v1.0.0:

```text
83 passed
```

Run the release check:

```powershell
python scripts/release_check.py --json
```

Expected result:

```json
{
  "accepted": true,
  "reason": "release check passed",
  "release_version": "1.0.0"
}
```

---

## 11. Browser UI

Start the API server:

```powershell
python scripts/run_api.py
```

Then open these links:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/failure-lab
http://127.0.0.1:8000/action-playground
http://127.0.0.1:8000/evidence-pack
```

Use `/docs` as the source of truth for the currently registered API routes.

### What to check in the UI

Check that the dashboards show:

- accepted valid executions,
- rejected tampered executions,
- rejected missing-evidence cases,
- proof bundle details,
- replay trace details,
- evidence pack output,
- report paths,
- hashes,
- scenario results.

The important thing is not just that a page loads.

The important thing is that each page demonstrates one of the core claims:

> Valid actions pass.  
> Invalid actions fail.  
> Evidence is exported.  
> Evidence can be verified later.

---

## 12. Main CLI Validation Commands

### 12.1 Run full tests

```powershell
python -m pytest
```

Expected:

```text
83 passed
```

### 12.2 Run release check

```powershell
python scripts/release_check.py --json
```

Expected:

```json
{
  "accepted": true,
  "reason": "release check passed"
}
```

### 12.3 Generate proof bundle demo

```powershell
python scripts/demo_proof_bundle.py
```

Expected output includes:

```text
accepted: True
bundle_verified: True
verify_reason: proof bundle valid
```

### 12.4 Verify proof bundle

```powershell
python scripts/verify_proof_bundle.py artifacts\proof_bundle_demo.json --json
```

Expected:

```json
{
  "accepted": true,
  "reason": "proof bundle valid"
}
```

### 12.5 Generate replay verifier demo

```powershell
python scripts/demo_replay_verifier.py
```

Expected output includes:

```text
REPLAY VERIFIER: PASS
REPLAY REASON: offline replay verification passed
```

### 12.6 Run failure lab

```powershell
python scripts/demo_failure_lab.py
```

Expected output includes five passing scenarios:

```text
valid_system
tampered_proof_bundle
tampered_trace
missing_proof_bundle
missing_trace
```

### 12.7 Generate evidence pack

```powershell
python scripts/demo_evidence_pack.py --json
```

Expected:

```json
{
  "accepted": true,
  "reason": "evidence pack generated"
}
```

Expected generated files include:

```text
artifacts\proof_bundle_demo.json
traces\replay-verifier-demo.jsonl
artifacts\failure_lab\failure_lab_report.json
artifacts\evidence_pack\evidence_pack_report.json
artifacts\evidence_pack\omega_evidence_pack.zip
```

### 12.8 Verify complete runtime system

```powershell
python scripts/verify_runtime_system.py `
  --proof-bundle artifacts\proof_bundle_demo.json `
  --trace traces\replay-verifier-demo.jsonl `
  --json
```

Expected reason:

```text
system verification passed
```

---

## 13. Runtime Concepts

### 13.1 Action

An `Action` is a request to execute a tool.

It contains fields such as:

- `run_id`
- `step_index`
- `tool`
- `args`
- `nonce`

Example:

```python
Action(
    run_id="demo-run",
    step_index=1,
    tool="sandbox.read_file",
    args={"path": "sandbox/input.txt"},
    nonce="demo-nonce",
)
```

The action is canonicalized and hashed before certification.

If any field changes after certification, the action hash changes and verification fails.

---

### 13.2 Certificate

A certificate is a signed authorization object.

It binds together:

- the action hash,
- the policy hash,
- the run identity,
- the step index,
- the trusted key id,
- the signature,
- the payload hash.

The runtime checks the certificate before executing the action.

A certificate is rejected if:

- it is missing,
- it has the wrong key,
- its signature is invalid,
- its payload hash does not match,
- its action hash does not match the requested action,
- its policy hash does not match the current policy manifest.

---

### 13.3 Policy Manifest

The policy manifest defines what the runtime allows.

It protects the runtime from policy tampering.

The certificate is bound to a policy hash. If the policy changes after the certificate is issued, OMEGA rejects the execution.

This prevents the attack:

```text
1. Issue certificate under safe policy.
2. Modify policy later.
3. Try to execute with old certificate.
4. Runtime detects the policy mismatch and rejects.
```

---

### 13.4 OmegaProxy

`OmegaProxy` is the controlled execution gateway.

Tools should not be executed directly.

Instead, a caller sends:

1. an action,
2. a certificate.

The proxy verifies both before dispatching the tool.

The proxy returns a structured result containing:

- accepted or rejected decision,
- reason,
- output,
- receipt,
- counterexample when rejected.

---

### 13.5 Receipt

A receipt proves that a tool execution happened through the controlled runtime.

It records:

- run id,
- step index,
- action hash,
- output hash,
- execution status,
- detail string.

Receipts are later used in proof bundles, episode bundles, replay verification, evidence packs, and audits.

---

### 13.6 Counterexample

A counterexample is produced when the runtime rejects an action.

It explains:

- what invariant failed,
- what was expected,
- what was observed,
- which run and step failed,
- why the decision was `REJECT`.

Example failure categories:

- missing certificate,
- invalid signature,
- wrong certificate key,
- policy admission failure,
- path escape,
- replay attempt,
- illegal transition,
- terminal re-entry,
- policy manifest integrity failure.

Counterexamples make rejection machine-checkable and human-readable.

---

### 13.7 Invariants

Invariants are named runtime safety rules.

They classify failures precisely.

Examples include:

- wrong certificate key,
- certificate signature tamper,
- policy manifest integrity,
- path escape,
- action tamper,
- replay rejection,
- illegal transition,
- terminal re-entry.

This prevents vague rejection reasons.

Each rejection maps to a specific failed rule.

---

### 13.8 Gates

Gates are ordered checks.

Gate order matters.

Examples:

- wrong certificate key must be detected before a generic policy failure,
- policy manifest integrity must be detected before ordinary certificate mismatch,
- signature tampering must not be misclassified as policy denial.

The tests enforce this ordering.

---

### 13.9 Decision Firewall

The decision firewall protects the boundary between:

- verifier decision,
- runtime execution,
- receipt emission,
- final result.

It prevents unsafe or invalid runtime decisions from silently passing as accepted executions.

---

### 13.10 Trace Chain

The trace chain records execution events in a hash-linked structure.

Each trace entry can bind:

- action,
- certificate,
- receipt,
- previous entry hash,
- current entry hash.

This creates tamper evidence.

If an attacker changes an earlier entry, later hashes no longer match.

---

### 13.11 Replay Verifier

The replay verifier checks a trace offline.

It verifies that:

- entries are well formed,
- hash links are valid,
- replayed actions match certificates,
- receipts match executed actions,
- tampering is detected.

This means execution does not only need to pass live. It can be independently verified later.

---

### 13.12 Proof Bundle

A proof bundle packages a single verified execution into a portable artifact.

It contains:

- bundle type,
- action,
- certificate,
- receipt,
- accepted decision,
- reason,
- verification summary,
- bundle hash.

Verify a proof bundle with:

```powershell
python scripts/verify_proof_bundle.py artifacts\proof_bundle_demo.json --json
```

A valid proof bundle returns:

```json
{
  "accepted": true,
  "reason": "proof bundle valid"
}
```

If the bundle is modified, verification fails.

---

### 13.13 Episode Bundle

An episode bundle packages multiple related execution steps.

It represents a multi-step agent episode.

It contains:

- run id,
- final output,
- step count,
- ordered steps,
- action hashes,
- certificate hashes,
- receipt hashes,
- verification summary,
- bundle hash.

It verifies that:

- all steps belong to the same episode,
- all certificates are bound,
- all receipts are bound,
- all receipts correspond to executed actions,
- final output has not been tampered with,
- the bundle hash is stable.

---

### 13.14 Final Verifier Report

The final verifier report summarizes the verification state of a completed run.

It can include:

- proof bundle status,
- replay status,
- episode bundle status,
- accepted or rejected status,
- final reason,
- aggregate hash.

This layer turns low-level proofs into a final verification statement.

---

### 13.15 Auditor

The auditor verifies supplied runtime artifacts.

It can audit:

- proof bundles,
- traces,
- generated reports.

Example:

```powershell
python scripts/audit_runtime.py --proof-bundle artifacts\proof_bundle_demo.json --json
```

Example:

```powershell
python scripts/audit_runtime.py --trace traces\replay-verifier-demo.jsonl --json
```

If no artifacts are supplied, the auditor intentionally rejects:

```json
{
  "accepted": false,
  "reason": "no artifacts supplied"
}
```

---

### 13.16 System Verifier

The system verifier verifies multiple artifact types together.

Example:

```powershell
python scripts/verify_runtime_system.py `
  --proof-bundle artifacts\proof_bundle_demo.json `
  --trace traces\replay-verifier-demo.jsonl `
  --json
```

Expected valid reason:

```text
system verification passed
```

---

### 13.17 Evidence Pack

The evidence pack is the portable audit bundle.

It gathers important proof artifacts into one exportable package.

It can include:

- proof bundle,
- replay trace,
- failure lab report,
- evidence pack report,
- evidence pack zip archive,
- hashes for files inside the archive.

Generate it with:

```powershell
python scripts/demo_evidence_pack.py --json
```

Expected generated archive:

```text
artifacts\evidence_pack\omega_evidence_pack.zip
```

The evidence pack is useful when someone asks:

> Show me everything I need to verify this run later.

---

### 13.18 Release Check

The release check verifies that the repository is structurally ready for release.

It checks:

- project root,
- required files,
- required directories,
- package version,
- milestone tags,
- test suite presence,
- release scripts.

Run:

```powershell
python scripts/release_check.py --json
```

Expected:

```json
{
  "accepted": true,
  "reason": "release check passed",
  "release_version": "1.0.0"
}
```

---

## 14. What Inputs Are Being Checked?

OMEGA checks several classes of input.

### 14.1 Action input

The action input includes:

- tool name,
- arguments,
- run id,
- step index,
- nonce.

Example:

```json
{
  "tool": "sandbox.read_file",
  "args": {
    "path": "sandbox/input.txt"
  }
}
```

OMEGA checks whether this exact action is the action that was approved.

---

### 14.2 Policy input

The policy defines what is allowed.

Example questions:

- Is this tool allowed?
- Is this path allowed?
- Is this action inside the sandbox?
- Is this transition legal?

OMEGA checks that the policy used during execution matches the policy bound to the certificate.

---

### 14.3 Certificate input

The certificate proves authorization.

OMEGA checks:

- trusted key id,
- payload hash,
- action hash,
- policy hash,
- signature.

---

### 14.4 Runtime state input

Stateful runs must move through legal states.

OMEGA checks:

- valid transition order,
- no illegal transition,
- no terminal re-entry,
- no replay violation.

---

### 14.5 Artifact input

Artifacts include:

- proof bundles,
- traces,
- reports,
- evidence packs.

OMEGA checks:

- existence,
- hash integrity,
- internal consistency,
- replay validity,
- aggregate report validity.

---

## 15. Failure Scenarios OMEGA Demonstrates

### 15.1 Valid system

A valid proof bundle and valid replay trace should pass.

Expected:

```text
ACCEPT
system verification passed
```

### 15.2 Tampered proof bundle

If the proof bundle changes after generation, verification fails.

Expected:

```text
REJECT
bundle_hash mismatch
```

### 15.3 Tampered replay trace

If the trace changes after generation, replay verification fails.

Expected:

```text
REJECT
entry_hash mismatch
```

### 15.4 Missing proof bundle

If the proof bundle artifact is missing, system verification rejects or reports missing evidence.

Expected:

```text
REJECT
missing proof bundle
```

### 15.5 Missing replay trace

If the trace artifact is missing, system verification rejects or reports missing evidence.

Expected:

```text
REJECT
missing trace
```

### 15.6 Missing certificate

If an action arrives without a certificate, the proxy rejects the action.

Expected:

```text
REJECT
missing certificate
```

### 15.7 Wrong key

If the certificate uses an untrusted key id, verification fails.

Expected:

```text
REJECT
wrong key
```

### 15.8 Signature tampering

If the certificate signature is changed, verification fails.

Expected:

```text
REJECT
invalid signature
```

### 15.9 Action tampering

If the action is changed after certificate issuance, the action hash no longer matches.

Expected:

```text
REJECT
action hash mismatch
```

### 15.10 Path escape

If the action tries to read outside the sandbox, the runtime rejects it.

Example unsafe path:

```text
../README.md
```

Expected:

```text
REJECT
path escape
```

### 15.11 Policy tampering

If the policy manifest changes after certificate issuance, the certificate no longer binds to the active policy.

Expected:

```text
REJECT
policy manifest mismatch
```

### 15.12 Replay violation

If a previous authorization is reused incorrectly, replay protection rejects it.

Expected:

```text
REJECT
replay rejected
```

### 15.13 Illegal transition

If runtime state moves through an invalid transition, verification rejects it.

Expected:

```text
REJECT
illegal transition
```

### 15.14 Terminal re-entry

If a completed run tries to re-enter active execution, verification rejects it.

Expected:

```text
REJECT
terminal re-entry
```

---

## 16. API and Dashboard Routes

Start the server:

```powershell
python scripts/run_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
```

Common local dashboard links:

```text
http://127.0.0.1:8000/failure-lab
http://127.0.0.1:8000/action-playground
http://127.0.0.1:8000/evidence-pack
```

Common API routes include:

```text
GET  /health
GET  /docs

GET  /failure-lab
POST /failure-lab/run
GET  /failure-lab/report

GET  /action-playground
GET  /action-playground/scenarios
POST /action-playground/run
POST /action-playground/run-all
GET  /action-playground/report
```

Use `/docs` to inspect the exact route contract of the current build.

---

## 17. File-by-File Explanation

### `omega_runtime/api.py`

Creates the FastAPI application and registers API/dashboard routes.

This is the browser and HTTP entry point.

---

### `omega_runtime/action_playground.py`

Implements the action playground.

It provides scenarios that show:

- allowed file read,
- blocked path escape,
- missing certificate,
- tampered action,
- runtime rejection paths.

This is useful for demonstrating what the agent firewall catches.

---

### `omega_runtime/evidence_pack_ui.py`

Implements the evidence pack browser UI.

It helps demonstrate:

- generated artifacts,
- evidence pack report,
- archive path,
- artifact hashes,
- audit-friendly export.

---

### `omega_runtime/failure_lab_dashboard.py`

Implements the failure lab dashboard.

It shows the difference between a normal agent log and OMEGA proof-carrying execution.

It demonstrates:

- valid system acceptance,
- tampered proof bundle rejection,
- tampered trace rejection,
- missing proof bundle rejection,
- missing trace rejection.

---

### `omega_runtime/release_check.py`

Implements the release readiness checker.

It verifies:

- required files,
- required directories,
- package version,
- milestone tags,
- test suite presence,
- release scripts.

---

### `omega_runtime/core/actions.py`

Defines the action object.

The action is the atomic request to execute a tool.

---

### `omega_runtime/core/canonical.py`

Provides canonical serialization and hashing helpers.

Canonicalization ensures that logically equivalent objects hash consistently.

---

### `omega_runtime/core/certificates.py`

Handles certificate issuance and verification.

Responsibilities include:

- building certificate payloads,
- computing payload hashes,
- signing payloads,
- verifying trusted key id,
- verifying payload hash,
- verifying certificate signature.

---

### `omega_runtime/core/policy.py`

Evaluates whether an action is allowed by policy.

---

### `omega_runtime/core/policy_manifest.py`

Handles policy manifest creation, hashing, signing, and integrity verification.

---

### `omega_runtime/core/proxy.py`

Implements `OmegaProxy`, the controlled execution gateway.

---

### `omega_runtime/core/counterexamples.py`

Builds structured counterexamples for rejected executions.

---

### `omega_runtime/core/invariants.py`

Defines invariant identifiers and maps failure reasons to invariant names.

---

### `omega_runtime/core/gates.py`

Defines gate ordering and gate-related checks.

Gate order ensures that failures are classified correctly.

---

### `omega_runtime/core/trace_chain.py`

Implements hash-linked trace entries.

---

### `omega_runtime/core/replay_verifier.py`

Verifies trace files offline.

---

### `omega_runtime/core/proof_bundle.py`

Exports and verifies single-step proof bundles.

---

### `omega_runtime/core/episode_bundle.py`

Exports and verifies multi-step episode bundles.

---

### `omega_runtime/core/final_verifier_report.py`

Builds final machine-readable verification reports.

---

### `omega_runtime/core/auditor.py`

Audits runtime artifacts.

---

### `omega_runtime/core/system_verifier.py`

Verifies multiple runtime artifacts together as one system-level evidence set.

---

### `omega_runtime/core/state.py`

Defines runtime state objects.

---

### `omega_runtime/core/transitions.py`

Defines and validates state transitions.

---

### `omega_runtime/core/stateful_proxy.py`

Adds stateful execution controls around proxy-based execution.

---

### `omega_runtime/tools/sandbox_tools.py`

Contains sandboxed file tools used by tests and demos.

The tools are intentionally restricted to prevent unsafe path access.

---

### `scripts/run_api.py`

Starts the local API server.

Use it before opening browser dashboards.

---

### `scripts/demo_proof_bundle.py`

Generates a valid proof bundle demo.

---

### `scripts/verify_proof_bundle.py`

Verifies a proof bundle from disk.

---

### `scripts/demo_replay_verifier.py`

Generates a replayable trace and verifies it offline.

---

### `scripts/demo_failure_lab.py`

Runs failure scenarios and writes a failure lab report.

---

### `scripts/demo_evidence_pack.py`

Generates a portable evidence pack archive.

---

### `scripts/release_check.py`

Runs the release readiness check from CLI.

---

### `scripts/audit_runtime.py`

Audits runtime artifacts such as proof bundles and traces.

---

### `scripts/verify_runtime_system.py`

Verifies a proof bundle and trace together as a system-level evidence set.

---

## 18. Test Coverage

The v1.0.0 suite contains 83 passing tests.

### 18.1 Certificate tests

Covered by:

- `test_no_certificate_rejected.py`
- `test_wrong_key_rejected.py`
- `test_signature_tamper_rejected.py`
- `test_certificate_binds_policy_manifest.py`

These prove that the runtime rejects missing, forged, tampered, or stale certificates.

---

### 18.2 Policy tests

Covered by:

- `test_policy_manifest_valid.py`
- `test_policy_manifest_tamper_rejected.py`
- `test_policy_manifest_signature_tamper_rejected.py`

These prove that policy integrity is enforced.

---

### 18.3 Action and path safety tests

Covered by:

- `test_action_tamper_rejected.py`
- `test_path_escape_rejected.py`
- `test_counterexample_on_path_escape.py`

These prove that action mutation and unsafe file paths are rejected.

---

### 18.4 Runtime state tests

Covered by:

- `test_valid_transition_sequence.py`
- `test_illegal_transition_rejected.py`
- `test_terminal_reentry_rejected.py`

These prove that state transitions are controlled.

---

### 18.5 Counterexample tests

Covered by:

- `test_counterexample_on_tamper.py`
- `test_counterexample_on_path_escape.py`
- `test_no_counterexample_on_accept.py`

These prove that rejection creates useful counterexamples and acceptance does not.

---

### 18.6 Replay and trace tests

Covered by:

- `test_replay_rejected.py`
- `test_replay_verifier.py`
- `test_trace_chain.py`
- `test_trace_tamper_detected.py`

These prove that traces are hash-linked and replay-verifiable.

---

### 18.7 Proof bundle tests

Covered by:

- `test_proof_bundle_export.py`
- `test_proof_bundle_cli.py`

These prove that proof bundles can be exported and verified offline.

---

### 18.8 Episode bundle tests

Covered by:

- `test_episode_bundle.py`

These prove that multi-step episodes can be exported and verified.

---

### 18.9 Final report tests

Covered by:

- `test_final_verifier_report.py`

These prove that final reports are valid, hash-bound, and tamper-detecting.

---

### 18.10 Auditor tests

Covered by:

- `test_auditor.py`

These prove that artifact-level audits work correctly.

---

### 18.11 System verifier tests

Covered by:

- `test_system_verifier.py`

These prove that multiple artifacts can be verified together.

---

### 18.12 UI and API tests

Covered by:

- `test_api.py`
- `test_ui_dashboard.py`
- `test_ui_dashboard_routes.py`
- `test_failure_lab_dashboard.py`
- `test_action_playground.py`
- `test_evidence_pack_ui.py`

These prove that browser/API routes are registered and return usable results.

---

### 18.13 Release hardening tests

Covered by:

- `test_release_hardening.py`

These prove that the release checker works and validates the current release structure.

---

## 19. What Counts as a Valid Execution

A valid execution must satisfy all of the following:

1. the action is well formed,
2. the action is allowed by policy,
3. the policy manifest is intact,
4. the certificate uses a trusted key id,
5. the certificate payload hash is correct,
6. the certificate signature is valid,
7. the certificate action hash matches the action,
8. the certificate policy hash matches the active policy,
9. the tool path is safe,
10. the action is not a replay violation,
11. the state transition is legal,
12. the proxy executes the tool,
13. the receipt binds to the executed action,
14. the trace entry binds to the receipt,
15. the exported proof artifact verifies offline.

If any condition fails, the runtime rejects execution.

---

## 20. What Counts as Tampering

Tampering includes unauthorized mutation to:

- an action,
- action arguments,
- policy manifest,
- policy signature,
- certificate payload,
- certificate signature,
- certificate key id,
- receipt,
- trace entry,
- proof bundle,
- episode bundle,
- final report,
- audit input artifact,
- evidence pack contents.

OMEGA detects tampering through:

- hash mismatch,
- signature mismatch,
- invariant failure,
- replay verification failure,
- bundle verification failure,
- system verification failure.

---

## 21. Why Hashes Matter

Hashes are used throughout the system to bind objects together.

Examples:

- action hash binds certificate to action,
- policy hash binds certificate to policy,
- output hash binds receipt to result,
- entry hash binds trace entry to contents,
- previous hash links trace entries,
- bundle hash binds proof bundle contents,
- archive hash binds evidence pack contents,
- aggregate hash binds release and audit reports.

This creates a chain of evidence.

If an attacker changes one part, the hash chain breaks.

---

## 22. Why Canonical Serialization Matters

JSON can be formatted in different ways while representing the same object.

For example:

```json
{"a":1,"b":2}
```

and:

```json
{
  "b": 2,
  "a": 1
}
```

contain the same logical data but different text.

Canonical serialization ensures that the runtime hashes the logical object consistently.

This is required for stable signatures and reproducible verification.

---

## 23. Why Offline Verification Matters

A runtime decision is more trustworthy when it can be checked again later.

OMEGA supports offline verification of:

- proof bundles,
- episode bundles,
- trace files,
- final reports,
- system verification reports,
- evidence packs,
- release reports.

This means the runtime does not only say:

> Trust me, this action was valid.

It produces artifacts that let another verifier check:

> This action was valid because these hashes, signatures, receipts, policies, and traces match.

---

## 24. Suggested Demo Flow

Use this flow when explaining the project to someone.

### Step 1: Prove the repository is healthy

```powershell
python -m pytest
python scripts/release_check.py --json
```

Look for:

```text
83 passed
release check passed
```

### Step 2: Show normal proof-carrying execution

```powershell
python scripts/demo_proof_bundle.py
```

Look for:

```text
accepted: True
proof bundle valid
```

### Step 3: Show replay verification

```powershell
python scripts/demo_replay_verifier.py
```

Look for:

```text
REPLAY VERIFIER: PASS
offline replay verification passed
```

### Step 4: Show failure lab

```powershell
python scripts/demo_failure_lab.py
```

Look for:

```text
tampered proof bundle rejected
tampered trace rejected
missing evidence rejected
```

### Step 5: Show evidence pack export

```powershell
python scripts/demo_evidence_pack.py --json
```

Look for:

```text
evidence pack generated
omega_evidence_pack.zip
```

### Step 6: Show browser UI

```powershell
python scripts/run_api.py
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/failure-lab
http://127.0.0.1:8000/action-playground
http://127.0.0.1:8000/evidence-pack
```

---

## 25. Milestone History

### v0.1.0 — Stable Runtime Foundation

Established the early runtime foundation.

### v0.2.0 — CLI Packaging

Added command-line packaging and verification workflows.

### v0.3.0 — API Foundation

Added FastAPI foundation and API runtime access.

### v0.4.0 — UI Dashboard

Added browser dashboard support.

### v0.5.0 — Failure Demonstration Lab

Added controlled scenarios that prove tampering and missing evidence are rejected.

### v0.6.0 — Failure Lab Dashboard

Connected the failure lab to a browser dashboard.

Routes include:

```text
GET  /failure-lab
POST /failure-lab/run
GET  /failure-lab/report
```

### v0.7.0 — Agent Action Playground

Added an interactive playground for allowed and rejected action scenarios.

Routes include:

```text
GET  /action-playground
GET  /action-playground/scenarios
POST /action-playground/run
POST /action-playground/run-all
GET  /action-playground/report
```

### v0.8.0 — Evidence Pack

Added portable evidence pack generation.

Main command:

```powershell
python scripts/demo_evidence_pack.py --json
```

### v0.9.0 — Evidence Pack UI

Added a browser UI for evidence pack generation and inspection.

Open:

```text
http://127.0.0.1:8000/evidence-pack
```

### v1.0.0-rc1 — Release Hardening

Added release readiness checks.

Main command:

```powershell
python scripts/release_check.py --json
```

### v1.0.0 — Final Release

Promoted the runtime to final v1.0.0.

Validation state:

```text
83 tests passing
release check passing
v1.0.0 tag created
main clean
```

---

## 26. Development Workflow

Before making changes:

```powershell
git status
python -m pytest
python scripts/release_check.py --json
```

Create a branch:

```powershell
git switch main
git pull origin main
git switch -c feature/my-change
```

After changes:

```powershell
python -m pytest
python scripts/release_check.py --json
git status
git diff --stat
```

Commit:

```powershell
git add <files>
git commit -m "describe the change"
```

Merge when ready:

```powershell
git switch main
git pull origin main
git merge --no-ff feature/my-change -m "merge my change"
python -m pytest
python scripts/release_check.py --json
git push origin main
```

---

## 27. Git Validation

Check the current branch:

```powershell
git branch --show-current
```

Check clean state:

```powershell
git status
```

Expected:

```text
nothing to commit, working tree clean
```

Check recent history:

```powershell
git log --oneline --decorate -10
```

Check tags:

```powershell
git tag
```

Expected to include:

```text
v1.0.0
```

---

## 28. Generated Files

OMEGA generates runtime evidence files during demos.

Common generated paths:

```text
artifacts\proof_bundle_demo.json
traces\replay-verifier-demo.jsonl
artifacts\failure_lab\failure_lab_report.json
artifacts\evidence_pack\evidence_pack_report.json
artifacts\evidence_pack\omega_evidence_pack.zip
artifacts\release\release_check_report.json
```

These files are useful for local validation and demos.

They should generally not be committed unless intentionally adding a golden fixture.

---

## 29. Production Roadmap

OMEGA v1.0.0 is a strong local verification foundation.

Possible next milestones:

1. production-grade key management,
2. public-key certificate verification,
3. certificate revocation lists,
4. richer tool permission schemas,
5. network/API sandboxing,
6. external SaaS tool policy enforcement,
7. multi-user authorization,
8. multi-agent run identity preservation,
9. formal transition specifications,
10. machine-checkable proof exports,
11. signed final verifier reports,
12. CI pipeline enforcement,
13. packaged CLI entry points,
14. documentation site,
15. example notebooks,
16. adversarial red-team scenario expansion,
17. cloud deployment guide,
18. hardware-backed signing option,
19. audit dashboard,
20. policy authoring UI.

---

## 30. Summary

OMEGA Runtime demonstrates a working proof-carrying runtime for controlled agent execution.

It proves that a tool-using runtime can:

- prevent unauthorized tool calls,
- enforce policy-bound certificates,
- reject tampering,
- emit structured counterexamples,
- produce verifiable receipts,
- generate hash-linked traces,
- verify execution offline,
- export portable proof artifacts,
- generate evidence packs,
- audit runtime evidence,
- verify the full system state,
- validate release readiness.

The central achievement is:

> Every accepted execution is backed by verifiable evidence.  
> Every rejected execution is explained by a concrete invariant failure.  
> Every exported artifact can be checked again offline.

OMEGA Runtime is the foundation for building safer, more accountable, and more formally controlled tool-using AI agents.
