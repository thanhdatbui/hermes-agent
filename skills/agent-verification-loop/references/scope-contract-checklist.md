# Scope-contract checkpoint

Use this before implementation, verification, delegation, or a final report.

## Contract

```text
Task (latest user wording):
Goal:
In scope (exact files/routes/components):
Non-goals (must remain untouched):
Acceptance criteria:
Allowed commands/actions:
Stop condition:
```

## Checkpoint questions

- Does the proposed next action directly satisfy an acceptance criterion?
- Is the target inside the explicit allowlist?
- Am I following the latest user message rather than a stale plan, TODO,
  compaction summary, worker handoff, or prior assumption?
- Is this a focused verification required by the contract, or unrelated full-suite
  cleanup?
- Would this action expand from one route/component to a sibling route/system?
- If yes, have I asked for approval instead of proceeding?

## Stop and report

If a new failure, route, file, or test family is outside the allowlist:

1. do not edit it;
2. do not repair its test just to make a broad suite green;
3. classify it as `OUT_OF_SCOPE` or `NEEDS_USER_DECISION`;
4. finish the requested focused work, or ask before expanding.

A worker prompt must include this contract verbatim or an equivalent exact
allowlist/non-goals block. A worker that discovers scope drift returns a handoff
without changing the newly discovered area.

## Done gate

Stop once the focused acceptance criteria pass and the requested artifact is
verified. Do not add adjacent hardening, documentation, audits, or full-suite
reconciliation merely because they are available. Report any broader failures
separately as historical or unrelated evidence.
