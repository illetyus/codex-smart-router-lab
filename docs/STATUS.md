# Status

Last updated: 2026-11-03

## Completed

- Public repository created: `illetyus/codex-smart-router-lab`.
- LiteLLM source pinned to verified commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` (source version 1.109.0).
- ChatGPT subscription baseline config includes direct `gpt-6.1-sol`, explicit `gpt-image-2`, and `codex-*` review/approval passthrough.
- Catalog-free Auto Router uses internal Luna/Terra/GPT-6.1-Sol/Astra tier aliases.
- Explicit Superpowers worker routes are exposed under known Codex slugs: `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6-sol`, and `gpt-6-astra`.
- No OpenAI API key or paid API fallback is present.
- Gateway is localhost-only; Postgres has no host-published port and its image is pinned by digest.
- Models remain Git/YAML-owned with `STORE_MODEL_IN_DB=False`.
- Windows preflight/install/verify/uninstall plus key provision/revoke, drift-safe rollback, and managed AGENTS policy scripts are present.
- Pre-live evidence collection, routing calibration fixtures, and deterministic escalation fixtures are present.
- Exact-main validation checkpoint `385ee15faf7b32bfa32b488952af40871128cb78` passed:
  - CI run `41326907192`: success; 59 pytest contract tests passed, PowerShell behavior tests passed, upstream source contracts passed.
  - Heavy Docker smoke run `41326907185`: success; pinned LiteLLM source built, Postgres readiness passed, restricted K2 key worked, model-probe mode restarted cleanly, and `/auto_router/test_routing` selected the expected SIMPLE/Luna route.
- Final pre-live security hardening is now encoded in tests/config:
  - direct-client `trusted_proxy_ranges: []`,
  - disabled Admin UI and API documentation surfaces,
  - server-side 30-day virtual-key lifetime cap,
  - Heavy Smoke assertions for the disabled surfaces and overlong-key rejection.

## Current gate

The hardening change must pass normal branch CI, merge to `main`, and then pass Heavy Docker smoke on that merged code-bearing SHA. A later documentation-only evidence commit may record that SHA without invalidating the runtime smoke result.

## Not yet proven

- Real Codex Windows App forwarding the user's ChatGPT OAuth through the local gateway.
- Live restricted LiteLLM virtual-key path from the user's Windows Codex process.
- Live access to all target models on the user's subscription.
- Real routed model decisions in subscription-backed LiteLLM logs.
- Installed Superpowers/native-subagent effective `model` + `reasoning_effort` metadata.
- Deterministic test/build failure → fresh stronger worker escalation on the installed App/plugin versions.

## Next gate

After the hardening merge's exact-main Heavy Docker smoke passes, repository-side pre-install validation is complete. K2 begins on the user's Windows machine in `subscription` mode, not Auto Router mode.
