# K2 — Windows Codex subscription passthrough

K2 proves one thing before Auto Router is enabled: **Codex Windows App keeps the user's ChatGPT login while requests pass through the local LiteLLM gateway.**

Do not enable `autorouter` mode until every gate below passes.

## 1. Start the baseline gateway

The primary user path is native Windows. Install PostgreSQL 16.15 and its command-line tools, then run:

```powershell
pwsh -File .\scripts\windows\provision-postgres.ps1
pwsh -File .\scripts\windows\preflight.ps1 -Runtime native
pwsh -File .\scripts\windows\install.ps1 -Runtime native -Mode subscription
```

Expected state:

- LiteLLM listens only on `127.0.0.1:4000`.
- PostgreSQL runs as a local Windows service and is reached through the private `DATABASE_URL` in `%LOCALAPPDATA%\CodexSmartRouter\router.env`.
- The native LiteLLM process is installed from the audited source commit, not a floating package.
- `configs/litellm/subscription.yaml` exposes direct `gpt-6.1-sol` plus `gpt-image-2` and `codex-*` passthrough.
- No `OPENAI_API_KEY` exists in the gateway configuration.
- Docker is not required on the user's PC; Docker remains a CI/Heavy Smoke validation path.

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:4000/health/liveliness
```

## 2. Provision a restricted LiteLLM virtual key

Preferred path:

```powershell
pwsh -File .\scripts\windows\provision-codex-key.ps1 -Profile k2
```

The helper prefers the native gateway master key from `%LOCALAPPDATA%\CodexSmartRouter\router.env` and falls back to the repository `.env` only for the Docker/CI-compatible path. It asks the localhost LiteLLM gateway for a `codex-k2` virtual key and stores only the resulting virtual key in `%USERPROFILE%\.codex\.env`. The key value is never printed. If a Codex `.env` already exists, its other lines are preserved and a one-time `.env.pre-litellm-backup` is created.

The K2 allowlist is exactly:

- `gpt-6.1-sol`
- `codex-*`

Why `codex-*` is required: Codex can issue approval/review requests such as `codex-auto-review` in addition to the selected GPT model. LiteLLM's official Codex subscription guide requires both GPT and Codex routes.

Do not put the LiteLLM master key in the Codex `.env` file. The local dashboard can still be used as a manual fallback, but the scripted path is the repeatable installation path.

## 3. Configure the Codex provider with rollback

Close Codex App, then run:

```powershell
pwsh -File .\scripts\windows\configure-codex-provider.ps1
```

The helper creates `%USERPROFILE%\.codex\config.toml.pre-litellm-backup` once, preserves existing model/reasoning/features settings, replaces only the top-level `model_provider`, removes any older duplicate LiteLLM provider table, and writes exactly one tested provider block:

```toml
model_provider = "litellm_subscription"

[model_providers.litellm_subscription]
name = "LiteLLM subscription"
base_url = "http://127.0.0.1:4000/v1"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = true
env_http_headers = { "x-litellm-api-key" = "LITELLM_API_KEY" }
```

**Do not set `env_key`.** The helper never writes it and never reads or changes `auth.json`. Leaving `env_key` unset is what lets Codex keep its own ChatGPT `Authorization` credential while the LiteLLM virtual key travels separately in `x-litellm-api-key`.

Fully restart Codex Windows App after this step.

## 5. Exact live probe

Start a fresh Codex chat with GPT-6.1 Sol and send exactly:

> Reply with exactly Hello. Do not use tools.

Expected response: `Hello`.

Then inspect LiteLLM Logs. The request must show:

- model/group corresponding to `gpt-6.1-sol`,
- the K2 virtual key,
- input/output token counts,
- recorded ChatGPT-subscription cost of `$0`,
- no OpenAI API deployment/fallback.

If an approval/review turn occurs, `codex-auto-review` or another `codex-*` request must also pass through rather than returning model-access/404 errors.

## 6. Failure conditions — K2 does not pass

K2 is **not** complete if any of the following occurs:

- no request appears in LiteLLM Logs,
- LiteLLM says the gateway key is missing,
- `Authorization` is replaced by the gateway credential,
- OpenAI rejects the ChatGPT login,
- `codex-auto-review` / `codex-*` is denied,
- an API-backed OpenAI deployment serves the request,
- Codex works only after adding an `OPENAI_API_KEY`.

## 7. Rollback proof

Close Codex App, restore the pre-LiteLLM Codex configuration and dotenv, then stop the native gateway:

```powershell
pwsh -File .\scripts\windows\restore-codex-provider.ps1
pwsh -File .\scripts\windows\uninstall.ps1 -Runtime native
```

The restore helper copies the original `config.toml` backup back byte-for-byte. If a pre-LiteLLM `.env` backup exists it restores that too; otherwise it removes only the `LITELLM_API_KEY` line. It never modifies ChatGPT authentication files.

Restart Codex and prove a direct Codex chat works again before K2 is marked complete.

## Sources

- https://docs.litellm.ai/docs/tutorials/openai_codex_byok
- https://docs.litellm.ai/docs/tutorials/codex_chatgpt_auto_router
- https://docs.litellm.ai/docs/proxy/virtual_keys


## Restart is part of the evidence gate

The desktop app/background server may retain the provider environment that existed when it started. After writing `%USERPROFILE%\.codex\.env` or changing `config.toml`, fully exit the Codex/ChatGPT desktop process and start it again. A file-only verification is not sufficient.

K2 passes only when a brand-new Codex turn after that restart appears in LiteLLM logs through the local gateway. The prompt remains the minimal no-tool probe. Do not infer passthrough from `verify.ps1` alone.

The K2 virtual key is created with a 30-day lifetime, is ACL-restricted to the current Windows user, and includes the explicit `gpt-image-2` route needed by Codex image generation. The production provisioner validates the allowlist from `/key/generate`; it does not put the real virtual key in a URL.
