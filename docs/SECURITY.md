# Security model

- LiteLLM binds to `127.0.0.1` only.
- Postgres has no host-published port.
- No OpenAI API key or paid fallback is configured in the baseline.
- Secrets live only in untracked `.env` or `%USERPROFILE%\.codex\.env` files.
- ChatGPT OAuth remains owned/refreshed by Codex; it is not committed to this repository.
- LiteLLM source is pinned to a reviewed full Git commit SHA rather than an unpinned package/image tag.
- LiteLLM 1.107.0 is explicitly prohibited because the published PyPI/Docker artifacts were compromised on 2026-10-21.
- Do not enable prompt/header storage until redaction behavior is revalidated for the exact LiteLLM version.


## ChatGPT credential mode

This repository uses the Codex-forwarded subscription flow documented in LiteLLM's Codex Auto Router tutorial: Codex owns the ChatGPT `Authorization` credential and the gateway key travels separately in `x-litellm-api-key`. It does **not** mount or persist a LiteLLM `CHATGPT_TOKEN_DIR` / `auth.json` credential for the proxy. Those are a different saved-account mode and are intentionally excluded from the baseline.
