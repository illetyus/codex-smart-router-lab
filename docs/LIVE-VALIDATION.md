# Live Validation Evidence Runbook

This file defines the evidence package to collect once the repository-side pre-live gate is green. It intentionally does not claim that a live Codex/ChatGPT OAuth request has been executed.

## Repository gate

The exact main commit must have a successful **heavy-smoke** run before K2 starts. Record the main SHA and workflow URL in `docs/EVIDENCE.md`.

## K2 — subscription passthrough

Create `evidence/k2-passthrough.json` from the observed LiteLLM request/log data after a full Codex desktop restart and a brand-new task. Record only non-secret metadata: timestamp, requested model, served model, gateway key alias/id if non-secret, token counts, HTTP success, and confirmation that no paid API fallback was configured. Never copy ChatGPT Authorization headers, cookies, or the virtual-key secret.

## K3 — model/effort entitlement

Run the verified model/effort probes and write `evidence/supported-model-effort.json`. Use `tools/collect_rollout_evidence.py` against `%USERPROFILE%\.codex\sessions` to capture Codex-local model/effort metadata. Note: persisted `turn_context.effort` is Codex's local resolved context setting; LiteLLM logs remain authoritative for the physical model selected by Auto Router.

## K4 — routing calibration

Use `configs/calibration/prompts.json`. Record the four observed decisions in `evidence/routing-calibration.json`: requested router group, selected tier, cause, selected physical model, effective effort where observable, prompt/input token count, and success/failure. Abort if unknown-model behavior causes abnormal prompt inflation.

## K5 — subagent proof

Run one explicit worker per role and save `evidence/subagent-evidence.json`. Include parent/child thread IDs, agent role, requested model/effort and rollout-observed model/effort. Parent inheritance when explicit routing was required is a failure.

## K5 — escalation proof

Use `fixtures/escalation_lab` as the deterministic failure fixture. The command:

```powershell
python -m pytest -q fixtures/escalation_lab/failure_case.py
```

must start with exactly one failing test, `test_discount_rounding_boundary`. Exercise the documented Superpowers fix loop and save `evidence/escalation-evidence.json` with rounds, worker identities, model/effort, failing-test evidence, fresh-worker promotion, and breaker outcome.

Do not use hidden reasoning transcripts as handoff evidence. Use repository state, diff, deterministic failure output, and a concise failure summary.

## Release gate

The release candidate is eligible for K6/K7 only when all named evidence artifacts exist and their corresponding gates passed:

- heavy-smoke
- `k2-passthrough.json`
- `supported-model-effort.json`
- `routing-calibration.json`
- `subagent-evidence.json`
- `escalation-evidence.json`

Secrets and raw OAuth credentials must never be committed.
