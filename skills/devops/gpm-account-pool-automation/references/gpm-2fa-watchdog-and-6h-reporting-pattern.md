# GPM 2FA Watchdog and 6-Hour Aggregated Reporting Pattern

## Pattern Summary
Khi thiết kế cron watchdog tự động vận hành các profile GPM (như bật 2FA, OAuth, login), luôn tuân thủ nguyên tắc tách rời:
1. **Background Runner:** Chạy mỗi 5-15 phút, cấu hình `deliver: local` để chạy ngầm hoàn toàn im lặng. Cập nhật state vào JSON file (`post_morning_gmail_2fa_state.json`) kèm danh sách `events` lưu timestamp.
2. **Aggregated 6H Reporter:** Tạo cronjob độc lập chạy `0 */6 * * *` với `deliver: telegram:-5373649734` (Farm Alerts) để đọc state và xuất báo cáo tổng quan.
3. **Session Verification:** Luôn đọc trực tiếp từ SQLite cookie file của profile GPM (`Default/Cookies` hoặc `Default/Network/Cookies`) để kiểm tra `SID, SSID, HSID, SAPISID` thay vì dựa vào trường boolean rỗng.
