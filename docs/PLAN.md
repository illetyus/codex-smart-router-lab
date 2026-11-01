# Delivery phases

- K0: repository contract, security gates, rollback documentation, CI.
- K1: source-pinned LiteLLM + local Postgres stack; static/compose validation.
- K2: single-model ChatGPT subscription passthrough on Windows Codex; verify logs show subscription path and no API fallback.
- K3: verify the account can call the target Luna/Terra/Sol/Astra set; enable the catalog-free Auto Router by shadowing the known `gpt-6.1-sol` slug.
- K4: install Superpowers from the official Codex plugin marketplace and verify explicit subagent model + reasoning effort.
- K5: add deterministic test/build/review failure summaries and fresh-worker escalation policy.
- K6: controlled repository pilot; measure selected model, effort, turns, tokens, elapsed time, retries, and test outcome.
- K7: harden update policy, signed-release migration, backup/restore, and repeatability.


### Routing alias ruling

For the first Windows App pilot, use the documented catalog-free pattern: expose the Auto Router under the known `gpt-6.1-sol` slug instead of adding an unknown custom router alias. This removes a separate catalog-generation dependency from the pilot. If the account/model metadata later requires a custom alias, add a generated `model_catalog_json` only after the direct pilot is measured.
