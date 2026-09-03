# Tiktok_Reg relaunch: concurrency-gate self-block + OTP newest-mail + resume-vs-restart (2026-08-11)

## Triệu chứng khi chạy lại `social_reg_v1.py 30 --resume`

1. `[device-lock] SKIP ... device lock active: path=...machine_30.lock.json pid=<dead>` — lock file
   cũ (status=`handoff`, `owner_active=false`, PID đã chết) vẫn nằm ở
   `C:\Users\Kibe\.codex\device-locks\{machine_<stt>,serial_<serial>}.lock.json`.
2. Sau khi xoá lock, chạy lại → `✗ STOPPED: [gate] MACHINE_IN_USE` dù KHÔNG có worker nào thật.

## Root cause gate self-block (không phải lock tự sinh)

- `preflight_concurrency_gate` → `_list_external_automation_processes` (powershell `Get-CimInstance
  Win32_Process`) → `_filter_external_automation_processes` loại trừ `_current_process_tree_pids`
  (walk chain ppid từ `os.getpid()`).
- Chạy qua `env -u PYTHONPATH .../python` trong git-bash: MSYS chèn process `env.exe` trung gian
  (bash → env.exe → python). Chain-walk gặp PID không có trong scan (env.exe) là dừng sớm → bash
  wrapper CHA (cmdline chứa `social_reg_v1.py 30`) KHÔNG được loại trừ → gate BLOCK chính lệnh
  đang chạy. Minh chứng log:
  `[gate] BLOCK pid=<bash-wrapper-pid> reason=MACHINE_IN_USE cmd="...bash.exe" -lic "...social_reg_v1.py 30..."`
- Bash wrapper treo từ background run cũ (`2>&1 | tail -150` giữ bash sống sau khi python thoát)
  có cùng cmdline → cũng bị tính là conflict.

## Cleanup + relaunch an toàn (đã chạy thành công)

```bash
# 1. Dọn MỌI process có cmdline khớp script (kể cả bash wrapper treo)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match 'social_reg_v1\.py' } | ForEach-Object { try { Stop-Process -Id \$_.ProcessId -Force -ErrorAction Stop } catch {} }"
# 2. Xoá lock handoff PID chết (cả 2 alias machine + serial)
rm -f ~/.codex/device-locks/machine_30.lock.json ~/.codex/device-locks/serial_<serial>.lock.json
# 3. Chạy KHÔNG qua env — dùng bash assignment để python là con TRỰC TIẾP của bash wrapper
cd /d/Taadaa/Tiktok_Reg && PYTHONPATH= /d/Taadaa/python-envs/automation/Scripts/python -u social_reg_v1.py 30 --resume --ss --defer-tracking-write
```

`PYTHONPATH= cmd` (bash assignment) ≠ `env -u PYTHONPATH cmd` (env.exe): cái trước giữ chain ppid
→ gate loại trừ đúng wrapper của mình. Nếu vẫn cần chờ, `process(action="wait")` giới hạn 60s/lần.

## OTP newest-mail reader (patch đã verify)

- Reader Hotmail/Outlook dùng `_outlook_newest_tiktok_row` — chọn mail TikTok MỚI NHẤT theo
  time/order evidence, KHÔNG quét DOM tùy tiện lấy code mail cũ (trước đó đọc mail cũ → nhập code
  cũ → reject loop). Log chuẩn:
  `[otp-newest] Newest TikTok row: bounds=[...] time_evidence=Y reason=newest-first DOM row with time token`
- Mail mới nhất KHÔNG có code 6 số → fail-closed đúng (không nhập code cũ).
- Resend node không tìm thấy → `FINAL_BLOCKED OTP_RESEND_NODE_MISSING` — thường vì màn OTP đã
  thoát (máy về feed account cũ). Evidence: `blocked_30_otp_otp_resend_node_missing_*.png`.

## Resume-vs-restart (giới hạn quy tắc "cấm restart mid-flow")

- "Reg mid-flow: CẤM restart — dùng `--resume` tại màn" CHỈ áp dụng khi màn target còn đó
  (vd `CommonFlowActivity` nhập mã còn focus).
- Khi flow đã thoát hẳn (máy về `MainActivity` feed của account CŨ khác, màn CommonFlowActivity
  biến mất) → không còn mid-flow nữa → `--resume` vô dụng, restart flow từ đầu là lựa chọn duy
  nhất. Kiểm tra bằng `dumpsys window | grep mCurrentFocus` + mở profile xem account đang login
  (content-desc `Hồ sơ <tên>` / username @...).

## Repo/machine scope (user correction)

Chat TG gắn 1 repo: chỉ báo/xử lý máy thuộc repo đó — m30 reg = repo `Tiktok_Reg`,
m74 upload = repo `Tiktok-video`. Không lôi trạng thái repo khác vào status report của chat này
(user: "đây repo tiktok reg thì xử lý 30 thôi còn 74 bên repo tiktopk upload ai mươn m gọi").