# Evidence directory

This directory is intentionally empty in source control except for this guide. Live validation writes local evidence files here. Do not commit secrets, OAuth headers, cookies, or virtual-key values.

Expected live artifacts:

- `k2-passthrough.json`
- `supported-model-effort.json`
- `routing-calibration.json`
- `subagent-evidence.json`
- `escalation-evidence.json`

The rollout collector records Codex-local session metadata. LiteLLM logs remain authoritative for the physical model selected by Auto Router.
