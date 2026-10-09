# Account Switcher Sticky Header, Save Login & Email Disable Enforcement (07/09/2026)

## 1. Bản Vá Cốt Lõi Lỗi `SWITCHER_OPEN_FAILED` (Máy 1)

### Vấn đề thực tế:
Khi chạy kịch bản bật 2FA (`run_capture_phase_b.py`), máy dừng lại ở trang Profile và văng ngoại lệ `SWITCHER_OPEN_FAILED` sau 3 lượt thử.

### Bộ 3 nguyên nhân gốc rễ & Cách khắc phục chuẩn:
1. **Bắt nhầm Username ở Thân Profile (`account_switcher.py`):**
   - Trong hàm `find_switcher_anchor()`, đoạn lọc `username_candidates` có nhánh:
     `or (has_profile_menu and node.attributes.get("clickable") == "true")`
     nhánh này thiếu chặn trần tọa độ Y.
   - Trên TikTok Máy 1, node text `@tranngan767` nằm ở thân profile dưới avatar (`bounds=[400,594][679,639]`, `center_y = 616`) nhưng lại có `clickable="true"` và có `has_profile_menu=True`.
   - Hậu quả: `find_switcher_anchor` chọn nhầm text ở giữa màn hình làm anchor. Vì `anchor is not None`, code bỏ qua hàm `prepare_switcher_anchor()` (swipe 400px lên) và tap trượt vào thân profile.
   - **Khắc phục:** Bổ sung điều kiện `and node.center[1] <= generic_header_y` cho `username_candidates`, `identity_candidates`, `preferred_candidates`. Đảm bảo mọi candidate mở switcher ở header PHẢI nằm trong khu vực header đỉnh (`center_y <= generic_header_y`).

2. **Xung đột cặp Resource Node Cha-Con (`pmi` vs `pmf`):**
   - Sau khi thực hiện vuốt nhẹ `prepare_switcher_anchor()` (`swipe 540 1248 540 806 150`), sticky header hiển thị trên đỉnh gồm:
     - Node cha `pmi`: `LinearLayout` bao bọc ngoài (`clickable="true"`, `bounds=[377,72][704,228]`).
     - Node con `pmf`: `TextView` tên nick bên trong (`clickable="false"`, `bounds=[377,117][704,183]`).
   - Cả 2 node đều khớp đuôi `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`, làm danh sách `resource_candidates` có độ dài bằng 2. Code cũ chỉ kiểm tra `if len(resource_candidates) == 1:` nên bỏ qua luôn, không chọn được anchor nào.
   - **Khắc phục:** Khi `len(resource_candidates) > 1`, ưu tiên lọc các node có `clickable="true"`:
     ```python
     if len(resource_candidates) > 1:
         clickable = [n for n in resource_candidates if n.attributes.get("clickable", "false").casefold() == "true"]
         if len(clickable) == 1:
             resource_candidates = clickable
     ```

3. **Bẫy `attempts=1` trong Consumer Adapter (`account_preflight.py`):**
   - Hàm `verify_and_switch_account` gọi `canonical.open_switcher(adapter, attempts=1)`.
   - Khi `attempts=1`, attempt 0 chạy `prepare_switcher_anchor()` (vuốt 400px lên) rồi gặp `continue`, khiến vòng lặp kết thúc ngay lập tức trước khi attempt 1 kịp tap vào sticky header vừa lộ ra.
   - **Khắc phục:** Đổi sang `attempts=2 if adb is not None else 1`. Khi chạy live trên máy thật (`adb is not None`) dùng 2 attempts để vuốt và tap; khi chạy unit test mock (`adb is None`) giữ 1 attempt để không làm cạn kiệt mock iterator.

---

## 2. Bắt Buộc Gạt BẬT "Lưu thông tin đăng nhập" (Save Login)

### Yêu cầu vận hành:
- Khi bật 2FA trên tài khoản farm, **BẮT BUỘC gạt BẬT công tắc "Lưu thông tin đăng nhập"** (`checked="true"` / nhãn BẬT).
- **Mục đích:** Giúp TikTok ghi nhớ phiên đăng nhập của nick trên thiết bị này. Sau này khi chuyển đổi tài khoản (Account Switcher) hoặc trong các ca chạy nuôi tự động, máy sẽ không bị văng hỏi lại mật khẩu.

### Tích hợp chuẩn vào `live_phase_b_adapter.py`:
1. **Hàm `ensure_save_login_enabled(self)`:**
   Quét UI dump tối đa 3 lần tìm switch `Lưu thông tin đăng nhập`. Nếu `checked == False`, tap vào switch để bật sang `checked == True`.
2. **Điểm gọi:**
   Gắn trực tiếp vào `navigate_and_verify_account()` ngay sau khi vào màn hình `Bảo mật & quyền` (`F2AScreen.SECURITY`) và trước khi bấm vào `Xác minh 2 bước`.

---

## 3. Bắt Buộc Tắt Xác Minh Qua Email Sau Khi Bật Authenticator

### Yêu cầu vận hành:
- Sau khi bật thành công **Trình xác thực (Authenticator)**, tài khoản **BẮT BUỘC phải tắt phương thức xác minh qua Email**.
- **Mục đích:** Đảm bảo tài khoản 100% chỉ sử dụng Secret Key TOTP để xác thực 2 bước. Nếu vẫn để Email bật, khi đăng nhập từ thiết bị lạ TikTok sẽ ưu tiên gửi OTP về email, gây kẹt hoặc lỗi xác minh nếu hộp thư gặp sự cố.

### Thao tác chuẩn trong `disable_email_and_confirm_stable()`:
1. Tap vào dòng `Email` (có text hoặc content-desc bắt đầu bằng "Email").
2. Dialog xuất hiện với thông báo *"Bạn hiện đang sử dụng email này để nhận mã xác minh."* $\rightarrow$ Bấm nút **"Xóa"**.
3. Dialog xác nhận xuất hiện *"Xóa email?"* $\rightarrow$ Bấm nút **"Xác nhận"**.
4. Polling kiểm tra lại XML: `_method_checked(xml, "Email") is False`.
5. Trạng thái chuẩn cuối cùng của màn hình Xác minh 2 bước:
   - **Email:** `Tắt` (Checked = False).
   - **Điện thoại:** `Tắt` (Checked = False).
   - **Trình xác thực:** `Bật` (Checked = True).
   - **Mật khẩu:** `Bật` (Checked = True).

---

## 4. Checklist Nghiệm Thu 4 Điểm (Bắt Buộc Xác Minh Bằng Ảnh Thật)

Trước khi báo cáo hoàn thành ca Add 2FA cho bất kỳ máy nào, Coordinator BẮT BUỘC đối chiếu ảnh chụp màn hình thật với 4 tiêu chí:
- [ ] **1. Đúng Username:** Tên tài khoản hiển thị trên màn hình phải khớp 100% với nick được giao (cấm nhìn nhầm nick cũ).
- [ ] **2. Xác minh 2 bước = BẬT:** Dòng "Xác minh 2 bước" phải hiển thị chữ **`Bật`** (hoặc thanh trạng thái đỉnh ghi "Xác minh 2 bước đang bật").
- [ ] **3. Lưu thông tin đăng nhập = BẬT:** Switch "Lưu thông tin đăng nhập" phải ở trạng thái **`checked="true"`** (màu xanh).
- [ ] **4. Email = TẮT:** Trong chi tiết các phương thức, mục Email phải hiển thị chữ **`Tắt`** (chỉ còn Trình xác thực và Mật khẩu là Bật).
