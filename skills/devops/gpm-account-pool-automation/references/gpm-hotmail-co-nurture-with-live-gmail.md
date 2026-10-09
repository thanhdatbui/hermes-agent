# Ngâm Hotmail Kết Hợp Nuôi Profile GPMLogin Có Sẵn Google Session

## 1. Ràng Buộc Preflight Cookie Guard Trong Script Nuôi GPM
- Script nuôi tự động `cron_gpm_gmail_nurture.py` kiểm tra live session Google trước khi thực hiện lướt web/YouTube:
  ```python
  live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
  found_session = {c.get("name") for c in live_cookies if c.get("name") in ("SID", "SSID", "HSID", "SAPISID")}
  if len(found_session) < 2:
      logger.warning(f"[{email}] CẢNH BÁO: Profile chưa có acc Google hoặc mất session -> Dừng nuôi!")
      return False, "NEEDS_LOGIN"
  ```
- Nếu gán Hotmail vào profile GPM chưa có Google session sống thật sự: Profile sẽ bị dừng nuôi ngay ở preflight, cookie Hotmail không bao giờ được lướt web và không thể tích lũy trust 7 ngày.

## 2. Quy Chuẩn Nạp Hotmail Vào Profile Đã Có Sẵn Gmail
1. Truy xuất danh sách profile Google LIVE từ `gpm_gmail_nurture_state.json` (`status == 'success'`).
2. Mở Profile qua GPM Local API (`19995`), kết nối CDP Playwright.
3. Đăng nhập `login.live.com`, chọn **KMSI Yes** (Duy trì đăng nhập) để lưu Cookie.
4. Ghi nhận `eligible_change_pass_date` (now + 7 days) vào `gpm_hotmail_nurture_tracker.json`.
5. Đợi đủ 7 ngày nuôi song song cùng Gmail trước khi tiến hành đổi mật khẩu.
