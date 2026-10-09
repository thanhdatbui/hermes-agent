# GPM OAuth Feeder: Upfront Candidate Validation, Telemetry Concurrency & Google Challenge Disambiguation

## 1. Upfront Candidate Validation (Chống Báo Động Giả Lỗi Script)

Trong các batch worker nạp OAuth Google/Antigravity từ GPM lên OmniRoute (ví dụ `cron_gpm_oauth_full_pool.py`), việc lựa chọn ứng viên phải kiểm tra điều kiện dữ liệu **ngay tại tầng `filter_candidates()`**, trước khi cấp phát proxy slot:
- **Kiểm tra Mật khẩu**: Bắt buộc kiểm tra `CredentialLookup.get(email).get("password")`. Nếu không có mật khẩu trong Excel/Database quản lý, loại bỏ ngay tại bước lọc candidate.
- **Kiểm tra Recovery Blacklist**: Nếu email khôi phục dính `khoaleemagic` (hoặc blacklist tương đương), loại bỏ ngay.
- **Hệ quả nếu không lọc upfront**: Profile không đủ điều kiện sẽ chiếm slot proxy trong batch, worker bốc trúng rồi mới skip và return `fail_type="SCRIPT"`. Điều này làm báo cáo tổng kết nhảy số "⚠️ Lỗi script: N accounts" gây hoang mang cho user, làm tưởng lầm môi trường/automation bị lỗi trong khi thực chất là dữ liệu profile không đủ điều kiện.

## 2. Telemetry State & Multi-Worker Concurrency

Khi sử dụng đa luồng (`ThreadPoolExecutor`, ví dụ 5 workers):
- **Nguyên nhân mất mát dữ liệu**: Nếu luồng chính đọc `daily_state = load_daily_state()` trước khi spawn workers, và các worker ghi sự kiện song song, sau đó luồng chính dùng lại biến `daily_state` cũ để cập nhật `used_proxies` rồi gọi `save_daily_state(daily_state)` $\rightarrow$ toàn bộ event mới ghi trong file đĩa sẽ bị ghi đè hoàn toàn bởi bản copy cũ trong RAM của luồng chính.
- **Hậu quả thực tế**: Cronjob nạp thành công 9 accounts nhưng Báo cáo 6h (`cron_gpm_oauth_pool_6h_report.py`) lại in ra `✓ Thành công: 0 accounts`, vì các event SUCCESS bị xóa mất và chỉ còn lại các event lỗi cũ.
- **Quy tắc thi công chuẩn**:
  - Toàn bộ việc ghi nhận telemetry (`events`, `used_proxies`, `success_emails`, `failed_script_emails`) phải được đồng bộ hóa tập trung tại luồng chính khi duyệt qua `as_completed(futures)`.
  - Luôn gọi `load_daily_state()` tươi mới từ đĩa trước khi append và save.

## 3. Google 2FA Disambiguation: `challenge/selection` vs `challenge/iap`

Khi tự động hóa đăng nhập Google trong GPM:
- **`challenge/selection` (Chọn cách đăng nhập)**: Google đưa ra danh sách các lựa chọn 2FA (Authenticator app, Mã bảo mật trên điện thoại S7, SMS...). **ĐÂY TUYỆT ĐỐI KHÔNG PHẢI LỖI NỀN TẢNG HAY CHECKPOINT SĐT.**
- **Cấm làm**: Không được đánh dấu `challenge/selection` là `PLATFORM_FAIL` và khóa proxy port. Điều này khiến các nick có 2FA Authenticator hoặc S7 Security Code bị dừng oan và khóa nhầm IP.
- **Hành vi chuẩn**:
  1. Khi gặp `challenge/selection`: Tìm và click selector Authenticator (`div[data-challengetype="6"]`, text "Authenticator", "xác thực") để điều hướng vào `challenge/totp`.
  2. Nếu có TOTP Secret trong kho dữ liệu: Điền mã 6 số từ `pyotp.TOTP(secret).now()` và bấm Next.
  3. Chỉ khi URL chứa `challenge/iap` (bắt buộc nhập số điện thoại để mở khóa tài khoản) hoặc bị `rejected` mới đánh dấu `PLATFORM_FAIL` và khóa IP đến hết ngày theo Farm Safety Rule.

## 4. Periodic Reporting Deduplication & Event Rehydration

Trong các script báo cáo định kỳ (ví dụ `cron_gpm_oauth_pool_6h_report.py` chạy mỗi 6h):
- **Nguy cơ spam dòng lặp**: Feeder chạy định kỳ (mỗi 30 phút $\rightarrow$ 12 nhịp/6h). Nếu một vài tài khoản gặp lỗi lặp lại trong nhiều ca (ví dụ 8 accounts bị lỗi qua 3 ca liên tiếp), danh sách `events` trong khung 6h sẽ tích lũy 24 sự kiện lỗi, in ra 24 dòng lặp lại cùng một email, làm biến dạng thống kê.
- **Quy tắc Deduplicate chuẩn**:
  - Gom nhóm `recent_events` theo `email.lower()` lấy trạng thái mới nhất:
    ```python
    recent_events_map = {}
    for ev in events:
        if ev.get("at") and datetime.fromisoformat(ev["at"]) >= six_hours_ago:
            em = ev.get("email", "").lower()
            if em:
                recent_events_map[em] = ev
    recent_events = list(recent_events_map.values())
    ```
  - Báo cáo phải in rõ: `⚡ Tổng kết 6h vừa qua ({len(recent_events)} tài khoản đã xử lý):`.
- **Rehydration đối soát trạng thái thành công**:
  - Nếu `success_emails` trong state ngày ghi nhận tài khoản thành công nhưng trong danh sách `events` bị thiếu (do lỗi đồng bộ luồng trước đó), script báo cáo hoặc watchdog phải tự động đối soát với `used_proxies` để bổ sung event `SUCCESS`, tuyệt đối không để xảy ra mâu thuẫn hiển thị: "Tổng acc nạp thành công: 9" nhưng "6h vừa qua Thành công: 0".
