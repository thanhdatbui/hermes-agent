# GPM 2FA Watchdog Decoupling & 6-Hour Aggregated Reporting Architecture

## 1. Vấn đề gốc rễ (Root Cause: Cron Output Spam & Polling Noise)
- Khi một watchdog tự động bật 2FA GPM (`post_morning_gmail_2fa_watchdog.py`) chạy tuần hoàn mỗi 5 phút với `no_agent: true`:
  - Nếu script in báo cáo ra `stdout` mỗi khi có tài khoản `PENDING_GPM_LOGIN_NO_SESSION` hoặc khi không có gì thay đổi, Hermes scheduler sẽ chuyển tiếp toàn bộ output đó lên kênh Telegram Farm Alert.
  - Hậu quả: Người dùng bị spam liên tục mỗi 5 phút cùng một nội dung báo cáo tiến độ dở dang, gây ức chế và làm loãng kênh cảnh báo nông trại.

## 2. Mô hình phân tách chuẩn (Decoupled Worker vs 6H Reporter)
Để đảm bảo tiến độ xử lý nhanh mà không làm phiền người dùng, bắt buộc tách thành 2 tầng độc lập:

### Tầng 1: Background Execution Worker (Xử lý ngầm, hoàn toàn im lặng)
- **Cấu hình cron:** `schedule: */5 ...` (hoặc `*/15`), `deliver: local`.
- **Nhiệm vụ:**
  - Quét candidate đủ điều kiện (đã qua soaking gate nuôi ít nhất 1 phiên thành công).
  - Kiểm tra device lock và lịch nuôi feed để tránh va chạm.
  - Chạy Playwright qua CDP bật 2FA Google Authenticator, trích xuất Base32 Secret Key và lưu đồng bộ vào Excel (`master_gmail_manager.xlsx`, `gmail_clean_v2.xlsx`).
  - Ghi nhận lịch sử vào `post_morning_gmail_2fa_state.json`: lưu danh sách `events` gồm `{email, machine, status, secret_key, at}`.
  - **Kỷ luật output:** Tuyệt đối KHÔNG in ra stdout nếu không có lỗi chí mạng; không gửi thông báo về Telegram.

### Tầng 2: Aggregated 6-Hour Reporter (Gom báo cáo 6 tiếng / lần)
- **Cấu hình cron:** `schedule: 0 */6 * * *` (chạy vào 00:00, 06:00, 12:00, 18:00), `deliver: telegram:-5373649734` (Farm Alerts).
- **Script phụ trách:** `cron_gmail_gpm_2fa_6h_report.py`.
- **Nhiệm vụ:**
  - Đọc SQLite GPM DB (`profile_data.db`) đếm tổng số profile Group 10.
  - Đọc Excel Master & Clean v2 đối soát tỷ lệ đã có 2FA.
  - Đọc `gpm_gmail_nurture_state.json` xác định số tài khoản đang ngâm.
  - Đọc `events` trong `post_morning_gmail_2fa_state.json` lọc ra các hành động diễn ra trong 6 giờ qua (`now - timedelta(hours=6)`).
  - Xuất báo cáo cô đọng chuẩn format:
    ```text
    📊 [BÁO CÁO 6H: 2FA GMAIL QUA GPM PROFILE]
    • Tổng số profile GPM (Group 10): 71
    • Đã bật 2FA thành công: 69/71 (97.2%)
    • Đang ngâm (chờ phiên nuôi): 2
    • Sẵn sàng bật 2FA: 0

    ⚡ Tiến độ xử lý trong 6h vừa qua: 3 sự kiện
      + M18 | hakha18062003@gmail.com: SUCCESS (Q42DP2HH...FEO6)
      + M26 | quachtrang19022003@gmail.com: SUCCESS (T3WJF4F4...HYBW)
      + M38 | benghowelltpkf1@gmail.com: SUCCESS (WAQUWOHR...PTOY)
    ```

## 3. Pitfalls kỹ thuật cần tránh
1. **Time-window check block cron schedule:**
   - Tránh để hàm `is_within_time_window((8, 30), (11, 30))` hoặc `is_feed_ca1_finished()` trong các script chạy tuần hoàn định kỳ 6h. Nếu để, script sẽ tự exit 0 tại các mốc 00:00, 06:00, 12:00, 18:00 và không bao giờ xuất báo cáo hay xử lý tài khoản.
2. **Missing `profile_path` dẫn đến false negative session:**
   - Hàm `_profile_has_google_session()` phải nhận dict có chứa key `"profile_path"`.
   - Script phải đọc trực tiếp tệp SQLite cookie (`Default/Cookies` hoặc `Default/Network/Cookies`) để đếm các cookie xác thực cốt lõi (`SID`, `SSID`, `HSID`, `SAPISID` >= 2).
   - Tuyệt đối không kiểm tra trường boolean rỗng nếu danh sách ứng viên chưa được enrich từ trước.
3. **State event rollover:**
   - Khi ghi `save_state_results`, luôn nạp `events` cũ từ file state, nối thêm các sự kiện mới trong tick hiện tại và cắt đuôi giữ lại tối đa 50-100 events gần nhất để file state không bị phình to.
