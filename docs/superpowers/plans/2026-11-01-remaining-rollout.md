# Remaining Codex Smart Router Rollout Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the router lab from the current hardened PR through a proven, reversible Codex Windows App deployment that uses the user's ChatGPT subscription, automatic model/effort routing, Superpowers subagents, and verified escalation without paid API fallback.

**Architecture:** Merge the audited repository only after review, prove the exact merged tree with a source-built Heavy Docker smoke, then roll out one layer at a time on Windows. Codex keeps ChatGPT OAuth; LiteLLM owns only gateway authorization/routing; Superpowers owns task decomposition and fix-loop escalation; deterministic tests and rollout metadata are the acceptance evidence.

**Tech Stack:** Codex Windows App, LiteLLM 1.109.0 pinned source, Docker Compose, PostgreSQL 16, PowerShell 7, Python/pytest, GitHub Actions, Superpowers.

**Spec:** `docs/ARCHITECTURE.md`

## Global Constraints

- No live Codex/ChatGPT OAuth request before the exact-main Heavy Docker smoke passes.
- No OpenAI API key and no paid API fallback at any stage.
- Gateway remains bound to `127.0.0.1:4000`; PostgreSQL remains unexposed to the host.
- Git-tracked YAML remains the model/router source of truth; `STORE_MODEL_IN_DB=False`.
- ChatGPT OAuth remains owned by Codex; LiteLLM receives a separate restricted virtual key.
- `context_compaction: false` remains mandatory for the subscription Auto Router path until the documented issue is fixed and reverified.
- Every Codex config/.env change must be restart-tested in a **new** task/session.
- K3 probes model **and reasoning-effort pairs**; unsupported pairs are disabled rather than silently substituted with API-backed models.
- Superpowers explicit dispatch/fix-loop is the load-bearing escalation path. Codex hook issues #49736 and #34289 prevent treating PreToolUse/PostToolUse as hard enforcement today.
- Main merges are allowed only after branch CI and review evidence are green.

## Review Focus

- Desktop/background-server state can retain stale provider/model configuration after files change.
- A virtual key may be valid while the ChatGPT subscription does not expose a requested model/effort pair.
- A router alias unknown to Codex can cause huge tool-schema retransmission; the known-slug shadow pattern must remain verified.
- A failed worker must not carry a huge failed reasoning trajectory into the stronger worker; handoff is diff + deterministic failure evidence + concise summary.
- Rollback must preserve post-install user edits and revoke the current gateway key without deleting unrelated user state.

---

### Task 1: Finish PR #8 review and freeze the audited tree

**Files:** PR #8, `docs/STATUS.md`, `docs/EVIDENCE.md`

**Interfaces:**
- Consumes: current audit branch and green branch CI.
- Produces: one reviewed immutable head SHA eligible for merge.

- [ ] **Step 1: Confirm PR #8 head has a successful full CI run**
  - Check all jobs on the current PR head SHA.
  - Expected: contract tests, Windows PowerShell behavior tests, and upstream-contract checks all pass.

- [ ] **Step 2: Complete independent code review**
  - Review API contracts, secrets, rollback, router config, Windows behavior, and docs/code consistency.
  - Expected: no Critical or Important findings remain open.

- [ ] **Step 3: Re-run CI if review fixes changed the branch**
  - Expected: the final reviewed head is green.

- [ ] **Step 4: Record review result in `docs/EVIDENCE.md`**
  - Record PR number, reviewed head SHA, CI run URL, and any accepted limitations.

- [ ] **Step 5: Merge PR #8 to `main`**
  - Merge commit message must contain `[heavy-smoke]`.
  - Expected: one exact main SHA becomes the deployment candidate.

### Task 2: Exact-main Heavy Docker smoke

**Files:** `.github/workflows/heavy-smoke.yml`, `docs/STATUS.md`, `docs/EVIDENCE.md`

**Interfaces:**
- Consumes: exact merged main SHA.
- Produces: repository-side pre-live release candidate.

- [ ] **Step 1: Verify the Heavy Docker smoke starts on the merge SHA**
  - Do not accept a run from an earlier branch SHA.

- [ ] **Step 2: Build pinned LiteLLM source**
  - Expected: source SHA `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` builds successfully.

- [ ] **Step 3: Start PostgreSQL + LiteLLM in subscription mode**
  - Expected: `/health/liveliness` and `/health/readiness` pass.

- [ ] **Step 4: Exercise real LiteLLM virtual-key management API**
  - Generate disposable restricted key, inspect allowlist with the documented management contract, then revoke it.
  - Expected: key lifecycle passes without real user credentials.

- [ ] **Step 5: Restart in Auto Router mode and run `/auto_router/test_routing`**
  - Expected: valid routing decision and one of the pinned internal upstream aliases.

- [ ] **Step 6: Clean up containers/volumes and record artifacts/logs**
  - Expected: Heavy Smoke green on exact main SHA.
  - **Gate:** K2 is forbidden until this step passes.

### Task 3: K2 Windows single-model subscription passthrough

**Files:** `scripts/windows/preflight.ps1`, `install.ps1`, `provision-codex-key.ps1`, `configure-codex-provider.ps1`, `verify.ps1`, `docs/K2-WINDOWS.md`

**Interfaces:**
- Consumes: Heavy-smoke-approved main.
- Produces: proof that Codex Windows App uses ChatGPT subscription through LiteLLM.

- [ ] **Step 1: Clone/pull exact approved main and run preflight**
  - Expected: PowerShell 7, Docker, Compose, Codex config, and port ownership checks pass.

- [ ] **Step 2: Install gateway in `subscription` mode only**
  - Auto Router remains off.
  - Expected: local Postgres + LiteLLM ready; no Codex config mutation yet.

- [ ] **Step 3: Create the K2 restricted 30-day virtual key**
  - Allow only baseline `gpt-6.1-sol`, explicit `gpt-image-2`, and `codex-*`.
  - Expected: key written to `~/.codex/.env`, ACL restricted to the current Windows user.

- [ ] **Step 4: Configure the subscription provider**
  - `requires_openai_auth=true`, Responses API, separate `x-litellm-api-key`, no `env_key` replacing ChatGPT OAuth.

- [ ] **Step 5: Fully exit/restart Codex/ChatGPT desktop and start a brand-new task**
  - Existing tasks do not count because model/provider defaults can be session-scoped.

- [ ] **Step 6: Send the exact no-tool probe**
  - Prompt: `Reply with exactly Hello. Do not use tools.`
  - Expected: `Hello`.

- [ ] **Step 7: Inspect LiteLLM logs**
  - Must show successful request, virtual-key attribution, ChatGPT subscription-backed model, token counts, and no paid API fallback.
  - **Gate:** K3 begins only after this evidence is recorded.

- [ ] **Step 8: Perform one rollback rehearsal**
  - Restore Codex provider/key state, confirm unrelated config survives, then reapply K2.
  - Expected: recovery path is proven before routing complexity is added.

### Task 4: K3 model + effort entitlement matrix

**Files:** `configs/litellm/model-probe.yaml`, `docs/K3-MODEL-PROBE.md`, `docs/EVIDENCE.md`

**Interfaces:**
- Consumes: proven K2 passthrough.
- Produces: account-specific supported model/effort matrix.

- [ ] **Step 1: Provision the K3 restricted probe key**
  - Allow Luna, Terra, Sol, Astra, `gpt-image-2`, and `codex-*`.

- [ ] **Step 2: Probe each target pair in a new task/session**
  - `gpt-6-luna / medium`
  - `gpt-6.1-terra / medium`
  - `gpt-6-sol / high`
  - `gpt-6-astra / high`

- [ ] **Step 3: Read effective rollout metadata**
  - Verify actual `model` and `effort`; do not trust only picker labels.

- [ ] **Step 4: Verify `gpt-image-2` and `codex-*` auxiliary traffic**
  - Expected: explicit image/review routes work through the subscription path.

- [ ] **Step 5: Produce `supported-model-effort.json` evidence**
  - Unsupported pairs are removed/lowered in policy.
  - No API-backed substitute is added.
  - **Gate:** K4 uses only verified pairs.

### Task 5: K4 Auto Router activation and calibration

**Files:** `configs/litellm/autorouter.yaml`, `configs/routing/escalation-policy.yaml`, `docs/K4-ROUTING.md`

**Interfaces:**
- Consumes: K3 verified matrix.
- Produces: validated automatic controller routing.

- [ ] **Step 1: Adjust router tiers to the verified K3 matrix**
  - Initial intended ladder: SIMPLE→Luna/medium, MEDIUM→Terra/medium, COMPLEX→Sol/high, REASONING→Astra/high.

- [ ] **Step 2: Switch gateway to `autorouter` mode**
  - Keep router exposed under the already-known `gpt-6.1-sol` slug.
  - Keep real tier models behind private `*-upstream` aliases.

- [ ] **Step 3: Restart LiteLLM and fully restart Codex desktop**
  - New task/session required.

- [ ] **Step 4: Run a four-class routing calibration suite**
  - Simple mechanical prompt.
  - Normal implementation prompt.
  - Cross-module/debug prompt.
  - Architecture/reasoning-heavy prompt.

- [ ] **Step 5: Inspect LiteLLM routing metadata**
  - Record tier, cause/score, selected physical model, and effort.
  - Picker/model-group name is not accepted as evidence.

- [ ] **Step 6: Check prompt/token inflation**
  - Known-slug shadow route should avoid unknown-alias tool-schema retransmission.
  - If prompts inflate unexpectedly, stop and investigate before K5.

### Task 6: K5 Superpowers + native subagent execution

**Files:** `configs/codex/AGENTS.smart-router.md`, policy installer, Superpowers plugin, rollout inspection tools

**Interfaces:**
- Consumes: calibrated router and K3 model/effort matrix.
- Produces: explicit worker routing proven in Codex rollout metadata.

- [ ] **Step 1: Install/verify Superpowers from the official Codex plugin source**
  - Confirm installed version/commit if exposed.

- [ ] **Step 2: Install the managed smart-router AGENTS block**
  - Preserve unrelated existing AGENTS instructions.

- [ ] **Step 3: Verify Codex loads the policy in a new task**
  - New session after policy/config changes.

- [ ] **Step 4: Dispatch one worker per role with explicit model + effort**
  - Mechanical → Luna.
  - Integration → Terra.
  - Difficult debugging → Sol.
  - Architecture/reviewer → Astra.

- [ ] **Step 5: Inspect child rollout metadata**
  - Expected: child `model`, `effort`, `parent_thread_id`, and role match the dispatch.
  - Parent inheritance is a failure if explicit worker selection was expected.

- [ ] **Step 6: Verify reviewers use fresh context**
  - Hand off repository state, diff, deterministic failures, and concise summary only.

### Task 7: K5 failure-driven escalation proof

**Files:** `docs/K5-ESCALATION.md`, test fixture/pilot repository task, rollout evidence

**Interfaces:**
- Consumes: verified explicit subagent dispatch.
- Produces: real proof of fresh-worker escalation.

- [ ] **Step 1: Create a deterministic intentionally failing coding task**
  - Failure must be test/build/lint observable; no subjective pass criterion.

- [ ] **Step 2: Exercise Superpowers fix rounds 1-3**
  - Same worker may continue while measurable progress exists.

- [ ] **Step 3: Force/observe round 4 escalation**
  - Expected: fresh worker, at least one verified tier stronger.

- [ ] **Step 4: Verify handoff content**
  - Current diff + failing test/build/lint + concise failure summary.
  - No long failed hidden-reasoning trajectory.

- [ ] **Step 5: Verify breaker after round 5**
  - Return to controller review instead of unlimited recursive retries.

- [ ] **Step 6: Record effective child model/effort metadata**
  - **Gate:** real project pilot is forbidden until this succeeds.

### Task 8: K6 controlled real-project pilot

**Files:** a small reversible task in the target project plus router telemetry/evidence

**Interfaces:**
- Consumes: proven routing and escalation.
- Produces: comparison against current manual Sol workflow.

- [ ] **Step 1: Select a bounded non-critical task**
  - No major R6/R7 phase as the first pilot.

- [ ] **Step 2: Run with smart routing**
  - Record controller/worker/reviewer choices.

- [ ] **Step 3: Measure**
  - Wall time, turns, input/output tokens, chosen models/efforts, retries, tests, and final review result.

- [ ] **Step 4: Compare with existing workflow**
  - Focus on completion quality and total subscription consumption, not only raw token count.

- [ ] **Step 5: Tune tier thresholds only from evidence**
  - Change one routing policy variable at a time and repeat a comparable task if needed.

### Task 9: K7 production-readiness freeze

**Files:** `docs/STATUS.md`, `docs/EVIDENCE.md`, `docs/SECURITY.md`, `docs/ROLLBACK.md`, release/tag

**Interfaces:**
- Consumes: successful controlled pilot.
- Produces: reproducible installation release.

- [ ] **Step 1: Re-run complete repository CI and Heavy Docker smoke**
  - Exact candidate SHA only.

- [ ] **Step 2: Re-run Windows verify + rollback + key revoke/re-provision**
  - Expected: no data loss or unrelated config mutation.

- [ ] **Step 3: Freeze versions and evidence**
  - LiteLLM source SHA, Postgres digest, workflow action SHAs, installed Codex version, Superpowers version/commit, supported model/effort matrix.

- [ ] **Step 4: Document update policy**
  - No unpinned `latest`.
  - Re-run upstream-contract + Heavy Smoke before every LiteLLM/Codex/Superpowers upgrade.

- [ ] **Step 5: Tag first validated release**
  - Suggested tag: `v0.1.0-windows-validated`.

## Final Acceptance Criteria

The system is complete only when all of the following are true:

1. Exact-main Heavy Docker smoke is green.
2. Codex Windows App request is observed passing through LiteLLM with the user's ChatGPT subscription and no API fallback.
3. Every production model/effort pair is verified on the account.
4. Auto Router decisions are observable and do not cause abnormal prompt inflation.
5. Native subagents show the explicitly requested model + effort in rollout metadata.
6. A deterministic failing task demonstrably escalates to a fresh stronger worker and eventually trips the breaker.
7. Rollback, key revocation, and re-provision have been rehearsed successfully.
8. A bounded real-project pilot passes tests/review and improves or at least preserves completion quality at lower expected subscription cost.
9. The final validated commit is tagged and all evidence is recorded.
