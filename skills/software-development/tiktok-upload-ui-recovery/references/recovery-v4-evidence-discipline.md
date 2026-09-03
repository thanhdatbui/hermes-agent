# Recovery-v4 evidence discipline

This reference captures a reusable evidence pattern for bounded, user-authorized TikTok upload recovery.

## Gates

- Read the newest report by serial before retrying. Retry only if `post_submission_state=null` and `post_verified=false`.
- Archive only exact `machine_<N>.lock.json` and `serial_<serial>.lock.json` aliases after matching project/status, `owner_active=false`, and a Windows `tasklist /FI "PID eq X" /NH` proof that the PID is dead. Copy first to timestamped backup; include PID proof, release reason, and untouched-foreign-locks evidence.
- Launch one independent background workflow per target with the approved template config and both recovery flags. Never substitute manual ADB, tap/back/reboot, or outside-script coordinate actions.
- Wait for every worker and read its final report. `WORKER_EXIT=0`, a live lock, or a process poll is not completion proof. Success requires `status=SUCCESS`, `post_verified=true`, and accepted/verified post state.

## Log interpretation

Record only observed markers: feed wait timeout; splash recovery #1/#2; ATX-kill (B1); bounded force-stop/relaunch (B2); actual soft reboot (B3); post-boot watcher/proxy readiness; coordinate fallback; and `MANUAL_REVIEW`.

`non_xml_ui_dump` at `CONNECT_DEVICE` or `close_all_apps_start` is a startup prerequisite failure. If the workflow ends there, classify `ladder_not_entered`; recovery flags do not prove B1/B2/B3 ran. Preserve the handoff lock and stop fail-closed.

B3 requires both an actual reboot marker and post-boot watcher/proxy-ready recapture. The allow flag alone is authorization, not evidence.

## Runtime budget

A wait timeout is not a worker result. If the runtime session ends while a worker is alive, report `INCOMPLETE_PENDING_WORKER` with PID/log and do not fabricate a final total. Keep the lock until a final verifier decides its state.
