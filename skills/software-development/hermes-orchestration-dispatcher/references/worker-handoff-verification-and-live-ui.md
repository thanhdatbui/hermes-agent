# Worker handoff verification and live UI evidence

## Why this exists

A delegation banner or worker summary is not proof that a shared-repository change landed. In one dashboard task, a worker reported completion while the parent workspace still had no feature anchors; a later worker also timed out before producing a verifiable handoff. The coordinator must verify the artifact, not the narrative.

## Required parent verification

1. **Scope/status:** run `git status --short` in the intended repository and confirm every modified path is allowlisted. Do not infer shared state from a child summary.
2. **Diff/artifact:** run `git diff --stat`, then check each requested anchor with an exact, bounded search. For a monolith, require unique anchors before dispatch; after dispatch, verify the new IDs/functions and the surrounding old behavior.
3. **Syntax:** run the language compiler or parser before tests.
4. **Focused regression:** run the named test file or smallest relevant test selection and record the actual exit code/output. A worker's claimed test result is not sufficient.
5. **Runtime proof:** for a local dashboard/service, verify the endpoint status and inspect the served HTML/DOM. If the request changes UI, take a screenshot after navigation and after each state-changing click/type/submit checkpoint; attach the real `MEDIA:` path when reporting to the user.
6. **Restart/cache:** only after code and tests pass, restart the service using its existing launcher if needed, re-check the port, and verify the served version. A browser cache explanation is not a substitute for checking the live response.

## Circuit-breaker handling

- `completed` + `0 files modified`, missing anchors, timeout, or lost child workspace = **structural failure**.
- Do not retry the same open-ended prompt. Narrow to one feature/phase, give exact `old_string -> new_string` anchors, name the focused test, and inject a fail-fast rule for the first three iterations.
- Keep code-surgery separate from long batch/render/download jobs. The latter needs a background launcher and an external monitor, not a large coding worker.
- After two materially failed dispatches, stop and report the blocker or ask for a scope decision; do not silently fall back to unverified direct edits.

## Dashboard-specific lessons

- A chart with Follower, Tim, Following, and Video should use small multiples or normalized/indexed views; a single raw linear Y-axis hides the smaller series.
- When farm actions include cross-follow and cross-like, `Tim/Follower` is only a heuristic, not proof of organic reach. Label it as a candidate signal and combine it with time-series growth, delta patterns, video-level signals, and machine/cluster health before prioritizing a nick.
- A fleet heatmap should summarize machine-level LIVE/DIE/stagnant/growing counts and link each cell back to the filtered account list. It is an operational diagnosis view, not a replacement for account-level history.
- Display machine and Tik slot identifiers on every account row so a suspicious account can be traced to its physical/logical placement without opening another screen.

## Minimal handoff template

```text
Worker result: <claimed status>
Parent verification:
- allowlisted files: <paths + git status>
- anchors/artifacts: <present/missing>
- compile: <command + exit>
- focused test: <command + exit + count>
- live endpoint/UI: <status + screenshot path if UI changed>
Decision: VERIFIED | STRUCTURAL_FAILURE | BLOCKED
```
