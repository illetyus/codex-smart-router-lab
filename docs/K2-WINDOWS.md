# K2 — Windows Codex subscription passthrough

K2 proves one thing before Auto Router is enabled: **Codex Windows App keeps the user's ChatGPT login while requests pass through the local LiteLLM gateway.**

Do not enable `autorouter` mode until every gate below passes.

## 1. Start the baseline gateway

From this repository in PowerShell:

```powershell
pwsh -File .\scripts\windows\preflight.ps1
pwsh -File .\scripts\windows\install.ps1 -Mode subscription
```

Expected state:

- LiteLLM listens only on `127.0.0.1:4000`.
- Postgres is reachable only inside the Compose network.
- `configs/litellm/subscription.yaml` exposes direct `gpt-6.1-sol` plus `codex-*` passthrough for Codex approval/review requests.
- No `OPENAI_API_KEY` exists in the gateway configuration.

Check health:

```powershell
Invoke-RestMethod http://127.0.0.1:4000/health/liveliness
```

## 2. Create a restricted LiteLLM virtual key

Open the local LiteLLM dashboard, then **Virtual Keys → + Create New Key**.

For the K2 key:

- Name/alias: `codex-k2`
- Allowed models: `gpt-6.1-sol` and `codex-*`
- Do not grant an API-backed fallback model.

Why `codex-*` is required: Codex can issue approval/review requests such as `codex-auto-review` in addition to the selected GPT model. LiteLLM's official Codex subscription guide explicitly requires both GPT and Codex routes.

Save the generated virtual key in:

`%USERPROFILE%\.codex\.env`

```dotenv
LITELLM_API_KEY=sk-<your-litellm-virtual-key>
```

Do not put the LiteLLM master key in the Codex `.env` file.

## 3. Back up Codex configuration

Before changing the provider:

```powershell
$codex = Join-Path $env:USERPROFILE '.codex'
Copy-Item "$codex\config.toml" "$codex\config.toml.pre-litellm-backup" -Force
```

The ChatGPT auth files are not copied or modified by this project.

## 4. Connect Codex Windows App

Open `%USERPROFILE%\.codex\config.toml` (or Settings → Configuration → Open config.toml in Codex App).

Keep the existing model and reasoning settings. Set the top-level provider:

```toml
model_provider = "litellm_subscription"
```

Add:

```toml
[model_providers.litellm_subscription]
name = "LiteLLM subscription"
base_url = "http://localhost:4000/v1"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = true
env_http_headers = { "x-litellm-api-key" = "LITELLM_API_KEY" }
```

**Do not set `env_key`.** Leaving it unset is what keeps Codex's ChatGPT `Authorization` credential instead of replacing it with the LiteLLM virtual key.

Fully restart Codex Windows App after changing either `config.toml` or `%USERPROFILE%\.codex\.env`.

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

Close Codex App, restore the backup, stop the local gateway, then restart Codex:

```powershell
$codex = Join-Path $env:USERPROFILE '.codex'
Copy-Item "$codex\config.toml.pre-litellm-backup" "$codex\config.toml" -Force
pwsh -File .\scripts\windows\uninstall.ps1
```

A direct Codex chat must work again before K2 is marked complete.

## Sources

- https://docs.litellm.ai/docs/tutorials/openai_codex_byok
- https://docs.litellm.ai/docs/tutorials/codex_chatgpt_auto_router
- https://docs.litellm.ai/docs/proxy/virtual_keys
