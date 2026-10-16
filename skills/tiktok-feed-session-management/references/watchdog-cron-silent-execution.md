# Watchdog Cronjob Execution & Silent Output Pattern

## Bối cảnh
Khi chạy cronjob giám sát phiên nuôi TikTok định kỳ (ví dụ mỗi 5 phút với `feed_session_watchdog.py`):
- Script sử dụng `feed_session_reported.json` (hoặc `follow_session_reported.json`) để theo dõi các phiên đã gửi báo cáo.
- Trong lúc phiên nuôi đang diễn ra hoặc sau khi phiên đã hoàn tất và đã được báo cáo thành công, script sẽ exit 0 và không in bất kỳ nội dung nào ra stdout.

## Quy tắc điều phối cho Coordinator
1. **Lệnh terminal chạy watchdog:**
   - Foreground terminal calls bắt buộc luôn truyền tham số `timeout` (ví dụ: `timeout: 60`) để thỏa mãn guard `GUARD_FOREGROUND_TIMEOUT_MISSING`.
2. **Xử lý kết quả Cronjob `[SILENT]`:**
   - Khi chạy script kiểm tra watchdog mà không có phiên mới cần báo cáo (output rỗng / không có báo cáo mới), Coordinator chạy dưới vai trò cron job BẮT BUỘC trả về chính xác chuỗi `[SILENT]` duy nhất.
   - Tuyệt đối không tự bịa đặt nội dung báo cáo hay gửi thông báo rác khi watchdog không phát hiện phiên hoàn tất mới.
