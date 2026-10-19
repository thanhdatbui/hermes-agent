# Quy Hoạch Reg Gmail Ban Đêm (00:00 - 02:30) & Tách Nhóm Báo Cáo Telegram (20/10/2026)

## 1. Bối Cảnh & Lý Do Chuyển Reg Gmail Về Đêm

### A. Vấn đề của khung giờ trưa (14:30 - 17:30)
- Khoảng nghỉ giữa Ca 2 và Ca 3 nuôi feed rất hẹp.
- Nếu Ca 2 kết thúc trễ hoặc các thiết bị S7 chưa kịp nhả device lock / kết thúc swipe, `post_noon_chain_watchdog` sẽ bỏ qua phiên (`is_feed_runner_active()` hoặc `has_active_device_locks()` return True).
- Dẫn đến tình trạng nhiều ngày liên tiếp không tạo được tài khoản Gmail bù mới.

### B. Lợi thế vượt trội của khung giờ đêm (00:00 - 02:30)
- **Quỹ thời gian lớn:** 21:30 - 05:15 máy hoàn toàn không phải nuôi feed TikTok.
- **Né các khung giờ bận đêm:**
  - 21:00 - 23:30: Upload Avatar (`post_evening_avatar_watchdog`).
  - 03:00 - 04:30: Dọn cache TikTok 40 workers (`cron_clear_tiktok_cache`).
  - 05:15 - 05:30: Farm Reboot PC chuẩn bị Ca 1 sáng.
  - $\rightarrow$ **00:00 – 02:30 là khung giờ an toàn lý tưởng.**
- **Mạng 4G MobiProxy sạch:** Ban đêm lưu lượng ít, IP ít bị spam, tỉ lệ Google bắt Phone Verify giảm rõ rệt.
- **Tốc độ:** Tối đa 15 máy đủ cooldown 5 ngày chạy song song, chỉ mất khoảng 15–25 phút.

---

## 2. Quy Tắc Định Tuyến Báo Cáo Telegram (Per-Phase Sinks)

- Khi tích hợp chuỗi đêm (Reg Gmail ➔ Add 2FA TikTok), **CẤM** gửi chung vào 1 kênh làm loãng thông tin:
  - Báo cáo kết quả Reg Gmail: BẮT BUỘC gửi thẳng về nhóm **Gmai reg** (`-5139245637`).
  - Báo cáo kết quả Add 2FA TikTok: BẮT BUỘC gửi thẳng về nhóm **Tiktok add 2fa** (`-5468653590`).
  - Cấu hình cronjob Hermes: Giữ `deliver: local` để tránh gửi trùng lặp hoặc spam Farm Alerts (`-5373649734`).

```python
# Helper chuẩn từ automation_core.alerts
from automation_core.alerts import _load_bot_token, _send_telegram_text

token = _load_bot_token()
# Gửi về nhóm Gmai reg:
_send_telegram_text(token, "-5139245637", gmail_report_text)
```
