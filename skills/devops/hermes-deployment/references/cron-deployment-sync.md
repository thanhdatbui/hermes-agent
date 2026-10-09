# Cron Configuration and Scripts Deployment (Multi-Machine)

## Architecture & Storage

- **Repository Source (Shared)**:
  - `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json`: Canonical definitions for recurring jobs (feed runners, watchdogs, lock reapers, render monitors).
  - `D:\Taadaa\Hermes\deploy\hermes-home\scripts\`: All Python scripts invoked by cron jobs.
  - `D:\Taadaa\Hermes\deploy\CRON_DEPLOYMENT_GUIDE.md`: Deployment guide.

- **Local Machine Runtime**:
  - `%LOCALAPPDATA%\hermes\cron\jobs.json`: Active cron job configuration.
  - `%LOCALAPPDATA%\hermes\scripts\`: Active script executables.
  - `%LOCALAPPDATA%\hermes\cron\executions.db`: Local SQLite execution history (machine-local, NOT committed).

## Multi-Host Boundaries: Local Runner vs Cross-Host Orchestration

### Why Secondary Host (Admin) MUST Run Its Own Local Hermes Cron
Never orchestrate USB device tasks cross-host from Kibe to Admin:
1. **Physical USB & ADB Daemon Isolation:** Phones 201-280 are plugged into Admin PC. Exposing ADB over LAN (`adb -H <ip>`) for 70-80 devices causes socket drops, XML/screencap timeouts, and ADB daemon hangs.
2. **Resource Exhaustion (Worker Cap):** Kibe already runs 74-80 devices (max 30 concurrent workers). Adding 80 Admin devices pushes to 150+ workers, saturating Kibe CPU/RAM and creating a single point of total farm failure.
3. **Host-Config & Lock Collisions:** Kibe uses `kibe.yaml` (dải 1-80) while Admin uses `admin.yaml` (dải 200-999). Cross-running jobs leads to corrupt device locks, wrong workbook paths, and invalid proxy resolutions.

### Cron Job Partitioning (Host-Local vs Global-Singleton)

When provisioning secondary machines (Admin), partition cron jobs strictly:

| Job Type | Scope | Target Machine | Reason |
|---|---|---|---|
| `taikhoan-run-safe-sync` | Host-Local | Both Kibe & Admin | Syncs each host's local `taikhoan_dat_v2.xlsx` to `taikhoan_run_safe.xlsx` in its own `workbook_root`. |
| `reap-dead-owner-locks` | Host-Local | Both Kibe & Admin | Cleans dead device locks in each host's local `runtime_root`. |
| TikTok feed picker/runner/watcher | Host-Local | Both Kibe & Admin | Drives physical devices plugged into the respective host. |
| `sync-hermes-skills-to-git` | Global-Singleton | **Kibe ONLY** | Only the primary host pushes skills to git fork; running on Admin causes git commit/push races. |
| `sync-gmail-clean-v2-to-tong` | Global-Singleton | **Kibe ONLY** | Global account aggregation to `TaadaaData/admin/gmail_live_tong.txt`. |
| `onedrive-multicloud-sync-watchdog` | Global-Singleton | **Kibe ONLY** | Cloud backup daemon; duplicate runs waste API quotas. |
| `daily-manual-stock-checklive` | Global-Singleton | **Kibe ONLY** | Global stock check on Telegram channel. |
| `avatar-post-feed-watchdog` | Host-Local | Both Kibe & Admin | Tự động kích hoạt upload avatar cho Row cuối ngày sau khi Ca 3 hoàn tất. |
| `mobiproxy-auto-healer-watchdog` | Host-Local | Both Kibe & Admin | Tự động kiểm tra và auto-heal cụm 32 modem MobiProxy 4G khi cổng bị 502/down. |

### Automated Provisioning & 1-Click Sync (Eliminating Manual Setup Drift)

To prevent operator error when setting up or updating cron on Admin:
1. `D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1` đồng bộ cả `cron\jobs.json` sang `%LOCALAPPDATA%\hermes\cron\jobs.json` nếu chưa tồn tại (hoặc nạp các job mẫu).
2. Package all secondary machine cron job definitions and launcher copies into a single idempotent script (`D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_cron.py`).
3. Secondary machine executes 1 command: `python D:\Taadaa\tools\setup_admin_cron.py` (or `--dry-run` to inspect).

#### Prompt điều phối ngắn gọn cho bot Admin (Quick Dispatch Prompt)
Khi operator cần Admin cập nhật cron nuôi acc và kiểm tra tiến độ:
- **Bước 1 (Phía Kibe):** Bắt buộc force-sync scripts & jobs.json lên OneDrive Shared trước:
  `python "C:/Users/Kibe/AppData/Local/hermes/scripts/cron_sync_watchdog.py" --force`
- **Bước 2 (Prompt gửi bot Admin ngắn gọn):**
  ```text
  Đồng bộ cron nuôi acc từ Kibe (chạy python D:\OneDrive\Taadaa_Sync_Shared\tools\setup_admin_cron.py) rồi kiểm tra hermes cron list và báo cáo tiến độ ca nuôi acc gần nhất.
  ```
  *(Nếu muốn Admin kéo cả git code & template mới: `git -C D:\Taadaa\Hermes pull --rebase fork main && powershell -NoProfile -ExecutionPolicy Bypass -File D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1`)*

4. Script `setup_admin_cron.py` đảm bảo:
   - All cron jobs are `no_agent: true` (0 token, immune to model drift and missing API keys).
   - Dynamic runtime states (`last_error`, `last_delivery_error`, `run_claim`, `fire_claim`) được reset về `null` trước khi lưu vào repo `deploy/hermes-home/cron/jobs.json`.
   - Launcher scripts are copied to `%LOCALAPPDATA%\hermes\scripts\`.
   - Host paths resolve dynamically from `TAADAA_HOST_CONFIG` (`D:\Taadaa\machine-config\admin.yaml`).
   - Creates a timestamped/safety backup `jobs.json.bak` before writing changes.
   - Sets correct execution working directory (`workdir: r"D:\Taadaa\tiktok-luot nuoi acc"`) for runner/picker/lock-reaper jobs.

### Danh Mục Cron Jobs Toàn Farm & Thống Nhất Đích Farm Alerts (`-5373649734`)
Danh mục đầy đủ trên hệ thống runtime và repo `D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json` (tất cả watchdog phiên, dọn cache và lỗi diện rộng đều thống nhất đẩy về Farm Alerts):
1. `sync-hermes-skills-to-git` (`*/5 * * * *`, deliver: `local`, Kibe only)
2. `taikhoan-run-safe-sync` (`*/5 * * * *`, deliver: `local`)
3. `reap-dead-owner-locks` (`*/15 * * * *`, workdir: `D:\Taadaa\tiktok-luot nuoi acc`, deliver: `local`)
4. `phase9-staging-picker` (`0 6 * * *`, workdir: `D:\Taadaa\tiktok-luot nuoi acc`, deliver: `local`)
5. `auto-trim-startup-files` (`0 3 * * 0`, deliver: `origin` hoặc `telegram:-5188753741`)
6. `phase9-runner-tiktok-feed` (`*/15 * * * *`, workdir: `D:\Taadaa\tiktok-luot nuoi acc`, deliver: `local`)
7. `daily-manual-stock-checklive` (`0 7 * * *`, deliver: `local`)
8. `device-locks-watchdog` (`1,16,31,46 * * * *`, deliver: `local`)
9. `end-of-day-clear-tiktok-cache` (`*/10 1,2,3,4 * * *`, deliver: `telegram:-5373649734`)
10. `tiktok-feed-session-watchdog` (`*/5 * * * *`, deliver: `telegram:-5373649734`)
11. `farm-render-download-watchdog` (`0 * * * *`, deliver: `telegram:-5373649734`)
12. `post-morning-gmail-2fa-watchdog` (`*/5 8,9,10,11 * * *`, deliver: `telegram:-5373649734`)
13. `post-noon-chain-watchdog` (`*/5 14,15,16,17 * * *`, deliver: `telegram:-5373649734`)
14. `post-evening-avatar-watchdog` (`*/10 21,22,23 * * *`, deliver: `telegram:-5373649734`)
15. `post-evening-gpm-login-watchdog` (`*/10 21,22,23 * * *`, deliver: `telegram:-5373649734`)
16. `sync-all-tik-keywords-cron` (`*/15 * * * *`, deliver: `local`)
17. `sync-gmail-clean-v2-to-tong` (`0 8 * * *`, deliver: `local`, Kibe only)
18. `onedrive-multicloud-sync-watchdog` (`0 */6 * * *`, deliver: `origin`, Kibe only)
19. `hermes-stale-watchdog` (`*/2 * * * *`, deliver: `origin` hoặc `telegram:-5188753741`)
20. `mobiproxy-auto-healer-watchdog` (`*/5 * * * *`, deliver: `local`)

### Invariant Đích Báo Cáo Cron & Farm Alerts Trên Máy Admin
Khi đồng bộ cấu hình cron sang Admin PC để nhận diện lỗi diện rộng (>30% hoặc >10 máy) và báo cáo phiên:
1. **Bot Token & Quyền Thành Viên Nhóm (BẮT BUỘC):** Bot Telegram của máy Admin BẮT BUỘC phải được thêm vào nhóm **Farm Alerts** (`-5373649734`) và cấp quyền gửi tin nhắn / ảnh. Nếu thiếu, Telegram API sẽ trả lỗi `Forbidden: bot is not a member of the group chat`.
2. **Cấu hình 1-Lệnh Idempotent (`setup_admin_cron.py`):**
   Chạy lệnh trên Admin PC:
   `python "D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\setup_admin_cron.py"`
   Script tự động copy các runner/watchdog scripts mới nhất vào `%LOCALAPPDATA%\hermes\scripts\`, backup `jobs.json.bak`, và cập nhật cấu hình `deliver: "telegram:-5373649734"`.
3. **Phạm Vi Máy Host-Aware (`admin.yaml`):**
   `D:\Taadaa\machine-config\admin.yaml` phải cấu hình đúng `machine_range: [200, 999]`, `workbook_root` và `runtime_root` để watchdog không quét chéo vào dải máy Kibe (1..80).

### Shared Review Tools & Root Wrappers Pattern
- Move review tools from `D:\Taadaa\` root to `D:\OneDrive\Taadaa_Sync_Shared\tools\`:
  - `review_gate.py`
  - `run_plan_review_gate.py`
- Expose via NTFS junction `D:\Taadaa\tools` on both hosts.
- At `D:\Taadaa\` root, maintain lightweight proxy wrappers importing `tools/review_gate.py` to preserve backwards compatibility with any existing scripts invoking `python D:\Taadaa\review_gate.py`.

### Pattern Wrapper Cron Cho Clean Telegram Output (Tránh Bloat Log)
Khi tạo cron chạy công cụ phân tích hoặc quét dữ liệu dài (ví dụ: `tiktok_account_tracker.py` theo dõi follow/video toàn farm):
- **Vấn đề:** Nếu cron gọi trực tiếp tool phân tích, hàng trăm dòng log quét (`Loading...`, `Tracking worker...`, `Saving DB...`) sẽ bị đẩy thẳng vào nhóm Telegram qua cơ chế `no_agent`, gây tràn tin nhắn (spam) và khó quan sát.
- **Giải pháp:** Viết một launcher wrapper script (ví dụ: `cron_tiktok_daily_tracker.py`) đồng bộ vào 3 thư mục chuẩn cron. Wrapper thực hiện:
  1. Chạy tool qua `subprocess.run(capture_output=True, text=True, encoding="utf-8")`, truyền tiếp `sys.argv[1:]` (cho phép test với `--limit`, `--workers`, v.v.).
  2. Khi `exit_code == 0`: Trích xuất duy nhất phần tóm tắt summary (từ marker phân cách như `========================================` đến cuối) để in ra stdout cho Telegram nhận.
  3. Khi `exit_code != 0`: In rõ lỗi, mã thoát (`exit_code`) cùng toàn bộ stderr để người vận hành nắm bắt sự cố.

### Pitfall: Hardcoded Kibe Paths in Cron Launchers & Host-Aware Pattern
When copying scripts directly from Kibe's `%LOCALAPPDATA%\hermes\scripts\`, beware of hardcoded paths that break Admin (200-999). Use the host-aware resolver pattern reading `TAADAA_HOST_CONFIG` (defaulting to host config YAML):
- `ensure_row_accounts.py`: Must not hardcode `range(1, 81)`, `D:\OneDrive\TaadaaData\kibe`, or `--append-kibe`. Use `taadaa_host.load_host_config()` to dynamically resolve `workbook_root`, detect machines by scanning actual 8-row blocks in `taikhoan_run_safe.xlsx` (supporting both 1..80 and 201..280), and dynamically pass `--append-admin` vs `--append-kibe` to `buy_hotmail.py`. When `load_host_config` fails, log explicit `sys.stderr.write` warning instead of silent fallback.
- `tiktok_runner.py`: Must dynamically resolve `_workbook_root` and `_runtime_root` via `taadaa_host.load_host_config()` instead of hardcoded `ACCOUNT_WORKBOOK` and `STATE_DIR`. When migrating runner architecture to 4 Ca x 2 Phiên with `_preflight_ensure_accounts(row)`, deploy template `deploy/hermes-home/scripts/tiktok_runner.py` must be committed and pushed to `fork main` so Admin receives the on-demand reg flow upon `sync-from-kibe.ps1`. In `_save_state`, always suffix temporary files with process PID (`.runner_simple_state.{os.getpid()}.tmp`) before atomic `os.replace` to prevent race conditions during concurrent cron ticks.
- `feed_session_watchdog.py`: Implement `_get_runtime_root()` resolving `LIVE_ROOT`, `STATE_FILE`, and `SOURCE_CONFIG` dynamically under `runtime_root` (`D:\Taadaa\runtime\admin\...`) rather than hardcoded `runtime\kibe`. Ensure indentation conforms strictly to PEP8 4-space indent across nested `if/elif/else` branches to prevent silent syntax failures.
- `feed_session_watchdog.py`: Implement `_get_runtime_root()` resolving `LIVE_ROOT`, `STATE_FILE`, and `SOURCE_CONFIG` dynamically under `runtime_root` (`D:\Taadaa\runtime\admin\...`) rather than hardcoded `runtime\kibe`.
- `cron_clear_tiktok_cache.py`: Implement `_get_tik1_path()` resolving `TIK1_WORKBOOK` under `workbook_root` from `TAADAA_HOST_CONFIG`.
- `night_chain_reg_pipeline_launcher.py`: Respects `TAADAA_HOST_CONFIG` or defaults to `admin.yaml` when running on Admin host.

*String escape pitfall in Windows scripts:* When scripting replacements in Windows paths containing `\runtime`, beware that `\r` can be parsed as a carriage return byte (0x0D), corrupting the string into a broken multiline literal. Use forward slashes `D:/Taadaa/runtime` or `os.path.join` to prevent escaping collisions.

### Shared Tools Junction & Cron Distribution
- All cross-machine tools and automation helpers reside in `D:\OneDrive\Taadaa_Sync_Shared\tools\` and are exposed locally via NTFS junction `D:\Taadaa\tools`. Ad-hoc patch files at `D:\Taadaa\` root should not be copied to shared tools.
- To distribute updated cron runner scripts to Admin without waiting for Git commits, sync the latest runner scripts from `%LOCALAPPDATA%\hermes\scripts\` to `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\`. `setup_admin_cron.py` pulls directly from there into Admin's `%LOCALAPPDATA%\hermes\scripts\`.

## Synchronization Workflow

1. **Bootstrap on New / Admin Machine**:
   - Running `.\deploy\setup-admin.ps1` automatically copies missing `jobs.json` and syncs `scripts/*.py` via robocopy.
   - `sync-from-kibe.ps1` also copies `deploy\hermes-home\cron\jobs.json` to `%LOCALAPPDATA%\hermes\cron\jobs.json` if it does not yet exist on the secondary machine.

2. **Sanitizing Runtime State when Syncing jobs.json Back to Deploy Template**:
   - When copying `%LOCALAPPDATA%\hermes\cron\jobs.json` back to repo `deploy/hermes-home/cron/jobs.json`, always reset ephemeral runtime failure/claim fields to `null`:
     `last_error: null`, `last_delivery_error: null`, `run_claim: null`, `fire_claim: null`.
   - This ensures host-specific lock timeouts (e.g. `reap-dead-owner-locks`) or missing Telegram thread notifications are not baked into the shared repository template.

3. **Watchdog Output Format & Unit Test Alignment**:
   - `feed_session_watchdog.py` formats released follow summaries using `(N máy)` and uppercase `M<stt>` (e.g. `M1`, `M2 (3 lượt)`).
   - Any updates to watchdog summary logic must be accompanied by corresponding updates in `deploy/hermes-home/scripts/test_feed_session_watchdog.py` to ensure test gates pass 100%.

4. **Cron Scheduling Rule**:
   - Use fixed 5-field cron format (e.g. `*/15 * * * *`) rather than loose interval strings (`every 30m`) for critical maintenance tasks like `reap-dead-owner-locks` to avoid ticker clock drift over long sessions.

3. **Lock File Schema Compatibility**:
   - Devices locks across different repos may use either `machine`/`project`/`serial` or `stt`/`owner`/`device_id`.
   - Watchdogs and parsers must support both schemas and regex fallback from filename `machine_(\d+).lock.json` to prevent `Máy None` / `unknown` false alerts.
