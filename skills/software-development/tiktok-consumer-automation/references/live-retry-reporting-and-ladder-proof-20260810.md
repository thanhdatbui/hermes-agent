# Live retry reporting and ladder proof (2026-08-10)

## Purpose

Sanitized operator note from a three-machine direct retry. It captures how to report what the worker actually did, without treating flags or exit codes as evidence.

## Guard sequence

1. Fresh-check newest `report.json` per target. Retry only `post_submission_state == null` and `post_verified == false`.
2. Scan actual `python.exe`/`pythonw.exe` metadata for `-m tiktok_workflow --machine N`; ignore the coordinator shell's command line.
3. For stale takeover, re-read exactly `machine_N.lock.json` and `serial_<serial>.lock.json`; require matching identity, `project=tiktok-upload`, `status=handoff`, `owner_active=false`, and two independent Windows PID checks showing no process.
4. Copy exactly those aliases to a timestamped archive/evidence directory, then move the originals. Leave foreign consumer locks untouched.
5. Launch each target as its own background process with the template config and both recovery flags. Require the log line `effective config rebound to this row`.
6. Wait for every worker. Resolve report paths from each log. Success requires `status=SUCCESS`, `post_verified=true`, and `post_submission_state=ACCEPTED` (or a documented equivalent). Verify successful aliases are released and blocked/manual targets retain inactive handoff locks.

## Ladder classification

| Evidence in log | Classification |
|---|---|
| `non_xml_ui_dump` at `CONNECT_DEVICE/close_all_apps_start`, no recovery markers | Startup failure; `ladder_not_entered` |
| `=== ... ATX ... ===` or equivalent explicit kill marker | B1 observed |
| Explicit recovery force-stop/relaunch marker | B2 observed |
| Ordinary `[OPEN_TIKTOK] Force-stop + relaunch 1/2` | Normal startup relaunch; do not count as B2 by itself |
| Actual soft-reboot marker plus watcher/proxy-ready post-boot evidence | B3 observed |
| Screenshot/coordinate fallback during normal `VIDEO_PICK` | Normal flow fallback; do not count as post-ladder coordinate fallback |
| `MANUAL_REVIEW` report with inactive handoff lock | Fail-closed terminal outcome |

A recovery flag authorizes stages; it never proves that stages executed. Likewise, phrases such as “ladder exhausted” are not proof without stage markers.

## Timeout reporting

If the repeated signature is `non_xml_ui_dump`, report whether the log explicitly contains `timeout=60` (or an equivalent bounded-time marker). If it does not, say the signature recurred but the runtime's 60-second wait is not observable; do not infer it from source intent or CLI flags.

## Sanitized observed pattern

- Target A: stopped at startup `non_xml_ui_dump`; no ATX, B2, B3, watcher, or coordinate-ladder markers; report `MANUAL_REVIEW`, retain handoff aliases.
- Target B: reached Post and profile tile increment; report `SUCCESS` only after `ACCEPTED` + `post_verified=true`; release aliases.
- Target C: startup succeeded, but picker verification failed; an ordinary create-button fallback occurred, not a full recovery ladder; report `MANUAL_REVIEW`, retain handoff aliases.

Never perform manual ADB taps, app restarts, device restarts, or outside-script coordinate recovery to manufacture missing ladder evidence. If the consumer exits before the required ladder, preserve artifacts and stop fail-closed unless the code path is fixed and separately authorized.