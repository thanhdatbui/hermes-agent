# TikTok Reg with Gmail Provider & Rotation Lock Hardening (2026-08-18)

## 1. Portrait Lock Hardening (Samsung TouchWiz / Android 8.0)
- **Problem**: Calling `settings put system accelerometer_rotation 0` gets silently overwritten to `1` by Samsung TouchWiz when opening certain full-screen Activities/WebViews (e.g. Gmail welcome/onboarding tour).
- **Fix**: Write directly to the settings content provider:
  ```bash
  content insert --uri content://settings/system --bind name:s:accelerometer_rotation --bind value:i:0
  content insert --uri content://settings/system --bind name:s:user_rotation --bind value:i:0
  ```
  Integrated into `automation_core.startup.lock_portrait_rotation`.

## 2. VPN Gate Policy (Proxy vs Unmapped Direct IP)
- **Mapped Proxy**: If the machine's serial has a non-empty `proXy` cell in `PROXYgandienthoai.xlsx`, VPN (`tun0` UP) is mandatory (`vpn_required = True`).
- **Unmapped Proxy**: If the machine has no proxy configured (empty / None, e.g. M77, M78, M79), direct IP is allowed (`vpn_required = False`).
- **Case Sensitivity**: Core returns lowercase `'connected'`, consumer must compare `status_res.upper() in ("OK", "PASSED", "CONNECTED", "BYPASSED_UNMAPPED")`.

## 3. TikTok Navigation from Home Feed
- If TikTok opens on Home Feed (videos playing) instead of directly on onboarding, inspect bottom navigation:
  - If `Hồ sơ` (Profile) tab exists -> `go_to_profile()` -> `open_account_dropdown()` -> `tap_add_account()` -> `choose_email_login()` ("Tiếp tục với email").
  - Do NOT assume a machine on Home Feed is a fresh install without profile navigation.

## 4. Gmail OTP Retrieval & Auto-Sync Gotcha
- Reading OTP from Gmail app (`_try_get_otp_gmail_app`) can timeout if:
  - Gmail app has "Auto-sync" disabled for the account or shows "Không có kết nối" / "Tính năng tự động đồng bộ hóa đang tắt".
  - Searching "TikTok" or "verification" returns no results until the inbox is explicitly refreshed (pull-to-refresh or master sync enabled).
