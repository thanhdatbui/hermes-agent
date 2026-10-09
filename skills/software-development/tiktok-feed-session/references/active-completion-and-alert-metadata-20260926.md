# Active completion and alert metadata contract

## Why this exists
The coordinator repeatedly stopped after an inspect, a worker timeout, a stale fixture, or an ordinary cross-repo scope rule even though offline patch/test work remained. This is a workflow failure, not a valid blocker.

## Required ladder after an explicit user fix command
1. Inspect the named machine with `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. Read the exact fresh log/artifact and identify the source flow.
3. Patch the smallest exact source contract; shared/canonical edits are allowed when the user explicitly authorizes them.
4. Repair stale mocks/fixtures when the failure proves the fixture no longer matches the flow; do not alter production merely to appease a stale fixture.
5. Run one focused offline test/compile.
6. Run the official target-scoped canary, then report `DONE`, `PARTIAL`, or `BLOCKED` with command, exit code, and artifact evidence.

Do not stop because of dirty files outside the allowlist, a stale fixture, a first worker timeout, or missing live evidence when offline work is still possible. Retry transient worker failures; narrow ambiguous patches to a unique anchor. `BLOCKED` requires a real permission/credential/mapping/irreversible-action blocker or a failed canary with concrete evidence.

## Farm Alert metadata invariant
Metadata must survive the full path:
`machine → row/source_row/slot → account/username → serial → artifact/log → alert formatter`.

- Missing values are `UNKNOWN`/`None`; never fabricate `row=1` or `latest/summary.txt`.
- New alerts must include Machine, Row, Source row/Slot, Nick/account, Serial, Artifact, Log, and correlation/run ID when available.
- For old alerts missing username/row, reconcile targeted artifacts, DB, workbook, manifest, machine, and timestamp before asking the user to choose among rows.
- If a named machine has multiple workbook rows and no timestamp/account correlation, report the exact unresolved mapping evidence; never guess a farm asset.

## Style correction
The user prefers direct Vietnamese status: do the next action instead of explaining why work is stopping. Report only verified facts, but do not turn uncertainty in one gate into refusal to complete independent code/test gates.
