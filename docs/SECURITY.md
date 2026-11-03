# Security model

- LiteLLM binds to `127.0.0.1` only.
- Native PostgreSQL is a local Windows service; the user path does not require a remote listener or firewall exception. Docker CI still publishes no Postgres host port.
- No OpenAI API key or paid fallback is configured in the baseline.
- Native gateway secrets live in ACL-restricted `%LOCALAPPDATA%\CodexSmartRouter\router.env`; Docker compatibility uses the ignored repository `.env`; Codex receives only its restricted virtual key in `%USERPROFILE%\.codex\.env`.
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

The project does not use LiteLLM's browser administration surface. Both Docker CI and the native Windows launcher set `DISABLE_ADMIN_UI=True`. Swagger/ReDoc/OpenAPI discovery is also unnecessary, so both runtime paths set `NO_DOCS=True`, `NO_REDOC=True`, and `NO_OPENAPI=True`. The native launcher also sets `CHECKPOINT_DISABLE=1` and binds the CLI explicitly to `127.0.0.1`; it never relies on LiteLLM's interface default.

For the pinned LiteLLM source `4bdeb137...`, `/ui` static assets remain mounted even when `DISABLE_ADMIN_UI=True`; `/ui` therefore normalizes to `/ui/` and may return HTTP 200. That static response is not the authorization boundary. Heavy Smoke instead verifies the server-side discovery flag `admin_ui_disabled=true` at `/.well-known/litellm-ui-config` and verifies that a normal `/sso/key/generate` request returns the explicit `Admin UI is Disabled` page before authentication.

The same pinned source contains a deliberate CLI SSO exception: `/sso/key/generate?source=litellm-cli` may pass the first Admin-UI-disabled gate when it carries a valid CLI flow handle. This deployment has no SSO provider credentials in Compose (`GOOGLE_CLIENT_ID`, `MICROSOFT_CLIENT_ID`, and `GENERIC_CLIENT_ID` are not passed, and SAML is not configured), so the exception cannot complete an SSO login and falls back to the disabled boundary. This is why the security claim is scoped to the current no-SSO localhost deployment. If SSO is introduced later, re-audit this path and extend Heavy Smoke before release.

If the LiteLLM pin changes, revalidate these exact-version semantics.

## Secret lifetime and Windows ACLs

The native gateway `router.env`, Docker compatibility `.env`, and Codex `.env` are explicitly ACL-restricted to the current Windows user by the installation/provisioning scripts. Existing placeholder files containing `CHANGE_ME`, malformed short secrets, or `OPENAI_API_KEY` are rejected instead of silently used.

Codex gateway virtual keys default to a 30-day lifetime. All committed LiteLLM modes also enforce a server-side `litellm_settings.upperbound_key_generate_params.duration: 30d` cap, so a client cannot request a longer-lived key by overriding the PowerShell default. Re-provisioning replaces the local key line; no paid OpenAI API fallback exists. The production provisioner does not place the real virtual key in a URL. The disposable Heavy-smoke key is allowed to exercise the documented `/key/info?key=...` management contract because it exists only for the isolated test stack.

Rollback conflict copies of Codex `.env` are treated as secret material and receive the same ACL restriction.

## Primary hardening references

- https://docs.litellm.ai/docs/proxy/security_best_practices
- https://docs.litellm.ai/docs/proxy/config_settings
- https://docs.litellm.ai/docs/proxy/ui
