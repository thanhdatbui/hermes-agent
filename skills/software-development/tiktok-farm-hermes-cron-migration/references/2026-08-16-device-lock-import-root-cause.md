# 2026-08-16 — DeviceLockNeedsUserDecision ImportError root cause

## Symptom
Mọi slot feed FAILED từ 14/08 (row 1-6, ca 06:00/12:00/17:00):
`ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\automation_core\device_lock.py)`
Log thật: `python_runner/runs/launcher/20260816-*.log`, `python_runner/runs/scheduler.jsonl`.

## Chuỗi gọi (đã verify từng mắt xích)
1. `TikTokScheduler` (Windows Task Scheduler, At logon) → powershell → `& $Python -m scheduler --live` + launcher chạy `scripts/run-feed-session.ps1 -Preset full -Row N -Run`.
2. `run-feed-session.ps1:34`: `[string]$Python = "python"` → `& $Python @arguments` (bare python).
3. Task Scheduler spawn với PATH = HKCU user env → `HKCU:\Environment Path` có `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts` **ĐẦU TIÊN** → bare `python` = hermes venv.
4. hermes venv có automation_core **0.4.43** (thiếu class) → ImportError.
5. `python_runner/core/device_lock.py` chỉ là compatibility wrapper import từ `automation_core.device_lock` — KHÔNG phải nguồn lỗi.

## Version matrix automation_core (verify 16/08 bằng python -c từng env)
| Interpreter | Version | DeviceLockNeedsUserDecision |
|---|---|---|
| hermes venv (`hermes-agent\venv`) | 0.4.43 | KHÔNG |
| Python312 global (`AppData\Local\Programs\Python\Python312`) | 0.4.44 (wheel từ automation-core/dist) | KHÔNG |
| python-envs/automation | 0.4.45 (wheel từ automation-core-user-lock-gate-wt/dist) | CÓ |
| automation-core repo HEAD (d0bab14 feat device-lock) | — | CÓ |

## Vì sao shell agent ≠ Task Scheduler (PITFALL lớn nhất)
- Bash MSYS session: `which python` → Python312 (PATH session MSYS riêng) → suy luận sai hướng fix (tưởng cài vào Python312 là đủ).
- Task Scheduler: PATH = HKCU user env → hermes venv trước.
- **Ground truth = path interpreter trong traceback của log thật** (`python_runner/runs/launcher/*.log`), không phải `which python` của shell mình.

## Wheel diff 0.4.44 → 0.4.45 (additive check — chạy trước khi quyết pin)
```bash
unzip -oq /d/Taadaa/automation-core/dist/automation_core-0.4.44-py3-none-any.whl -d /tmp/w44
unzip -oq /d/Taadaa/automation-core-user-lock-gate-wt/dist/automation_core-0.4.45-py3-none-any.whl -d /tmp/w45
diff <(cd /tmp/w44 && find automation_core -name '*.py' | sort) <(cd /tmp/w45 && find automation_core -name '*.py' | sort)  # thêm adapters.py, escalation.py
for v in 44 45; do grep -rhoE '^class [A-Za-z_]+' /tmp/w$v/automation_core --include='*.py' | sort -u > /tmp/allcls_$v.txt; done
diff /tmp/allcls_44.txt /tmp/allcls_45.txt   # CHỈ THÊM class
for v in 44 45; do grep -rhoE '^def [A-Za-z_]+' /tmp/w$v/automation_core --include='*.py' | sort -u > /tmp/alldef_$v.txt; done
diff /tmp/alldef_44.txt /tmp/alldef_45.txt   # KHÔNG XÓA hàm nào
grep -iE 'Requires-Dist' /tmp/w4*/automation_core-*.dist-info/METADATA  # không dep mới
```
Kết quả 16/08: thêm DeviceLockNeedsUserDecision, DeviceLockOpenAudit, _UnlockedDeviceLockLease, escalation.py (EscalationError/Hook/Outcome/Registry/Result), adapters.py (ConsumerRecoveryAdapter), NonRetryableFailureError, RecoveryBudgetExhaustedError. 0 hàm xóa, 0 dep mới → **additive, pin an toàn**.

## Hướng fix (2 lựa chọn — đang chờ audit Sol 16/08, chưa hành động)
- **A.** Pin wheel 0.4.45 vào hermes venv (nơi bare python resolve khi Task Scheduler chạy):
  `~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe -m pip install --force-reinstall "file:///D:/Taadaa/automation-core-user-lock-gate-wt/dist/automation_core-0.4.45-py3-none-any.whl"`
  Rủi ro: hermes venv là venv agent — automation_core là dep phụ, cần verify Hermes/plugin không phụ thuộc hành vi cũ.
- **B.** Sửa `run-feed-session.ps1` default `$Python` → `D:\Taadaa\python-envs\automation\Scripts\python.exe` (tuyệt đối, hết float theo PATH). Ưu điểm: không đụng venv agent. Cần rà các nơi khác gọi bare python cho repo (scheduler tiktok-log-in / add-bao-mat-f2a / add-mail chạy Python312 0.4.44).
- Trạng thái: user yêu cầu audit độc lập TRƯỚC (`codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol` chạy nền) — không cài gì trước verdict.

## Bài học reusable (cho mọi lần "python sai version")
1. Path interpreter trong traceback log thật = ai resolve trong context runtime — đừng dùng `which python` của shell agent (MSYS PATH riêng).
2. Debug "python nào đang chạy" cho Task Scheduler → đọc `HKCU:\Environment Path` (user env), không phải PATH của terminal.
3. Trước khi pin/nâng package trên máy có nhiều env: unzip wheel + diff `^class |^def ` + METADATA → chứng minh additive trong 1 phút.
4. User rule: audit độc lập Sol trước CẢ thay đổi môi trường (pip install), không chỉ trước sửa code.