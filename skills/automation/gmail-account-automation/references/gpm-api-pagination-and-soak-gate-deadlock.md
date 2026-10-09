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

## 3. Playwright Google 2FA Challenge Loop Guard
- **Pitfall**:
  Khi tự động hóa bật 2FA tại `myaccount.google.com/two-step-verification/authenticator`:
  Sau khi submit form mật khẩu (`#passwordNext`), trang có thể vẫn giữ URL dạng `challenge/pwd` trong khi chuyển tiếp sang thử thách tiếp theo (reCAPTCHA, thông báo điện thoại, hoặc xác minh danh tính).
  Nếu vòng lặp thử lại kiểm tra `if "challenge/pwd" in page.url` mà gọi thẳng `page.locator('input[type="password"]').fill(pwd)` mà không kiểm tra trường input có hiển thị hay không, Playwright sẽ bị treo chờ locator 35 giây dẫn đến `Timeout 35000ms exceeded`.
- **Rule**:
  Luôn bọc kiểm tra `pwd_inp.count() > 0 and pwd_inp.is_visible()` trước khi `.fill()`, và ghi nhận rõ trạng thái màn hình nếu Google chuyển hướng sang bước thử thách bảo mật phụ.
