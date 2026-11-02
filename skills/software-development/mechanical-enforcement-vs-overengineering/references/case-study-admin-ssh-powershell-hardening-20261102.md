# Case Study: Admin SSH PowerShell Allowlist & Mock Hardening (2026-11-02)

## 1. Sự Cố Hiện Trường
- File `deploy/hermes-home/scripts/cron_night_tiktok_2fa_watchdog.py` cần đọc file `summary.json` từ xa trên Admin PC.
- Worker viết lệnh PowerShell gán biến ở đầu: `$min = ...; Get-Content ...`.
- Trong file unit test, Worker mock `subprocess.run` trả về text JSON $\rightarrow$ test pass 100%.
- Khi chạy thật, `admin_ssh.py` chặn ngay với exit code 2 vì `$min` không nằm trong `ALLOWED_COMMAND_PREFIXES`.

## 2. Giải Pháp Triển Khai
1. Sửa lệnh trong `cron_night_tiktok_2fa_watchdog.py` mở đầu trực tiếp bằng cmdlet `Get-Content`:
   ```powershell
   Get-Content (Get-ChildItem -Path 'D:\CodexRuntime\codex_gmail_debug-register-gmail\logs_parallel_*\summary.json' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Raw -Encoding UTF8
   ```
2. Thêm module kiểm tra offline trong `D:/Taadaa/tools/admin_ssh.py`:
   - `validate_command(cmd)`: Kiểm tra allowlist và dangerous patterns.
   - `assert_command_allowed(cmd)`: Ném AssertionError nếu lệnh vi phạm.
   - CLI flag `--check / --validate-only`: Exit code 0 nếu hợp lệ, exit code 2 nếu vi phạm.
3. Cài chốt chặn vào `tests/test_cron_night_tiktok_2fa_watchdog.py`:
   - Gọi `admin_ssh.assert_command_allowed(ps_cmd)` trước khi mock.
   - Giờ đây nếu Worker đổi câu lệnh thành cú pháp sai, test suite sẽ gãy ngay lập tức trong 0.1s offline.
