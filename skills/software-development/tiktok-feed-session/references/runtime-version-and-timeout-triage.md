# Runtime version and timeout triage

## Purpose

Use this reference when a farm alert says a machine is still running old behavior or still timing out after a code/config change.

## Evidence order

1. **Identify the exact run** from the alert timestamp and machine number. Resolve the target-scoped artifact root; do not rely on a Telegram screenshot alone.
2. **Read the machine `log.jsonl`** around startup, the runtime configuration event, the last completed action, and the terminal event. Look for explicit fields such as:
   - `requested_min_total_videos`
   - `requested_max_total_videos`
   - `selected_total_videos`
   - timeout/deadline values
   - `artifact_path`, `xml_path`, and `screenshot_path`
3. **Inspect the live process command line** when the process is still running. Record executable/interpreter, repo path, launcher arguments, artifact-root argument, and process creation time.
4. **Compare source chronology** only after the live/runtime evidence is collected. A current worktree constant or commit proves source state, not what an already-running process loaded.
5. **Reconcile timestamps:** process start ≤ target log startup ≤ configuration event ≤ last observed action. If the log and process do not align, mark provenance `UNPROVEN`.

## Timeout interpretation

A lower work target does not imply a lower wall-clock cost. The deadline may include:

- device preparation and TikTok launch;
- account/profile navigation and verification;
- screenshot and XML capture;
- keyboard detection/cleanup;
- popup detection, bounded action, and post-action recapture;
- watch delay and swipe execution;
- final profile/navigation verification and cleanup.

Build a timeline from actual JSONL timestamps. Do not attribute a timeout to the video count merely because the alert mentions a feed session. If the exact target log ends before the reported timeout, write `timeout not yet confirmed`; report the last observed step instead of inventing a terminal cause.

## Reporting template

- `Mục đích`
- `Máy/run`
- `Runtime version`: confirmed / unproven
- `Target`: requested and selected values from log
- `Timeout`: confirmed / not yet confirmed
- `Confirmed`: exact evidence
- `Excluded`: hypotheses contradicted by evidence
- `Unproven/blocker`: missing artifact, timestamp mismatch, or incomplete run

Keep the final report short. Do not report a code fix, deploy, or live repair unless a separate action actually performed and verified it.
