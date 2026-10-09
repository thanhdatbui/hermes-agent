# Worker Budget & Telegram Farm Alert Safety Contract

## 1. Worker Budget & Anti-Overengineering (Anti-Scope-Creep)

### Root Cause of Long-Running Subagents
Khi `delegation.max_iterations` để quá cao (100–150) và prompt giao việc không khóa cứng phạm vi, worker subagent rất dễ rơi vào bẫy **Scope Creep / Over-investigation**:
- Gặp lỗi nhỏ trong module phụ $\rightarrow$ tự ý đào sâu reverse engineering toàn bộ tiến trình mẹ, truy vết PID, subprocess, sys.path.
- Tự tiện sửa thêm code không liên quan, chạy full monorepo `pytest` (hàng ngàn test dính timeout 15 phút).
- Kéo dài thời gian chạy lên 1–2 tiếng (100+ tool calls), lãng phí tài nguyên và làm session bị treo.

### Quy tắc bất biến (Enforced Constraints)
1. **Trần cứng nền tảng (`config.yaml`):**
   - Khóa `delegation.max_iterations: 35` (chặn cứng tại runtime).
2. **Task Read-only / Inspect / OCR / Query:**
   - CẤM TUYỆT ĐỐI sửa code, CẤM chạy pytest test-suite, CẤM commit.
   - Bắt buộc trả kết quả ngay trong `<= 10 tool calls` (`< 10 phút`).
3. **Task Fix Code / Recovery:**
   - Scope Lock: Chỉ sửa đúng file flow / module chỉ định.
   - Test Lock: Chỉ chạy focused test (`pytest <test_file> -k <test_name>`) `< 30s`. CẤM chạy pytest trần monorepo.
   - Hoàn thành toàn bộ quy trình trong `<= 20 tool calls` (`< 15 phút`).
4. **Tránh Coordinator phản hồi trùng lặp (Double-reply):**
   - Khi dispatch worker chạy ngầm (`delegate_task`), Coordinator chỉ xác nhận ngắn gọn hoặc dùng `[SILENT]`, không đưa ra nhận định dài dòng trước khi worker trả kết quả để tránh gửi 2 tin trùng lặp cho user.

---

## 2. Telegram Farm Alert Media Caption Limit & Delivery Contract

### Giới hạn kỹ thuật Telegram API
- `sendMessage` (Text message): Tối đa **4,096 ký tự**.
- `sendPhoto` (Photo caption): Trần cứng **1,024 ký tự**.
- Vượt quá 1,024 ký tự $\rightarrow$ Telegram trả về mã lỗi HTTP `400 Bad Request: MEDIA_CAPTION_TOO_LONG` và từ chối ảnh.

### Chuẩn xử lý Split Message & Truncate HTML
- **Tin nhắn 1 (Ảnh Banner Đỏ):**
  - Giữ nguyên 100% thiết kế: vẽ thanh banner đỏ `[MAY N] - HH:MM:SS DD/MM` trên đỉnh ảnh màn hình lỗi.
  - Caption đi kèm ảnh: Chỉ chứa `summary_caption` (máy, serial, account, lỗi, hiện trường) và ghi chú xem tin tiếp theo.
  - Bắt buộc đi qua `_safe_truncate_html(photo_caption, max_len=1024)` để bảo toàn tính hợp lệ của các thẻ HTML (`<b>`, `<code>`, `<pre>`).
- **Tin nhắn 2 (Văn bản chi tiết):**
  - Gửi ngay bên dưới bằng `_send_telegram_text`, chứa đầy đủ quy trình 5 bước recovery, lệnh `inspect_machine.py`, file flow, file log và lệnh Canary test đầy đủ.

### Chuẩn Fail-Closed & Retry trong Claim File
1. **Không nuốt lỗi mạng:**
   - `send_farm_machine_alert` phải lưu `sent = bool(...)`. Khi rớt mạng hoặc Telegram timeout/DNS error, hàm BẮT BUỘC trả về `False` (CẤM `return True` vô điều kiện).
2. **Atomic Claim Retry:**
   - Tại consumer (`multi_machine_feed_session.py` / `_claim_machine_alert_once`):
     - Nếu `delivered = send_alert()` trả về `False`, tự động xóa file claim (`claimed.unlink(missing_ok=True)`).
     - Tuyệt đối không ghi `status=delivered` khi gửi thất bại. Điều này cho phép chu kỳ cron tiếp theo retry gửi lại khi mạng phục hồi, chống mất alert.
