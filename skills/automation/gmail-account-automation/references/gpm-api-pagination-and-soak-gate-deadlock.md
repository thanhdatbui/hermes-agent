# GPM Local API Pagination Pitfall & Soaking Gate Pipeline Stalls

## 1. GPM Local API Pagination Pitfall
- **Endpoint**: `GET /api/v3/profiles?page={page}&per_page={size}`
- **Response Structure**:
  ```json
  {
    "success": true,
    "data": [...],
    "pagination": {
      "total": 599,
      "page": 1,
      "page_size": 300,
      "total_page": 2
    }
  }
  ```
- **Pitfall**:
  Hardcoding `page=1&per_page=300` silently truncates profiles when the local GPM database grows beyond 300 profiles. Profiles on `page >= 2` are completely invisible to consumer loops.

- **Canonical Pattern**:
  ```python
  def get_all_gpm_profiles() -> list:
      all_profiles = []
      page = 1
      while True:
          try:
              res = requests.get(f"{GPM_API_BASE}/profiles?page={page}&per_page=300", timeout=15).json()
              data = res.get("data")
              items = data if isinstance(data, list) else (data or {}).get("list", [])
              if not items:
                  break
              all_profiles.extend(items)
              total_page = (res.get("pagination") or {}).get("total_page", 1)
              if page >= total_page:
                  break
              page += 1
          except Exception as e:
              logger.error(f"Lỗi kết nối GPM API: {e}")
              break
      return all_profiles
  ```

---

## 2. Soaking Gate Silent Pipeline Deadlock
- **Mechanism**:
  Watchdogs (e.g. `post_morning_gmail_2fa_watchdog.py`) enforce a mandatory **Soaking Gate** before enabling 2FA:
  A profile must have at least one successful nurture session logged in `gpm_gmail_nurture_state.json` (`status == "success"` and valid `last_nurtured`) before it is eligible for 2FA activation.
- **Symptom / Signature**:
  - Báo cáo 6h (`cron_gmail_gpm_2fa_6h_report.py`) bị đứng số liên tục nhiều ca:
    ```
    • Tổng số profile GPM (Group 10): 76
    • Đã bật 2FA thành công: 73/76 (96.1%)
    • Đang ngâm (chờ phiên nuôi): 3
    • Sẵn sàng bật 2FA: 0
    ⚡ Tiến độ xử lý trong 6h vừa qua: 0 sự kiện
    ```
  - Không có lỗi (0 exceptions, cron chạy bình thường), nhưng 3 tài khoản không bao giờ tiến triển vì bị lọt khỏi danh sách nuôi do lỗi phân trang.
- **Resolution**:
  - Vá vòng lặp phân trang ở tầng lấy profile.
  - Chạy canary nuôi đơn lẻ (`--email <target>`) để đưa profile qua Soaking Gate mà không cần chờ toàn bộ chu kỳ 5 ngày.

---

## 2.1. Tri-State Deadlock (`NEEDS_LOGIN` Zombie Loop & Orphaned Group 10)
- **Cơ chế bẫy vòng lặp (Circular Skip Dependency)**:
  Khi một profile GPM trong Group 10 bị rớt session Google (`has_google_session == False` trong file cookie `Default/Network/Cookies` thiếu `SID/SSID/HSID`):
  1. `cron_gpm_gmail_nurture.py` quét thấy `info.get("status") == "NEEDS_LOGIN"` -> `continue` (bỏ qua, không nuôi).
  2. `post_morning_gmail_2fa_watchdog.py` kiểm tra Soaking Gate thấy `status != "success"` -> `continue` (bỏ qua, không bật 2FA).
  3. `post_evening_gpm_login_watchdog.py` chỉ quét các tài khoản Gmail LIVE *chưa có trong Group 10* -> bỏ qua vì profile này *đã nằm trong Group 10*!
- **Hậu quả**:
  Tài khoản bị biến thành "xác sống" (zombie profile), kẹt vĩnh viễn ở trạng thái `Đang ngâm (chờ phiên nuôi): 1`. Cả 3 watchdog đều chủ động bỏ qua nó.
- **Dấu hiệu nhận biết**:
  Báo cáo `gmail-gpm-2fa-6h-report` đứng im qua nhiều ngày:
  `Đã bật 2FA thành công: 82/83 (98.8%) | Đang ngâm (chờ phiên nuôi): 1 | Tiến độ trong 6h: 0 sự kiện`.
- **Khắc phục**:
  - **Cấp bách**: Chạy luồng login khẩn cấp khôi phục session Google cho profile hoặc login bù bằng tay/script để cập nhật lại `status: "success"` sau khi nuôi 1 phiên.
  - **Tận gốc**: Bổ sung nhánh phục hồi trong `post_evening_gpm_login_watchdog.py`: nếu profile Group 10 mang cờ `NEEDS_LOGIN`, tự động đưa vào hàng đợi login làm mới session thay vì chỉ quét tài khoản mới.

---

## 2.2. Watchdog Silent Invariant & Context Triage Pitfall
- **Watchdog Silent Invariant**:
  Mọi script watchdog báo cáo định kỳ (như `cron_gmail_gpm_2fa_6h_report.py`) chạy qua cronjob `no_agent: true` BẮT BUỘC tuân thủ:
  Nếu `len(recent_6h_events) == 0` và số liệu tổng không thay đổi so với lần chạy trước, script PHẢI IM LẶNG (`sys.exit(0)`, không in ra stdout).
  Việc in báo cáo tĩnh lặp đi lặp lại khi không có tiến triển mới bị coi là vi phạm kỷ luật spam Telegram.
- **Context Triage Pitfall (Tránh ngáo ngữ cảnh khi User phản ánh)**:
  Khi User hỏi cụt lủn hoặc phàn nàn ("Sao cứ báo như v hoài thế", "sao lại lỗi này"):
  Coordinator BẮT BUỘC phải kiểm tra tin nhắn Bot/Cronjob vừa gửi đến hoặc thẻ `reply_to` trước tiên.
  TUYỆT ĐỐI CẤM nhảy ngay vào suy diễn các sự cố kỹ thuật nền (như Closeout Gate, build, worker) khi User đang phản ánh về một thông báo cron vừa nảy trên màn hình!

---

## 3. Playwright Google 2FA Challenge Loop Guard
- **Pitfall**:
  Khi tự động hóa bật 2FA tại `myaccount.google.com/two-step-verification/authenticator`:
  Sau khi submit form mật khẩu (`#passwordNext`), trang có thể vẫn giữ URL dạng `challenge/pwd` trong khi chuyển tiếp sang thử thách tiếp theo (reCAPTCHA, thông báo điện thoại, hoặc xác minh danh tính).
  Nếu vòng lặp thử lại kiểm tra `if "challenge/pwd" in page.url` mà gọi thẳng `page.locator('input[type="password"]').fill(pwd)` mà không kiểm tra trường input có hiển thị hay không, Playwright sẽ bị treo chờ locator 35 giây dẫn đến `Timeout 35000ms exceeded`.
- **Rule**:
  Luôn bọc kiểm tra `pwd_inp.count() > 0 and pwd_inp.is_visible()` trước khi `.fill()`, và ghi nhận rõ trạng thái màn hình nếu Google chuyển hướng sang bước thử thách bảo mật phụ.
