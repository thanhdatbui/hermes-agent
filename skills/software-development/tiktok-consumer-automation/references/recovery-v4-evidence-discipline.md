# Recovery-v4 evidence discipline

Session-derived, sanitized reference for bounded TikTok upload recovery. It records evidence patterns, not machine/account credentials.

## Required evidence order

1. **Fresh-check:** stop if any target has a live batch/worker or an ambiguous owner. Read the newest report by serial. Retry only when `post_submission_state=null` and `post_verified=false`.
2. **Lock archive:** for each named target, inspect exactly `machine_<N>.lock.json` and `serial_<serial>.lock.json`; verify matching fields, expected project/status, `owner_active=false`, and PID dead with `tasklist /FI "PID eq <pid>" /NH`. Copy all exact aliases before removal. Evidence should contain timestamp, backup path, alias list, PID proof, release reason, and an explicit untouched-foreign-locks statement.
3. **Launch:** one background process per target, using the approved template config and both recovery flags. Do not use a shell loop or create per-machine configs. Keep the command/log path in the evidence.
4. **Verify:** wait until every process exits; resolve the final report path from that target's log. Success requires report fields, not `WORKER_EXIT=0`.

## Marker interpretation

- `WAIT_FEED` timeout and `Splash-stuck recovery #1/#2` are observed feed-opening markers.
- `ATX-kill recovery (ladder bước 1)` is B1.
- `Force-stop + relaunch` is B2 only when it is the bounded ladder relaunch, not an earlier splash helper; preserve the exact log wording and count.
- B3 requires an actual soft-reboot marker, followed by post-boot watcher/proxy readiness and recapture. The presence of `--allow-device-reboot-recovery` proves authorization only.
- Coordinate fallback and `MANUAL_REVIEW` must be reported only when the log shows them.
- `non_xml_ui_dump` at `CONNECT_DEVICE`/`close_all_apps_start` is a startup prerequisite failure. If the workflow stops there, classify it as `ladder_not_entered`; do not claim any B1/B2/B3 stage ran.

## Classification examples

- **Target A:** log ends after `close_all_apps_start: failed (ui_dump_error: non_xml_ui_dump)`, report is `MANUAL_REVIEW`, lock retained → `FINAL_BLOCKED`/handoff with ladder not entered.
- **Target B:** log shows feed timeout, splash #1/#2, ATX-kill, bounded relaunch, then account/profile readiness and upload progression → ladder markers are partially exercised; still unresolved until Post verifier and final report complete.
- **Target C:** an explicit foreign registration lock is stale and user-authorized for release → archive only its two aliases and preserve the exact reason in evidence. Do not use that authorization for any other foreign lock.

## Runtime-budget safety

A process poll or wait timeout is not a worker result. If the orchestration session ends while a worker remains alive, report `INCOMPLETE_PENDING_WORKER`, include its PID and log, and do not produce a final success/failure total. Locks remain owned by the workflow until a final verifier proves release is safe.
