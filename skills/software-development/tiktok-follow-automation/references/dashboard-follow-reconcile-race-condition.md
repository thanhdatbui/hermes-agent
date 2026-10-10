# Dashboard Following Reconcile Race Condition & Telemetry Diagnostic

## Hiện tượng
Trên Web Dashboard (`tiktok_dashboard.py` / cổng 1905), tài khoản hiển thị:
- `ĐÃ FOLLOW: X (+N)` (Ví dụ: 186 (+12) hoặc 12 (+1))
- `🔗 Nội bộ: +0` (hoặc lệch thấp hơn +N)

## Hai Nguyên Nhân Gốc Rễ

### Nguyên nhân 1: Leak Follow từ Popup Gợi Ý Bạn Bè / Danh Bạ trong Feed Session (`benign_popup.py`)
Khi tài khoản **nghỉ follow hoặc chưa đủ video** (`organic-rest-day-pure-feed`, `under-6-videos-follow-disabled`), runner không hề phát lệnh follow chéo nội bộ nào (`followed_count = 0`), bảng `daily_account_actions` ghi nhận `+0`. Tuy nhiên số `following` trên TikTok vẫn tăng (+1, +2):
- **Cơ chế gây leak:** Trong `automation-core/src/automation_core/tiktok/benign_popup.py`, bộ xử lý popup `detect_contact_follow_suggestion` (gợi ý kết bạn/danh bạ, thường xuất hiện khi lướt tab Bạn bè/Friends) có policy:
  `pre_action="tap_follow_button"` (hoặc trả về `follow_target` nếu không có nút X đóng).
- **Hiện trường kiểm chứng:**
  + So sánh file `profile_identity/ui.xml` ở đầu ca (ví dụ: `Đã follow = 0`) với `verify_profile/ui.xml` ở cuối ca (ví dụ: `Đã follow = 1`).
  + Kiểm tra `log.jsonl` của máy: tìm step `contact_follow_suggestion` hoặc `dismiss_not_interested_button`, tọa độ tap rơi vào nút Follow của card gợi ý bạn bè.
- **Xử lý:** Tắt `pre_action="tap_follow_button"` và nút bấm follow trong `benign_popup.py`, chỉ cho phép đóng (`dismiss`) hoặc swipe bỏ qua.

### Nguyên nhân 2: Race Condition giữa Snapshot Crawler và Watchdog Chốt Ca
1. **Thời điểm cào Snapshot toàn Farm:**
   - Hệ thống crawler snapshot toàn farm (`snapshots` table) cào định kỳ (thường vào sáng sớm, ví dụ 07:04:09).
   - Snapshot đọc trực tiếp số `following` công khai từ profile web của TikTok, ghi nhận mức tăng ngay lập tức (`delta_following = +12`).
2. **Thời điểm Watchdog chốt sổ Ca Nuôi/Follow:**
   - Ca chạy nuôi nick / follow chéo (ví dụ: ca sáng 06:00 - 07:35:55) ghi nhận chi tiết follow từng máy vào `follow_result.json`.
   - Bảng `session_account_actions` và bảng tổng hợp ngày `daily_account_actions` trong SQLite (`tiktok_tracker.db`) **CHỈ ĐƯỢC WATCHDOG GHI NHẬN KHI CA CHẠY KẾT THÚC HOÀN TOÀN** (hàm `save_session_action_stats` và `reconcile_cluster_following` chạy lúc ~07:35:58).
3. **Cửa sổ lệch pha (Race Window):**
   - Trong khoảng thời gian ca đang chạy (06:00 - 07:35), snapshot đã quét thấy following tăng (+12), nhưng bảng `daily_account_actions` của ngày đó chưa có bản ghi (hoặc chưa cập nhật máy này).
   - Dashboard truy vấn:
     `SELECT username, internal_follows FROM daily_account_actions WHERE target_date = ?`
     Do chưa có dữ liệu trong ngày, Dashboard fallback về `0` (`🔗 Nội bộ: +0`).

## Quy trình chẩn đoán (CẤM đoán mò "follow tự nhiên")
1. **CẤM TUYỆT ĐỐI phán đoán ẩu "đây là follow tự nhiên / kênh ngoài"** khi user đã cấu hình tắt follow tự nhiên trong feed runner.
2. **Kiểm tra thời điểm:**
   - So sánh `snapshots.timestamp` mới nhất với mtime của ca chạy (`runtime/kibe/live/<YYYY-MM-DD>/<run>/...`).
   - Kiểm tra ca chạy của máy/nick đó đã kết thúc (có `summary.txt`, `follow_result.json`) và Watchdog đã hoàn tất gửi báo cáo Telegram chưa.
3. **Kiểm tra nguồn tin cậy (Source of Truth):**
   - Đọc trực tiếp `follow_result.json` của máy trong thư mục run:
     Kiểm tra `followed_count`, danh sách `followed`, `mode2_followed_count` để xác nhận số lượt follow chéo thực tế do script thực hiện.
   - Kiểm tra SQLite `daily_account_actions` và `session_account_actions`:
     Nếu ca đã chốt nhưng Dashboard chưa cập nhật, kiểm tra cache TTL (15s) hoặc reload web.
