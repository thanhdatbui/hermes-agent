# Render Worker In-Flight Game Guard & Emergency Gate Discipline

## 1. Problem: The 15-Minute Watchdog Trap
- **Symptom:** User experiences severe game lag / FPS drop on Admin machine (e.g., during Warcraft 3 or TFT matches) even after a watchdog script (`watchdog_admin_render.py`) with game detection was installed.
- **Root Cause Analysis:**
  1. **Coarse Polling Interval:** The watchdog was scheduled in Windows Task Scheduler (`Taadaa_Admin_Render_15m`) to run once every 15 minutes. When a game starts between ticks, the render worker continues consuming 90%+ CPU for up to 15 minutes.
  2. **Blocking Subprocess Execution:** `run_admin_render_worker.py` executed render tasks via `subprocess.run(cmd, timeout=2400)`. This call blocks Python for up to 40 minutes per task, incapable of sensing new processes.
  3. **Immediate Task Advancement on External Kill:** When the external watchdog did kill `ffmpeg.exe` and `random_batch_render.py`, `subprocess.run` caught returncode 15, logged a warning, and immediately executed the next task in `for t in tasks:`, instantly spawning a new `ffmpeg.exe` while the user was still actively in-game!
  4. **The Downloader & Secondary Worker Blindspot:** While Render workers are guarded, secondary batch workers (such as `download_by_niche.py --parallel 40` via `Taadaa_Admin_Downloader_15m` or ad-hoc `register-gmail` / `run_all.ps1` runs) are frequently omitted from the game guard. A 40-worker downloader continuing to run saturates network/disk I/O and spawns sub-processes, causing the exact same stutter and screen-blinking issues ("chớp màn hình / nháy nháy") in DirectX games like Warcraft 3 (`w3l.exe`) or TFT.

## 2. Solution: In-Process In-Flight Game Polling (<= 2s Latency)
Instead of relying on an external periodic watchdog to police a blocking worker, the game detection logic MUST be embedded directly into the worker's execution loop:
1. **Pre-check:** Before picking or rendering any task, check `is_gaming_active()`. If active, kill any rogue ffmpeg and sleep 10s.
2. **In-Flight Polling (2s Interval):**
   ```python
   proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
   while proc.poll() is None:
       gaming, game_name = is_gaming_active()
       if gaming:
           # Kill child tree immediately
           parent = psutil.Process(proc.pid)
           for child in parent.children(recursive=True):
               try: child.kill()
               except Exception: pass
           parent.kill()
           kill_all_ffmpeg()
           # Enter standby loop until game exits
           while True:
               time.sleep(5)
               g_active, _ = is_gaming_active()
               if not g_active:
                   break
           break
       time.sleep(2)
   ```
3. **Exact Game Allowlist:**
   - Warcraft III: `war3.exe`, `frozen throne.exe`, `w3l.exe`, `warcraft iii.exe`
   - TFT in-match: `league of legends.exe`, `tftclient.exe`, `tftclient-win64-shipping.exe`
   - CẤM match background companion apps (`TFTAcademy.exe`, `Overwolf.exe`, `LeagueClientUx.exe`).

## 3. Downloader & Remote Dispatch Game Guarding
- **Downloader Watchdog Parity:** `watchdog_admin_downloader.py` MUST import and enforce `is_gaming_active()` identically to `watchdog_admin_render.py`. If active, immediately kill any running `download_by_niche.py` or `run_admin_downloader_service.py` and skip spawning.
- **Remote Pre-Flight Check Before Ad-hoc Dispatches:** Before triggering heavy remote scripts (e.g. `run_all.ps1`, `gmail_reg_v10.py`, multi-machine ADB feeds) via SSH from the controller to the Admin machine, check whether gaming is active (`is_gaming_active()`). Never dispatch ad-hoc batch automation while a game is running in Console Session 1.
- **Screen-Blinking Prevention in Legacy DirectX Games:** Games like Warcraft 3 running in exclusive/borderless fullscreen blink or minimize when background tasks launch non-hidden console windows (`conhost.exe`, `powershell.exe`, `cmd.exe`). Ensure all background and remote executions strictly use `CREATE_NO_WINDOW (0x08000000)` and `WindowStyle Hidden`.

## 3. Coordinator Discipline: Two-Phase Incident Response
When a user angrily reports game lag or system disruption caused by automation:
- **Phase 1: Zero-Code Emergency Relief (O(1) in <= 10s):**
  - Run remote/local commands to kill heavy processes (`Stop-Process -Name ffmpeg -Force`) and disable scheduled tasks.
  - DO NOT write code, DO NOT edit scripts, DO NOT touch files. Free the host CPU immediately so the user can play.
- **Phase 2: Structured 3-Step Gate (a, b, c) for Permanent Fixes:**
  - **Step a (Plan / Scope Lock):** Run `claude_worker.py --role planner` to define the exact change contract O(1).
  - **Step b (Worker Dispatch):** Dispatch an independent worker (Claude Haiku CLI or Agy CLI `ag_cli.py fix`). Coordinator MUST NOT cowboy-code >15 lines.
  - **Step c (Verification & Review Gate):** Run focused unit tests (<30s), verify live state, and gate through Closeout Reviewer before committing or reporting done.
- **Rejecting Reviewer Over-Engineering:**
  - AI Reviewers (like Claude Sonnet) when asked about Coordinator violations frequently hallucinate complex architectural solutions (OS-level ACLs, HMAC cryptographic deploy manifests, separate daemon architectures).
  - Recognise this as classic LLM over-engineering: the 3-step gate $(a, b, c)$ is already fully specified and sufficient; the failure was human/model non-compliance under stress, not a missing architectural layer.
