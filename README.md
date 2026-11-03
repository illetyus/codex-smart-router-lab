# codex-smart-router-lab

A Windows installation and validation lab for routing **Codex in ChatGPT Desktop** through a local LiteLLM gateway while preserving the user's own ChatGPT subscription authentication.

The user runtime is now **Native Windows**. Docker is not required on the user's PC; Docker Compose remains in the repository only for CI/Heavy Smoke validation of the same pinned LiteLLM source and routing contracts.

## Bring-up order

Do not enable Auto Router first. The sequence remains:

1. validate the local native runtime;
2. prove one-model ChatGPT-subscription passthrough with `gpt-6.1-sol` (K2);
3. verify the account can call Luna/Terra/Sol/Astra (K3);
4. enable/calibrate routing (K4);
5. prove Superpowers/native-subagent routing and escalation (K5);
6. run a real-project pilot (K6);
7. freeze the validated Windows release (K7).

## Runtime architecture

```text
ChatGPT Desktop / Codex
        |  ChatGPT OAuth
        |  + x-litellm-api-key
        v
127.0.0.1:4000
Native LiteLLM (Python 3.13 / uv)
        |
        v
PostgreSQL 16.15 Windows service
```

LiteLLM is source-pinned to `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` (source version 1.109.0). It is installed from that exact Git commit with the committed `uv.lock`; an unpinned `uv tool install litellm` is not the production path.

## Safety properties

- Gateway binds explicitly to `127.0.0.1:4000`.
- Native PostgreSQL is local and used for restricted virtual keys/usage state.
- Runtime secrets live under `%LOCALAPPDATA%\CodexSmartRouter\router.env`, ACL-restricted to the current Windows user.
- ChatGPT OAuth remains owned by Codex.
- LiteLLM master key and Codex virtual key remain separate.
- `STORE_MODEL_IN_DB=False`; model/router definitions remain Git/YAML-owned.
- Admin UI and Swagger/ReDoc/OpenAPI surfaces are disabled.
- No `OPENAI_API_KEY` and no paid OpenAI API fallback.
- Virtual keys have a server-side 30-day maximum lifetime.
- LiteLLM `1.107.0` remains prohibited due to the October 21, 2026 supply-chain compromise.

## Native Windows quick start

Install PostgreSQL 16.15 and its command-line tools first, then:

```powershell
pwsh -File .\scripts\windows\provision-postgres.ps1
pwsh -File .\scripts\windows\preflight.ps1 -Runtime native
pwsh -File .\scripts\windows\install.ps1 -Runtime native -Mode subscription
```

The native installer uses `uv`, Python 3.13 and the audited LiteLLM source commit, pre-generates Prisma, applies migrations, copies the reviewed configs into `%LOCALAPPDATA%\CodexSmartRouter`, and registers a current-user Task Scheduler job so LiteLLM starts hidden at logon.

Then continue with K2:

```powershell
pwsh -File .\scripts\windows\provision-codex-key.ps1 -Profile k2
pwsh -File .\scripts\windows\configure-codex-provider.ps1
pwsh -File .\scripts\windows\verify.ps1
```

Fully restart ChatGPT Desktop/Codex and start a brand-new task before the live probe.

See `docs/NATIVE-WINDOWS.md` for the full Dockerless install and `docs/K2-WINDOWS.md` through `docs/K5-ESCALATION.md` for the validation stages.

## Docker / CI role

`docker-compose.yml` is retained for **CI/Heavy Smoke**, not as a user prerequisite. It builds the same pinned LiteLLM source, uses a digest-pinned PostgreSQL 16.15 image, proves virtual-key management, health/readiness, hardening boundaries, model-probe startup and Auto Router dry-run.

No live Codex/ChatGPT OAuth request is considered validated merely because Docker CI is green. K2 still requires a real request from the user's Windows ChatGPT Desktop/Codex session to appear in LiteLLM logs.
