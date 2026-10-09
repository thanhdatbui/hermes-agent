# GPM Profile Nurture Preflight & Reporting Discipline

## 1. Bối cảnh & Mục đích
Khi tự động hóa nuôi định kỳ (nurture) profile trình duyệt GPM (xem YouTube, lướt Google News, Google Search), mục tiêu là bồi trust score và duy trì cookie cho tài khoản Google thật.
Nếu profile chưa đăng nhập Google (hoặc đã văng session), toàn bộ hành vi duyệt web chỉ bồi vào Cookie khách vãng lai (Guest/Anonymous), hoàn toàn không có giá trị nuôi tài khoản, đồng thời gây lãng phí băng thông proxy 4G và tài nguyên máy trạm.

## 2. Quy tắc Preflight Kiểm Tra Session (2 Lớp Bảo Vệ)
1. **Lớp 1 - Quét Offline SQLite (Fast Filter O(1) tại Candidate Selection):**
   - Trước khi cấp phát slot, chọn ứng viên nuôi (`target_profiles`), khởi động Chromium hay tiêu tốn proxy, script BẮT BUỘC đọc file SQLite cookie của từng profile trong thư mục GPM: `<profile_dir>/Default/Network/Cookies` (hoặc `Default/Cookies`).
   - Mở file dạng read-only: `sqlite3.connect("file:<path>?mode=ro", uri=True)`.
   - Điều kiện session Google sống:
     ```sql
     SELECT count(*) FROM cookies 
     WHERE host_key LIKE '%google.com' 
       AND name IN ('SID', 'SSID', 'HSID', 'SAPISID');
     ```
   - Chỉ coi profile hợp lệ khi đếm được **>= 2 cookie**.
   - **Ghi nhận trạng thái ngay khi lọc:** Nếu `< 2`, loại trừ ngay khỏi danh sách ứng viên nuôi (`continue`), đồng thời cập nhật ngay vào state:
     ```python
     update_profile_state(email, {
         "status": "NEEDS_LOGIN",
         "profile_id": p.get("id"),
         "last_checked": now_ts
     })
     log_telemetry_metric("preflight_cookie_rejected", {"email": email, "status": "NEEDS_LOGIN"})
     ```
   - Việc này ngăn chặn triệt để tình trạng cron nuôi bốc trúng 6 profile mất cookie liên tiếp khiến batch tốn hàng chục giây/phút bật tắt browser vô ích (`Hoàn tất nuôi 0/6 profile: NEEDS_LOGIN`).

2. **Lớp 2 - Live In-Browser CDP Validation:**
   - Ngay khi Playwright gắn vào CDP port của profile, kiểm tra trực tiếp context cookie trước khi thực thi bất kỳ tác vụ nào:
     ```python
     live_cookies = context.cookies(["https://accounts.google.com", "https://www.youtube.com", "https://google.com"])
     found = {c.get("name") for c in live_cookies if c.get("name") in ('SID', 'SSID', 'HSID', 'SAPISID')}
     if len(found) < 2:
         # Dừng nuôi ngay, ghi nhận trạng thái 'NEEDS_LOGIN'
         log_telemetry_metric("profile_session_lost", {"email": email, "status": "NEEDS_LOGIN", "tokens_found": len(found)})
         update_profile_state(email, {
             "last_checked": time.time(),
             "status": "NEEDS_LOGIN",
             "profile_id": p_id
         })
         browser.close()
         return False, "NEEDS_LOGIN"
     ```
   - Khi phát hiện mất phiên, ghi trạng thái `status: "NEEDS_LOGIN"` vào state JSON để pipeline login xử lý, không tiếp tục nuôi vô ích.

## 3. Cơ Chế Auto-Heal Cứu Profile Văng Session (Bridge sang Watchdog Login)
Hệ thống kết nối trực tiếp giữa Cron nuôi (`cron_gpm_gmail_nurture.py`) và Watchdog cứu đăng nhập (`post_evening_gpm_login_watchdog.py`, job id `30ffbf1672e7`):
1. **Lịch quét cứu hộ**: Chạy định kỳ `*/5 7,8,12,13,20,21,22,23 * * *` (các khung giờ chuyển ca Sáng 07:15–08:45, Trưa 12:00–13:45, Tối 20:15–23:45).
2. **Ưu tiên 1 (Priority 1 Dispatch)**:
   - Watchdog tự động đọc `D:/Taadaa/runtime/kibe/cron-state/gpm_gmail_nurture_state.json`.
   - Bất kỳ tài khoản nào mang trạng thái `"status": "NEEDS_LOGIN"` được xếp ngay vào **Priority 1 (`reason: "nurture_reported_needs_login"`)**.
   - Tài khoản này được **bypass kiểm tra trùng lặp trong ngày (`seen_emails`)** để được cứu ngay trong ca hiện tại.
3. **Thực thi phục hồi tự động**:
   - Tự động gọi `run_oauth_s7_pipeline.py <email>` (lấy mật khẩu Master Excel, giải mã 2FA TOTP, bypass audio reCAPTCHA).
   - Khi thành công: Cập nhật `GroupId = 10` trong SQLite GPM, chuyển state thành `"status": "LOGIN_RECOVERED"`, chuyển sang trạng thái ngâm (`GPM_SOAKING`) sẵn sàng cho ca nuôi tiếp theo.

## 4. An Toàn Đa Luồng Cho Telemetry JSONL
Khi cron nuôi chạy với concurrency (`--concurrency > 1`), việc ghi log telemetry có cấu trúc JSONL (`batch_gpm_supervisor_telemetry.jsonl`) bắt buộc phải bọc qua mutex lock:
```python
_telemetry_lock = threading.Lock()

def log_telemetry_metric(event_type: str, data: dict):
    metric = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "pid": os.getpid(),
        "data": data
    }
    logger.info(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}")
    try:
        TELEMETRY_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _telemetry_lock:
            with open(TELEMETRY_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return metric
```
Điều này đảm bảo không bao giờ bị đứt gãy dòng (partial write / race condition) khi nhiều worker ghi đồng thời.

## 5. Kỷ luật Báo Cáo Cron & Anti-Spam Media (Gate 6)
- **Cấm bắn MEDIA trong cron định kỳ không có can thiệp sửa chữa thiết bị:**
  - Cronjob nuôi định kỳ (nurture) chạy lặp nhiều lần trong ngày (mỗi 2 tiếng). TUYỆT ĐỐI KHÔNG in `MEDIA:<path>` ra stdout của cron report để tránh làm ngập (spam) nhóm Telegram.
  - Ảnh screenshot nghiệm thu (nếu có) chỉ lưu cục bộ tại thư mục debug (`D:\Taadaa\GPM auto\debug_screenshots`) để tra cứu khi có sự cố.

## 6. Tối ưu Thời Điểm Chụp Ảnh Debug YouTube
- **Tránh chụp ở giây thứ 1-5:** YouTube luôn có video quảng cáo preroll (5s - 15s) trước khi xuất hiện nút Skip Ad. Chụp ở giây thứ 2 chỉ ghi nhận màn hình quảng cáo hoặc nút "Đăng nhập", gây hiểu lầm là logic Skip Ad bị lỗi.
- **Thời điểm chụp chuẩn:**
  - Chụp sau khi video chính đã phát ổn định (từ giây thứ 25 trở đi của `watch_duration`).
  - Hoặc sau khi đã hoàn tất bước xử lý quảng cáo (Smart Ad Skip).
