# Quy Chuẩn Ngâm Hotmail 7 Ngày Trên GPMLogin & Ràng Buộc Profile Có Sẵn Gmail

## 1. Bản Chất Cơ Chế Bảo Mật Đổi Mật Khẩu Của Microsoft (Risk Engine Cooldown)
- Khi truy cập `account.live.com/password/change` trên một trình duyệt / Profile GPM mới:
  - Dù đăng nhập email + pass đúng 100%, Microsoft coi session này là **"Thiết bị mới / Phiên đăng nhập chưa được tin cậy" (Untrusted New Browser)**.
  - Khi bấm **"Lưu"** đổi mật khẩu, server Microsoft sẽ lập tức từ chối và báo lỗi đỏ:
    > *"Tạm thời có lỗi với dịch vụ. Xin vui lòng thử lại. Nếu bạn tiếp tục thấy thông báo này, xin vui lòng thử lại vào lúc khác."*
- **Quy tắc Bắt buộc**:
  - Hotmail sau khi đăng nhập vào Profile GPM cần chọn **"Duy trì đăng nhập" (KMSI - Yes)** để lưu cookie phiên.
  - Phải ngâm (warm-up / soak) tối thiểu **7 ngày** trên Profile GPM đó có phát sinh hành vi duyệt web tự nhiên thì Microsoft mới mở khóa quyền đổi mật khẩu và "Sign out of everywhere".

## 2. Invariant: BẮT BUỘC Nạp Hotmail Vào Profile GPM ĐÃ CÓ LIVE GMAIL SESSION
- **Cạm bẫy**: Nạp Hotmail vào profile GPM chưa đăng nhập Gmail (hoặc chỉ có tên profile nhưng chưa có session Google) với hy vọng ca login đêm sẽ login bù.
- **Tử huyệt**: Script nuôi định kỳ `cron_gpm_gmail_nurture.py` có cơ chế bảo vệ `Preflight Cookie Guard`:
  ```python
  live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
  found_session = {c.get("name") for c in live_cookies if c.get("name") in ("SID", "SSID", "HSID", "SAPISID")}
  if len(found_session) < 2:
      logger.warning(f"[{email}] CẢNH BÁO: Profile chưa có acc Google hoặc mất session -> Dừng nuôi!")
      return False, "NEEDS_LOGIN"
  ```
  - Nếu profile chưa có session Google, cron nuôi sẽ **dừng nuôi ngay lập tức**, dẫn đến Profile không bao giờ được mở lướt web, cookie Hotmail bị đóng băng và không thể tích lũy trust!
- **Quy tắc Thực Thi Chuẩn**:
  1. Tra cứu `D:\Taadaa\runtime\kibe\cron-state\gpm_gmail_nurture_state.json`.
  2. Lọc danh sách các profile có `status == "success"` (đã có verified Google session, đang được cron nuôi lướt YouTube / Google News hàng ngày).
  3. Gán và đăng nhập Hotmail trực tiếp vào các profile này.
  4. Ghi nhận thời gian bắt đầu ngâm vào `gpm_hotmail_nurture_tracker.json` (`eligible_change_pass_date = now + 7 days`).
