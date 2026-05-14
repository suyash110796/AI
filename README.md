
This repository is not just a demo runtime. It is a concrete verification framework for controlled agent execution.

---

## 1. What This Project Is

Omega Runtime is a runtime control and verification framework for advanced tool-using agents.

Its goal is to ensure that every tool execution is:

1. authorized by policy,
2. bound to a signed certificate,
3. tied to a specific action payload,
4. checked against runtime invariants,
5. executed only through a controlled proxy,
6. recorded in a replayable trace,
7. verifiable offline,
8. auditable as a complete system artifact.

In simple terms:

> An agent is not allowed to simply call tools.
> It must present proof that the requested action is lawful.
> The runtime verifies that proof before execution.
> Every result is recorded so the execution can be checked again later.

---

## 2. Why This Exists

Tool-using AI agents can perform real actions:

* read files,
* write files,
* call APIs,
* invoke tools,
* chain multiple steps,
* produce final outputs,
* create persistent traces.

Without a runtime verification layer, an agent can:

* call a forbidden tool,
* modify an action after approval,
* reuse an old certificate,
* drift from the original task,
* bypass policy,
* tamper with execution traces,
* forge final reports,
* hide invalid transitions,
* produce unverifiable outputs.

Omega Runtime prevents those failures by requiring proof-carrying execution.

---

## 3. Core Design Principle

The runtime follows this principle:

> No action executes unless the runtime can verify that the action, policy, certificate, trace, and result are mutually consistent.

This is enforced through:

* canonical hashing,
* certificate signing,
* policy manifest binding,
* invariant checking,
* controlled proxy execution,
* counterexample generation,
* append-only trace chains,
* replay verification,
* proof bundles,
* episode bundles,
* final verifier reports,
* system-level audits.

---

## 4. Repository Structure

```text
omega_runtime/
  core/
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

omega_runtime/
  tools/
    sandbox_tools.py

scripts/
  audit_runtime.py
  demo_decision_firewall.py
  demo_episode_bundle.py
  demo_final_verifier_report.py
  demo_proof_bundle.py
  demo_replay_verifier.py
  demo_trace_chain.py
  verify_episode_bundle.py
  verify_final_report.py
  verify_proof_bundle.py
  verify_runtime_system.py

tests/
  test_action_tamper_rejected.py
  test_auditor.py
  test_certificate_binds_policy_manifest.py
  test_counterexample_on_path_escape.py
  test_counterexample_on_tamper.py
  test_decision_firewall.py
  test_episode_bundle.py
  test_final_verifier_report.py
  test_gate_order_rejected.py
  test_illegal_transition_rejected.py
  test_no_certificate_rejected.py
  test_no_counterexample_on_accept.py
  test_path_escape_rejected.py
  test_policy_manifest_signature_tamper_rejected.py
  test_policy_manifest_tamper_rejected.py
  test_policy_manifest_valid.py
  test_proof_bundle_cli.py
  test_proof_bundle_export.py
  test_replay_rejected.py
  test_replay_verifier.py
  test_signature_tamper_rejected.py
  test_system_verifier.py
  test_terminal_reentry_rejected.py
  test_trace_chain.py
  test_trace_tamper_detected.py
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

traces/
  .gitkeep

sandbox/
  .gitkeep
```

---

## 5. Runtime Concepts

### 5.1 Action

An `Action` is a request to execute a tool.

An action contains fields such as:

* `run_id`
* `step_index`
* `tool`
* `args`
* `nonce`

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

The hash prevents tampering. If any field changes after certification, verification fails.

---

### 5.2 Certificate

A certificate is a signed authorization object.

It binds together:

* the action hash,
* the policy hash,
* the run identity,
* the step index,
* the trusted key id,
* the signature,
* the payload hash.

The runtime checks the certificate before executing the action.

A certificate is rejected if:

* it is missing,
* it has the wrong key,
* its signature is invalid,
* its payload hash does not match,
* its action hash does not match the requested action,
* its policy hash does not match the current policy manifest.

---

### 5.3 Policy Manifest

The policy manifest defines what the runtime allows.

It protects the runtime from policy tampering.

The manifest is checked before execution. If the policy is modified after certificate issuance, the runtime rejects the action.

This protects against this attack:

1. issue a certificate under a safe policy,
2. modify policy afterward,
3. try to execute with the old certificate.

Omega Runtime rejects this because the certificate is bound to the original policy hash.

---

### 5.4 OmegaProxy

`OmegaProxy` is the controlled execution gateway.

Tools are not supposed to be executed directly.

Instead, the caller must send:

1. an action,
2. a certificate.

The proxy verifies the action and certificate before dispatching the tool.

The proxy returns a structured result containing:

* accepted/rejected decision,
* reason,
* output,
* receipt,
* counterexample when rejected.

---

### 5.5 Receipt

A receipt proves that a tool execution happened through the controlled runtime.

It records details such as:

* run id,
* step index,
* action hash,
* output hash,
* execution status,
* detail string.

Receipts are used later in proof bundles, episode bundles, replay verification, and audits.

---

### 5.6 Counterexample

A counterexample is produced when the runtime rejects an action.

It explains:

* what invariant failed,
* what was expected,
* what was observed,
* which run and step failed,
* why the decision was `REJECT`.

Counterexamples make rejection machine-checkable and human-readable.

Example failure categories include:

* missing certificate,
* invalid signature,
* wrong certificate key,
* policy admission failure,
* path escape,
* replay attempt,
* illegal transition,
* terminal re-entry,
* policy manifest integrity failure.

---

### 5.7 Invariants

Invariants are named runtime safety rules.

They classify failures precisely.

Examples include:

* wrong certificate key,
* certificate signature tamper,
* policy manifest integrity,
* path escape,
* action tamper,
* replay rejection,
* illegal transition,
* terminal re-entry.

The invariant layer prevents vague rejection reasons. Each rejection maps to a specific failed rule.

---

### 5.8 Gates

Gates are ordered checks.

Gate order matters.

For example:

1. wrong certificate key must be detected before generic policy admission failure,
2. policy manifest integrity must be detected before ordinary certificate mismatch,
3. signature tampering must not be misclassified as a policy failure.

The tests enforce this ordering.

---

### 5.9 Decision Firewall

The decision firewall ensures that an unsafe or invalid runtime decision cannot be silently treated as valid.

It protects the boundary between:

* verifier decision,
* runtime execution,
* receipt emission,
* final result.

This prevents invalid states from passing through as accepted executions.

---

### 5.10 Trace Chain

The trace chain records execution events in a hash-linked structure.

Each trace entry can be bound to:

* the action,
* the certificate,
* the receipt,
* previous entry hash,
* current entry hash.

This creates tamper evidence.

If an attacker changes an earlier entry, later hashes no longer match.

---

### 5.11 Replay Verifier

The replay verifier checks a trace offline.

It can verify that:

* entries are well formed,
* hash links are valid,
* replayed actions match their certificates,
* receipts match executed actions,
* tampering is detected.

This means an execution does not only need to pass live. It can be independently verified later.

---

### 5.12 Proof Bundle

A proof bundle packages a single verified execution into a portable artifact.

It contains:

* bundle type,
* action,
* certificate,
* receipt,
* accepted decision,
* reason,
* verification summary,
* bundle hash.

A proof bundle can be verified offline using:

```powershell
python scripts/verify_proof_bundle.py artifacts/proof_bundle_demo.json --json
```

A valid proof bundle returns:

```json
{
  "accepted": true,
  "reason": "proof bundle valid"
}
```

If the bundle is modified, verification fails with a hash mismatch or binding failure.

---

### 5.13 Episode Bundle

An episode bundle packages multiple related execution steps.

It represents a multi-step agent episode.

It contains:

* run id,
* final output,
* step count,
* ordered steps,
* action hashes,
* certificate hashes,
* receipt hashes,
* verification summary,
* bundle hash.

It verifies that:

* all steps belong to the same episode,
* all certificates are bound,
* all receipts are bound,
* all receipts correspond to executed actions,
* final output has not been tampered with,
* the bundle hash is stable.

Verify an episode bundle with:

```powershell
python scripts/verify_episode_bundle.py path\to\episode_bundle.json --json
```

---

### 5.14 Final Verifier Report

The final verifier report summarizes the verification state of a completed run.

It is intended to be a high-level machine-readable and human-readable result.

It can include:

* proof bundle status,
* replay status,
* episode bundle status,
* accepted/rejected status,
* final reason,
* aggregate hash.

This is the layer that turns low-level proofs into a final verification statement.

---

### 5.15 Auditor

The auditor verifies supplied runtime artifacts.

It can audit:

* proof bundles,
* traces,
* generated reports.

Example:

```powershell
python scripts/audit_runtime.py --proof-bundle artifacts\proof_bundle_demo.json --json
```

Example:

```powershell
python scripts/audit_runtime.py --trace traces\replay-verifier-demo.jsonl --json
```

If no artifacts are supplied, the auditor rejects:

```json
{
  "accepted": false,
  "reason": "no artifacts supplied"
}
```

This is intentional.

---

### 5.16 System Verifier

The system verifier verifies multiple artifact types together.

It can check a proof bundle and a trace together:

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

The system verifier provides a higher-level judgment over the runtime evidence set.

---

## 6. Threat Model

Omega Runtime is designed to detect and reject common tool-agent integrity failures.

### 6.1 Missing Certificate

If an action is submitted without a certificate, the runtime rejects it.

Why it matters:

An agent should not be able to directly execute tools without proof.

---

### 6.2 Wrong Certificate Key

If a certificate has an untrusted key id, the runtime rejects it.

Why it matters:

An attacker should not be able to create a certificate using an unauthorized key.

---

### 6.3 Signature Tampering

If a certificate signature is modified, the runtime rejects it.

Why it matters:

A signed proof must be cryptographically stable.

---

### 6.4 Action Tampering

If an action is modified after certificate issuance, the runtime rejects it.

Example:

Certified action:

```json
{
  "path": "sandbox/input.txt"
}
```

Tampered action:

```json
{
  "path": "sandbox/evil.txt"
}
```

The action hash changes, so the certificate no longer binds to the action.

---

### 6.5 Policy Tampering

If the policy manifest changes after certificate issuance, the runtime rejects execution.

Why it matters:

The certificate must prove authorization under the exact policy that is currently active.

---

### 6.6 Policy Manifest Signature Tampering

If the policy manifest signature is modified, the runtime rejects it as a policy integrity failure.

Why it matters:

The policy itself must be protected against unauthorized modification.

---

### 6.7 Path Escape

Sandbox tools are restricted to safe paths.

A path escape attempt is rejected.

Example unsafe path:

```text
../secret.txt
```

Why it matters:

The agent must not escape its allowed filesystem area.

---

### 6.8 Replay Attack

A certificate or action cannot be reused in an invalid way.

Why it matters:

A valid previous action should not become unlimited future authority.

---

### 6.9 Illegal Transition

Stateful execution must follow valid transitions.

Invalid state movement is rejected.

Why it matters:

A runtime must not enter impossible or unauthorized states.

---

### 6.10 Terminal Re-entry

Once an execution reaches a terminal state, it cannot re-enter active execution.

Why it matters:

Completed runs must stay closed.

---

### 6.11 Trace Tampering

If a trace entry is modified after creation, replay verification detects it.

Why it matters:

Logs must be tamper-evident.

---

### 6.12 Bundle Tampering

If a proof bundle, episode bundle, or report is modified after export, verification fails.

Why it matters:

Portable proof artifacts must remain trustworthy.

---

## 7. Main Commands

### 7.1 Run All Tests

```powershell
python -m pytest
```

Expected stable result:

```text
50 passed
```

---

### 7.2 Generate a Proof Bundle Demo

```powershell
python scripts/demo_proof_bundle.py
```

Expected result includes:

```text
accepted: True
bundle_verified: True
verify_reason: proof bundle valid
```

---

### 7.3 Verify a Proof Bundle

```powershell
python scripts/verify_proof_bundle.py artifacts\proof_bundle_demo.json --json
```

---

### 7.4 Generate a Replay Trace Demo

```powershell
python scripts/demo_replay_verifier.py
```

Expected result includes:

```text
REPLAY VERIFIER: PASS
REPLAY REASON: offline replay verification passed
```

---

### 7.5 Audit a Proof Bundle

```powershell
python scripts/audit_runtime.py --proof-bundle artifacts\proof_bundle_demo.json --json
```

---

### 7.6 Audit a Trace

```powershell
python scripts/audit_runtime.py --trace traces\replay-verifier-demo.jsonl --json
```

---

### 7.7 Write an Audit Report

```powershell
python scripts/audit_runtime.py --out artifacts\audit_report.json --json
```

If no artifacts are supplied, this intentionally returns:

```json
{
  "accepted": false,
  "reason": "no artifacts supplied"
}
```

---

### 7.8 Verify the Whole Runtime System

```powershell
python scripts/verify_runtime_system.py `
  --proof-bundle artifacts\proof_bundle_demo.json `
  --trace traces\replay-verifier-demo.jsonl `
  --out artifacts\system_report.json `
  --json
```

Expected valid reason:

```text
system verification passed
```

---

## 8. Important Modules

### 8.1 `omega_runtime/core/actions.py`

Defines the runtime action object.

The action is the atomic request to execute a tool.

---

### 8.2 `omega_runtime/core/canonical.py`

Provides canonical serialization and hashing helpers.

Canonicalization matters because the same logical object must always produce the same hash.

This prevents inconsistent hash results caused by dictionary ordering or formatting differences.

---

### 8.3 `omega_runtime/core/certificates.py`

Handles certificate issuance and verification.

Responsibilities include:

* building certificate payloads,
* computing payload hashes,
* signing payloads,
* verifying trusted key id,
* verifying payload hash,
* verifying certificate signature.

---

### 8.4 `omega_runtime/core/policy.py`

Evaluates whether an action is allowed by policy.

---

### 8.5 `omega_runtime/core/policy_manifest.py`

Handles policy manifest creation, hashing, and integrity verification.

---

### 8.6 `omega_runtime/core/proxy.py`

Implements `OmegaProxy`.

This is the main controlled execution gateway.

---

### 8.7 `omega_runtime/core/counterexamples.py`

Builds structured counterexamples for rejected executions.

---

### 8.8 `omega_runtime/core/invariants.py`

Defines invariant identifiers and maps failure reasons to invariant names.

---

### 8.9 `omega_runtime/core/trace_chain.py`

Implements hash-linked trace entries.

---

### 8.10 `omega_runtime/core/replay_verifier.py`

Verifies trace files offline.

---

### 8.11 `omega_runtime/core/proof_bundle.py`

Exports and verifies single-step proof bundles.

---

### 8.12 `omega_runtime/core/episode_bundle.py`

Exports and verifies multi-step episode bundles.

---

### 8.13 `omega_runtime/core/final_verifier_report.py`

Builds final machine-readable verification reports.

---

### 8.14 `omega_runtime/core/auditor.py`

Audits runtime artifacts.

---

### 8.15 `omega_runtime/core/system_verifier.py`

Verifies multiple runtime artifacts together as one system-level evidence set.

---

### 8.16 `omega_runtime/tools/sandbox_tools.py`

Contains sandboxed file tools used by tests and demos.

The tools are intentionally restricted to prevent unsafe path access.

---

## 9. Test Coverage

The test suite covers the runtime from multiple angles.

### 9.1 Certificate Tests

Covered by:

* `test_no_certificate_rejected.py`
* `test_wrong_key_rejected.py`
* `test_signature_tamper_rejected.py`
* `test_certificate_binds_policy_manifest.py`

These prove that the runtime rejects missing, forged, tampered, or stale certificates.

---

### 9.2 Policy Tests

Covered by:

* `test_policy_manifest_valid.py`
* `test_policy_manifest_tamper_rejected.py`
* `test_policy_manifest_signature_tamper_rejected.py`

These prove that policy integrity is enforced.

---

### 9.3 Action and Path Safety Tests

Covered by:

* `test_action_tamper_rejected.py`
* `test_path_escape_rejected.py`
* `test_counterexample_on_path_escape.py`

These prove that action mutation and unsafe file paths are rejected.

---

### 9.4 Runtime State Tests

Covered by:

* `test_valid_transition_sequence.py`
* `test_illegal_transition_rejected.py`
* `test_terminal_reentry_rejected.py`

These prove that state transitions are controlled.

---

### 9.5 Counterexample Tests

Covered by:

* `test_counterexample_on_tamper.py`
* `test_counterexample_on_path_escape.py`
* `test_no_counterexample_on_accept.py`

These prove that rejection creates useful counterexamples and acceptance does not.

---

### 9.6 Replay and Trace Tests

Covered by:

* `test_replay_rejected.py`
* `test_replay_verifier.py`
* `test_trace_chain.py`
* `test_trace_tamper_detected.py`

These prove that traces are hash-linked and replay-verifiable.

---

### 9.7 Proof Bundle Tests

Covered by:

* `test_proof_bundle_export.py`
* `test_proof_bundle_cli.py`

These prove that proof bundles can be exported and verified offline.

---

### 9.8 Episode Bundle Tests

Covered by:

* `test_episode_bundle.py`

These prove that multi-step episodes can be exported and verified.

---

### 9.9 Final Report Tests

Covered by:

* `test_final_verifier_report.py`

These prove that final reports are valid, hash-bound, and tamper-detecting.

---

### 9.10 Auditor Tests

Covered by:

* `test_auditor.py`

These prove that artifact-level audits work correctly.

---

### 9.11 System Verifier Tests

Covered by:

* `test_system_verifier.py`

These prove that multiple artifacts can be verified together.

---

## 10. Current Stable Milestone

The current stable checkpoint is:

```text
stable proof carrying runtime checkpoint: 50 tests passing
```

The committed Git checkpoint is intended to represent the first stable proof-carrying runtime milestone.

At this milestone, the runtime can:

* issue certificates,
* verify certificates,
* reject wrong keys,
* reject signature tampering,
* bind certificates to policy manifests,
* reject policy tampering,
* reject unsafe paths,
* execute sandbox tools through a proxy,
* emit receipts,
* generate counterexamples,
* build trace chains,
* verify traces offline,
* export proof bundles,
* verify proof bundles offline,
* export episode bundles,
* verify episode bundles offline,
* generate final verifier reports,
* audit runtime artifacts,
* verify the complete runtime system.

---

## 11. What Counts as a Valid Execution

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

## 12. What Counts as Tampering

Tampering includes any unauthorized mutation to:

* an action,
* action arguments,
* policy manifest,
* policy signature,
* certificate payload,
* certificate signature,
* certificate key id,
* receipt,
* trace entry,
* proof bundle,
* episode bundle,
* final report,
* audit input artifact.

The runtime is designed so that tampering is detected through hash mismatch, signature mismatch, invariant failure, or replay verification failure.

---

## 13. Why Hashes Matter

Hashes are used throughout the system to bind objects together.

Examples:

* action hash binds certificate to action,
* policy hash binds certificate to policy,
* output hash binds receipt to result,
* entry hash binds trace entry to its contents,
* previous hash links trace entries,
* bundle hash binds proof bundle contents,
* aggregate hash binds audit reports.

This creates a chain of evidence.

If an attacker changes one part, the hash chain breaks.

---

## 14. Why Canonical Serialization Matters

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

Canonical serialization ensures the runtime hashes the logical object consistently.

This is required for stable signatures and reproducible verification.

---

## 15. Why Offline Verification Matters

A runtime decision is more trustworthy when it can be checked again later.

Omega Runtime supports offline verification of:

* proof bundles,
* episode bundles,
* trace files,
* final reports,
* system verification reports.

This means the runtime does not only say:

> Trust me, this action was valid.

It produces artifacts that let another verifier check:

> This action was valid because these hashes, signatures, receipts, and policies match.

---

## 16. What This Is Not Yet

This project is a strong runtime verification foundation, but it is not yet a complete production AGI safety system.

It does not yet provide:

* distributed key management,
* hardware-backed signing,
* external API policy enforcement,
* network sandboxing,
* multi-user authorization,
* formal theorem prover integration,
* cloud deployment,
* long-term certificate revocation,
* complete adversarial red-team coverage.

These are future extensions.

---

## 17. Future Roadmap

Possible next milestones:

1. replace test signing with stronger production key management,
2. add public-key verification for certificates,
3. add certificate revocation lists,
4. add richer tool permission schemas,
5. add network/API tool sandboxing,
6. add multi-agent run identity preservation,
7. add formal transition specifications,
8. add machine-checkable proof exports,
9. add signed final verifier reports,
10. add CI pipeline with test enforcement,
11. add package installation metadata,
12. add CLI entry points,
13. add documentation site,
14. add example notebooks,
15. add threat-model expansion.

---

## 18. Quick Start

From project root:

```powershell
python -m pytest
```

Generate demo artifacts:

```powershell
python scripts/demo_proof_bundle.py
python scripts/demo_replay_verifier.py
```

Audit generated artifacts:

```powershell
python scripts/audit_runtime.py --proof-bundle artifacts\proof_bundle_demo.json --json
python scripts/audit_runtime.py --trace traces\replay-verifier-demo.jsonl --json
```

Verify system evidence:

```powershell
python scripts/verify_runtime_system.py `
  --proof-bundle artifacts\proof_bundle_demo.json `
  --trace traces\replay-verifier-demo.jsonl `
  --json
```

---

## 19. Development Notes

Use this command before committing:

```powershell
python -m pytest
```

Expected result:

```text
50 passed
```

Generated files such as artifacts, sandbox outputs, trace logs, Python caches, and backup files should not be committed.

The repository `.gitignore` is configured to exclude those generated files.

---

## 20. Git Checkpoint

A clean stable checkpoint should look like:

```powershell
git status
```

Expected:

```text
nothing to commit, working tree clean
```

View the latest commit:

```powershell
git log --oneline --decorate -5
```

---

## 21. Summary

Omega Runtime demonstrates a working proof-carrying runtime for controlled agent execution.

It proves that a tool-using runtime can:

* prevent unauthorized tool calls,
* enforce policy-bound certificates,
* reject tampering,
* emit structured counterexamples,
* produce verifiable receipts,
* generate hash-linked traces,
* verify execution offline,
* export portable proof artifacts,
* audit runtime evidence,
* verify the full system state.

The central achievement is this:

> Every accepted execution is backed by verifiable evidence.
> Every rejected execution is explained by a concrete invariant failure.
> Every exported artifact can be checked again offline.

This is the foundation for building safer, more accountable, and more formally controlled tool-using AI agents.


```


## v0.6.0 — Failure Lab Dashboard

The v0.6.0 milestone connects the failure demonstration lab directly to the browser UI.

### What this adds

- `GET /failure-lab` — browser dashboard for demonstrating caught failures.
- `GET /ui/failure-lab` — alias route for the same dashboard.
- `POST /failure-lab/run` — runs the failure lab from the API and returns the machine-readable report.
- `GET /failure-lab/report` — returns the latest generated failure lab report, if present.
- `omega_runtime/failure_lab_dashboard.py` — isolated dashboard route module.
- `tests/test_failure_lab_dashboard.py` — route and API contract tests.

### Why this matters

The failure lab is the simplest way to show the value of the runtime.

A normal agent log can claim that a tool call succeeded. OMEGA goes further:

1. It checks whether the action was allowed.
2. It checks whether the action was bound to a certificate.
3. It checks whether the execution emitted receipts.
4. It checks whether the trace can be replayed offline.
5. It checks whether tampering is detected after the fact.
6. It checks whether the whole run survives system-level verification.

### Run the dashboard

```powershell
python scripts/run_api.py
```

Then open:

```text
http://127.0.0.1:8000/failure-lab
```

To generate a fresh failure report from the API:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/failure-lab/run
```

To read the latest generated report:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/failure-lab/report
```

