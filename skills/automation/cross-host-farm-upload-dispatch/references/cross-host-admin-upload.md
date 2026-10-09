# Cross-host Admin Upload Reference

## 1. Observed Incident Signature

### Pattern A: False Shortage (Local controller check against remote path)
- **Symptom:** Watchdog (`feed_session_watchdog.py`) alerts that 40+ Admin farm machines are `Hết video/Cần cào` (`status: "skipped", reason: "video_not_rendered"`).
- **Physical reality:** The remote render root on `admin-farm` (`D:\TIKTOK-videonuoinick-admin`) has tens of thousands of rendered `.mp4` files, and each reported device folder contains the next video.
- **Root cause:** The runner executes on the Kibe controller. At Gate 5 in `multi_machine_feed_session.py`, it evaluates:
  ```python
  video_file = media_root / folder_video / f"{next_video}.mp4"
  if not video_file.is_file() or video_file.stat().st_size == 0:
      return {"status": "skipped", "reason": "video_not_rendered"}
  ```
  Because `media_root` for machines >= 200 points to `D:\TIKTOK-videonuoinick-admin` which only exists on `admin-farm`, the local filesystem check on Kibe always returns `False`.

### Pattern B: True Shortage (Remote video pool deficit / Crash / Mapping mismatch)
- **Symptom:** Remote upload fails with `[VIDEO_PATH_ERROR] RESOLVE_NEXT_VIDEO: Cannot resolve video path: Video file not found: D:\TIKTOK-videonuoinick-admin\<folder_video>\<next_video>.mp4`.
- **Diagnostic check:**
  1. Inspect remote SQLite database: `D:\CodexRuntime\tiktok-video-machine2\state.db` -> `SELECT count(*), sum(video_count) FROM folders;`. Check if downloader crashed (e.g., `sqlite3.OperationalError: disk I/O error` under SQLite WAL with high concurrency `parallel >= 20`).
  2. Check remote cron jobs: verify if `farm-render-download-watchdog` is paused or alive on `admin-farm`.
  3. Check slot cross-mapping: Verify mapping in `Tik{slot}.xlsx` where `Folder Video` != `video gốc`. Ad-hoc background scripts that render 1:1 (`output_dir = render_root / d.name`) will produce empty target folders for Tik slots 2..8. Render scripts must follow workbook mappings (`admin_render_chain.py`).

## 2. Remote Dispatch Contract

When machine number is `>= 200`:
- **Host alias:** `ssh admin-farm`
- **Working directory:** `D:/Taadaa/Tiktok-video`
- **Python executable:** `D:/Taadaa/python-envs/automation/Scripts/python.exe`
- **Module:** `scripts.tiktok_workflow`
- **Config:** `D:/Taadaa/Tiktok-video/config-admin.yaml`
- **Workbook:** `D:/OneDrive/TaadaaData/admin/Tik{upload_row}.xlsx`
- **Target device:** `--single-device <account.serial>`
- **Video number:** `--video-number <next_video>`
- **Source root:** `--video-source-root D:/TIKTOK-videonuoinick-admin`
- **Flags:** `--allow-device-reboot-recovery --no-dry-run`
- **Environment:** Strip `ADB_SERVER_SOCKET` so the remote script connects to its local ADB server on `admin-farm`.

## 3. Verification Sequence

1. `python -m py_compile python_runner/flows/multi_machine_feed_session.py`
2. Run focused upload-hook test:
   `PYTHONPATH=. pytest python_runner/tests/test_upload_hook.py -k "test_upload_hook_gate5_video_not_rendered"`
3. Verify remote preflight over SSH:
   ```bash
   ssh admin-farm "cd /d D:/Taadaa/Tiktok-video && D:/Taadaa/python-envs/automation/Scripts/python.exe -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config-admin.yaml --workflow-workbook D:/OneDrive/TaadaaData/admin/Tik1.xlsx --single-device <serial> --video-number <num> --video-source-root D:/TIKTOK-videonuoinick-admin --preflight"
   ```
4. Device wake & preflight:
   - If device is sleeping (`mWakefulness=Dozing`), wake via `adb shell svc power wakeup` / `input keyevent KEYCODE_WAKEUP` and confirm `dumpsys power` reports `mWakefulness=Awake`. Do NOT treat sleeping device as a reason to avoid canary.
   - Capture pre-action screenshot to confirm clean Launcher state.
5. Background canary execution via `terminal(background=True, notify_on_complete=True)`.
6. Visual & Log evidence readback:
   - Extract `report.json` on `admin-farm` under `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/`.
   - Inspect `execution.log` for state transitions (`VERIFY_POST`, `Profile video tiles` increment).
   - SCP remote screenshots (`post-published-surface.png` and `profile-grid-verify_post-*.png`) to local image cache and present via `MEDIA:<path>`.
   - Update workbook tracking: increment `Video Đã Đăng` in `Tik{slot}.xlsx` and `taikhoan_run_safe.xlsx`.

## 4. Unit Test Assertion & Mock Isolation
- **Mock target pattern:** In tests for `_run_upload_hook`, avoid `sys.modules.get(...)` loops that fail to bind if a module is not pre-imported.
- **Assertion contract (`test_upload_hook_admin_remote_ssh_dispatch`):**
  - Verify that machine `>= 200` does NOT skip when local video path is missing.
  - Verify `subprocess.run` receives `ssh admin-farm` command with exact workbook and serial.
  - Verify `ADB_SERVER_SOCKET` is stripped from `proc.env` to prevent remote port conflicts.

## 5. Subagent Self-Report Verification & L2 Escalation
- Subagents delegated via `delegate_task` run in isolated contexts; if a subagent exhausts its iteration budget (`max_iterations`), its summary may claim files were modified even when no changes landed in the host working tree.
- Coordinator must independently verify `git diff -U0` on the target host files.
- If diff is missing after structural dispatch, execute L2 Emergency Surgery within the strict O(1) budget (<= 30 lines diff, 1 focused test) instead of endlessly re-dispatching.

## 6. Host Reboot Survival & Persistent Supervision (Dual-Tier Model)
Farm hosts (Admin-PC `admin-farm` and Kibe host) frequently undergo scheduled restarts (e.g. 04:45 AM farm reboot) or manual resets. To guarantee that video crawling (`download_by_niche.py`) and rendering (`random_batch_render.py`) resume automatically without manual intervention:
1. **Auto-Logon Prerequisite:** Ensure `AutoAdminLogon = 1` in `HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon`.
2. **Tier 1 - Windows Startup (Instant Reboot Recovery):**
   - Place a headless VBScript wrapper (`wscript.exe` with `SW_HIDE / 0`) in Windows Startup (`AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\`).
   - Example: `start_render_watchdog.vbs` and `start_downloader_watchdog.vbs`.
   - Fires immediately upon logon without popping up console windows or stealing focus.
3. **Tier 2 - Hermes Cron Watchdog (Continuous Liveness & Auto-Healing):**
   - Register a recurring watchdog cronjob (`*/15 * * * *`, deliver: local) on Hermes (`admin-render-worker-watchdog`, `admin-downloader-watchdog`, `kibe-render-worker-watchdog`).
   - If a worker crashes mid-run (e.g., SQLite WAL lock error or network glitch), the watchdog automatically revives it within 15 minutes.
4. **Kernel-level Single-Instance Lock (`msvcrt`):**
   - Both renderer and downloader must acquire non-blocking file locks via `msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)` at startup.
   - Prevents duplicate processes, enforces strict `Render 1 worker (--parallel 1)`, and eliminates database thrashing.

## 7. Lifecycle & Completion Semantics: Worker Auto-Exit vs Scheduler Smart Idle
When all video folders (640/640) reach target quota (>= 45 clips):
- **Heavy Workers (ffmpeg / downloader):** MUST self-terminate (`sys.exit(0)`) when `len(tasks) == 0`. Frees 100% CPU, GPU, and RAM. Never leave dead while-true sleep loops running.
- **Schedulers (Cron Watchdogs):** Do NOT pause or delete the cron schedule. Instead, implement **Smart Idle**:
  - Watchdog performs a lightweight preflight scan (< 0.05s) across the 8 Tik workbooks.
  - If `0` tasks are pending: exit immediately with code 0 (consumes 0% CPU, 0% RAM).
  - If video depletion occurs later (from regular farm upload shifts or new account provisioning): the watchdog immediately detects the deficit and respawns the worker automatically without user intervention.

