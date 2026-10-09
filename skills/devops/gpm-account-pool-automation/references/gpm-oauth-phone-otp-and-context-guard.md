# GPM OAuth Phone OTP & Playwright Context Guard (2026-09-19)

## 1. Ngữ cảnh & Triệu chứng
- Khi pipeline `run_oauth_s7_pipeline.py` login Google trên GPMLogin, Google có thể chuyển hướng sang `challenge/selection` và chọn gửi SMS OTP về SĐT đuôi 24 của Tad (`0906746624`).
- Trước đây script chỉ ghi ngầm ra file `C:\Users\Kibe\waiting_otp.json` và đợi file `otp_code.txt` trong 180s mà không gửi tin nhắn về Telegram, dẫn đến user không biết để đưa mã, script timeout và tự đóng profile Chromium.
- Ngoài ra, nếu user tự thao tác bấm xác minh trực tiếp trên màn hình browser, script vẫn tiếp tục đếm ngược 180s rồi báo `SMS_TIMEOUT` do không kiểm tra `captured_code`.
- Lỗi `NameError: name 'context' is not defined` tại dòng gọi `trigger_hot_chatgpt_oauth` vì biến context khai báo trong hàm là `ctx`.

## 2. Invariants & Kỷ luật xử lý
1. **Telegram Alert về Farm Alert**:
   - Khi phát hiện màn hình nhập SMS OTP cho SĐT 24, BẮT BUỘC gọi `send_telegram_otp_alert(email, mid, shot_path)`.
   - Đích gửi alert: Nhóm **Farm Alert** (`-5373649734`, fallback qua `DEFAULT_ALERT_CHAT_ID`), format:
     ```text
     ⚠️ [FARM ALERT] [MÁY {mid:02d}] 📱 Google gửi mã xác minh SMS về SĐT đuôi 24 (Tad)!
     - Email: {email}
     ⏱️ Vui lòng nhắn/nhập mã OTP 6 số (hạn 180s).
     ```
   - Kèm ảnh screenshot chụp màn hình chờ OTP.
2. **Early Break on `captured_code`**:
   - Trong vòng lặp chờ OTP (`wait_for_otp_or_code`), mỗi giây phải kiểm tra xem Authorization Code đã bắt được chưa (`if captured_code: break`).
   - Ngay khi có `captured_code`, dọn sạch `waiting_otp.json` và `otp_code.txt`, `continue` tiến trình exchange ngay, không chờ hết timeout.
3. **Playwright Context Variable**:
   - Dùng đúng `ctx` khi gọi `trigger_hot_chatgpt_oauth(page, ctx, email, mid, port, p_res)`.
