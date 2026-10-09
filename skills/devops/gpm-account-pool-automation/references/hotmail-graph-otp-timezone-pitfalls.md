# Microsoft Graph API & Hotmail ChatGPT Direct Registration Pitfalls

## 1. Timezone Skew between Local System Clock and Graph API UTC
- **Hiện tượng**: Polling OTP qua Microsoft Graph API bị timeout (`FAIL_OTP_TIMEOUT`) mặc dù email OTP thực tế đã về hộp thư.
- **Nguyên nhân**:
  - Microsoft Graph API trả về trường `receivedDateTime` dưới dạng ISO-8601 UTC (e.g. `2026-09-27T05:11:42Z`).
  - Nếu `otp_started_at` được lấy theo giờ hệ thống hoặc timezone naive / parse không chuẩn, phép so sánh `receivedDateTime < otp_started_at` sẽ loại bỏ toàn bộ email mới.
- **Quy tắc xử lý**:
  - Luôn chuẩn hóa cả `otp_started_at` và `receivedDateTime` sang UTC (`datetime.now(timezone.utc)` và `datetime.fromisoformat(val.replace("Z", "+00:00")).astimezone(timezone.utc)`).
  - Sử dụng buffer an toàn: cho phép nhận email gửi trước thời điểm bắt đầu request tối đa 2–5 phút (`received_after - timedelta(minutes=2)`).

## 2. ChatGPT Direct Registration Flow: OTP First
- **Hiện tượng**: Form đăng ký ChatGPT không hiển thị ô nhập password sau khi submit email mà chuyển thẳng sang màn hình OTP 6 số.
- **Xử lý**:
  - Kiểm tra DOM: Nếu trang chuyển sang form OTP (`input[inputmode="numeric"]`, `input#code`, `input[data-index]`) hoặc có text "hộp thư" / "verification code", flow phải chuyển ngay sang polling OTP thay vì báo lỗi thiếu password.
  - Sau khi submit OTP thành công, ChatGPT mới yêu cầu tạo mật khẩu mới hoặc điền "About you" (Họ tên, ngày sinh).
