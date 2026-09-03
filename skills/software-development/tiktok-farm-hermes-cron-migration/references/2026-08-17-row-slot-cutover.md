# Row-slot cutover + live spawn wiring (17/08/2026)

## Quyết định user (nguồn cao nhất)

- "Giữ nguyên, còn row thì kệ cha nó ví dụ row 3 trống của máy xx tới lịch mà nó row trống thì bỏ qua máy đó. Nhưng row 4 máy đó có thì tới lịch row 4 máy đó vẫn đc chạy. Tóm lại trc mỗi lần chạy phải gọi id tương ứng mỗi máy theo row, chứ t reg acc ms cập nhật liên tục"
- "Ủa thì đến lịch của row nào thì gọi máy tương ứng có acc trong row đó ra chạy máy đéo có acc thì bỏ qua. Có thế thôi sao mày xà quằn v?" — user bực khi mình over-engineer (lane A/B + đủ 3 acc). Bài học: user muốn ĐƠN GIẢN, hỏi/verify bằng dữ liệu thật trước, không tự phức tạp hóa.
- MaxWorkers = 30 ("đã đc chứng minh 30 vẫn ổn")

## Code changes (commit 597d7e7 + sau)

- `python_runner/hermes_cron/picker.py` `_entries`: bỏ lane/lane_rows/AccountBlock/jitter/pair_gap/RNG order; mỗi account feed-due → 1 entry với `slot_time` từ `row_slots = {1:"06:00", 2:"08:00", 3:"10:00", 4:"12:30", 5:"15:00", 6:"17:30"}`; blocks=[]; skipped: NOT_DUE / INVALID_FEED_STATE / UNSCHEDULABLE_CAPACITY (row>6). Bỏ check post-state khi pick (không còn NO_VIDEO_AVAILABLE từ picker).
- `manifest.py` validate_manifest no-block: `len(values) > 6 or gap < 90'` → UNSCHEDULABLE_CAPACITY.
- `generate_cron_source_config.py` `_read_projection`: bỏ ràng buộc `sorted(slots) == range(1, N+1)`; chỉ chặn duplicate/invalid (`len(set) != len or any < 1`).
- `feed_session_workbook.py` `select_feed_session_accounts`: thêm `elif not account.expected_username: reason = "account row {row_index} is empty (no username)... skipping"` → máy skip khi row trống.
- `run-feed-session.ps1`: `[int]$MaxWorkers = 30`.
- Wrappers: `repo_root()` ưu tiên `HERMES_CRON_REPO` → `os.getcwd()` → walk __file__; `build_child_env` forward gần đủ env trừ forbidden; `PYTHONPATH=repo`; `PYTHONTZPATH=tzdata`; runner/watcher bỏ `--seed`.

## Builder thật (ngoài repo, operator tool)

`D:\Taadaa\tmp_build_cron_inputs.py`:
- Input: `taikhoan_run_safe.xlsx` (workbook), `Tik1.xlsx` (device map serial thật), assignment manifest `%LOCALAPPDATA%\automation-core\assignments\tiktok-feed.json` (74 máy).
- Output: `D:/Taadaa/runtime/kibe/cron-source/{safe_projection.json, canonical_journal_facts.json, hermes_cron_source_config.json}` + `cron-state/{feed_state.json, post_state.json}`.
- feed_state schema đầy đủ: `{account_id, last_feed_success_at, unresolved_reservation, terminal_facts, state_revision}` (state_revision lấy từ config sau khi generate). post_state: `{account_id, status, video_available, target_count, state_revision}` — status "DUE" yêu cầu video_available bool.
- ⚠️ Cell Excel có quote-prefix `'` → strip `.lstrip("'")`; máy 38/66 serial = ngày tháng (data lỗi) → thay bằng serial Tik1 device map.
- E2E đúng: máy 22 → rows 1,2,4 (không có 3); máy 1 → 1,2,3,4; máy 75-80 (0 acc) → 0 entry; 247 acc → 247 entries, 74 máy.

## Live spawn (wrapper runner)

- Test mode: `HERMES_CRON_RUNNER_ENABLED=1` → offline child (hermes_cron_runner.py).
- Live mode: permit tồn tại + `HERMES_CRON_REPO` + `HERMES_CRON_FEED_WORKBOOK` → `_spawn_live()`: load active manifest (state_root/manifests/<day>/ACTIVE.json pointer) → `_due_entries` (slot ≤ now ≤ slot+90') → group by row → `powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File scripts/run-feed-session.ps1 -Row R -Machines <list> -SkipAccountWorkbookSync -ArtifactRoot <offline_root>/live/<day>/row-R-HHMMSS -Python <target> -Run` → Popen detached → lease `state_root/runner-live-lease/<day>.json` {pid, rows, day, started_at, expires_at +4h} → tick sau `_lease_alive` (os.kill pid 0) → no-op.
- Canary row 5 (15:45, máy 5,19,21,33,34,35): 21+34 success; 5,19,35 manual-needed (account switcher mở, nick row đúng CÓ trong danh sách nhưng classifier chặn — vấn đề đã biết từ canary 17/08, fix `9bfec1e` chưa phủ hết); 33 fail. Artifact: `D:\Taadaa\runtime\kibe\live\2026-08-17\row-5-154456\`.

## Pitfalls

1. `Internal Windows PowerShell error 8009001D` — child env thiếu quá nhiều keys → forward gần đủ env trừ forbidden.
2. MSYS env key case: `PSMODULEPATH` uppercase vs cần `PSModulePath` PascalCase cho child.
3. `\v1.0` escape → vertical tab; dùng raw string.
4. `repo_root()` deployed từ ~/hermes/scripts không thấy .git → silent mãi.
5. `verify_artifacts` format khác multi-machine artifact layout → verify summary.txt từng máy.
6. Manifest cũ không khớp source mới → fail-closed (đúng); xóa manifests + snapshot_bundles + journal để re-pick.
7. State root NGOÀI repo — `D:/Taadaa/runtime/kibe/cron-state`; xóa bằng path đầy đủ.
8. Wrapper test cần permit vắng mặt (mv ra ngoài → test → mv lại).

## Task Scheduler cũ (đã Disabled 16/08)

- `TikTokScheduler` (feed main) Disabled; `TikTokSchedulerTray`/`TikTokScheduleRecoveryHealth` Running (tray/health, không spawn feed); `TikTokAllSchedulerTray` Running = **run-proxy-watcher (GanProxy VPN) — GIỮ** (tắt = VPN chết = feed chết theo rule "k bật vpn k đc chạy").
- Cutover 17/08: user chốt "tắt hẳn task cũ chuyển qua hermes cron" — còn các scheduler repo khác (login/2FA/mail) không liên quan feed.
