# Canary Test Execution & Account Switcher Recovery Guidelines

## 1. Tránh nhiễm bẩn PYTHONPATH từ Hermes Shell
Khi chạy Canary test hoặc script runner từ terminal của Hermes:
- **Hiện tượng:** Shell của Hermes Agent thường inject `PYTHONPATH` chứa đường dẫn venv Python 3.11 của Hermes (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`). Trong khi đó, hệ điều hành và farm script chạy trên Python 3.12 (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`).
- **Lỗi phát sinh:** Khi `run-feed-session.ps1` hoặc `python run_tiktok.py` được gọi, Python 3.12 load nhầm binary wheel `.pyd` biên dịch cho Python 3.11 trong `PYTHONPATH`:
  ```text
  ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
  ```
- **Cách xử lý chuẩn:** Luôn chỉ định rõ `-Python "D:\Taadaa\python-envs\automation\Scripts\python.exe"` và chạy lệnh Canary test / PowerShell với `PYTHONPATH` rỗng:
  ```bash
  env PYTHONPATH="" powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
  Hoặc trong PowerShell context:
  ```powershell
  $env:PYTHONPATH = ""
  powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" `
    -Python "D:\Taadaa\python-envs\automation\Scripts\python.exe" `
    -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```
  *(Lưu ý: Không bỏ qua `-Python`, vì mặc định `$Python = "python"` sẽ gọi nhầm WindowsApps stub hoặc Hermes venv thiếu `automation_core`).*

## 2. Quy tắc xử lý Account Switcher Modal khi thiếu Account
Trong flow `verify_and_switch_profile` (`python_runner/flows/feed_swipe_smoke.py`):
- **Vấn đề:** Khi mở switcher modal mà không tìm thấy account mong đợi (`_is_account_switcher_missing_expected_reason(last_reason)`: `account-switcher-missing-expected` hoặc `profile username still mismatched after switch`), modal switcher vẫn mở che phủ toàn bộ màn hình.
- **Hậu quả:** Nếu gọi auto-login reconcile (`_maybe_recover_missing_account_via_login`) hoặc thoát flow mà modal chưa đóng, flow login/recovery hoặc thao tác UI tiếp theo sẽ bị tap nhầm vào modal hoặc bị modal chặn UI.
- **Giải pháp chuẩn:**
  1. Ghi nhận log action `dismiss_switcher_on_missing_account`.
  2. Gửi phím BACK (`ctx.adb.shell(["input", "keyevent", "4"])`) và sleep 1.0s để modal biến mất hoàn toàn.
  3. Sau đó mới gọi `_maybe_recover_missing_account_via_login` (nếu `allow_auto_reconcile=True`) hoặc trả row status `MANUAL_NEEDED`.
