# Claude-locked design → implementation → approval loop

## Session-specific learning

The Operator’s required workflow is not “ask Claude for advice and then improvise.” It is a gated control loop:

1. Dispatch Claude CLI in planner mode to discuss and lock the architecture.
2. Convert the decision into a finite patch contract: exact target files, unique anchors or public APIs, non-goals, file/line budget, and one focused offline test.
3. Implement only that slice through the approved worker gateway. Snapshot target hashes before and after; do not treat an exit code or worker summary as proof of a write.
4. Dispatch Claude reviewer mode against the actual diff, focused test output, contract, and hash evidence.
5. If rejected, classify the finding and issue a *new smaller* contract. Do not replay the same prompt or widen scope. Re-test and re-review until approved or the bounded strike ladder parks the affected lane.

For a mechanical guard system, Claude’s design must specify rule IDs, trust boundaries, closed predicate registries, allow/deny vectors, receipts or hashes binding decisions to the current artifact, and a deterministic `next_action`. A guard denial must lead to `repair`, `retry`, `park_and_release`, or `switch_task`; it must never create a conversational “wait for Operator” state. Park only the affected lane, release its locks, preserve an evidence ticket, and continue independent queue work.

The durable implementation principle is: **prompts specify intent; hooks, wrappers, executors, ACLs, receipts, hashes, ledgers, and tests enforce behavior**. Every new durable rule needs at least one positive vector, one negative vector, and a machine-executable next action.
