# K5 — Failure escalation policy

The target behavior is deterministic escalation without letting a weak model spin indefinitely.

## What Codex hooks can and cannot prove today

Current Codex source exposes lifecycle hooks including `PostToolUse`, `SubagentStop`, and `Stop`. A `PostToolUse` command receives the tool input and `tool_response`, and can feed additional context back to the model.

The current generic `PostToolUse` command schema does **not** provide a stable top-level `success`, `failed`, or shell `exit_code` field that this repository can safely treat as a universal test-result signal. OpenAI/Codex issue #34289 tracks this exact failure-signal gap.

Therefore this lab does not implement a brittle hook that guesses failure by regexing arbitrary Bash output.

## Deterministic source of failure state

For the first production design, the authoritative failure state is the Superpowers task/fix loop:

- rounds 1–3: same worker fixes its own issue;
- rounds 4–5: fresh implementer, at least one model tier stronger;
- after round 5: breaker/controller review instead of unlimited retries.

The exact routing ladder is stored in `configs/routing/escalation-policy.yaml`.

## Handoff rule

When escalation creates a stronger fresh worker, carry:

- current repository state,
- diff,
- failing test/build/lint evidence,
- concise failure summary.

Do not carry a large failed reasoning trajectory merely because it exists. This reduces handoff cost and avoids anchoring the stronger model on the weaker worker's unsuccessful path.

## Live K5 verification

After K2/K4 are proven on Windows:

1. create a deliberately failing isolated test task;
2. verify rounds 1–3 remain on the original implementer;
3. force/observe round 4;
4. verify a **fresh** worker is spawned;
5. inspect rollout metadata for its explicit promoted `model` and `reasoning_effort`;
6. verify the handoff contains test evidence and concise summary;
7. verify round >5 reaches the breaker rather than recursive fan-out.

## Future hook upgrade

If Codex adds a documented, stable failure field to `PostToolUse` or a dedicated tool-failure event, a repo-local hook may translate that event into structured failure evidence. Until that contract exists, hooks are useful for observation/feedback but are not the hard failure detector.

## Pinned evidence

- Codex source snapshot: `67f0994b532b8740f14b5b738af7b7b2a915b1d6`.
- Superpowers source snapshot: `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`.
- Codex issue: #34289, “PostToolUse payload carries no failure signal”.


## Enforcement boundary

The repository now ships a Codex AGENTS policy that mirrors the Superpowers fix loop, but it intentionally does not pretend to be a hard hook-based controller. Codex issue #49736 documents `PreToolUse` not firing for `spawn_agent` in affected interactive Windows sessions, and issue #34289 documents that generic `PostToolUse` lacks a reliable failure discriminator.

Therefore the load-bearing K5 path remains Superpowers' explicit worker dispatch and fix-loop state: rounds 1-3 same implementer, rounds 4-5 fresh stronger worker, then breaker/controller review. A future hard hook/controller may be added only after those upstream contracts are reverified on the installed Codex version.
