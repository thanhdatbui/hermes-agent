# Quy Trình Check Live Gmail, Xử Lý Mail DIE & Chính Sách Reg Gmail Tránh Bị Quét

## 1. Cơ Chế Check Live Gmail Bắt Buộc (Anti-False-Positive)
- **Vấn đề đã xác nhận thực tế (2026-09-12):** Hàm kiểm tra on-device cũ (`check_google_account_health_from_gmail`) trong app Gmail Android chỉ bắt được khi màn hình hiện Google CAPTCHA. Các tài khoản bị Google khóa ngầm / disable từ máy chủ sẽ KHÔNG văng lỗi rõ ràng trên app Gmail, dẫn đến ngộ nhận là tài khoản vẫn LIVE và đổ lỗi sai cho TikTok không phát OTP.
- **Quy chuẩn bắt buộc:**
  - Sử dụng API / Playwright qua `checkmail.live` (kết nối qua proxy mobile theo chuẩn repo `site ban hang clone`).
  - Đường dẫn tool: `D:/Taadaa/tools/check_gmail_live_fast.py`.
  - CẤM dựa vào on-device Google health check đơn thuần để kết luận trạng thái sống của Gmail.

## 2. Xử Lý Tự Động Khi Phát Hiện Gmail DIE
1. **Tại bước reg TikTok (7c OTP Timeout):**
   - Khi OTP không về, gọi `check_gmail_is_live(email)` qua `checkmail.live`.
   - Nếu kết quả là `DIE`:
     + Gọi ngay `remove_captcha_dead_email_from_source(email)` để tạo backup và xóa dòng mail đó khỏi `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx`.
     + Đẩy thông tin cách ly vào sheet `Audit Pending` trong `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`.
     + Dừng flow và ném exception rõ ràng (`google_captcha_dead_mail`).
2. **Xóa tài khoản DIE khỏi thiết bị Android:**
   - Khi quét định kỳ ra danh sách Gmail DIE, phân bổ mapping theo từng máy lưu vào `D:/Taadaa/runtime/kibe/gmail_die_by_machine.json`.
   - Trước mỗi ca Reg mới: script `preflight_s7_rolling_cleanup.py` (hàm `remove_account_adb()`) đọc danh sách này để gỡ sạch tài khoản Google DIE khỏi máy Android (`Settings -> Accounts -> Google -> Remove account`), giải phóng slot sạch trước khi reg mới.

## 3. Chính Sách Reg Gmail Chống Google AI Quét Hàng Loạt (Học từ vụ DIE 70% tháng 9/2026)
Qua kiểm chứng thực tế, dàn Gmail reg mới bị die 70% sau 3-5 ngày do 3 nguyên nhân cốt lõi:
1. **BẮT BUỘC Bật 2FA Google Authenticator (TOTP) ngay trong flow Reg:**
   - KHÔNG dùng chung 1 Email khôi phục (`thanhdatbui1995`): Trùng identity hàng loạt gây chain-ban và kẹt queue OTP.
   - Bật 2FA sinh ra Secret Key Base32 độc lập cho từng acc, nâng trust tài khoản lên mức tối đa.
   - **Thời điểm bật 2FA:** Phải bật NGAY LẬP TỨC khi vừa reg xong trong flow `gmail_reg_v10.py` (khi phiên đăng nhập đang Active). Không ngâm tài khoản nhiều ngày mới bật vì Google sẽ kích hoạt checkpoint yêu cầu verify/re-login.
2. **Quy Tắc Chọn Máy (Pick 15 máy có Proxy KHÁC NHAU):**
   - Dàn 80 máy gán trên 40 proxy (tỷ lệ 2 máy / cổng).
   - Khi chạy batch reg 15 máy, BẮT BUỘC gom nhóm sao cho 15 máy chạy trên **15 cổng proxy hoàn toàn khác nhau** (1 máy / proxy).
   - **CẤM TUYỆT ĐỐI đổi IP trước khi reg:** Giữ nguyên IP của proxy đang map, không reset/recreate modem.
3. **Tăng Tính Random / Entropy Khi Sinh Họ Tên & Username:**
   - Sử dụng đa dạng họ, tên đệm (1-2 chữ), tên chính kết hợp salt ngẫu nhiên 3-5 ký tự và suffix nghiệp vụ (`top`, `life`, `work`, `plus`...).
   - Tuyệt đối không dùng công thức đơn điệu `ho + dem + ten + year` khiến Google AI dễ dàng nhận diện pattern bot.
