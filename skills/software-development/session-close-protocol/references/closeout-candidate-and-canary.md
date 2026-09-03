# Gate 0 closeout evidence notes

## Dirty worktree without scope drift

The repository bootstrap gate may reject a working tree even when every dirty path is an approved in-scope source/test file. Do not reset, stash, clean, or commit the user's working tree merely to satisfy that gate. First snapshot the exact allowlist and preserve the main worktree. If Gate 0 must run against a clean candidate, materialize a temporary candidate from the same `HEAD`, apply only the allowlisted diff, and verify the candidate's status/path set before running live code. A linked Git worktree may be rejected by simple bootstrap scripts because `.git` is a file; when that happens, use a temporary normal clone instead. Any candidate-only checkpoint commit is verification scaffolding, not permission to push.

## Live canary target resolution

For a farm fix, identify the failing target from fresh runtime evidence, not from a screenshot alone. Resolve and record both `machine` and `row` from the actual runtime artifact path/manifest, then run the canonical canary with that exact pair. If the target row cannot be proven, stop before live execution. If the canary returns `manual-needed`, `needs-user-decision`, or a non-empty target `stop_reason`, preserve the artifact evidence and stop before review/commit/push; never unlock, kill, reboot, or force takeover to manufacture a pass.

## Atomic once-per-session alert dedupe

When a producer can be called by both a worker failure path and a watchdog/retry path, an in-memory `reported` set is insufficient across process retries. Guard the side effect at both producer call sites with a persistent, atomic claim keyed by `logical day + session window + machine`. Store the claim above per-run directories so independent cron relaunches share it. Use exclusive file creation (`O_CREAT|O_EXCL`) and fail closed on claim-store errors; test same machine/same session, different machine, different session, and separate run directories.
