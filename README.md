# codex-smart-router-lab

A public installation and validation lab for routing **Codex Windows App** requests through a local LiteLLM gateway while keeping the user's own ChatGPT subscription authentication.

This repository is deliberately staged. It does **not** enable Auto Router first. The sequence is: validate the local stack → prove one-model subscription passthrough with `gpt-6.1-sol` → verify the account can call Luna/Terra/Sol/Astra → enable routing → add Superpowers/native-subagent escalation.

## Current status

K0/K1 static gates are green on GitHub Actions: repository contract tests, independent validator, Docker Compose rendering with disposable CI values, Windows PowerShell parsing, and immutable upstream-contract checks all pass. The source-build/health heavy smoke gate is tracked separately. K2 live Codex/ChatGPT subscription passthrough has **not** been claimed yet and must be proven on the user's Windows Codex App.

The baseline has no OpenAI API key and no paid API fallback. LiteLLM is source-pinned to `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6`, which is after the merged subscription-passthrough change and reports version 1.109.0 in `pyproject.toml`.

## Safety properties

- Gateway: `127.0.0.1:4000` only.
- Postgres: internal Compose network only.
- Secrets: generated into ignored `.env` files, never committed; Windows scripts restrict their ACL to the current user and virtual keys default to a 30-day lifetime.
- ChatGPT OAuth: remains owned by Codex.
- Baseline text routing: one explicit text model, `chatgpt/gpt-6.1-sol`, plus explicit `gpt-image-2` and `codex-*` subscription routes.
- Paid fallback: intentionally absent.
- LiteLLM `1.107.0`: prohibited due to the October 21, 2026 supply-chain compromise.

## Windows bring-up (not yet the final Codex install)

```powershell
pwsh -File .\scripts\windows\preflight.ps1
pwsh -File .\scripts\windows\install.ps1 -Mode subscription
```

After K2 is proven, `-Mode autorouter` becomes eligible. In Auto Router mode the proxy deliberately exposes the router as the already-known `gpt-6.1-sol` slug while Luna/Terra/Sol/Astra use internal aliases. This avoids a custom Codex model-catalog entry and the large tool-schema resend penalty documented by LiteLLM. Do not begin with Auto Router.

See `docs/STATUS.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY.md`, `docs/EVIDENCE.md`, and `docs/ROLLBACK.md`.


## Pre-connection audit rule

No live Codex/ChatGPT OAuth request is allowed merely because normal CI is green. Before K2, the current main commit must have a successful Heavy Docker smoke proving the pinned LiteLLM source build, Postgres/proxy readiness, real virtual-key management API, router dry-run, and cleanup. K2 then requires a full desktop-app restart and a brand-new request observed in LiteLLM logs.
