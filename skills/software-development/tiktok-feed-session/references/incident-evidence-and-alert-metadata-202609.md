# Incident Evidence and Alert Metadata (2026-09)

## Lessons from recent feed-session incident

- When the user explicitly orders `fix`, `recover`, or `làm cho xong`, do not stop after inspection. Continue: exact evidence → worker patch → focused test → target-scoped canary → closeout.
- Stale test fixtures are valid patch targets when the failure is proven to be fixture/flow drift. Do not treat test edits as forbidden.
- Separate code-surgery from live waiting:
  - code worker patches source/tests offline and never waits on a device lock;
  - live monitor/preemption polls briefly and returns `LOCK_HELD` with owner PID, run ID, heartbeat, and reservation result;
  - long waits belong to a monitored job/runner, not an LLM child blocked for the full timeout.
- Never kill an active pinned lease or overlap a canary with a live fleet run.

## Delegation budget guidance

- Routine code: 25 iterations / 600s.
- Multi-file or multi-repo: 40 iterations / 1200s.
- Live monitor/preemption poll: 10 iterations / 300s.
- Hard policy cap: 50 iterations / 1800s per child; split work instead of exceeding it.
- A timeout with no artifact is transient. Retry with a changed/continuation contract; do not claim success.
- Workers must checkpoint before the deadline with changed files, diff, test state, and next action.

## Farm alert observability contract

Every new alert must preserve these fields end-to-end through batch parsing, result objects, and caption formatting:

`machine`, workbook `row`, `source_row`/`slot`, username/account, serial, artifact path, log path, and correlation/run ID.

Missing values must be `UNKNOWN`. Never fabricate `row=1` or `latest/summary.txt`.

## Evidence from the incident

- Canonical account-switcher recovery needed `ATX_SESSION_UNAVAILABLE` in both transient dump handling and recovery dispatch.
- Account-switcher routing had to preserve the specific manual reason rather than overwrite it with a generic message.
- Focused fixture drift was fixed by supplying the correct repeated XML sequence and a valid profile→switcher transition.
- M7 target reconciliation was proven as slot 4 / physical workbook row 53 / `luongbong055` / serial `9885f63030454d3055`; its active pinned fleet lease must not be killed or bypassed.
