# Live single-machine recovery: stop conditions and preservation

Use this reference for an explicitly authorized single-machine retry after a prior `MANUAL_REVIEW`/handoff.

## Safe sequence

1. Read the prior report/checkpoint and classify the exact failure signature. Check `post_submission_state` before any retry: `ACCEPTED` means the post was submitted and must not be retried; `None` is retryable only when the new handler and attempt budget permit it.
2. Verify the target lock's recorded PID is dead, no replacement `tiktok_workflow` worker is running for the same machine, and no foreign/active serial lock exists. Never archive a live or foreign lock.
3. Archive both same-target aliases (`machine_<N>.lock.json` and `serial_<serial>.lock.json`) into a timestamped runtime directory. Copy both files first, write redacted evidence containing the target, PID-dead proof, scope, and reason, then move the originals. Do not delete them.
4. Run the bounded recovery ladder exactly once per signature: ATX/UIAutomator recovery, then recapture. If the feed is already proven by UI dump plus foreground/activity evidence, stop the ladder; do not add a force-stop or reboot merely because a stale `SplashActivity` string remains in history.
5. Run one direct worker only, with the repository's required `PYTHONPATH`, config, machine number, and real-execution confirmation. Treat worker exit/status as provisional until the report/checkpoint verifier is read.
6. Declare success only when the report/checkpoint proves `status=SUCCESS`, `post_verified=true`, and the final recovery state is `VERIFIED_SUCCESS` (or an explicitly handled `ACCEPTED` path that finalizes safely). Otherwise preserve the handoff lock, checkpoint, report, and any reserved fingerprint for recovery review.

## Important outcome rule

A recovery can succeed at `OPEN_TIKTOK` while the upload retry fails later with a different signature. For example, feed recovery may pass, but `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` can still end in `MANUAL_REVIEW`. Do not reinterpret that as an upload success, do not run a third attempt, and do not clean a reserved media fingerprint or release the retained handoff lock outside the workflow's verified-success path.

## Evidence checklist

Record/report these paths and fields:

- `report.json`: exact `status`, `reason`, `post_submission_state`, `post_verified`, and `post_tap_attempted`.
- `checkpoint.json`: `last_state`, recovery attempt counters, `media_fingerprint_status`, and the handler's before/after artifacts.
- `execution.log`: transition through the recovery state and the final handler error.
- lock archive `evidence.json`, plus the current lock state after a blocked run.

A feed probe can use UI dump markers and activity state when screenshot vision is unavailable; if an auxiliary vision service fails authentication, record that limitation and do not claim visual confirmation from it. Runtime/generated artifacts may be preserved; do not edit source, docs, workbook, credentials, or unrelated foreign locks as part of this recovery.

## Observed ladder behaviors on the 2026-08-10 recovery code (6ad3cfd), machines 5/27/35/70

- New splash-stuck recovery logs as `[WAIT_FEED] Splash-stuck recovery #N: đã đóng Recent + relaunch TikTok; quay lại chờ feed (không tính ladder B2)` — budget 2, uses `monkey -p com.ss.android.ugc.trill -c LAUNCHER 1`, does NOT consume the B2 relaunch budget.
- ATX-kill logs as `[WAIT_FEED] uiautomator dump fail liên tiếp; đã ATX-kill recovery (ladder bước 1)`.
- B2 logs as `Force-stop + relaunch 2/2` inside OPEN_TIKTOK, or `[UI_FAILURE_LADDER_B2] force_stop_app/.../verify_app_focus: success` in DISMISS_POPUPS.
- B3 soft reboot: attempted when the ladder is exhausted; if the proxy-handoff owner pause is unsupported it fails immediately with checkpoint `soft_reboot_recovery.state=RECOVERY_FAILED`, `reason=DEVICE_LOCK_PROXY_HANDOFF_UNSUPPORTED`, `proxy_handoff_state=OWNER_PAUSE_FAILED` — **the device is NOT rebooted**. Do not read this as "reboot tried and didn't help".
- Coordinate fallback runs only after the ladder is exhausted (`Ladder cạn (relaunch x2 + soft-reboot đã thử)`); a visual gate with screencap `white=0.000 dark=1.000` (black screen) → `Coordinate fallback: không có evidence target rõ ràng trong ảnh -> FINAL_BLOCKED (không tap mù)` → MANUAL_REVIEW with the handoff lock retained.
- Worker exit codes are still provisional: m27 exited 0 with report `SUCCESS` + `post_submission_state=ACCEPTED` + `post_verified=true` (workbook updated to Video Đã Đăng = 8); m5/m35/m70 exited 2 with `MANUAL_REVIEW`, `post_submission_state=None`, `post_verified=false`, fingerprints not reserved.
- Handoff locks retained after failure carry the NEW worker PID (e.g. machine_5 pid 58116 at 13:04 UTC) but `owner_active=false`; verify dead via `wmic /format:list` (empty output) before any future reclaim.
