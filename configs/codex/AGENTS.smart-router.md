# Codex Smart Router Policy

This managed policy is installed only after K2/K3 have passed. It governs orchestration; it does not replace the LiteLLM gateway.

## Controller
- Keep the main controller on the public `gpt-6.1-sol` model name. In router mode that name is the local LiteLLM Auto Router.
- Never request the private `*-upstream` aliases directly.

## Subagent dispatch
For implementation plans with separable tasks, use Superpowers `subagent-driven-development`; its implementer/reviewer/fix loop is the authoritative failure-escalation path. When using Superpowers or native `spawn_agent`, always provide both `model` and `reasoning_effort`. An omitted model inherits the parent and violates this policy.

- Mechanical, bounded, repetitive work: `model=gpt-6-luna`, `reasoning_effort=medium`.
- Integration and ordinary debugging: `model=gpt-6.1-terra`, `reasoning_effort=medium`.
- Difficult debugging or cross-module implementation: `model=gpt-6-sol`, `reasoning_effort=high`.
- Architecture, final critical review, or a promoted fix-loop worker: `model=gpt-6-astra`, `reasoning_effort=high`.

The live K3/K4 model probe is authoritative. If the account does not support one of these model/effort pairs, do not silently use a paid API fallback; lower the policy to the strongest verified subscription pair.

## Fix loop
- Rounds 1-3: keep the same implementer while the failure is genuinely progressing.
- Rounds 4-5: dispatch a fresh worker at least one tier stronger than the worker that got stuck.
- After round 5: stop recursive retries and return to controller review.
- Handoff only current repository state, diff, failing test/build/lint evidence, and a concise failure summary. Do not hand off verbose hidden reasoning trajectories.

## Verification
Before calling a task complete, run the relevant deterministic tests/build/lint and report the observed result. Do not infer success from edits alone.

## Current enforcement limits
This file is an instruction-level governance layer, not a security boundary. Do not rely on a `PreToolUse` hook to rewrite or deny `spawn_agent`: OpenAI Codex issue #49736 documents interactive sessions where that hook does not fire for subagent spawn. Do not use generic `PostToolUse` as a hard failure detector either; issue #34289 documents that it lacks a stable exit-code/failure discriminator. Superpowers' explicit dispatch and fix-loop policy remain the load-bearing orchestration path until those contracts are fixed and reverified.
