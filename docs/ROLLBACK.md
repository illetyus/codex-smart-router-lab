# Rollback

1. Stop the gateway with `scripts/windows/uninstall.ps1` (without `-RemoveData` unless the database should also be destroyed).
2. Restore the pre-install `%USERPROFILE%\.codex\config.toml` backup if the Codex provider was changed.
3. Restart Codex Windows App and verify a direct model request.
4. Delete `%USERPROFILE%\.codex\.env` only if it contains no unrelated settings.

The installer in phase 1 does not edit Codex's config automatically; therefore rollback of the initial gateway bring-up is only `docker compose down`.
