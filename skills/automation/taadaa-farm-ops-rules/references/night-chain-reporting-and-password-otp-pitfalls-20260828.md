# Night Chain Pipeline Reporting & Registration Failures (2026-08-28)

## 1. Yêu cầu định dạng báo cáo chuỗi đêm (Gmail -> TikTok)
- Báo cáo chuỗi đêm `night-chain-reg-pipeline` BẮT BUỘC phân tách rõ kết quả từng phase:
  - **Phase 1: Reg Gmail** (Số lượng Total, Success, Failed; Liệt kê danh sách máy thành công và từng máy thất bại kèm lý do).
  - **Phase 2: Reg TikTok** (Số lượng Total, Success, Failed; Liệt kê danh sách máy thành công và từng máy thất bại kèm lý do).
- Không được trả dòng tóm tắt 1 dòng mơ hồ hoặc fallback chung chung.

## 2. Pitfall: OTP Entry bị gõ nhầm vào ô Mật khẩu khi TikTok báo "Mật khẩu sai"
- **Hiện tượng:** Sau bước điền mật khẩu đăng ký ([8] Fill password), TikTok không tạo acc mới mà chuyển sang flow đăng nhập tài khoản cũ và báo lỗi đỏ "Mật khẩu sai" (`resource-id="com.ss.android.ugc.trill:id/i7f"`).
- **Lỗi script:** Script nhảy sang bước sau lấy OTP Graph API 6 số, sau đó hàm `enter_otp_code` thấy màn hình có EditText (chính là ô password cũ) liền gõ thẳng 6 số OTP vào ô mật khẩu, dẫn tới lỗi lặp "Mật khẩu sai" và timeout.
- **Quy tắc an toàn:**
  - `enter_otp_code` và các hàm nhập OTP phải kiểm tra chính xác màn hình có phải là màn hình nhập mã xác minh (OTP/Verification code) hay không trước khi gõ.
  - Tuyệt đối không gõ OTP vào ô Password khi màn hình đang ở trạng thái Login / Mật khẩu sai.
