# Status

Last updated: 2026-11-01

## Completed

- Public repository created: `illetyus/codex-smart-router-lab`.
- LiteLLM source pinned to verified commit `4bdeb1378bb19a453cd3c49d383ebe76f057d2c6` (version 1.109.0).
- ChatGPT subscription baseline config includes direct `gpt-6.1-sol`, explicit `gpt-image-2`, and `codex-*` review/approval passthrough.
- Catalog-free Auto Router uses internal Luna/Terra/GPT-6.1-Sol/Astra tier aliases.
- Explicit Superpowers worker routes are exposed under known Codex slugs: `gpt-6-luna`, `gpt-6.1-terra`, `gpt-6-sol`, and `gpt-6-astra`.
- No OpenAI API key or paid API fallback is present.
- Gateway is localhost-only; Postgres has no host-published port and its image is pinned by digest.
- GitHub Actions and upstream orchestration source contracts are pinned to immutable revisions.
- Windows preflight/install/verify/uninstall plus key provision/revoke, drift-safe rollback, and managed AGENTS policy scripts added.
- Normal GitHub Actions CI is green on current main.
- K4 direct-worker routing was implemented with a RED→GREEN branch test and merged through PR #1.
- First heavy Docker smoke (initial published snapshot) succeeded:
  - pinned LiteLLM source build,
  - Compose/Postgres startup,
  - subscription baseline health,
  - Auto Router restart and health,
  - cleanup.

## In progress

- Final heavy Docker smoke on the current hardened main. This run additionally covers:
  - current `codex-*` passthrough config,
  - direct Superpowers worker routes,
  - pinned Postgres digest,
  - real LiteLLM `/auto_router/test_routing` dry-run against the committed router config.

## Not yet proven

- Real Codex Windows App forwarding the user's ChatGPT OAuth through the local gateway.
- Live restricted LiteLLM virtual-key path.
- Live access to all target models on the user's subscription.
- Real routed model decisions in subscription-backed LiteLLM logs.
- Installed Superpowers/native-subagent effective `model` + `reasoning_effort` metadata.
- Deterministic test/build failure → fresh stronger worker escalation.

## Next gate

If the final heavy smoke is green, repository-side pre-install validation is complete. K2 then begins on the user's Windows machine in `subscription` mode, not Auto Router mode.

## 2026-11-01 continuation verification

- Rechecked public main branch, workflow YAML and pinned LiteLLM source.
- The heavy Docker smoke workflow is **not verified as passing** by this checkpoint. It requires a GitHub Actions workflow run with recorded conclusion, not merely the presence of YAML.
- K2 live ChatGPT OAuth and Windows Codex App verification remain blocked until the heavy smoke evidence and local user-side probe are available.
- Do not enable Auto Router or install into Codex based on static tests alone.
- Next: dispatch `.github/workflows/heavy-smoke.yml` using GitHub Actions, inspect build and health logs, fix any failure in a branch, merge only after CI passes.


## Pre-connection audit hardening

The audit branch additionally closes the incorrect `/key/info` assumption, explicit image-tool routing, runtime key scoping, model+effort tier configuration, managed Superpowers/Codex policy loading, Windows secret ACLs, 30-day key expiry and revocation, config/dotenv drift preservation, readiness checks, placeholder-secret rejection, and config-owned model management (`STORE_MODEL_IN_DB=False`).

The remaining pre-live gate is objective: merge only after branch CI is green, then obtain a successful Heavy Docker smoke on that exact main commit. Live K2 remains blocked until that result exists.
