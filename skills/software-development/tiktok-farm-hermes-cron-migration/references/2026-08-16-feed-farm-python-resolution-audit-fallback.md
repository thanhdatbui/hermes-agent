# Feed farm: python resolution + audit fallback chain (2026-08-16)

## Python env resolution — EVIDENCE-BASED, đừng chốt 1 env từ 1 probe

3 bản automation_core lệch version: hermes venv **0.4.43**, Python312 global **0.4.44**, `python-envs/automation` **0.4.45**. Class `DeviceLockNeedsUserDecision` CHỈ có ở 0.4.45 (`python_runner/core/device_lock.py` là wrapper re-export từ `automation_core.device_lock`). Wheel diff 0.4.44→0.4.45 additive: thêm class/func (`DeviceLockNeedsUserDecision`, `DeviceLockOpenAudit`, `_UnlockedDeviceLockLease`, `adapters.py`, `escalation.py`, `ConsumerRecoveryAdapter`...), 0 hàm xóa, 0 dep mới.

Ba bằng chứng MÂU THUẪN nhau:
- **E1 (production launcher logs — ground truth)**: traceback path = `hermes-agent\venv\Lib\site-packages\automation_core\device_lock.py` → bare python trong context thật resolve hermes venv 0.4.43.
- **E2 (probe cmd.exe qua PowerShell)**: python → Python312 0.4.44 — NHƯNG probe kế thừa PATH của bash session (WindowsApps alias đứng trước) → KHÔNG phải mô phỏng trung thực env registry Task Scheduler.
- **E3 (audit độc lập R1)**: khẳng định production = Python312 (0.4.44) qua PythonManager, "cài hermes venv không fix" — nhưng audit cũng KHÔNG chạy probe env sạch, và audit sai khi nói "HKCU Path registry trống" (thực tế HKCU Path CÓ `hermes-agent\venv\Scripts` ở vị trí 2).

→ **KẾT LUẬN: không đủ bằng chứng sạch để chốt 1 env.** Fix vững = bỏ phụ thuộc bare python:
(a) launcher truyền python env rõ ràng: `-Python D:\Taadaa\python-envs\automation\Scripts\python.exe` (đúng guardrail "target Python explicit" trong skill Phase 9 live-wiring) — `scripts/run-feed-session.ps1:34` default `$Python="python"` và `scheduler/launcher.py` không pass `-Python`;
(b) upgrade CẢ Python312 lẫn hermes venv lên 0.4.45 (wheel additive đã diff).
Đừng chọn 1 env theo probe nhiễm. Cũng check `scripts/sync-safe-workbook.py` (import `automation_core.workbook` qua bare `$Python` — cùng rủi ro fragile env).

## Probe python resolution — các cách ĐỀU nhiễm trừ 1

- Bash `which python` / `python -c` = NHIỄM (PATH session bash, WindowsApps alias đứng trước).
- cmd.exe gọi TỪ PowerShell = NHIỄM (kế thừa PATH bash qua process tree).
- Probe sạch duy nhất: chạy qua **scheduled task thật** (At-logon context, registry PATH) — hoặc chấp nhận **traceback path trong launcher log THẬT làm ground truth** (E1), vì đó là cái production thực sự gặp phải.

## Audit execution fallback (16/08 — đã test thật)

- `codex exec` KHÔNG có flag `--model-provider` (`error: unexpected argument`) → dùng `-c 'model_provider="9router"'`.
- `-p "text"` bị hiểu là `--profile` → prompt dùng **positional arg** hoặc **stdin redirect `< file`**; không dùng `-p` với chuỗi dài.
- `localhost:60818` = **Codex API Service** (provider `codex_local_access`, service nền codex CLI, KHÔNG watchdog) — down → lỗi lặp `ERROR: stream disconnected ... 60818/v1/responses` dù retry 5/5. Check: `Get-NetTCPConnection -LocalPort 60818` rỗng = chết. 9router = **20128** (watchdog `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1` tự restart; `/v1/models` list được).
- 9router combo `gpt-5.6-sol/luna/terra` vẫn cần **codex credentials** → hết creds = **404 `No active credentials for provider: codex`** (kể cả qua 9router) → không dùng được lúc đó.
- Model audit chạy được qua 9router lúc đó: **`ag/claude-opus-4-6-thinking`** (16/08 audit OK ~15-17 phút), `claude-sonnet-4-6`, `deepseek-v4-flash/pro`, `opencode-free`, `worker`, `plan-review(-hard)`. Lệnh chuẩn: `codex exec --ephemeral --sandbox read-only -c 'model_provider="9router"' --model ag/claude-opus-4-6-thinking < prompt.md > transcript 2>&1`. Verdict ở CUỐI file; REJECT kèm `1. P1 — path:line — desc`.
- **User rule 16/08**: audit route fail hết → dùng **Claude CLI** làm audit.

## Audit R1 (ag/claude-opus-4-6-thinking) — REJECT, 4 findings

1. **P1** — cài 0.4.45 vào hermes venv không chắc fix production path (tranh cãi env thật — xem trên; fix vững = explicit `-Python` + upgrade cả 2 env).
2. **P1** — import chain thật chưa chứng minh: phải reproduce lỗi (run-feed-session.ps1 trong clean env) trước khi fix.
3. **P2** — `scripts/sync-safe-workbook.py` import `automation_core.workbook` qua bare `$Python` — cùng rủi ro fragile env.
4. **P2** — claim cũ "HKCU Path đầu = hermes venv" bị audit bác (audit nói registry trống) — nhưng thực tế HKCU Path CÓ hermes venv Scripts; CẢ HAI phía đều thiếu probe sạch → bài học: đừng khẳng định env resolution khi chưa có probe env sạch.

## Live-wiring gap Hermes cron tiktok (đã xác nhận 16/08)

- Wrapper `scripts/hermes_cron/tiktok_{picker,runner,watcher}.py` CHƯA copy vào `%LOCALAPPDATA%\hermes\scripts` (chưa chạy `deploy_hermes_cron_wrappers.ps1`); default-off: cần `HERMES_CRON_*_ENABLED=1` hoặc permit file.
- `ProductionFeedLauncherAdapter` (`hermes_cron/runner.py:170`): `enabled=False` hardcoded, `execute()` raise RuntimeError "disabled in offline harness"; `hermes_cron_runner.py:29` parser.error refuse `--execute`/`--repo`/`--feed-workbook`.
- `hermes_cron_schedule.json` (picker `0 6 * * *`, runner `*/15 * * * *`, watcher `7,22,37,52 * * * *`) chỉ là spec — chưa create cron jobs (cronjob list chỉ có 4 job unrelated).
- Task Scheduler `TikTokScheduler` (At logon, `-m scheduler --live --poll-seconds 30`) vẫn là nguồn chạy; từ 14/08 mọi slot FAILED ImportError → follow hook chết theo (follow chỉ chạy trong feed flow `multi_machine_feed_session.py:500` → `tiktok-follow\follow_runner\run_follow.py`). 2 process scheduler sống song song: automation env python + Python312 (`-m scheduler --live`).