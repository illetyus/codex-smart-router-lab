# Status

Last updated: 2026-11-01

## Completed

- Public repository created: `illetyus/codex-smart-router-lab`.
- LiteLLM source pinned to verified commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` (version 1.109.0).
- ChatGPT subscription baseline config created for direct `gpt-6.1-sol`.
- Catalog-free Auto Router config created with internal Luna/Terra/Sol/Astra aliases.
- No OpenAI API key or paid API fallback is present.
- Gateway is localhost-only; Postgres has no host-published port.
- Windows preflight/install/verify/uninstall scripts added.
- GitHub Actions normal CI is green:
  - Python contract suite: 19 tests.
  - Independent repository validator.
  - Docker Compose render with disposable non-secret values.
  - Windows PowerShell parser.
  - Immutable upstream source contract.

## In progress

- Heavy Docker smoke for the first publish commit: build pinned LiteLLM source, start subscription config, health check, recreate with Auto Router config, health check.

## Not yet proven

- Real Codex Windows App forwarding the user's ChatGPT OAuth through the local gateway.
- Live restricted LiteLLM virtual-key path.
- Live access to all four target models on the user's subscription.
- Real routing decisions in LiteLLM logs.
- Superpowers/native-subagent model+effort routing and deterministic failure escalation.

## Next gate

K2 begins only after the heavy Docker source/health smoke is green. K2 starts in `subscription` mode, not Auto Router mode.
