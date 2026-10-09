# Google SMS OTP Automation & Farm Alert Protocol

## 1. Vấn đề thực tế
Khi Google yêu cầu xác minh danh tính qua SMS gửi về SĐT quản trị (ví dụ: SĐT đuôi 24 của Tad):
- **Lỗi im lặng (Silent Timeout):** Script ghi trạng thái chờ ngầm vào file json (`waiting_otp.json`) hoặc đếm ngược 180s mà không phát cảnh báo ra ngoài. Người dùng không hề biết có SMS gửi về điện thoại, dẫn đến hết hạn 180s và tự đóng profile.
- **Kẹt vòng lặp chờ dù đã hoàn tất:** Nếu người dùng thao tác trực tiếp trên trình duyệt hoặc điện thoại và Google đã redirect trả về Authorization Code (`captured_code`), script nếu chỉ poll file OTP sẽ bị kẹt tiếp cho đến khi timeout.
- **Kênh thông báo sai đích:** Thông báo gửi OTP gửi vào kênh cá nhân hoặc tin nhắn trực tiếp thay vì nhóm **Farm Alert** (`-5373649734`) khiến thông báo bị phân tán hoặc trôi tin.

## 2. Quy chuẩn triển khai (Invariant Pattern)

### 2.1. Phát cảnh báo Telegram tức thì về Farm Alert
Ngay khi script phát hiện form yêu cầu SMS OTP hoặc bấm nút gửi OTP:
1. Chụp ảnh màn hình hiện trường (`waiting_otp_24.png`).
2. Gửi ngay ảnh chụp kèm nội dung cảnh báo về nhóm **Farm Alert** (`DEFAULT_ALERT_CHAT_ID = "-5373649734"`).
3. Định dạng tin nhắn chuẩn:
   ```text
   ⚠️ [FARM ALERT] [MÁY {mid:02d}] 📱 Google gửi mã xác minh SMS về SĐT đuôi 24 (Tad)!
   - Email: {email}
   ⏱️ Vui lòng nhắn/nhập mã OTP 6 số (hạn 180s).
   ```

### 2.2. Vòng lặp chờ OTP hỗ trợ Fast-Break (Thoát sớm)
Trong vòng lặp đếm ngược 180s chờ mã OTP từ file `otp_code.txt`:
- BẮT BUỘC kiểm tra biến `captured_code` (hoặc URL chuyển hướng đã thành công):
  ```python
  while time.time() - start_wait < 180:
      if captured_code:
          logger.info(f"[M{mid:02d}] 🎉 Bắt được Authorization Code trong lúc chờ OTP (user đã tự thao tác)!")
          break
      if os.path.exists(otp_file):
          # Đọc mã và điền form
          ...
      time.sleep(1)
  ```
- Nếu `captured_code` xuất hiện: dọn file tạm `waiting_otp.json` / `otp_code.txt` và `continue`/tiếp tục pipeline ngay lập tức, không đợi hết 180s.

### 2.3. Tránh lỗi biến Browser Context
Trong Playwright khi dùng `launch_persistent_context`:
- Biến trả về là `ctx` (hoặc `context`). Phải đồng nhất tên biến trong toàn bộ các hàm gọi downstream (ví dụ: `trigger_hot_chatgpt_oauth(page, ctx, email, mid, port, p_res)`), tránh gây `NameError: name 'context' is not defined`.
