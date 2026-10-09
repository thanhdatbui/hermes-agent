# GPM Gmail Nurture: Preflight Cookie Guard O(1) & Auto-Heal Relogin Recovery Loop

## 1. Bản chất sự cố & Cạm bẫy giả định (False Assumption Trap)
- **Bẫy ngầm**: Giả định rằng mọi profile nằm trong `GroupId = 10` (`Google_Live_Ready`) đều là tài khoản sống có sẵn session cookie Google.
- **Thực tế vận hành**:
  - Session cookie Google có thể bị hết hạn, bị thu hồi từ thiết bị chính (S7), hoặc bị văng session ngẫu nhiên (ví dụ: trong 76 profile Group 10 có tới 27 profile bị mất cookie).
  - Nếu kịch bản nuôi (`cron_gpm_gmail_nurture.py`) không tiền kiểm soát cookie trước khi khởi động trình duyệt:
    1. Script tuần tự gọi GPM API `start` -> khởi chạy Chromium -> kết nối Playwright qua CDP (mất 10-15s/profile).
    2. Sau khi đã tốn tài nguyên và thời gian mở trình duyệt, Playwright mới kiểm tra `context.cookies()` và thấy 0 token Google.
    3. Cảnh báo `NEEDS_LOGIN` và tắt trình duyệt.
    4. Hậu quả: Toàn bộ batch (ví dụ 6 profile) tốn gần 8-10 phút chạy mở/tắt liên tục mà kết quả nuôi đạt 0/6 (`CHƯA_LOGIN (NEEDS_LOGIN)`).

---

## 2. Giải pháp chuẩn hóa: Preflight Cookie Guard O(1) trên đĩa
Tuyệt đối **KHÔNG** khởi chạy GPM hay mở Playwright Chromium chỉ để kiểm tra trạng thái đăng nhập Google.

### Cơ chế kiểm tra SQLite trực tiếp:
- Đọc file cookie SQLite trực tiếp tại đường dẫn:
  `<GPM_PROFILE_BASE>/<profile_path>/Default/Network/Cookies` (hoặc fallback `Default/Cookies`).
- Sử dụng URI mode đọc an toàn `file:<path>?mode=ro`:
  ```python
  import sqlite3
  from pathlib import Path

  GPM_PROFILE_BASE = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile")

  def has_google_session(profile_path: str) -> bool:
      if not profile_path:
          return False
      base = GPM_PROFILE_BASE / profile_path
      for cp in (base / "Default" / "Network" / "Cookies", base / "Default" / "Cookies"):
          if cp.exists():
              try:
                  conn = sqlite3.connect(f"file:{cp}?mode=ro", uri=True)
                  cur = conn.cursor()
                  cur.execute(
                      "SELECT count(*) FROM cookies WHERE host_key LIKE '%google.com' "
                      "AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')"
                  )
                  cnt = cur.fetchone()[0]
                  conn.close()
                  return cnt >= 2
              except Exception:
                  pass
      return False
  ```
- **Tốc độ**: Quét toàn bộ 76-300 profile chỉ mất **0.05 giây**.
- **Xử lý khi thiếu cookie (< 2 token)**:
  1. Loại bỏ profile ngay tại khâu tiền lọc (`filter_nurture_candidates`), không bao giờ đưa vào danh sách `target_profiles`.
  2. Tự động cập nhật `status = "NEEDS_LOGIN"` vào `gpm_gmail_nurture_state.json`.

---

## 3. Luồng tự động cứu profile văng session (Auto-Heal Recovery Loop)
Hệ thống phối hợp khép kín giữa watchdog nuôi và watchdog login:

1. **Ghi nhận mất phiên**:
   `cron_gpm_gmail_nurture.py` đánh dấu `"status": "NEEDS_LOGIN"` vào `gpm_gmail_nurture_state.json`.
2. **Tiếp nhận & Ưu tiên tối đa (Priority 1)**:
   - Watchdog `post-evening-gpm-login-watchdog` (chạy tự động trong các khung giờ rảnh sau ca Sáng 07:15–08:45, ca Trưa 12:00–13:45, ca Tối 20:15–23:45) tự động quét file state này.
   - Các acc `NEEDS_LOGIN` được xếp vào **Ưu tiên 1 (`nurture_reported_needs_login`)**.
   - BẮT BUỘC cho phép các tài khoản này **bypass qua danh sách đã xử lý trong ngày (`seen_emails`)** để được cứu ngay trong ca hiện tại.
3. **Thực thi Re-login an toàn**:
   - Chạy pipeline `run_oauth_s7_pipeline.py <email>`:
     - Tự động lấy mật khẩu từ Master Excel.
     - Lấy mã 2FA TOTP hoặc tương tác xác nhận prompt trên S7.
     - Tự động giải audio reCAPTCHA nếu gặp challenge.
4. **Phục hồi & Trả về hàng đợi**:
   - Khi login thành công: cập nhật `GroupId = 10` trong SQLite GPM, chuyển trạng thái thành `"status": "LOGIN_RECOVERED"`.
   - Đưa profile vào trạng thái ngâm (`GPM_SOAKING`) để cron nuôi tiếp tục chăm sóc ở ca tiếp theo mà không gây gián đoạn.
