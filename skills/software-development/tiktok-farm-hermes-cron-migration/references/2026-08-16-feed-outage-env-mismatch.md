# Feed outage 14–16/08 — DeviceLockNeedsUserDecision env mismatch

## Timeline (python_runner/runs/scheduler.jsonl)
- 14/08 12:00 row4: `ModuleNotFoundError: No module named 'automation_core.escalation'`
- 14/08 17:00 → 16/08 17:00 mọi slot: `ImportError: cannot import name
  'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'`
  (path traceback = `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\automation_core\device_lock.py`)

## Root cause chain
1. `python_runner/core/device_lock.py` là wrapper: `from automation_core.device_lock import (..., DeviceLockNeedsUserDecision, ...)` — không phải nguồn lỗi.
2. Class `DeviceLockNeedsUserDecision` CHỈ có trong automation_core **0.4.45**:
   - automation env (`D:\Taadaa\python-envs\automation`): 0.4.45 ✅ (có class)
   - Python312 global: 0.4.44 ❌
   - hermes venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv`): 0.4.43 ❌
3. `scripts/run-feed-session.ps1:34` default `[string]$Python = "python"` → Task Scheduler
   (TikTokScheduler) spawn powershell non-interactive → bare `python` resolve theo
   **HKCU\Environment Path** (user env registry): `...\hermes\hermes-agent\venv\Scripts`
   đứng ĐẦU → hermes venv 0.4.43 → ImportError.
4. Log launcher thật xác nhận: `python_runner/runs/launcher/20260816-*.log` — traceback
   path = hermes venv (không phải Python312 như tưởng tượng ban đầu).

## Probe chẩn đoán (tái sử dụng được)
- Version matrix per-env:
  `/d/Taadaa/python-envs/automation/Scripts/python.exe -c "import automation_core.device_lock as d; print(hasattr(d,'DeviceLockNeedsUserDecision'))"`
  (lặp lại với bare `python` và hermes venv python)
- PATH user thật: `powershell -NoProfile -Command "Write-Output ('U=' + (Get-ItemProperty 'HKCU:\Environment').Path)"`
- Wheel diff additive check (TRƯỚC khi pin bất kỳ version nào):
  ```bash
  cd /tmp && unzip -oq <old>.whl -d w44 && unzip -oq <new>.whl -d w45
  for v in 44 45; do grep -rhoE '^class [A-Za-z_]+' /tmp/w$v/automation_core --include='*.py' | sort -u > /tmp/cls_$v.txt; done
  diff /tmp/cls_44.txt /tmp/cls_45.txt   # chỉ dòng '>' = additive
  for v in 44 45; do grep -rhoE '^def [A-Za-z_]+' /tmp/w$v/automation_core --include='*.py' | sort -u > /tmp/def_$v.txt; done
  diff /tmp/def_44.txt /tmp/def_45.txt   # rỗng = không hàm nào bị xóa
  ```
  0.4.44→0.4.45: THÊM `DeviceLockNeedsUserDecision`, `DeviceLockOpenAudit`,
  `_UnlockedDeviceLockLease`, `escalation.py`, `adapters.py`, `ConsumerRecoveryAdapter`,
  `NonRetryableFailureError`, `RecoveryBudgetExhaustedError`; 0 hàm xóa; 0 dep mới
  (METADATA Requires-Dist rỗng cả 2 bản).

## Hướng fix (chờ audit Sol chốt — user yêu cầu audit trước khi đụng môi trường)
- (a) Cài wheel 0.4.45 (`file:///D:/Taadaa/automation-core-user-lock-gate-wt/dist/automation_core-0.4.45-py3-none-any.whl`)
  vào hermes venv (nơi bare python resolve) — nguồn wheel giống automation env đang chạy ổn từ 14/08.
- (b) Sửa `run-feed-session.ps1` trỏ `-Python D:\Taadaa\python-envs\automation\Scripts\python.exe`
  (hoặc tham số) — không đụng venv Hermes.
- Lưu ý: hermes venv là venv của Hermes agent — cài package phụ (automation_core) additive
  nhưng phải audit trước.

## Trạng thái live-wiring Hermes cron (verify 16/08 — trả lời "cron đã auto chưa")
- 3 wrapper `scripts/hermes_cron/tiktok_{picker,runner,watcher}.py` tồn tại trong repo
  nhưng CHƯA copy vào `%LOCALAPPDATA%\hermes\scripts` (ls rỗng) → cron không gọi được.
- Mọi wrapper default-off: `if env.get(ACTIVATION_ENV) == "1"` (`HERMES_CRON_PICKER_ENABLED`,
  `HERMES_CRON_RUNNER_ENABLED`, `HERMES_CRON_WATCHER_ENABLED`); permit file non-symlink cũng kích hoạt.
- `python_runner/scripts/hermes_cron_runner.py` refuse `--execute`/`--repo`/`--feed-workbook`
  (offline harness, `run_entry(execute=False)`); `ProductionFeedLauncherAdapter`
  (runner.py:170-175) `enabled=False` mặc định.
- → Hermes cron feed CHƯA từng live; Windows Task Scheduler (`TikTokScheduler` →
  `python -m scheduler --live --poll-seconds 30`, còn nhiều task cũ: TikTokAllSchedulerTray,
  TikTokScheduleRecoveryHealth, TikTokSchedulerTray enabled; wake/recovery disabled) vẫn là
  nguồn chạy duy nhất.
- Wrapper có kill-switch tốt (activation env + permit) → tạo cron job paused trước, bật sau
  canary 1 máy (theo plan 08-16) là đường an toàn.

## Audit codex fallback (60818 vs 20128)
- `codex exec --model gpt-5.6-sol` fail `stream disconnected ... (http://localhost:60818/v1/responses)`
  lặp lại 2 lần = **Codex API Service (provider `codex_local_access`) down** — 60818 KHÔNG phải
  9router. Verify: `Get-NetTCPConnection -LocalPort 60818` rỗng, không process listen.
- 9router = port 20128, watchdog `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1`
  (powershell hidden, mutex `Local\9Router_Supervisor_Mutex_v2`, tự restart nếu port chết).
- Fallback chạy audit: `codex exec --ephemeral --sandbox read-only --model-provider 9router --model gpt-5.6-sol < prompt.md`
- Codex CLI trap: `-p "..."` bị hiểu là `--profile` → prompt qua positional arg / `--prompt`
  hoặc stdin redirect.
