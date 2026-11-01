# Codex Smart Router Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public, reproducible Windows Codex installation lab that proves ChatGPT subscription passthrough before enabling automatic model routing and escalation.

**Architecture:** Codex Windows App retains ChatGPT OAuth and sends requests through a localhost-only LiteLLM gateway backed by local Postgres. The repository separates baseline passthrough, Auto Router, Superpowers/subagent orchestration, and failure-driven escalation so each layer is independently testable and reversible.

**Tech Stack:** Docker Compose, LiteLLM source pinned to full Git SHA, Postgres 16, PowerShell 7, Python/pytest for repository contract tests, GitHub Actions.

**Spec:** `docs/ARCHITECTURE.md`

## Global Constraints

- Public repository must contain no credentials or ChatGPT tokens.
- No paid OpenAI API fallback in baseline or Auto Router pilot.
- Gateway listens only on `127.0.0.1:4000`; Postgres is not host-published.
- LiteLLM source ref is `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` until a reviewed signed release replaces it.
- `context_compaction: false` for the documented subscription Auto Router workaround.
- Real Codex config is not modified until K2 baseline passthrough is proven.

## Review Focus

- A missing Docker daemon fails preflight before any config mutation.
- An absent/invalid gateway key cannot silently replace ChatGPT OAuth.
- The public repo never contains generated secrets.
- Auto Router mode must not expose an unknown custom model alias to Codex; use the reviewed known-slug shadow pattern unless a catalog is explicitly generated and validated.
- Rollback remains possible without deleting Postgres data.

---

### Task 1: Repository contract and security baseline
**Files:** tests/test_repo_contract.py, docker-compose.yml, configs/*, docs/*
**Interfaces:** Produces the pinned source ref, localhost network boundary, and two-stage configs consumed by later tasks.
- [x] Write failing repository-contract tests.
- [x] Run them and observe failure before production files exist.
- [x] Add minimum configuration/docs required by the tests.
- [ ] Run the complete suite and validate Compose rendering.
- [ ] Commit.

### Task 2: Windows preflight and lifecycle scripts
**Files:** scripts/windows/*.ps1, .github/workflows/ci.yml
**Interfaces:** Produces preflight/install/verify/uninstall commands used by K1/K2.
- [ ] Parse every PowerShell file on windows-latest.
- [ ] Ensure install does not edit real Codex config in phase 1.
- [ ] Ensure uninstall preserves DB unless explicitly asked to remove it.
- [ ] Commit.

### Task 3: Upstream source contract
**Files:** .github/workflows/ci.yml, docs/SECURITY.md
**Interfaces:** Proves pinned source contains LiteLLM 1.109.0 and OpenAI Auto Router primitives.
- [ ] Verify source SHA is descendant of merged subscription passthrough PR.
- [ ] Verify pyproject version and Auto Router preset markers by immutable raw URLs.
- [ ] Document the 1.107.0 compromised-artifact prohibition.
- [ ] Commit.

### Task 4: K2 Windows subscription passthrough
**Files:** scripts/windows/verify.ps1, docs/K2-WINDOWS.md (future)
**Interfaces:** Produces evidence that Codex OAuth passes through LiteLLM without paid API fallback.
- [ ] Start the local stack on the user's Windows machine.
- [ ] Create a restricted LiteLLM virtual key for the explicit `gpt-6.1-sol` baseline route.
- [ ] Configure Codex provider while preserving OpenAI auth.
- [ ] Send the exact Hello/no-tools probe and inspect LiteLLM logs.
- [ ] Record evidence and rollback result.

### Task 5: Auto Router + live model verification
**Files:** configs/litellm/autorouter.yaml, docs/EVIDENCE.md
**Interfaces:** Produces the account-verified route map used by Superpowers workers.
- [ ] Verify the subscription can call `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol`, and `gpt-6-astra`.
- [ ] Keep unsupported tiers disabled rather than silently falling back to paid API routes.
- [ ] Expose the router under the known `gpt-6.1-sol` slug; keep actual models behind internal aliases.
- [ ] Verify short, normal, complex, and reasoning-heavy prompts route to expected tiers in LiteLLM logs.

### Task 6: Superpowers/subagents and escalation
**Files:** docs/K5-ESCALATION.md and hook scripts (future)
**Interfaces:** Produces deterministic fresh-worker escalation after verified failures.
- [ ] Install Superpowers from official Codex marketplace.
- [ ] Verify native subagent `model` and `reasoning_effort` appear in rollout metadata.
- [ ] Add failure summary hook without mid-trajectory model switching.
- [ ] Exercise a deliberate failing-test scenario and prove escalation.
