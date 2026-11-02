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

## Local gateway hardening

The gateway is a direct-client localhost deployment, not a reverse-proxy deployment. Every committed LiteLLM mode therefore sets:

```yaml
general_settings:
  trusted_proxy_ranges: []
```

LiteLLM documents `[]` for direct clients so the TCP peer address is used and caller-supplied `X-Forwarded-For` is ignored. This also removes the weaker-login-throttling startup warning seen when the setting is absent.

The project does not use LiteLLM's browser administration surface. Compose therefore sets `DISABLE_ADMIN_UI=True`. Swagger/ReDoc/OpenAPI discovery is also unnecessary for the Codex gateway, so `NO_DOCS=True`, `NO_REDOC=True`, and `NO_OPENAPI=True` are set. Inference, health, and authenticated management APIs remain available.

## Secret lifetime and Windows ACLs

The local gateway `.env` and Codex `.env` are explicitly ACL-restricted to the current Windows user by the installation/provisioning scripts. Existing placeholder files containing `CHANGE_ME`, malformed short secrets, or `OPENAI_API_KEY` are rejected instead of silently used.

Codex gateway virtual keys default to a 30-day lifetime. All committed LiteLLM modes also enforce a server-side `litellm_settings.upperbound_key_generate_params.duration: 30d` cap, so a client cannot request a longer-lived key by overriding the PowerShell default. Re-provisioning replaces the local key line; no paid OpenAI API fallback exists. The production provisioner does not place the real virtual key in a URL. The disposable Heavy-smoke key is allowed to exercise the documented `/key/info?key=...` management contract because it exists only for the isolated test stack.

Rollback conflict copies of Codex `.env` are treated as secret material and receive the same ACL restriction.

## Primary hardening references

- https://docs.litellm.ai/docs/proxy/security_best_practices
- https://docs.litellm.ai/docs/proxy/config_settings
- https://docs.litellm.ai/docs/proxy/ui
