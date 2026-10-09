# Sensitive Classifier Invariant: Tiered Action Validation

## Nguyên tắc cốt lõi khi sửa `has_sensitive_marker()`
Trong `automation-core` (`automation_core/tiktok/benign_popup.py`), hàm `has_sensitive_marker()` là chốt chặn bảo vệ tối cao phát hiện màn hình nhạy cảm (đăng nhập, đổi mật khẩu, OTP, captcha).

### 1. Phân biệt rõ rệt 2 lớp hành động tương tác:
- **Lớp 1: Hành động nhạy cảm thực sự (`real_sensitive_actions`)**
  - Gồm: `"đăng nhập"`, `"sign in"`, `"login"`, `"mật khẩu"`, `"password"`, `"tiếp tục"`, `"continue"`, `"xác minh"`, `"verify"`, `"gửi mã"`, `"send code"`.
  - Phải được kiểm tra **TRƯỚC** bất kỳ ngoại lệ nào. Nếu xuất hiện bất kỳ phần tử clickable nào có các nhãn này -> **BẮT BUỘC `return True`**.
- **Lớp 2: Miễn trừ có điều kiện cho Card/Popup đề xuất lành tính**
  - Ví dụ: `detect_contact_follow_suggestion(root)`.
  - Đặt sau Lớp 1. Điều này đảm bảo: nếu giao diện là trạng thái hỗn hợp (Mixed UI - vừa có card đề xuất vừa có form đăng nhập/xác minh), hệ thống vẫn ưu tiên tính an toàn và chặn đứng fail-closed.
- **Lớp 3: Hành động đóng chung chung (`generic_close_actions`)**
  - Gồm: `"đóng"`, `"close"`.
  - Đặt sau Lớp 2. Các popup khác nếu chỉ có chữ "tài khoản" và nút đóng nhưng không phải card đề xuất đã được kiểm chứng thì vẫn bị coi là nhạy cảm.

### 2. Tiêu chuẩn Reviewer APPROVED (OmniRoute Gate 1):
Mọi bản vá sửa `has_sensitive_marker()` phải chứng minh được:
1. Không tạo nhánh `return False` bao trùm (blanket early return).
2. Không thể bị bypass bởi một màn hình đăng nhập giả mạo có chèn thêm card bạn bè.
3. Vượt qua 100% test suite `tests/test_tiktok_benign_popup.py`.
