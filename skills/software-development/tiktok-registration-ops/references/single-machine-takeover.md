# Single-machine takeover during a live farm session

## Trigger
Use when the user explicitly requests taking over one machine that is currently part of a multi-machine farm session.

## Required behavior
1. Resolve the exact machine and serial from the canonical mapping.
2. Inspect both machine and serial lock files, including owner PID, host, project, run ID, and active status.
3. Do **not** stop the shared PID/cohort or the whole farm session. Other machines must continue.
4. Use the official per-machine exclusion/withdrawal mechanism so only the requested machine is removed from the active cohort. Never delete or overwrite an active lock blindly.
5. Wait for that machine's lease/lock to be safely released, then acquire both aliases for the takeover worker.
6. Run only the official registration runner for the selected machine. Keep its lock for the complete flow; on failure retain `FAILED_LOCKED`/handoff.
7. Verify final status with result/artifact evidence and confirm other-machine process continuity.

## Fail-closed conditions
Use `FINAL_BLOCKED` if there is no safe per-machine exclusion handler, the target mapping is unproven, ownership is inconsistent, or the active owner cannot release only the target machine. Do not kill the shared process, reclaim an active lock, or proceed with a parallel run.

## Reporting
For the user's preferred concise format, report only:
- `Success: M<id>`; or
- `Fail: M<id> — <error signature>`;
then one blocker/artifact line when relevant. Do not narrate every intermediate machine or print credentials.

## Related overlap
This procedure complements, rather than replaces, the broader farm lock and cron-operation skills; keep shared-session safety in the umbrella skill and use this reference for the single-machine takeover pattern.
