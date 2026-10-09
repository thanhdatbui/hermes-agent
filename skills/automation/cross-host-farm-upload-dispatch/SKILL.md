---
name: cross-host-farm-upload-dispatch
description: "Use when one controller orchestrates remote farm media."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [phone-farm, cross-host, remote-upload, ssh, storage-ownership, canary]
    related_skills: [tiktok-feed-session, verification-evidence, concurrent-workspace-safety]
---

# Cross-host Farm Upload Dispatch

## Trigger

Use when a controller machine runs the feed/upload runner for devices whose video library, workflow runtime, or ADB server belongs to a remote farm host. The canonical Taadaa case is Kibe controlling Admin machines 201–280 on `admin-farm`.

## Core model

The controller is an orchestrator, not the owner of remote filesystem state. A path such as `D:\\TIKTOK-videonuoinick-admin` is meaningful on Admin-PC, not on Kibe. A controller-local `Path.is_file()` check against that path can create a false `video_not_rendered` result even when the remote render pool is healthy.

## Procedure

1. **Inspect one affected device first.** For an alert `[MÁY N]`, run the mandated bounded extraction `python D:/Taadaa/tools/inspect_machine.py N`. Do not use ADB input taps as a workaround and do not scan the disk broadly.
2. **Prove ownership and availability on the owner host.** Use a bounded SSH/preflight check against `admin-farm` and the expected exact video path. Keep Kibe's local Farm Kibe path separate from Admin's remote path. Do not introduce SMB mounts, copied media, or guessed local mirrors.
3. **Patch at the Gate 5 / dispatch boundary.** For Kibe machines 1–80, preserve the local existence check and local workflow. For Admin machines >=200, skip controller-local media inspection and dispatch the workflow through `ssh admin-farm`.
4. **Use the owner-host runtime and paths.** The Admin command must execute with remote cwd `D:/Taadaa/Tiktok-video`, runtime `D:/Taadaa/python-envs/automation/Scripts/python.exe`, `scripts.tiktok_workflow`, `D:/Taadaa/Tiktok-video/config-admin.yaml`, the matching remote Admin Tik workbook, exact device serial, exact next video number, and source root `D:/TIKTOK-videonuoinick-admin`. Do not pass Kibe's `ADB_SERVER_SOCKET` into the remote subprocess.
   - **Idempotency & Safe Dispatch Contract (Claude CLI Architecture):** Use a single SSH command with `-o BatchMode=yes -o ConnectTimeout=10 -o ServerAliveInterval=15` to avoid SSH session hangs. Ensure the remote runner checks `.posted` file markers adjacent to the video file on Admin-PC to prevent race conditions or double-posting across network hiccups. Enforce that the remote process outputs a single strict JSON line at stdout tail, which Kibe captures and appends into `upload_result.json`.
5. **Preserve fail-closed verification.** Keep existing report/ledger validation. A zero exit code is not success by itself: require existing success markers and matching device/video/account evidence. Remote timeout, missing marker, report veto, or ledger failure remains a failed result.
6. **Verify narrowly before live execution.** Run `py_compile` for the changed production file and the smallest focused mocked upload-hook test. Preserve dirty unrelated worktree changes and avoid line-ending normalization. Add a mocked assertion for Admin command construction if the test surface allows it.
7. **Run one real canary only after offline proof.** Use a single Admin device such as M201.
   - **Device wake invariant:** If device is sleeping/dozing (`mWakefulness=Dozing` or screen off), NEVER refuse canary. Wake via `adb shell svc power wakeup` or `input keyevent KEYCODE_WAKEUP`, verify `mWakefulness=Awake`, then capture the pre-action screenshot.
   - **Full remote artifact readback:** Do not verify by exit code alone. From `admin-farm` (`D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`), read `report.json` (`status: SUCCESS`, `post_verified: true`, `post_submission_state: ACCEPTED`), inspect `execution.log` (profile video tiles incremented), and scp the visual artifacts (`post-published-surface.png` or `profile-grid-verify_post-*.png`) to local cache to deliver as `MEDIA:<path>`.
   - **Tracking reconciliation:** Readback and synchronize the incremented video count in `D:/OneDrive/TaadaaData/admin/Tik{slot}.xlsx` and `taikhoan_run_safe.xlsx`.

## Common pitfalls

- **False shortage vs True remote shortage:** Watchdog sees `status=skipped, reason=video_not_rendered`. First verify whether the controller inspected the wrong host (false shortage) OR if remote storage has an actual deficit (true shortage). For true shortage:
  - Inspect remote `state.db` (`video_count` per folder) and check if the remote downloader crashed (e.g., SQLite WAL `disk I/O error` under high concurrency) or if remote cron watchdogs are paused.
  - **Slot Cross-Mapping Invariant:** Tik slots 1..8 cross-map `Folder Video` from `video gốc` via `Tik{slot}.xlsx` (e.g., Tik6 maps `video gốc` 401..480 to `Folder Video` 6, 14, 22...). Never run ad-hoc render scripts assuming `output_dir = render_root / d.name` (1:1), which dumps clips into wrong slots/niches and leaves required upload folders empty. Always use canonical workbook-driven render scripts (`admin_render_chain.py` / `run_tik*_random_render.ps1`).
- **Reboot Survival & Lifecycle Discipline:** Ensure both Kibe and Admin hosts maintain dual-tier reboot recovery (Windows Startup VBS + Hermes Cron Watchdog) with `msvcrt` single-instance locks. Workers must self-terminate upon 100% completion (0 tasks pending), while watchdogs run in Smart Idle mode (instant 0.05s check with 0% CPU consumption) to automatically resume whenever future shortages occur. See `references/cross-host-admin-upload.md` sections 6 & 7.
- **Remote command drift:** Hardcoding a local config, workbook, runtime, or source root silently routes the job back to Kibe. Assert each remote argument in a mocked test.
- **Credential/env leakage:** Never include secrets in logs or send Kibe's ADB socket environment to the remote workflow.
- **Overclaiming canary:** `post_verified=true` and a remote report are stronger evidence than process exit code; a teardown screenshot at Launcher is not post-publication proof.
- **Dirty worktree damage:** Do not reset, stash-drop, normalize, or overwrite unrelated existing hunks while applying the focused remote branch.
- **Subagent self-report discrepancy:** Child agents running via `delegate_task` may report successful patching even if their workspace was discarded upon hitting the iteration limit. Coordinator must verify host `git diff` independently before canary or triage.

## Cross-host downloader and proxy-pool integrity

When a controller starts or supervises a remote downloader, treat the launcher command as the source of truth—not the intended configuration. Read back the exact live parent and child command lines on the owner host before claiming proxy coverage. A launcher hardcoded to a direct-only pool can silently exclude MikroTik entries even when the canonical downloader supports proxy rotation.

Use a deterministic pool resolver: prefer the combined pool (MikroTik + direct/Mobi) when present, otherwise fall back to the legacy direct pool. Verify the combined pool exists on both hosts, compare a redacted SHA-256/hash and entry counts, then verify the live child command uses the combined path. Do not kill a running downloader merely to change its pool; stage the launcher fix and restart only at a controlled lifecycle boundary, preserving locks and downloader state.

Smart-idle completion must be based on actual owner-host filesystem counts for folders 1..640 (not DB alone): only `640/640` folders with `>=45` `.mp4` files counts as complete. The recurring watchdog stays scheduled and remains silent when complete; it may spawn one locked worker only when a shortage is observed. Keep Kibe and Admin source roots, state DBs, and process ownership separate.

## Evidence template

For a completed fix, record: target file and exact Gate 5/dispatch delta; compile output; focused test command/result; remote preflight result; canary machine/serial; remote report status and `post_verified`; screenshot paths and what each image actually proves; remaining limitations.

## Supporting detail

See `references/cross-host-admin-upload.md` for the Taadaa-specific command contract, observed false-alert chain, and verification matrix.
