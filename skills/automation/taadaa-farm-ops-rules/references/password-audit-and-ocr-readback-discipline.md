# Quy chuẩn Đối soát Mật khẩu & Evidence First OCR Readback

## 1. Nguyên tắc cốt lõi
- **Không suy đoán mò:** Khi gặp lỗi, BẮT BUỘC chụp ảnh đóng băng hiện trường (Freeze Screenshot) và chạy WinRT OCR đọc 100% text trước khi đưa ra nhận định. CẤM chỉ nhìn Accessibility XML rồi bịa nguyên nhân ("kẹt nút", "mất callback JS").
- **Khai thác chữ đỏ thông báo lỗi:** Mọi thông báo lỗi màu đỏ trên màn hình ("Số lần nhập sai tài khoản hoặc mật khẩu đã đạt giới hạn", "Mật khẩu đó không đúng với tài khoản Microsoft của bạn", "Phiên đã hết hạn") phải được trích nguyên văn làm căn cứ số 1.
- **Đối soát mật khẩu:** Khi tài khoản bị báo sai mật khẩu:
  1. Tra cứu ngược file Handoff và log chạy cũ trong `.ai-runs/`.
  2. Xác định tài khoản có bị luồng `change_info` đổi mật khẩu hay không.
  3. Nếu TikTok reg không yêu cầu nhập pass thì cột PASS Excel BẮT BUỘC để trống, TUYỆT ĐỐI CẤM tự sinh pass random ghi đè vào Excel.
- **Khôi phục Hotmail:**
  - Nếu Microsoft chặn mật khẩu cũ nhưng cho phép gửi mã đến email khôi phục `th*****@gmail.com` (`thanhdatbui1995@gmail.com`): Sử dụng cơ chế IMAP `poll_latest_otp` để đọc mã OTP tự động.
  - Thử tối đa 2 tài khoản fail liên tiếp là BẮT BUỘC dừng (Circuit Breaker) để tránh cháy IP và tránh bị khóa 24h.
