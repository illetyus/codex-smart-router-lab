# K4 — Explicit Superpowers worker routes

K4 solves a different problem from the controller Auto Router.

The main Codex/controller request keeps using `gpt-6.1-sol`. In Auto Router mode that public slug is the LiteLLM complexity router, so a normal turn can land on Luna, Terra, GPT-6.1 Sol, or Astra.

Superpowers and Codex native subagents also need to be able to request a model **explicitly** through `spawn_agent(model=..., reasoning_effort=...)`. For that reason the proxy exposes these additional model names directly:

| Worker role | Public model name | ChatGPT upstream |
| --- | --- | --- |
| Mechanical / bounded | `gpt-6-luna` | `chatgpt/gpt-6-luna` |
| Integration / debugging | `gpt-6.1-terra` | `chatgpt/gpt-6.1-terra` |
| Direct Sol worker | `gpt-6-sol` | `chatgpt/gpt-6-sol` |
| Architecture / critical review | `gpt-6-astra` | `chatgpt/gpt-6-astra` |

`gpt-6.1-sol` is intentionally **not** also exposed as a direct worker route because that exact public slug is reserved for the Auto Router. The Auto Router can still use GPT-6.1 Sol through its private `sol-upstream` tier target.

## Virtual-key scope for K4

After K2 has passed, create/replace the K4 key with access to:

- `gpt-6.1-sol` — controller-facing Auto Router
- `gpt-6-luna` — explicit Luna worker
- `gpt-6.1-terra` — explicit Terra worker
- `gpt-6-sol` — explicit direct Sol worker
- `gpt-6-astra` — explicit Astra worker
- `codex-*` — Codex review/approval traffic

Do not grant `*-upstream` aliases to the developer key. They are implementation details of the router, not user-facing models.

No `gpt-*` catch-all route is used. The public model surface is explicit and testable.

## Effective-model verification

After Superpowers is installed from the official Codex marketplace, run four isolated subagent probes and inspect rollout/subagent metadata:

1. mechanical task → `model=gpt-6-luna`, low/medium effort;
2. integration task → `model=gpt-6.1-terra`, medium/high effort;
3. difficult direct worker → `model=gpt-6-sol`, high effort;
4. architecture/final review → `model=gpt-6-astra`, high/xhigh effort.

For each probe, verify both `model` and `reasoning_effort`; an omitted model inherits the controller/session model and fails the K4 contract.

## Why no wildcard

LiteLLM supports wildcard model deployments, but this lab does not need one. Explicit routes avoid making exact-vs-wildcard resolution a load-bearing part of the installation and ensure the virtual key exposes only the worker models we intentionally tested.

## Source contracts

- Codex source snapshot: `67f0994b532b8740f14b5b738af7b7b2a915b1d6` — MultiAgentV2 `spawn_agent` accepts explicit `model` and `reasoning_effort`.
- Superpowers source snapshot: `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b` — explicitly requires a model on dispatch and raises capability on fix-loop rounds 4–5.
