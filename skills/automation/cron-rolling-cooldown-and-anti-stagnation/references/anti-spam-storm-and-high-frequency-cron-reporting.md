# Case Study: Bão Spam Telegram do Cron Ngắn Bắn Lẻ Tẻ (2026-11-04)

## 1. Hiện Tượng (User Signal)
User gửi ảnh chụp màn hình Telegram Desktop và phàn nàn:
> *"gì spam dữ v"*

Ảnh chụp màn hình thể hiện:
- Kênh **Farm Alerts** (`-5373649734`) nhận liên tiếp 3 tin nhắn:
  - 18:06: `CRON CHATGPT POOL REPORT` (Thất bại: 10)
  - 18:19: `CRON CHATGPT POOL REPORT` (Thất bại: 8)
  - 18:23: `CRON CHATGPT POOL REPORT` (Thất bại: 6)
- Kênh **GPM Auto** (`-5256944036`) nhận tin nhắn lúc 18:34:
  - `CRON CHATGPT POOL REPORT` (Thất bại: 1)

## 2. Nguyên Nhân Kỹ Thuật Cốt Lõi
1. **Thiếu Frequency-Aware Telemetry trên Cron Ngắn (15 phút/lần):**
   - Script `cron_auto_feed_chatgpt_pool.py` được lên lịch chạy mỗi 15 phút (`*/15 7,8,12,13,18,19,20,21 * * *`).
   - Sau khi hoàn thành mỗi đợt 10 tài khoản, script luôn gọi `send_telegram_report(report_msg)` để in danh sách tài khoản bị đưa vào cooldown 12h.
   - Khi cron chạy thường trực, việc mỗi 15 phút lại nhận một sớ email thất bại tạo cảm giác hệ thống bị spam, che khuất các thông báo khẩn cấp khác.

2. **Bẫy Default Channel Bleed (`REPO_GROUP_ROUTING['default']`):**
   - Trong `telegram_report.py`, kênh mặc định `REPO_GROUP_ROUTING['default']` trỏ về `-5373649734` (kênh Farm Alerts của máy thật).
   - Khi script chạy thử nghiệm chưa cấu hình đúng `TELEGRAM_CHAT_ID` hoặc biến môi trường `TELEGRAM_BOT_TOKEN` bị rỗng, tin nhắn bị xả thẳng vào Farm Alerts thay vì nhóm nghiệp vụ GPM Auto.

## 3. Quy Chuẩn Khắc Phục (Invariant)
1. **Silent Watchdog cho Cron chu kỳ <= 30 phút:**
   - Các script quét cuốn chiếu tự động (auto-feed, auto-nurture, cleanup) bắt buộc chạy im lặng:
     - Ghi nhận trạng thái vào SQLite / JSON cục bộ.
     - Cập nhật cooldown / blacklist mềm.
     - KHÔNG gọi API gửi tin nhắn Telegram mỗi tick.
2. **Báo cáo gộp định kỳ 6h/12h:**
   - Gom danh sách thất bại vào các cron báo cáo tổng kết định kỳ (`cron_gpm_oauth_pool_6h_report.py`, `cron_hotmail_gpm_lifecycle_6h_report.py`).
3. **Cấm tuyệt đối Fallback về Farm Alerts:**
   - Subsystem scripts (GPM, ChatGPT, Orders, Shop) nếu không có kênh riêng thì ghi log stderr/stdout, cấm fallback về `-5373649734`.
