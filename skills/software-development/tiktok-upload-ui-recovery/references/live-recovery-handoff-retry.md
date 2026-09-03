# Live single-machine recovery: stale handoff to bounded retry

Session-derived checklist for an explicitly authorized one-machine TikTok upload recovery. Keep this reference generic; replace `<N>` and `<serial>` only after binding them from the two lock aliases.

## Evidence-first preflight

1. Read the prior `report.json` and worker log. Classify the exact failure signature and inspect `post_submission_state` before touching the device.
   - `ACCEPTED` + `post_verified=false` means the submission may already be live: do not retry; finalize through the accepted-publication procedure.
   - `null` + `post_verified=false` means the worker failed before submission and can be retryable only if handler/attempt budget remains.
2. Bind `machine_<N>.lock.json` and `serial_<serial>.lock.json`. Require matching project, machine, serial, and `lock_id`; verify `owner_active=false`; prove the recorded PID is absent using a command-line-aware process query; separately search for a replacement worker for the same machine/config.
3. If stale and owned by this consumer, move both aliases into one timestamped backup directory and write redacted JSON evidence. Never archive foreign, watcher-owned, active, or unverifiable locks.
4. Before each recovery action, save a timestamped screenshot, UI-dump stdout/stderr, and probe metadata. Do not use a screenshot as the sole success verifier.

## Bounded ladder

Use one tier per failure signature, in order. Recapture and verify after each tier; stop if the feed is valid.

1. ATX/uiautomator cleanup.
2. Exactly one force-stop plus:
   `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1`
3. Exactly one soft reboot, only when the operator authorized it and all preconditions are met.
4. After reboot, wait for `sys.boot_completed=1`, a changed readiness `boot_id`, `proxy_ready`, `tun0` with an `inet` address, and a live ViChanger PID. Then launch TikTok once with `monkey` and recapture.
5. If the consumer has an implemented evidence-gated coordinate fallback for the current state, it may run only through that handler. Never perform an ad-hoc coordinate action outside the state machine.

The Samsung `sec_debug/recovery_cause` warning can be emitted even when the reboot succeeds. Treat it as informational only after the post-boot gates pass.

## Worker retry and terminal boundary

Run one direct worker in its own bounded process with a dedicated log. Do not put multiple workers in one shell or use a loop that can orphan children and leave stale locks.

The worker must be judged by its final report/checkpoint:

- Success requires `SUCCESS`/`VERIFIED_SUCCESS` and `post_verified=true`, or the explicitly handled accepted-publication path.
- If the worker confirms the feed visually but later fails in `DISMISS_POPUPS` with `UI_DUMP_FAILED` / `uiautomator_idle_state_error`, and the report has `post_submission_state=null` and `post_verified=false`, no upload occurred.
- A later read-only UI dump that recovers does not rewind the attempt budget or authorize another retry. Preserve the report, log, capture artifacts, and handoff lock; escalate instead of creating a third attempt for the same signature.

## Evidence bundle

Keep, at minimum:

- stale-lock backup and ownership evidence (when reclaim was needed);
- pre/post artifacts for each ladder tier;
- direct worker log and final `report.json`;
- core UI-capture artifact referenced by the report;
- final lock state and a target-worker process scan.

Do not update workbook, finalize media, clean up upload state, or release a failure handoff as success without verified publication.
