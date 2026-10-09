# Sensitive Marker Exemption & Mixed-UI Review Pattern

## Bối cảnh bài học (Case 174 — 17/09/2026)
Trên các hệ thống nhận diện giao diện và phân loại màn hình (như `has_sensitive_marker()` trong `automation-core` và `python_runner`), các quy tắc nhạy cảm thường kết hợp giữa:
1. `SENSITIVE_POPUP_TERMS` (từ khóa văn bản: *"tài khoản"*, *"credential"*, v.v.)
2. `sensitive_action_terms` (nút bấm hành động: *"đăng nhập"*, *"login"*, *"xác minh"*, *"tiếp tục"*, *"đóng"*, *"close"*).

Khi một popup lành tính (ví dụ: Card gợi ý bạn bè / *"Tài khoản được đề xuất"* trên TikTok Friends tab) mang tiêu đề chứa từ *"tài khoản"* và có nút icon *"Đóng"*, bộ lọc sẽ kích hoạt nhầm thành `manual-needed:login` (báo động giả mất phiên / văng account).

---

## 1. Sai lầm phổ biến & Bị OmniRoute Gate 1 REJECT
### Anti-Pattern: Early Blanket Bypass
Chèn điều kiện miễn trừ ngay đầu hàm:
```python
# SAI LẦM: Bị Reviewer REJECT vì tạo lỗ hổng bảo mật
if detect_contact_follow_suggestion(root) is not None:
    return False
```
* **Lý do bị REJECT:** Nếu một giao diện độc hại hoặc sự cố kết hợp xuất hiện (Mixed-UI: vừa có card gợi ý bạn bè, vừa có ô nhập mật khẩu, Captcha, hoặc dialog bắt đăng nhập tài khoản thực sự), việc `return False` sớm sẽ vô hiệu hóa toàn bộ các bước kiểm tra an toàn phía sau, dẫn tới bỏ lọt màn hình nhạy cảm.

---

## 2. Giải pháp chuẩn đạt APPROVED: Phân Tầng Thao Tác Nhạy Cảm Thực Sự (Tiered Action Validation)
Thay vì bypass toàn bộ, phải tách các hành động nhạy cảm thành 2 nhóm:

1. **Nhóm Hành Động Nhạy Cảm Tuyệt Đối (`real_sensitive_actions`):**
   * Bao gồm: `"đăng nhập"`, `"sign in"`, `"login"`, `"mật khẩu"`, `"password"`, `"tiếp tục"`, `"continue"`, `"xác minh"`, `"verify"`, `"gửi mã"`, `"send code"`.
   * Luôn kiểm tra nhóm này **TRƯỚC**. Nếu UI có bất kỳ nút nào thuộc nhóm này -> **BẮT BUỘC `return True` ngay lập tức**.

2. **Điểm Miễn Trừ Có Điều Kiện Cho Popup Lành Tính:**
   * Sau khi đã loại trừ `strong_terms` (captcha, otp, challenge), loại trừ `EditText`, và loại trừ `real_sensitive_actions`:
   ```python
   # Exempt contact/follow suggestions only when confirmed to lack real sensitive actions
   if detect_contact_follow_suggestion(root) is not None:
       return False
   ```

3. **Nhóm Hành Động Chung Chung (`generic_close_actions`):**
   * Bao gồm các nút thông thường: `"đóng"`, `"close"`.
   * Đặt ở cuối cùng. Chỉ những popup nhạy cảm khác (không phải suggestion đã được miễn trừ) mới bị đánh cờ nhạy cảm vì nút đóng.

---

## 3. Checklist Khi Sửa Bộ Lọc Phân Loại Màn Hình (Screen Classifier)
1. Có phân tách giữa hành động nhạy cảm đặc trưng (login, pass, otp) và hành động chung (close, back) không?
2. Có nguy cơ bypass nhầm khi màn hình xuất hiện đồng thời cả UI rác và UI bảo mật thực sự (mixed state) không?
3. Có chạy kiểm thử hồi quy trên cả 2 trường hợp:
   - [x] UI dump thật của sự cố (phải nhận diện đúng thành benign popup).
   - [x] Canonical test suite của repo (không được làm gãy các test bảo mật hiện có).
