# Clean Environment Invocation for Subprocess Canary & Pytest

Khi điều phối worker hoặc chạy test/canary trong môi trường Windows:
1. **Lỗi `_imaging` từ PIL:** Hermes process tự động export `PYTHONPATH` và `VIRTUAL_ENV` của hermes-agent.
2. **Kỷ luật chạy lệnh:**
   - Khi chạy lệnh PowerShell:
     ```bash
     env -u PYTHONPATH -u VIRTUAL_ENV powershell.exe -ExecutionPolicy Bypass -Command "$env:PYTHONPATH=''; $env:VIRTUAL_ENV=''; powershell.exe -ExecutionPolicy Bypass -File 'D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1' -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Python 'C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe' -Run"
     ```
   - Khi chạy Python unit test:
     Chạy trực tiếp qua binary Python hệ thống `C:/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe` với `workdir` chỉ định chính xác repo root để `sys.path` không bị dính packages lạ.
