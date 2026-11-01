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
