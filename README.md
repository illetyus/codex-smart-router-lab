# codex-smart-router-lab

A public installation and validation lab for routing **Codex Windows App** requests through a local LiteLLM gateway while keeping the user's own ChatGPT subscription authentication.

This repository is deliberately staged. It does **not** enable Auto Router first. The sequence is: validate the local stack → prove one-model subscription passthrough with `gpt-6.1-sol` → verify the account can call Luna/Terra/Sol/Astra → enable routing → add Superpowers/native-subagent escalation.

## Current status

K0/K1 scaffold is under test. The baseline has no OpenAI API key and no paid API fallback. LiteLLM is source-pinned to `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6`, which is after the merged subscription-passthrough change and reports version 1.109.0 in `pyproject.toml`.

## Safety properties

- Gateway: `127.0.0.1:4000` only.
- Postgres: internal Compose network only.
- Secrets: generated into ignored `.env` files, never committed.
- ChatGPT OAuth: remains owned by Codex.
- Baseline routing: one explicit model only, `chatgpt/gpt-6.1-sol`.
- Paid fallback: intentionally absent.
- LiteLLM `1.107.0`: prohibited due to the October 21, 2026 supply-chain compromise.

## Windows bring-up (not yet the final Codex install)

```powershell
pwsh -File .\scripts\windows\preflight.ps1
pwsh -File .\scripts\windows\install.ps1 -Mode subscription
```

After K2 is proven, `-Mode autorouter` becomes eligible. In Auto Router mode the proxy deliberately exposes the router as the already-known `gpt-6.1-sol` slug while Luna/Terra/Sol/Astra use internal aliases. This avoids a custom Codex model-catalog entry and the large tool-schema resend penalty documented by LiteLLM. Do not begin with Auto Router.

See `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, and `docs/ROLLBACK.md`.
