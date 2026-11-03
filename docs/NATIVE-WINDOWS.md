# Native Windows runtime (no Docker)

This is the primary user installation path for Codex Smart Router on Windows. **Docker is not required** on the user's PC. Docker remains a CI/Heavy Smoke tool for reproducible repository validation.

## Runtime shape

```text
ChatGPT Desktop / Codex
        |
        | ChatGPT OAuth + x-litellm-api-key
        v
127.0.0.1:4000
Native LiteLLM (Python 3.13 / uv)
        |
        v
PostgreSQL 16.15 (Windows service)
```

LiteLLM is installed from audited source commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6`, not an unpinned `latest` package. The native launcher restores the Docker CI hardening environment and binds explicitly to `127.0.0.1:4000`.

## Prerequisites

- Windows 11 or a comparable supported 64-bit Windows desktop.
- PowerShell 7.
- Git.
- `uv`.
- Node.js 24.x. LiteLLM's Prisma database tooling uses Node; the router itself remains Python.
- PostgreSQL 16.15 with command-line tools (`psql`, `createdb`, `pg_isready`).
- ChatGPT Desktop/Codex already signed in, with `%USERPROFILE%\.codex\config.toml` present.

Use the official PostgreSQL Windows installer linked by PostgreSQL.org. Keep PostgreSQL local; this project does not require a firewall exception or remote database listener.

## 1. Provision PostgreSQL

```powershell
pwsh -File .\scripts\windows\provision-postgres.ps1
```

The helper prompts for the local PostgreSQL administrator password, creates or updates a dedicated `litellm` login and database, generates a random application password, and stores only the resulting `DATABASE_URL` in `%LOCALAPPDATA%\CodexSmartRouter\router.env`. The file ACL is restricted to the current user. The administrator password exists only in the process-level `PGPASSWORD` variable while `psql` runs and is removed afterward.

## 2. Native preflight

```powershell
pwsh -File .\scripts\windows\preflight.ps1 -Runtime native
```

Native preflight checks Windows, PowerShell 7, Git, uv, Node, PostgreSQL command-line tools, the Codex config, and the loopback port. It does not require Docker.

## 3. Install the pinned native gateway

Start with K2 subscription mode:

```powershell
pwsh -File .\scripts\windows\install.ps1 -Runtime native -Mode subscription
```

The installer clones/fetches the exact LiteLLM commit, checks it out detached, runs `uv sync --frozen --python 3.13 --extra proxy --extra extra_proxy`, pre-generates Prisma and applies migrations, copies reviewed configs into the private runtime directory, generates persistent LiteLLM master/salt keys, and registers a current-user Task Scheduler entry.

Installed files live under `%LOCALAPPDATA%\CodexSmartRouter`. Task Scheduler starts the router hidden at user logon, retries a bounded number of failures, and has no execution time limit.

## 4. Native hardening

The launcher forces:

```text
STORE_MODEL_IN_DB=False
DISABLE_ADMIN_UI=True
NO_DOCS=True
NO_REDOC=True
NO_OPENAPI=True
CHECKPOINT_DISABLE=1
```

It rejects `OPENAI_API_KEY` in the router env file. There is no paid OpenAI API fallback. Do not change the listener from `127.0.0.1:4000` to `0.0.0.0`.

## 5. K2 live passthrough

```powershell
pwsh -File .\scripts\windows\provision-codex-key.ps1 -Profile k2
pwsh -File .\scripts\windows\configure-codex-provider.ps1
pwsh -File .\scripts\windows\verify.ps1
```

Fully exit ChatGPT Desktop/Codex, restart it, create a brand-new task, and send:

> Reply with exactly Hello. Do not use tools.

K2 passes only when the matching request appears in LiteLLM logs through the ChatGPT subscription path.

## 6. Later phases

- K3: `model-probe` and the real account model/effort matrix.
- K4: `autorouter` calibration.
- K5: Superpowers/native-subagent routing and escalation.
- K6: real reversible project pilot.
- K7: rollback/revoke rehearsal, evidence freeze, release tag.

Re-run `install.ps1 -Runtime native -Mode <mode>` to update the installed config/task mode while preserving existing native secrets.

## 7. Uninstall

```powershell
pwsh -File .\scripts\windows\uninstall.ps1 -Runtime native
```

This unregisters the scheduled task but preserves runtime files and the PostgreSQL database. Add `-RemoveData` to remove installed LiteLLM source/config/secrets/logs. The PostgreSQL database is preserved even with `-RemoveData`; database deletion is intentionally not automated.

## Sources

- LiteLLM Proxy CLI quick start: https://docs.litellm.ai/docs/proxy/quick_start
- LiteLLM virtual keys/PostgreSQL: https://docs.litellm.ai/docs/proxy/virtual_keys
- LiteLLM Prisma/uv upgrades: https://docs.litellm.ai/docs/troubleshoot/pip_venv_upgrade
- LiteLLM outbound/Prisma downloads: https://docs.litellm.ai/docs/proxy/outbound_requests
- PostgreSQL Windows installer: https://www.postgresql.org/download/windows/
