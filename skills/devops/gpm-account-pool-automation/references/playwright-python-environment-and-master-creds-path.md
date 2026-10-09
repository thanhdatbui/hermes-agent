# Môi Trường Python Playwright & Đường Dẫn Master Creds

## 1. Môi trường Python chạy Playwright CDP (`run_oauth_s7_pipeline.py`, `cdp_stealth_login_and_oauth.py`)
- **Vấn đề**:
  - Python mặc định của session Hermes bị lỗi binary C-extension greenlet (`ModuleNotFoundError: No module named 'greenlet._greenlet'`).
  - Python trong venv automation-core (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) thiếu thư viện `playwright`.
- **Python chuẩn**:
  - Máy chủ Kibe có Python 3.12 cài sẵn Playwright 1.62.0 tại:
    `C:\Users\Kibe\AppData\Local\Programs\Python\Python312\python.exe`
  - Vì Hermes session tự động inject `PYTHONPATH` vào global environment, nếu không strip `PYTHONPATH` thì Python 3.12 vẫn import nhầm module lỗi từ Hermes venv.
- **Lệnh thực thi chuẩn**:
  ```bash
  env -u PYTHONPATH /c/Users/Kibe/AppData/Local/Programs/Python/Python312/python.exe <script.py> [args]
  ```

## 2. Đường dẫn Master Gmail Manager
- **File**: `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx`
- **Sheet S7**: `Kibe_Farm_S7`
- **Cấu trúc cột**:
  - Cột B (`r[1]`): Email (ví dụ: `trieutruc05051997@gmail.com`)
  - Cột C (`r[2]`): Password
  - Cột D (`r[3]`): Recovery email
  - Cột E (`r[4]`): TOTP secret (2FA)
- Helper truy xuất có sẵn: `from run_oauth_s7_pipeline import get_creds`.
