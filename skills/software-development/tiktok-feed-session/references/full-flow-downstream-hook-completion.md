# Full-flow completion and downstream hook handling

## Trigger
Use this when a feed-session runner has designed post-feed stages such as follow, upload, sync, or another cross-repo hook.

## Required sequence
1. Treat the feed child result as an intermediate milestone, not the whole job result.
2. Keep the canonical wrapper alive until its terminal result. Do not kill it merely because the feed child reports `success`.
3. Inspect the target-scoped log tail for the downstream stage start and terminal record.
4. Inspect the stage artifact/result file when available, for example `follow_result.json`, hook-specific logs, and the final machine/run manifest.
5. Report stage statuses independently: feed, profile verification, cleanup, follow, upload, and final wrapper.
6. If a hook is still running, report `chưa xong` and continue waiting within its documented bounded timeout. Do not launch a duplicate run.
7. If the hook reaches `MANUAL_REVIEW`, `TIMEOUT`, or script error, preserve the feed success evidence and report the hook blocker separately; do not relabel the feed as failed.
8. Stop a process tree only when the canonical wrapper is terminal, or when the exact hook's own bounded timeout has elapsed and a recorded timeout/failure result exists. Verify target lock/artifact state afterward.

## Evidence pattern
A valid closeout includes:
- feed `final_status` and requested/completed swipes;
- profile/postcondition evidence where configured;
- downstream hook result and artifact path;
- final wrapper status/exit code;
- lock terminal state.

Wrapper output alone is insufficient, and an old feed manifest cannot prove that a later hook completed.
