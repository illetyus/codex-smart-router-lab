# Rollback

1. Stop the gateway with `scripts/windows/uninstall.ps1` (without `-RemoveData` unless the database should also be destroyed).
2. Restore the pre-install `%USERPROFILE%\.codex\config.toml` backup if the Codex provider was changed.
3. Restart Codex Windows App and verify a direct model request.
4. Delete `%USERPROFILE%\.codex\.env` only if it contains no unrelated settings.

The installer in phase 1 does not edit Codex's config automatically; therefore rollback of the initial gateway bring-up is only `docker compose down`.


## Drift-safe rollback

The configurator records a SHA-256 of the exact Codex config it installed, and the key provisioner records a SHA-256 of the Codex dotenv it last wrote. If either file changes later, rollback first writes a timestamped `pre-litellm-restore-conflict` copy before restoring the pre-LiteLLM snapshot. This prevents silent data loss while still providing a deterministic emergency rollback.

The managed smart-router AGENTS block has a separate surgical removal script:

```powershell
pwsh -File .\scripts\windows\restore-smart-router-policy.ps1
```

It removes only the marked smart-router block and preserves unrelated AGENTS instructions.
