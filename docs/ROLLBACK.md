# Rollback

The primary Windows runtime is native. Rollback keeps the PostgreSQL database unless the user explicitly removes it outside these scripts.

1. Close ChatGPT Desktop/Codex.
2. Restore the pre-install Codex provider and dotenv with `scripts/windows/restore-codex-provider.ps1`.
3. Stop/unregister the native router with `scripts/windows/uninstall.ps1 -Runtime native`.
4. Restart ChatGPT Desktop/Codex and verify a direct Codex request.

By default `uninstall.ps1 -Runtime native` preserves `%LOCALAPPDATA%\CodexSmartRouter` and the local PostgreSQL database. Add `-RemoveData` only when the installed LiteLLM source/config/secrets/logs should also be removed. Database deletion is deliberately not automated.

The Docker compatibility/CI path can still be stopped explicitly with:

```powershell
pwsh -File .\scripts\windows\uninstall.ps1 -Runtime docker
```

Use `-RemoveData` on the Docker path only when the disposable Compose PostgreSQL volume should be deleted.

## Drift-safe Codex rollback

The configurator records a SHA-256 of the exact Codex config it installed, and the key provisioner records a SHA-256 of the Codex dotenv it last wrote. If either file changes later, rollback first writes a timestamped `pre-litellm-restore-conflict` copy before restoring the pre-LiteLLM snapshot. This prevents silent data loss while still providing a deterministic emergency rollback.

The managed smart-router AGENTS block has a separate surgical removal script:

```powershell
pwsh -File .\scripts\windows\restore-smart-router-policy.ps1
```

It removes only the marked smart-router block and preserves unrelated AGENTS instructions.
