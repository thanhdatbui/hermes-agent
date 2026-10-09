# Bounded Subagent Handoff

Use this reference when a delegated investigation has an exact file allowlist or a hard tool/iteration budget.

## Required evidence

- List every named path that existed or was missing. Do not substitute similarly named files unless explicitly allowed.
- Cite exact source/test anchors (`path:line`) for each finding.
- Record the focused offline command actually executed and its real result.
- Separate confirmed root cause from an unverified patch hypothesis.
- State which external artifact (workbook, live run, database, device state) was not inspected.
- State that no files were edited or committed when the task is read-only.

## First three passes

1. Verify path existence/size and repository context.
2. Read the exact producer/consumer anchors and trace the data flow.
3. Run one focused offline probe or existing test, or document why no red-capable probe is available.

Avoid recursive whole-drive/repository scans when the user supplied concrete targets. If the call budget is exhausted, return the partial evidence table and blockers; never replace the final handoff with a generic tool-error message or claim that no summary can be produced.

## Stateful bug contract

For cross-session counters, distinguish per-session computation from persisted history. Name the identity key (for example date + cluster + row + machine/account), the ledger read point, the commit/write point, and the idempotency rule. A current-session list or counter is not evidence of historical deduplication.
