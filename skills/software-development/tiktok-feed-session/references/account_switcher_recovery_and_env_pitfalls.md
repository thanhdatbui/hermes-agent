# Account Switcher Recovery & Environment Pitfalls (2026-09-06)

## 1. Hermes Terminal PYTHONPATH Poisoning Fix
- **Hiện tượng:** Khi chạy `powershell.exe -File run-feed-session.ps1` hoặc `python run_tiktok.py` từ Hermes Agent terminal, gặp lỗi:
  ```
  ImportError: cannot import name '_imaging' from 'PIL' (C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages\PIL\__init__.py)
  ```
- **Nguyên nhân:** Session terminal của Hermes Agent inject `PYTHONPATH` trỏ vào venv của Hermes agent (`.../hermes-agent/venv/Lib/site-packages`). Các tiến trình Python con bị ép load PIL từ venv này nhưng binary C-extension không tương thích với Python runtime ngoài.
- **Cách xử lý chuẩn:**
  Dùng `env -u PYTHONPATH` khi gọi powershell / python từ terminal:
  ```bash
  env -u PYTHONPATH powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row <R> -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
  ```

## 2. Account Switcher Missing Expected Recovery
- **File phụ trách:** `D:\Taadaa\tiktok-luot nuoi acc\python_runner\flows\feed_swipe_smoke.py`
- **Hàm:** `_is_account_switcher_missing_expected_reason(reason: str | None) -> bool`
  Cần bao gồm cả chuỗi `"profile username still mismatched after switch"`:
  ```python
  def _is_account_switcher_missing_expected_reason(reason: str | None) -> bool:
      r = str(reason or "").lower()
      return "account-switcher-missing-expected" in r or "profile username still mismatched after switch" in r
  ```
  Điều này giúp flow nhận diện được trường hợp đã switch nhưng username trên profile vẫn không khớp để kích hoạt recovery login fallback thay vì coi là hard blocker dừng luôn session.

## 3. Account Switch Transition Settle Time
- **Hàm:** `verify_and_switch_profile(...)`
- Sau khi tap lựa chọn tài khoản từ switcher popup, TikTok cần thời gian chuyển cảnh và cập nhật lại view profile.
- Tăng settle delay từ `time.sleep(random.uniform(2.0, 3.0))` lên `time.sleep(random.uniform(3.5, 5.0))` trước khi gọi `_navigate_profile_for_preflight` và đọc lại profile identity.
