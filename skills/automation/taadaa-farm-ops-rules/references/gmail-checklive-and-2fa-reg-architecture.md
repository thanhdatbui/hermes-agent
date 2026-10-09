# Gmail Health & 2FA Setup Architecture for Farm Operations

## 1. Cơ Chế Check Live Gmail: Web API (checkmail.live) vs On-Device Health Check
- **Vấn đề On-Device Check cũ (`check_google_account_health_from_gmail`)**:
  - Khi Google khóa/vô hiệu hóa (disable) tài khoản Google ngầm từ server, ứng dụng Gmail trên Android không tự động văng lỗi hay hiện thông báo lỗi rõ ràng.
  - Script kiểm tra trên thiết bị ngộ nhận tài khoản vẫn `LIVE`, dẫn đến việc đổ lỗi nhầm cho TikTok không phát OTP về hộp thư.
- **Giải pháp chuẩn hóa**:
  - BẮT BUỘC sử dụng dịch vụ check live qua web `checkmail.live` (sử dụng Playwright persistent context kết hợp proxy mobi theo chuẩn repo `site ban hang clone`).
  - Khi kết quả trả về `[die]`:
    1. Xóa dòng tài khoản khỏi file nguồn (`gmail_clean_v2.xlsx`) kèm tạo bản backup atomic.
    2. Ghi nhận tài khoản vào sheet `Audit Pending` trong `taikhoan_dat_v2_updated .xlsx`.
    3. Đánh dấu theo máy để gỡ bỏ tài khoản Google khỏi thiết bị Android qua module `preflight_s7_rolling_cleanup.py`.

## 2. Chiến Lược Reg Gmail Tránh Google Quét Hàng Loạt (70% Die Mitigation)
- **Tách Biệt Đường Truyền (Proxy Mapping)**:
  - Farm 80 máy phân bổ trên 40 cổng proxy duy nhất (2 máy / cổng).
  - Khi pick batch chạy reg (ví dụ 15 máy), **BẮT BUỘC chọn các máy có proxy map KHÁC NHAU**. Đảm bảo mỗi cổng proxy chỉ có tối đa 1 máy chạy trong cùng một thời điểm.
  - **CẤM TUYỆT ĐỐI đổi IP / reset modem trước khi reg** (giữ nguyên kết nối ổn định đã cấp phát).
- **Tăng Cường Entropy / Random Hóa Danh Tính**:
  - Thuật toán sinh họ tên `build_username()` kết hợp: họ + tên đệm (1-2 từ) + tên chính + keyword nghiệp vụ tự nhiên (`top`, `life`, `pro`, `plus`...) + salt ngẫu nhiên 3-5 ký tự + số ngẫu nhiên.
  - Triệt tiêu hoàn toàn công thức ghép chuỗi đơn điệu dạng `ho + dem + ten + year` vốn dễ bị Google AI nhận diện bot fingerprint.

## 3. Kiến Trúc Bật 2FA Google Authenticator Cho Gmail Mới Tạo
- **Tại sao không dùng Mail khôi phục chung (`thanhdatbui1995@gmail.com`)**:
  - Dùng chung 1 mail khôi phục khiến các máy phải xếp hàng chờ nhận OTP $\rightarrow$ gây timeout hàng đợi và dễ bị Google chain-ban toàn bộ đàn tài khoản.
- **Tại sao phải Bật 2FA Ngay Trong Flow Reg (Không ngâm tài khoản rồi bật sau)**:
  - Khi truy cập vào mục **Bảo mật và đăng nhập $\rightarrow$ Xác minh 2 bước** trên Google Account, Google **BẮT BUỘC yêu cầu nhập lại mật khẩu của tài khoản** để xác minh danh tính.
  - Nếu ngâm vài ngày mới bật 2FA: Tài khoản có thể bị khóa re-login/checkpoint, đồng thời mất mật khẩu nếu không được lưu trước.
  - **Quy trình chuẩn tối ưu**:
    1. Tích hợp bước Bật 2FA **ngay sau Bước 13 của `gmail_reg_v10.py`** (khi tài khoản vừa đăng nhập thành công vào Gmail).
    2. Mật khẩu `acc["pass"]` đang có sẵn trong RAM $\rightarrow$ tự động điền vào màn hình xác minh danh tính của Google.
    3. Chọn phương thức *Ứng dụng Authenticator* $\rightarrow$ nhấn *Không thể quét mã QR* $\rightarrow$ trích xuất Base32 Secret Key (32 ký tự).
    4. Sinh mã OTP 6 số tức thời qua thư viện `pyotp.TOTP(secret_key).now()`.
    5. Điền OTP xác nhận kích hoạt 2FA thành công.
    6. Lưu `secret_key` vào payload kết quả `machine_XX.success.json` để script `merge_success_results.py` đồng bộ thẳng vào Cột 4 (`2FA`) của `gmail_clean_v2.xlsx`.
