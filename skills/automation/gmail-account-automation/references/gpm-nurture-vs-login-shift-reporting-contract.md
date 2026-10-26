# GPM Gmail Nurture vs Login Shift Reporting & Telemetry Contract

## 1. Phân định vai trò Nurture Runner vs Login Watchdog
- **`cron_gpm_gmail_nurture.py` (Nurture Runner, schedule `0 * * * *`):**
  - Thực hiện hành vi nuôi tuần tự (YouTube / Google Search / Google News) qua Playwright CDP trên GPM profiles Group 10.
  - Preflight Cookie Guard: Kiểm tra cookies `SID`, `SSID`, `HSID`, `SAPISID`. Nếu `< 2` tokens -> đánh dấu `NEEDS_LOGIN` vào `gpm_gmail_nurture_state.json`.
  - Hạn ngạch an toàn: `MAX_DAILY_NURTURE = 30` profile/ngày.
  - Cách tính hạn ngạch ngày chuẩn xác: Duyệt qua `state.values()`, kiểm tra `datetime.fromtimestamp(last_nurtured).date() == today`. Runner **KHÔNG** ghi key `_daily_stats`.

- **`cron_gpm_gmail_nurture_6h_report.py` (6H Nurture Report, schedule `0 */6 * * *`):**
  - Báo cáo định kỳ gửi về Telegram kênh GPM Reports (`telegram:-5256944036`).
  - **Bẫy hiển thị trần an toàn (Daily Count Trap):** Tuyệt đối không chỉ đọc `state.get("_daily_stats")` vì runner chính không lưu key này, dẫn đến báo cáo sai lệch `Tiến độ trần an toàn hôm nay: 0/30` dù đã nuôi đủ 30 acc.
  - **Chuẩn hóa:** Bắt buộc cài đặt hàm `count_nurtured_today(state, now_ts)` quét timestamp `last_nurtured` khớp `datetime.date.today()` tương tự runner chính.

- **`post_evening_gpm_login_watchdog.py` (Login Watchdog, ca rảnh 09:30, 15:30, 21:30):**
  - Chịu trách nhiệm thực hiện login thật cho các acc mới hoặc acc văng cookie (`NEEDS_LOGIN`).
  - Có cơ chế miễn trừ cooldown 24h proxy cho acc re-login (`is_relogin = True`).

## 2. Chuẩn hóa Báo cáo Thất bại Login (Anti-Blindspot)
- **Vấn đề:** Nếu chỉ in `[LOGIN GPM - TỔNG KẾT] • Kết quả ca: ✓ X | ✗ Y`, điều phối viên và user bị mù hoàn toàn danh tính tài khoản thất bại và nguyên nhân.
- **Contract chuẩn cho `_format_summary_report`:**
  - Thu thập danh sách `failed_details` gồm `{"email": ..., "fail_type": ..., "mid": ...}` trong suốt ca chạy và lưu vào `state`.
  - Định dạng hiển thị bắt buộc:
    ```text
    ⚠️ Chi tiết N acc thất bại:
      - email1@gmail.com (PLATFORM - SMS_CHECKPOINT)
      - email2@gmail.com (SCRIPT - TIMEOUT)
    ```
  - Phân loại lỗi chuẩn:
    + `PLATFORM`: Google challenge, hard phone, recaptcha, rejected -> tính vào quota proxy.
    + `SCRIPT`: Mất kết nối local, lỗi mở GPM profile, thiếu mật khẩu Excel -> không phạt proxy, cho phép thử lại.
