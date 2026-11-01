# K3 — Router-free model probe

K3 verifies the target ChatGPT subscription model set **before** the Auto Router is enabled.

Do not use `autorouter` mode until every direct model probe below succeeds.

## 1. Start model-probe mode

From the repository in PowerShell:

```powershell
pwsh -File .\scripts\windows\install.ps1 -Mode model-probe
pwsh -File .\scripts\windows\verify.ps1
```

This loads `configs/litellm/model-probe.yaml`. It contains only direct ChatGPT subscription routes; there is no `auto_router/complexity_router` deployment.

## 2. Scope a temporary K3 virtual key

Create a LiteLLM virtual key that allows exactly:

- `gpt-6.1-sol`
- `gpt-6-luna`
- `gpt-6.1-terra`
- `gpt-6-sol`
- `gpt-6-astra`
- `codex-*`

Store the virtual key as `LITELLM_API_KEY` in `%USERPROFILE%\.codex\.env`. Never place the LiteLLM master key there.

## 3. Direct model probes

Fully restart Codex after changing gateway mode or `.codex\.env`.

For each target model, start a fresh Codex conversation, select that exact model, and send:

> Reply with exactly MODEL_OK. Do not use tools.

Probe in this order:

1. `gpt-6.1-sol`
2. `gpt-6-luna`
3. `gpt-6.1-terra`
4. `gpt-6-sol`
5. `gpt-6-astra`

For every probe require all of the following:

- response is exactly `MODEL_OK`;
- LiteLLM logs show the requested `chatgpt/` upstream and the K3 virtual key;
- no `openai/` API deployment or API-key fallback serves the request;
- the request remains subscription-covered;
- no model-access, 404, device-code-login, or unsupported-model error occurs.

The model picker alone is not evidence. Account/catalog availability is proven only by a successful request through this gateway.

## 4. Inspect the effective Codex rollout

After each probe:

```powershell
pwsh -File .\scripts\windows\inspect-session.ps1
```

The script ignores `codex-auto-review` rollouts and returns the newest real rollout as JSON. Check `Model` and `Effort` against the probe you just ran.

## 5. Gate

K3 passes only when all five direct model probes succeed.

Only then switch to:

```powershell
pwsh -File .\scripts\windows\install.ps1 -Mode autorouter
```

If any model fails, keep Auto Router disabled and adjust the routing ladder to the model set the account actually exposes. Do not silently substitute an API-backed deployment.

## Evidence note

The pinned LiteLLM 1.109 source forwards ChatGPT Responses requests generically, but static catalog/cost metadata is not treated as proof of account entitlement. K3 intentionally uses live subscription probes as the source of truth.
