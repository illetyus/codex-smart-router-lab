# Architecture

Codex Windows App keeps ownership of the user's ChatGPT OAuth session. Requests are sent to a local LiteLLM gateway on `127.0.0.1:4000`; the gateway credential is separate from the ChatGPT credential. LiteLLM forwards the caller's ChatGPT credential only to the ChatGPT/Codex upstream and records routing/usage metadata.

The default bring-up configuration is `subscription.yaml`: it has no Auto Router and no paid OpenAI API fallback. Only after passthrough is proven should `autorouter.yaml` be enabled.

The initial Auto Router policy is intentionally conservative: SIMPLE→Luna/medium, MEDIUM→Terra/medium, COMPLEX→Sol/high, REASONING→Astra/high. This is a starting policy, not a claim that every account exposes every model. The Windows pilot must discover the actual model slugs and adjust the mapping before production use.

Superpowers and Codex native subagents are the orchestration layer. LiteLLM classifies a new user turn; Superpowers owns task decomposition, review, and fix-loop escalation. Failure-driven model escalation should happen at a fresh-worker boundary, not by repeatedly changing models inside one long trajectory.


## Catalog-free router alias

The first production candidate does not expose a new `codex-smart-router` model name to Codex. In Auto Router mode, LiteLLM exposes the router as `gpt-6.1-sol`, which Codex already knows, while the actual deployments are internal aliases (`luna-upstream`, `terra-upstream`, `sol-upstream`, `astra-upstream`). This follows LiteLLM's documented alternative to maintaining a custom Codex model catalog and avoids unknown-model tool-schema retransmission overhead.

The trade-off is intentional: the Codex picker still says GPT-6.1 Sol while LiteLLM may execute another model. LiteLLM logs are therefore the source of truth for the routed model. The baseline `subscription.yaml` remains available to test real direct GPT-6.1 Sol without routing.


## Configuration ownership

PostgreSQL remains required for virtual-key state, but `STORE_MODEL_IN_DB=False`. Model and router definitions are owned by the pinned YAML files in this repository; the Admin UI/database is not allowed to silently become the model source of truth.

The gateway also exposes explicit `gpt-image-2 -> chatgpt/gpt-image-2` and `codex-* -> chatgpt/codex-*` routes so Codex image generation and review/approval traffic do not depend on a broad `gpt-*` wildcard.

## Orchestration enforcement boundary

The managed global AGENTS block makes Superpowers SDD the required implementation/fix-loop path and requires explicit worker model + effort. This is governance, not a hard security hook. Codex issue #49736 currently prevents treating `PreToolUse(spawn_agent)` as a reliable enforcement boundary; issue #34289 prevents treating generic `PostToolUse` as a reliable exit-code failure detector.
