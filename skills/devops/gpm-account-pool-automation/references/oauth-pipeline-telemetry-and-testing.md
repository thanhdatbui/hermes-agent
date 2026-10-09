# OAuth Pipeline Telemetry & Unit Testing Standard

## 1. Trích xuất Helper chờ OTP / Authorization Code
Khi tự động hóa luồng OAuth Google/ChatGPT có tương tác giữa người dùng (nhập OTP SMS) và trình duyệt (bắt Authorization Code khi người dùng tự thao tác tay qua màn hình OAuth):
- **Tách hàm helper độc lập**: Luôn trích xuất logic vòng lặp chờ ra khỏi hàm monolithic lớn (`wait_for_otp_or_code(mid, otp_file, waiting_file, get_captured_code, timeout)`).
- **Callback `get_captured_code`**: Sử dụng lambda hoặc getter để đọc giá trị động của biến bắt code từ request/redirect listener, giúp kiểm tra loop break ngay lập tức khi code xuất hiện mà không cần chờ hết timeout.
- **Dọn dẹp file tạm an toàn**: Bọc `os.remove(otp_file)` và `os.remove(waiting_file)` trong khối try-except để không làm crash pipeline khi file bị xóa bởi tiến trình khác.

## 2. Telemetry & Correlation ID
Để đạt tiêu chuẩn audit cao (>= 85 điểm Sol Auditor / Telemetry Standard):
- Mọi log alert và xử lý luồng phải có `correlation_id`, ví dụ: `f"m{mid:02d}_{int(time.time())}"` hoặc `mid`.
- Gắn nhãn phân loại rõ ràng: `alert_type=OTP_SMS`, `status=...`, `latency=...ms`.
- Không nuốt âm thầm các ngoại lệ cấu hình (như fallback từ `automation_core.alerts`); phải ghi log warning chi tiết kèm correlation ID trước khi dùng giá trị mặc định.

## 3. Unit Test trực tiếp hàm Production
- Tránh viết unit test chỉ mô phỏng lại logic bằng vòng lặp while trong test script (mocking the pattern instead of the code).
- Import trực tiếp helper từ production script (`from scripts.run_oauth_s7_pipeline import wait_for_otp_or_code`) để test:
  1. Early break khi `captured_code` xuất hiện ngay trước/trong khi chờ.
  2. Xử lý khi nhận được OTP 6 số hợp lệ từ `otp_file`.
  3. Timeout behavior khi cả hai đều không xuất hiện.
