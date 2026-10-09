# ChatGPT Mobile Registration & S7 App Sync Safeguards

## 1. Direct Email OTP Only (STRICT INVARIANT)
- **Tuyệt đối cấm Google SSO ("Continue with Google")**:
  - Không bao giờ click vào Google SSO hoặc popup account chooser của Chrome trên Android khi reg/login ChatGPT.
  - Khi xuất hiện popup gợi ý tài khoản Google của Chrome (`"Tiếp tục bằng tài khoản của..."`, `"Đăng nhập bằng Google"`): BẮT BUỘC bấm `[Bỏ qua]` / `(540, 1780)` để đóng popup.
  - Luôn điền email trực tiếp vào ô `Email address` (`540, 1280`) -> bấm `[Tiếp tục]` (`540, 1485`) -> nhận mã 6 số OTP từ hòm thư -> điền OTP.
- **Tiêu chí nghiệm thu ChatGPT ĐĂNG NHẬP THÀNH CÔNG**:
  - TUYỆT ĐỐI KHÔNG coi màn hình có nút `[Đăng nhập]` / `[Log in]` là đã đăng nhập thành công (đó chỉ là trang chủ ở trạng thái khách).
  - Chỉ nghiệm thu thành công khi:
    1. Đã mất hoàn toàn nút `[Đăng nhập]`.
    2. Xuất hiện nút `+ Nâng cấp gói` / avatar tài khoản / lịch sử chat.
    3. Hoặc trích xuất được Session/OAuth Token hợp lệ.

## 2. Gốc rễ lỗi đồng bộ Gmail App trên Android 8 (Samsung S7)
- **Tài khoản DIE làm treo Gmail Sync**:
  - Khi 1 tài khoản Gmail trên máy bị DIE (vô hiệu hóa/khóa bởi Google), Google Services kích hoạt màn hình chặn `com.google.android.libraries.appselements.appupdate.OsVersionNudgeActivity` ("Hãy cập nhật thiết bị để đảm bảo an toàn").
  - Màn hình này làm tê liệt toàn bộ luồng đồng bộ nền (Sync service) của app Gmail trên máy, khiến cả các tài khoản LIVE khác cũng không thể kéo thư mới về.
- **Biện pháp xử lý**:
  - Phải dùng tool `check_gmail_live_fast.py` kiểm tra live TRƯỚC khi gán hoặc chạy bất kỳ tác vụ nào.
  - Gỡ bỏ ngay lập tức tài khoản Google đã DIE trong *Cài đặt Android -> Cloud và Tài khoản -> Xóa tài khoản*.
  - Sau khi gỡ tài khoản DIE, app Gmail sẽ phục hồi đồng bộ bình thường.
