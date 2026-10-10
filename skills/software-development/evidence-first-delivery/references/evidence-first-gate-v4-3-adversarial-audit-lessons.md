# BÀI HỌC KIẾN TRÚC & THẨM ĐỊNH EVIDENCE-FIRST GATE V4.3 (CLAUDE CODE CLI AUDIT)

Tài liệu đúc kết từ 9 vòng thẩm định đối kháng nghiêm ngặt (Adversarial Audit Rounds 1 -> 9) giữa Claude Code CLI và Hermes Coordinator tại plugin `farm-coordinator-guard` (`deploy/hermes-home/plugins/farm-coordinator-guard/__init__.py`).

---

## 1. BẪY GHÉP ẢNH (COLLAGE BYPASS) & STRICT PER-IMAGE BINDING

### Cạm bẫy:
Coordinator phát ngôn: `"Đã bật 2FA thành công cho nick @user_a"`, đính kèm 2 ảnh:
- **Ảnh A**: Màn hình Account Switcher chứa username `@user_a` (không có thông tin 2FA).
- **Ảnh B**: Màn hình 2FA TikTok đang bật của nick `@user_other` (không chứa username `@user_a`).

Nếu Gate quét nội dung bằng cách gộp chung (combine) văn bản OCR của tất cả các ảnh đính kèm:
- Tìm thấy `@user_a` (từ ảnh A).
- Tìm thấy `"xác minh 2 bước đang bật"` (từ ảnh B).
➔ Gate bị đánh lừa là hợp lệ và cho qua!

### Giải pháp cơ học (Strict Per-Image Action-Entity Binding):
Mỗi username được nêu trong báo cáo bắt buộc phải xuất hiện trong **ÍT NHẤT 1 ẢNH THỎA MÃN ĐỒNG THỜI** cả tên username lẫn nội dung hợp lệ của action (2FA ON / Login Switcher / Password Reset).
Nếu không có ảnh đơn lẻ nào chứa đủ cả hai ➔ FAIL-CLOSED chặn đứng ngay lập tức!

---

## 2. BẪY ĐỒNG THỜI CÓ CHỮ BẬT VÀ TẮT TRONG CÙNG ẢNH (DUAL-CONDITION 2FA VETO)

### Cạm bẫy:
Một màn hình cài đặt bảo mật có thể vừa có chữ *"xác minh 2 bước đang bật"* (tiêu đề chung), nhưng mục phương thức bên dưới lại ghi *"2FA: off"* hoặc *"Trình xác thực: Tắt"*.
Nếu gate chỉ kiểm tra sự hiện diện của cụm từ dương tính (positive match) mà không kiểm tra phủ quyết âm tính chặt chẽ, báo cáo sai trạng thái sẽ lọt qua.

### Giải pháp cơ học:
Mở rộng danh sách regex phủ quyết (veto patterns):
- `\b2fa\s*[:=]\s*(?:off|tắt)\b`
- `\b(?:xác\s+minh\s+2\s+bước|2\s+bước|two-step|two-factor)\s*[:=]?\s*(?:đang\s+)?(?:tắt|off)\b`
- `\btrình\s+xác\s+thực\s*[:=]?\s*(?:tắt|off)\b`
- `\bvô\s+hiệu\s+hóa\b`

Nếu ảnh chứa bất kỳ biến thể tắt nào trên ➔ Tự động loại trừ ảnh đó khỏi danh sách bằng chứng hợp lệ cho claim 2FA.

---

## 3. BẪY DỰNG TRANG HTML CỤC BỘ ĐỂ GIAN LẬN VISION (LOCAL HTML SPOOFING)

### Cạm bẫy:
Coordinator có thể tự dùng `write_file` tạo ra 1 file HTML giả mạo (`fake_2fa.html`) chứa nội dung văn bản *"Xác minh 2 bước đang bật @user"*, dùng `browser_navigate` mở `file:///fake_2fa.html`, rồi gọi `browser_vision` chụp ảnh màn hình đó.
Vì screenshot sinh ra từ browser và có chứa đúng từ khóa, Gate sẽ bị đánh lừa là ảnh hợp lệ từ hệ thống!

### Giải pháp cơ học:
Tại hook `_on_post_tool_call` của `browser_vision`:
- Bắt buộc kiểm tra `last_navigated_local_file` từ session state.
- NẾU URL điều hướng trước đó là file cục bộ có đuôi `.html` hoặc `.htm` ➔ FAIL-CLOSED từ chối ghi nhận verified ngay lập tức!

---

## 4. BẪY DÙNG BẢNG EXCEL LÀM BẰNG CHỨNG THAO TÁC THIẾT BỊ (EXCEL VS DEVICE PROOF)

### Cạm bẫy:
Sau khi đổi pass hoặc bật 2FA, Coordinator render bảng tính Excel (`excel_pass_audit_proof.png`) hiển thị cột Pass mới và 2FA Secret, rồi dùng ảnh đó làm bằng chứng hoàn thành đổi pass.
Bảng Excel chỉ chứng minh **dữ liệu trên file sheet đã sửa**, HOÀN TOÀN KHÔNG CHỨNG MINH **mật khẩu trên TikTok đã được đổi thành công**.

### Giải pháp cơ học:
- Xóa bỏ hoàn toàn các từ khóa chung chung như `đối soát`, `excel`, `stt` khỏi bộ nhận diện của action `password`.
- Bắt buộc ảnh bằng chứng của `password` phải chứa các từ khóa đặc trưng của màn hình thiết bị TikTok thật: `mật khẩu mới`, `tạo mật khẩu mới`, `đã đổi mật khẩu`, `thay đổi mật khẩu`.

---

## 5. KỶ LUẬT KIỂM THỬ AN TOÀN HERMETIC (100% TEMPORARY DIRECTORY & REAL DISK SHA-256)

Khi viết test suite cho các plugin guard:
1. **Không bao giờ hard-code ổ đĩa:** Tránh dùng `D:/Taadaa/tmp` hoặc `C:/Users/...` trong unit test. Bắt buộc dùng `tempfile.TemporaryDirectory()`.
2. **Không mock hàm băm khi test tampering:** Phải ghi file thật lên đĩa, tính SHA-256 thật, sau đó ghi đè nội dung file thật để xác nhận hàm `_compute_file_sha256()` tự phát hiện sai lệch và kích hoạt fail-closed.
3. **Phân biệt Session ID bằng UUID:** Sử dụng `uuid.uuid4().hex` cho từng ca test để triệt tiêu hoàn toàn race condition và ô nhiễm session state (`sess_state`) giữa các lần chạy test.
