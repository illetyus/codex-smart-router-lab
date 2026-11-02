# Evidence ledger

This repository separates claims that can be proven before installation from claims that require the user's live Codex/ChatGPT session.

## Proven before Windows installation

- LiteLLM's official **Auto Router with Codex and your ChatGPT subscription** tutorial states that, since the 1.109 development line, Codex can keep its own ChatGPT login in `Authorization` while a separate LiteLLM gateway credential travels in `x-litellm-api-key`.
- The same tutorial requires `context_compaction: false` for this subscription Auto Router path until the documented compaction/auth interaction is fixed.
- The tutorial documents a catalog-free alternative: expose the router under a model slug Codex already knows and keep the real models under internal aliases. This avoids the very large tool-schema retransmission observed for unknown model aliases.
- LiteLLM source commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` reports version `1.109.0`, is GitHub-signature verified, and is 108 commits after subscription-passthrough merge `2e27a02a9fce9bdc6ece13ba3cb8222dc5b6ecfa`.
- LiteLLM's October 2026 incident notice identifies the compromised 1.107.0 artifacts; this repository blocks that version and does not use an unpinned `latest`/`main-stable` image.

## Repository validation checkpoint

The last completed pre-hardening code-bearing main checkpoint is:

- main SHA: `385ee15faf7b32bfa32b488952af40871128cb78`
- CI run: `41326907192` — success
- Heavy Docker smoke run: `41326907185` — success
- observed readiness: LiteLLM healthy and database connected
- restricted K2 key allowlist: `gpt-6.1-sol`, `gpt-image-2`, `codex-*`
- Auto Router dry-run: SIMPLE → `luna-upstream`, `reasoning_effort=medium`

The final hardening change adds runtime assertions for disabled management/documentation surfaces and rejection of a 31-day virtual key under the 30-day server cap. After that code merges, Heavy Docker smoke must run again on the merged code-bearing SHA.

## LiteLLM release maturity

As of 2026-11-03, GitHub's published LiteLLM releases include `v1.109.0-dev.1` and `v1.109.0-dev.2` as pre-releases; the release list does not contain a stable `v1.109.0`. The repository therefore treats `4bdeb137...` as a reviewed source snapshot needed for the subscription-forwarding feature, **not** as evidence of a stable 1.109 release.

K7 must revisit this pin. If a suitable stable 1.109.x or later release contains the required subscription-forwarding behavior, upgrade by exact version/SHA and rerun upstream-contract, CI, Heavy Smoke, and K2-K5 regression gates before release.

## Important mode distinction

LiteLLM also documents a different ChatGPT-provider mode in which the proxy owns a saved `CHATGPT_TOKEN_DIR/auth.json` login. That mode is process-wide and is not the architecture used here. This lab intentionally uses the Codex-forwarded subscription path and contains no proxy-side ChatGPT auth file.

## Must still be proven on the user's Windows machine

- Codex Windows App actually forwards the user's current ChatGPT OAuth through the configured local provider.
- The current subscription can call all target routing models: `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6.1-sol`, and `gpt-6-astra`.
- LiteLLM logs show the selected routing tier/model without a paid OpenAI API fallback.
- The Windows App process receives `LITELLM_API_KEY` and reloads provider/config changes as expected.

## Primary sources

- https://docs.litellm.ai/docs/tutorials/codex_chatgpt_auto_router
- https://docs.litellm.ai/docs/tutorials/openai_codex_byok
- https://docs.litellm.ai/docs/providers/chatgpt
- https://docs.litellm.ai/docs/proxy/security_best_practices
- https://docs.litellm.ai/docs/proxy/config_settings
- https://docs.litellm.ai/blog/security-incident-oct-21-2026
- https://github.com/BerriAI/litellm/commit/4bdeb1378bb19a453cd3c49d383ebe76f057d2c6
- https://github.com/BerriAI/litellm/releases

## Orchestration source contracts

The repository also pins evidence snapshots for the orchestration layer:

- Codex source `67f0994b532b8740f14b5b738af7b7b2a915b1d6`: MultiAgentV2 `SpawnAgentArgs` contains both `model: Option<String>` and `reasoning_effort: Option<ReasoningEffort>`, and passes both into `ThreadSpawnRequest`.
- Superpowers source `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`: SDD requires explicit model selection for subagent dispatch and specifies a stronger model on fix-loop rounds 4–5.
- These are source-contract proofs, not claims that the user's installed Windows App/plugin is already on those exact revisions. K5 still verifies effective rollout metadata on the user's machine.

## Supply-chain pins

- PostgreSQL: `postgres:16.10-bookworm@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74`.
- GitHub Actions checkout: `3d3c42e5aac5ba805825da76410c181273ba90b1`.
- GitHub Actions setup-python: `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0`.

## Additional pre-connection evidence

- LiteLLM's virtual-key API documents `GET /key/info?key=<virtual-key>` authenticated by the master key. The disposable Heavy-smoke test exercises this exact pinned-server contract. The production Windows provisioner instead validates the `models` returned by `/key/generate`, avoiding a real user virtual key in a URL.
- The pinned LiteLLM source test suite contains `chatgpt/gpt-image-2`, providing source-level evidence for the explicit Codex image route.
- OpenAI Codex issue #49736 remains evidence that `PreToolUse` must not be a load-bearing `spawn_agent` guard until reverified on the installed version.
- OpenAI Codex issue #34289 remains evidence that generic `PostToolUse` must not be used as a deterministic failure/exit-code signal.
- LiteLLM documentation states that `STORE_MODEL_IN_DB=True` allows Admin UI/database model configuration to override YAML. This lab therefore keeps it `False` so Git-tracked model config remains authoritative.
- LiteLLM security guidance says direct clients should use `trusted_proxy_ranges: []`, unused Admin UI and API documentation surfaces can be disabled, and `upperbound_key_generate_params` enforces hard upper bounds on key-generation parameters.
- Exact-version caveat: pinned LiteLLM `4bdeb137...` keeps static `/ui` assets mounted even with `DISABLE_ADMIN_UI=True`, so `/ui` → 307 → `/ui/` → HTTP 200 is not by itself a failure. The authoritative runtime proof is `/.well-known/litellm-ui-config` reporting `admin_ui_disabled=true` plus `/sso/key/generate` returning the explicit `Admin UI is Disabled` page before authentication.
