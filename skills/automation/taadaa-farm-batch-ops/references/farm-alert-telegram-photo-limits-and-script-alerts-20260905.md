# Farm Alert Telegram Photo Limits & Script Alerts (2026-09-05)

## 1. Sự cố mất ảnh Farm Alert & Giới hạn 1,024 ký tự của Telegram
- **Hiện tượng**: Farm Alert bắn về Telegram chỉ có tin nhắn văn bản, hoàn toàn mất ảnh chụp màn hình có banner đỏ số máy (`[MAY <N>] - HH:MM:SS DD/MM`).
- **Nguyên nhân cốt lõi**:
  - API `sendPhoto` của Telegram chỉ chấp nhận `caption` có độ dài tối đa **1,024 ký tự**.
  - Template 5 bước recovery chuẩn kèm lệnh Canary và chi tiết lỗi proxy/UIDump dài ~1,070 – 1,230 ký tự.
  - Telegram trả về `HTTP 400 Bad Request: MEDIA_CAPTION_TOO_LONG`. Code cũ bị fallback nuốt ảnh và chỉ gửi tin nhắn text.
- **Giải pháp chuẩn hóa trong `automation_core/alerts.py`**:
  - Tách nội dung thành 2 phần:
    1. `summary_caption` (Quy trình, STT máy, Serial, Nick, Triệu chứng, Hiện trường): Luôn $\le 1024$ ký tự, gửi cùng ảnh.
    2. `instructions` (5 bước recovery + lệnh Canary test): Gửi bằng `sendMessage` ngay sau ảnh.
  - Hàm `_safe_truncate_html()`: Đảm bảo cắt chuỗi không làm vỡ HTML entities và tự động đóng các thẻ `<b>`, `<code>`, `<pre>`.

## 2. Sự cố nuốt lỗi mạng và kẹt Alert Claim
- **Nguyên nhân sáng 05/09/2026**:
  - Mạng Telegram bị lỗi DNS / timeout từ 06:02 đến 06:06.
  - Hàm `send_farm_machine_alert()` cũ luôn `return True` vô điều kiện ở cuối hàm dù `_send_telegram_photo` và `_send_telegram_text` trả về `False`.
  - Cơ chế `_claim_machine_alert_once()` tưởng tin đã đến đích nên ghi file `machine_<N>.claimed` với `status=delivered`.
  - Ở các lần quét tiếp theo của cron, file `.claimed` ngăn chặn gửi lại, làm mất hoàn toàn Farm Alert của 45 máy.
- **Quy tắc chuẩn hóa**:
  - `send_farm_machine_alert()` trả về `False` khi không có request nào thành công.
  - Khi `delivered is False`, caller BẮT BUỘC xóa file claim tạm (`claimed.unlink(missing_ok=True)`) để cho phép retry.

## 3. Cảnh báo lỗi cấp Script / Pipeline tổng (`send_farm_script_alert`)
- Dành cho các lỗi không gắn với từng máy lẻ (crash PowerShell, import error, timeout hàng loạt >50% máy):
  - Chuỗi đêm Reg Gmail -> Reg TikTok -> Add 2FA (`night_chain`).
  - Dọn cache TikTok cuối ngày (`clear_cache`).
  - Check live kho acc (`checklive`).
- Bắn thẳng về nhóm Farm Alerts (`-5373649734`) với cấu trúc:
  ```text
  🚨 [FARM ALERT: LỖI SCRIPT / PIPELINE]
  • Quy trình / Script: <Tên script>
  • Chi tiết lỗi: <Error>
  📋 BẮT BUỘC KIỂM TRA & XỬ LÝ:
  1. File thực thi: <flow_file>
  2. File log: <log_path>
  3. Lệnh chạy kiểm chứng: <canary_cmd>
  ```
