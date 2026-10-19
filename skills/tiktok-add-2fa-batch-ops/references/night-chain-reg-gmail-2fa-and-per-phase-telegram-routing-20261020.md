# Night Chain (Reg Gmail -> Add 2FA TikTok) & Per-Phase Telegram Routing (20/10/2026)

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause)

### A. Cron Add 2FA không thấy báo cáo về nhóm TikTok 2FA (`-5468653590`)
- **Bug xung đột logic 6H vs Ca nuôi:**
  - Trong `cron_night_tiktok_2fa_watchdog.py`, script được thiết kế chỉ in ra `stdout` ở 4 mốc 6H: `0h, 6h, 12h, 18h` (nếu `now.minute < 30`).
  - Tuy nhiên, hàm kiểm tra an toàn `is_safe_rolling_window()` lại chặn chạy trong 3 ca nuôi: `05:15–09:30`, `11:45–15:30`, `17:45–21:30`.
  - Hậu quả: Mốc **6h, 12h, 18h** luôn bị `is_safe_rolling_window()` chặn ngay từ đầu (`return 0` im lặng).
  - Với mốc **0h**: Nếu batch chạy kéo dài hoặc bị lệch cờ `already_reported_6h`, script không in ra `stdout`.
  - Trong cơ chế Hermes `no_agent=True`, **stdout rỗng = Silent Watchdog** (Hermes không gửi tin nhắn nào). Do đó nhóm `-5468653590` bị im lặng nhiều ngày.

### B. Cron Gmail Register không thấy báo cáo về nhóm Gmail (`-5139245637`)
- Farm không có cronjob độc lập tên `gmail-register`. Đăng ký Gmail nằm trong **Phase 1 của `post-noon-chain-watchdog`**.
- Tuy nhiên, cron `post-noon-chain-watchdog` được cấu hình `deliver: telegram:-5373649734` (đẩy toàn bộ về **Farm Alerts**, không đẩy về nhóm Gmail).
- Hơn nữa, ca trưa thường bị hẹp thời gian giữa Ca 2 và Ca 3; nếu Ca 2 kết thúc muộn hoặc máy chưa nhả lock, chuỗi trưa bị bỏ qua hoàn toàn.

---

## 2. Giải Pháp Kiến Trúc: Night Chain & Per-Phase Telegram Routing

### A. Chuyển / Bổ sung Reg Gmail về Ban Đêm (00:00 - 02:30)
- **Quỹ thời gian:** Ban đêm từ 21:30 đến 05:15 máy rảnh nuôi feed. Khung giờ **00:00 – 02:30** là lý tưởng nhất:
  - Tránh Upload Avatar tối (21:00 – 23:30).
  - Tránh Dọn cache TikTok toàn farm (03:00 – 04:30).
  - Tránh Farm Reboot PC (05:15 – 05:30).
- **Mạng 4G MobiProxy ban đêm:** Ít nghẽn, IP sạch hơn, tỉ lệ Google bắt Phone Verify giảm.
- **Tuần tự không xung đột:** Chạy Phase 1 (Reg Gmail, tối đa 15 máy đủ cooldown 5 ngày) ➔ Phase 2 (Add 2FA TikTok cuốn chiếu).

### B. Nguyên Tắc Báo Cáo Độc Lập Theo Từng Phase (Per-Phase Sinks)
Khi một Watchdog chạy chuỗi liên hoàn nhiều nghiệp vụ khác nhau (Gmail Reg + TikTok 2FA), **CẤM** gom chung vào một stdout duy nhất gửi về 1 nhóm Telegram (hoặc Farm Alerts).
- **Phase 1 (Reg Gmail):** Script tự dispatch báo cáo trực tiếp đến nhóm **Gmai reg** (`-5139245637`).
- **Phase 2 (Add 2FA TikTok):** Script tự dispatch báo cáo trực tiếp đến nhóm **Tiktok add 2fa** (`-5468653590`).
- **Cronjob Hermes:** Đặt `deliver: local` để lưu log cục bộ, chống gửi trùng lặp hoặc làm ô nhiễm kênh khác.

```python
# Helper gửi Telegram trực tiếp theo nhóm nghiệp vụ
from automation_core.alerts import _load_bot_token, _send_telegram_text

def send_telegram_report(chat_id: str, text: str) -> bool:
    token = _load_bot_token()
    if not token:
        logger.warning("Không tìm thấy TELEGRAM_BOT_TOKEN")
        return False
    return _send_telegram_text(token, chat_id, text)

# Phase 1:
send_telegram_report("-5139245637", gmail_report_text)

# Phase 2:
send_telegram_report("-5468653590", tiktok_2fa_report_text)
```

### C. Xóa bỏ bẫy kiểm tra 6H gây câm báo cáo
- Xóa bỏ điều kiện `is_6h_window` xung đột với `is_safe_rolling_window`.
- Mỗi khi một đợt chạy ban đêm hoàn tất (hoặc có kết quả máy thành công/thất bại thực tế), lập tức gửi báo cáo về nhóm tương ứng để người vận hành nắm bắt hiện trường realtime.

---

## 3. Kỷ Luật Crash Safety & Bắt Ngoại Lệ Trong Điều Phối Đa Phase
Trong các watchdog chạy liên hoàn tuần tự nhiều phase nghiệp vụ (`run_gmail_phase` -> `run_tiktok_phase`):
- **Bẫy Unhandled Exception Ở Phase Sau:** Nếu phase 2 bị lỗi unhandled exception (lỗi cú pháp lệnh SSH, timeout bất ngờ, lỗi đọc workbook), tiến trình có thể crash trực tiếp từ `main()` mà không kịp lưu state hoặc dispatch thông báo lỗi ra Telegram.
- **Mô Thức Crash Handler Bắt Buộc (`_handle_phase_crash`):**
  - Bọc từng phase trong khối `try/except Exception` riêng biệt tại `main()`.
  - Khi phase sau gặp ngoại lệ, gọi crash handler ghi nhận state `status="failed"`, `failure_reason=...` và dispatch alert cảnh báo khẩn cấp về đúng nhóm Telegram của nghiệp vụ đó trước khi trả mã lỗi.
  - Đảm bảo tính độc lập: Phase 1 lỗi không được làm chết Phase 2, và Phase 2 lỗi phải để lại audit trail đầy đủ.
