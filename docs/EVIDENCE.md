# Evidence ledger

This repository separates claims that can be proven before installation from claims that require the user's live Codex/ChatGPT session.

## Proven before Windows installation

- LiteLLM's official **Auto Router with Codex and your ChatGPT subscription** tutorial states that, since v1.109.0, Codex can keep its own ChatGPT login in `Authorization` while a separate LiteLLM gateway credential travels in `x-litellm-api-key`.
- The same tutorial requires `context_compaction: false` for this subscription Auto Router path until the documented compaction/auth interaction is fixed.
- The tutorial documents a catalog-free alternative: expose the router under a model slug Codex already knows and keep the real models under internal aliases. This avoids the very large tool-schema retransmission observed for unknown model aliases.
- LiteLLM source commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` reports version `1.109.0`, is GitHub-signature verified, and is after subscription-passthrough merge `2e27a02a9fce9bdc6ece13ba3cb8222dc5b6ecfa`.
- LiteLLM's October 2026 incident notice identifies the compromised 1.107.0 artifacts; this repository blocks that version and does not use an unpinned `latest`/`main-stable` image.

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
- https://docs.litellm.ai/blog/security-incident-oct-21-2026
- https://github.com/BerriAI/litellm/commit/4bdeb1378bb19a453cd3c49d383ebe76f057d2c6
- https://github.com/BerriAI/litellm/pull/41522

## Orchestration source contracts

The repository also pins evidence snapshots for the orchestration layer:

- Codex source `67f0994b532b8740f14b5b738af7b7b2a915b1d6`: MultiAgentV2 `SpawnAgentArgs` contains both `model: Option<String>` and `reasoning_effort: Option<ReasoningEffort>`, and passes both into `ThreadSpawnRequest`.
- Superpowers source `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`: SDD requires explicit model selection for subagent dispatch and specifies a stronger model on fix-loop rounds 4–5.
- These are source-contract proofs, not claims that the user's installed Windows App/plugin is already on those exact revisions. K4 still verifies effective rollout metadata on the user's machine.

## Supply-chain pins

- PostgreSQL: `postgres:16.10-bookworm@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74`.
- GitHub Actions checkout: `11d5960a326750d5838078e36cf38b85af677262`.
- GitHub Actions setup-python: `a26af69be951a213d495a4c3e4e4022e16d87065`.
