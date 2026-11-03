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
- Final pre-live security hardening is encoded and tested:
  - direct-client `trusted_proxy_ranges: []`,
  - Admin UI authentication disabled for the pinned LiteLLM runtime,
  - Swagger/ReDoc/OpenAPI surfaces disabled,
  - server-side 30-day virtual-key lifetime cap,
  - no SSO provider credentials passed into the container,
  - Heavy Smoke assertions for the management boundary and overlong-key rejection.
- Final hardened code-bearing checkpoint `0af84ab3b2a32af43a2d46afe2243259cffd1625` passed:
  - CI run `41539957203`: success.
  - Heavy Docker smoke run `41539957189`: success.
  - The smoke built the pinned LiteLLM source, connected Postgres, verified liveness/readiness, proved the restricted K2 key and duration cap, exercised the pinned Admin UI disable boundary, restarted cleanly in model-probe mode, restarted in Auto Router mode, and completed the real-proxy routing dry-run.

## Current gate

Repository-side pre-install validation is complete.

The next evidence boundary is K2 on the user's Windows machine in `subscription` mode. Documentation-only commits made after the code-bearing checkpoint above do not change the runtime artifact that passed Heavy Docker Smoke.

## Not yet proven

- Real Codex Windows App forwarding the user's ChatGPT OAuth through the local gateway.
- Live restricted LiteLLM virtual-key path from the user's Windows Codex process.
- Live access to all target models on the user's subscription.
- Real routed model decisions in subscription-backed LiteLLM logs.
- Installed Superpowers/native-subagent effective `model` + `reasoning_effort` metadata.
- Deterministic test/build failure → fresh stronger worker escalation on the installed App/plugin versions.

## Next gate

Run K2 on Windows: preflight, subscription-mode gateway, restricted key, Codex provider configuration, full Desktop restart, a brand-new task, the exact Hello probe, LiteLLM log correlation, sanitized evidence capture, and rollback rehearsal.
