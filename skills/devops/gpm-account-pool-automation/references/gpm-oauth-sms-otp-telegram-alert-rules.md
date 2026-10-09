# Quy tắc Alert Telegram khi Google yêu cầu SMS OTP (SĐT 24 của Tad)

## 1. Bối cảnh & Vấn đề phát sinh
Khi pipeline login GPM (`run_oauth_s7_pipeline.py`) chạy tự động sau ca tối, nếu Google bắt gặp challenge xác minh SĐT và chọn gửi SMS về SĐT đuôi 24 của Tad (`0906746624`):
- **Lỗi cũ:** Script chỉ ghi trạng thái ngầm vào file `C:\Users\Kibe\waiting_otp.json` và mở vòng lặp chờ 180s file `otp_code.txt`. Người dùng (Tad) không hề biết máy nào gửi mã, mã gửi lúc nào dẫn đến hết hạn 180s đóng profile (`SMS_TIMEOUT`).
- **Lỗi kẹt loop khi user thao tác tay:** Nếu user nhập trực tiếp trên trình duyệt hoặc điện thoại, Google chuyển hướng trả về `Authorization Code` (`captured_code`), nhưng script vẫn tiếp tục lặp đủ 180s rồi báo lỗi.

## 2. Quy tắc bắt buộc (Hard Invariants)
1. **Chủ động Alert Telegram ngay lập tức:**
   - Khi trigger màn hình yêu cầu OTP SMS, bắt buộc chụp màn hình debug (`shot_path`) và gọi ngay hàm `send_telegram_otp_alert(email, mid, shot_path)`.
   - **Kênh nhận alert:** BẮT BUỘC gửi về nhóm **Farm Alert** (`-5373649734` hoặc `DEFAULT_ALERT_CHAT_ID` từ `automation_core.alerts`), TUYỆT ĐỐI KHÔNG gửi về kênh cá nhân để tránh phân tán thông tin vận hành farm.
   - **Format tin nhắn:** Bắt buộc có tiền tố chuẩn Farm Alert:
     ```text
     ⚠️ [FARM ALERT] [MÁY {mid:02d}] 📱 Google gửi mã xác minh SMS về SĐT đuôi 24 (Tad)!
     - Email: {email}
     ⏱️ Vui lòng nhắn/nhập mã OTP 6 số (hạn 180s).
     ```

2. **Early Break trong vòng lặp chờ OTP (Thoát sớm thông minh):**
   - Trong vòng lặp đếm ngược 180s chờ OTP:
     ```python
     while time.time() - start_wait < 180:
         if captured_code:
             logger.info(f"[M{mid:02d}] 🎉 Bắt được Authorization Code trong lúc chờ OTP (user đã tự thao tác)!")
             break
         # check file otp_code.txt ...
     ```
   - Khi `captured_code` xuất hiện, lập tức dọn `otp_file` và `waiting_file`, bỏ qua việc chờ điền OTP để tiếp tục luồng OAuth exchange.

3. **Cẩn trọng tên biến Browser Context:**
   - Trong Playwright sync API: nếu khai báo `with sync_playwright() as p: ctx = p.chromium.launch_persistent_context(...)`, biến context là `ctx`. Khi gọi hàm phụ trợ (như `trigger_hot_chatgpt_oauth(page, ctx, ...)`), tránh nhầm lẫn biến thành `context` gây `NameError: name 'context' is not defined`.
