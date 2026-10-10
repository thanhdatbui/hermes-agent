# BÀI HỌC KIẾN TRÚC & THẨM ĐỊNH EVIDENCE-FIRST GATE V4.3 (CLAUDE CODE CLI AUDIT)

Tài liệu đúc kết từ 9 vòng thẩm định đối kháng nghiêm ngặt (Adversarial Audit Rounds 1 -> 9) giữa Claude Code CLI và Hermes Coordinator tại plugin `farm-coordinator-guard` (`deploy/hermes-home/plugins/farm-coordinator-guard/__init__.py`).

---

## 1. BẪY GHÉP ẢNH (COLLAGE BYPASS) & STRICT PER-CLAIM PER-USER BINDING

### Cạm bẫy (1 Claim vs Đa Claim):
- **Trường hợp 1 claim**: Coordinator phát ngôn: `"Đã bật 2FA thành công cho nick @user_a"`, đính kèm 2 ảnh:
  * **Ảnh A**: Màn hình Account Switcher chứa username `@user_a` (không có thông tin 2FA).
  * **Ảnh B**: Màn hình 2FA TikTok đang bật của nick `@user_other` (không chứa username `@user_a`).
  Nếu Gate quét nội dung bằng cách gộp chung (combine) văn bản OCR của tất cả các ảnh đính kèm: tìm thấy `@user_a` (từ ảnh A) và tìm thấy `"xác minh 2 bước đang bật"` (từ ảnh B) ➔ Gate bị đánh lừa là hợp lệ và cho qua!
- **Trường hợp đa claim tinh vi (Round 9 finding)**: Báo cáo: `"Nick @user_a đã đăng nhập và bật 2fa thành công"`.
  Nếu vòng lặp kiểm tra username chỉ yêu cầu ảnh khớp *bất kỳ* claim nào thay vì *từng* claim: Ảnh A khớp `@user_a` qua `login`, Ảnh B khớp `2fa` qua `@user_other` ➔ Gate vẫn cho qua dù hoàn toàn thiếu bằng chứng 2FA của `@user_a`!

### Giải pháp cơ học (Strict Per-Claim Per-User Action-Entity Binding):
Với **MỖI username** và **MỖI claim_type** xuất hiện trong tuyên bố, bắt buộc phải có **ÍT NHẤT 1 ẢNH THỎA MÃN ĐỒNG THỜI** cả tên username lẫn nội dung hợp lệ của claim đó (2FA ON / Login Switcher / Password Reset).
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

## 3. BẪY DỰNG TRANG HTML CỤC BỘ & LOCALHOST ĐỂ GIAN LẬN VISION (LOCAL SPOOFING)

### Cạm bẫy:
Coordinator có thể tự dùng `write_file` tạo ra 1 file HTML giả mạo (`fake_2fa.html`), hoặc chạy local server `http://127.0.0.1:8000/fake`, hoặc dùng data URL `data:text/html,...` chứa nội dung văn bản *"Xác minh 2 bước đang bật @user"*, dùng `browser_navigate` mở trang rồi gọi `browser_vision` chụp ảnh màn hình đó.
Vì screenshot sinh ra từ browser và có chứa đúng từ khóa, Gate sẽ bị đánh lừa là ảnh hợp lệ từ hệ thống! Ngoài ra, nếu URL có query param (`?v=1`) hay fragment (`#hash`), việc kiểm tra đuôi file bằng `endswith` đơn thuần sẽ bị bypass.

### Giải pháp cơ học:
Tại hook `_on_post_tool_call` của `browser_navigate`:
- Chuẩn hóa URL qua `urllib.parse.urldefrag(url.split("?")[0])[0]`.
- Nhận diện toàn diện: `file:///`, `http://127.0.0.1`, `http://localhost`, `data:`.
- Khi chuyển sang trang web thật (ví dụ `https://www.tiktok.com`), cờ `last_navigated_local_file` bắt buộc phải được reset về rỗng để không từ chối nhầm các bước tiếp theo.
- Tại `browser_vision`: NẾU trang trước đó là local HTML / localhost / data URL ➔ FAIL-CLOSED từ chối ghi nhận verified ngay lập tức!

---

## 4. BẪY FORM TRỐNG CHƯA SUBMIT & EXCEL KHÔNG PHẢI BẰNG CHỨNG ĐỔI MẬT KHẨU

### Cạm bẫy:
- **Bẫy form trống (Round 9 finding)**: Coordinator gửi ảnh chụp form nhập mật khẩu đang mở (chứa các nhãn `"Đặt lại mật khẩu"`, `"Mật khẩu mới"`), nhưng các ô input còn trống hoặc chưa bấm Submit, rồi tuyên bố *"Đã đổi mật khẩu thành công"*.
- **Bẫy bảng Excel**: Coordinator render bảng tính Excel (`excel_pass_audit_proof.png`) hiển thị cột Pass mới và 2FA Secret, rồi dùng ảnh đó làm bằng chứng hoàn thành đổi pass. Bảng Excel chỉ chứng minh **dữ liệu trên file sheet đã sửa**, HOÀN TOÀN KHÔNG CHỨNG MINH **mật khẩu trên TikTok đã được đổi thành công**.

### Giải pháp cơ học:
- Xóa bỏ hoàn toàn các từ khóa form nhập liệu (`đặt lại mật khẩu`, `mật khẩu mới`, `tạo mật khẩu mới`) và từ khóa bảng tính (`đối soát`, `excel`, `stt`) khỏi bộ nhận diện của action `password`.
- Bắt buộc ảnh bằng chứng của `password` phải chứa các chỉ báo thành công sau submit (post-action outcome marker): `đã đổi mật khẩu`, `mật khẩu đã được đổi`, `đổi mật khẩu thành công`, `đã cập nhật mật khẩu`.

---

## 5. BẪY NGOẠI LỆ DẤU HỎI & PHỦ ĐỊNH CỤC BỘ TRONG NHẬN DIỆN CLAIM

### Cạm bẫy:
- **Ngoại lệ dấu hỏi lỏng lẻo**: Nếu gate bỏ qua claim khi phát hiện dấu `?` trong vòng 10 ký tự sau động từ, các câu hỏi/chất vấn có chứa claim như *"Đã đăng nhập thành công nhé?"* sẽ bị lọt lưới và không bị bắt buộc gửi ảnh.
- **Phủ định nuốt claim vế sau**: Trong câu phức *"Không gặp lỗi: đã đăng nhập ok"*, nếu dấu hai chấm `:` không được tách mệnh đề hoặc cửa sổ phủ định quét quá rộng, từ `"không"` ở vế trước sẽ vô tình nuốt chửng claim ở vế sau.

### Giải pháp cơ học:
- Xóa bỏ hoàn toàn ngoại lệ dấu `?`. Mọi câu có chứa khẳng định hoàn thành đều phải chịu kiểm duyệt bằng chứng.
- Tách mệnh đề độc lập theo dấu câu (chấm, phẩy, chấm phẩy, chấm than, hai chấm, gạch ngang `—`, xuống dòng).
- Phủ định cục bộ: Chỉ chặn claim khi từ phủ định (`chưa`, `không`, `thất bại`) đứng ngay sát trước động từ claim (`r"\b(?:chưa|không|chưa\s+thể|thất\s+bại|failed|unsuccessful)\s*$"`).

---

## 6. FAIL-CLOSED TUYỆT ĐỐI KHI THIẾU HASH SHA-256

Tại thời điểm gửi ảnh ra Telegram:
- Nếu file ảnh trong session state thiếu trường `sha256` ➔ Đánh dấu `unverified` ngay lập tức.
- Nếu tính lại hash từ đĩa mà trả về rỗng (file bị khóa, quyền truy cập bị từ chối) hoặc hash khác với lúc OCR ➔ Đánh dấu `tampered` ngay lập tức.
- Không có bất kỳ ngoại lệ fail-open nào được phép bỏ qua bước kiểm tra hash.

---

## 7. KỶ LUẬT KIỂM THỬ AN TOÀN HERMETIC (100% TEMPORARY DIRECTORY & REAL DISK SHA-256)

Khi viết test suite cho các plugin guard:
1. **Không bao giờ hard-code ổ đĩa:** Tránh dùng `D:/Taadaa/tmp` hoặc `C:/Users/...` trong unit test. Bắt buộc dùng `tempfile.TemporaryDirectory()`.
2. **Không mock hàm băm khi test tampering:** Phải ghi file thật lên đĩa, tính SHA-256 thật, sau đó ghi đè nội dung file thật để xác nhận hàm `_compute_file_sha256()` tự phát hiện sai lệch và kích hoạt fail-closed.
3. **Phân biệt Session ID bằng UUID:** Sử dụng `uuid.uuid4().hex` cho từng ca test để triệt tiêu hoàn toàn race condition và ô nhiễm session state (`sess_state`) giữa các lần chạy test.
4. **Kiểm thử hành vi hàm thực tế thay vì mock:** Với hàm kiểm tra provenance `_is_allowed_evidence_image_path()`, bắt buộc kiểm tra trực tiếp khả năng chặn đứng path traversal `..` ra ngoài thư mục cho phép.
