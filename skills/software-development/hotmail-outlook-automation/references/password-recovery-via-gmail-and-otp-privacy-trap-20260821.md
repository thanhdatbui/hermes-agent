# Khôi phục mật khẩu Hotmail qua Gmail & Bẫy bóc tách OTP Microsoft (2026-08-21)

## 1. Khôi phục mật khẩu Hotmail bị sai Pass qua Gmail khôi phục

Khi tài khoản Hotmail trong kho bị sai mật khẩu (hoặc báo lỗi `! Mật khẩu đó không đúng...`):
- **Không cần mật khẩu cũ:** Nếu tài khoản đã được liên kết với email khôi phục `thanhdatbui1995@gmail.com`, có thể đặt lại mật khẩu trực tiếp qua cổng `https://account.live.com/password/reset`.
- **Quy trình Reset:**
  1. Mở Chrome trên máy tương ứng (chạy qua IP Proxy của máy).
  2. Điều hướng vào `https://account.live.com/password/reset`.
  3. Nhập địa chỉ Hotmail cần khôi phục -> Bấm **Tiếp theo**.
  4. Microsoft hiển thị màn hình *"Chúng tôi cần xác nhận định danh của bạn"* với tùy chọn radio *"Gửi email đến th*****@gmail.com"*.
  5. Điền phần tên email `thanhdatbui1995` (màn này đã có sẵn đuôi `@gmail.com` cố định) -> Bấm **Nhận mã**.
  6. Script tự động kết nối IMAP `imap.gmail.com` vào `thanhdatbui1995@gmail.com` (sử dụng Google App Password) để lấy mã 6 chữ số.
  7. Nhập mã OTP vào ô *"Nhập mã"* -> Bấm **Tiếp theo**.
  8. Màn hình chuyển thẳng sang **"Đặt lại mật khẩu của bạn"** -> Nhập mật khẩu mới vào cả 2 ô và Lưu.

---

## 2. Bẫy bóc tách OTP: Link ID `521839` của Microsoft

### Triệu chứng lỗi:
Script đọc OTP từ Gmail trả về mã `521839`, nhập vào Microsoft báo đỏ: *"Mã này không hoạt động. Kiểm tra mã và thử lại."*

### Nguyên nhân:
Cuối mọi email xác thực và đặt lại mật khẩu của Microsoft luôn có dòng điều khoản quyền riêng tư:
`Điều khoản về Quyền riêng tư: https://go.microsoft.com/fwlink/?LinkId=521839`
Hàm regex bóc tách mã 6 chữ số nếu tìm chung chung hoặc tìm từ dưới lên sẽ bắt nhầm chuỗi số `521839` (LinkId của Microsoft) thay vì mã OTP thực tế (`578147`, `633406`, ...).

### Cách xử lý chuẩn (`flows/hotmail_recovery.py`):
1. Ưu tiên bóc tách theo cụm từ chính xác: `(?:ma cua ban|code is|security code is|ma bao mat)[^\d]{0,20}(\d{6})`.
2. Lọc bỏ tuyệt đối chuỗi `521839` trong danh sách candidates mã 6 số.

---

## 3. Phân biệt ô nhập Email khôi phục: Reset Form vs Security Proof Form

- **Màn hình Reset (`account.live.com/password/reset`):** Form có sẵn đuôi `@gmail.com` cố định ở bên ngoài ô nhập -> Chỉ cần gõ prefix: `thanhdatbui1995`.
- **Màn hình Security Proof khi đăng nhập Chrome (`login.live.com` - "Xác minh email của bạn"):** Ô nhập liệu có nhãn "Email" trống hoàn toàn -> **BẮT BUỘC gõ đầy đủ toàn bộ địa chỉ:** `thanhdatbui1995@gmail.com`. Nếu chỉ gõ prefix `thanhdatbui1995`, Microsoft sẽ báo lỗi đỏ: *"Email này không trùng với email thay thế liên kết với tài khoản của bạn. Email chính xác bắt đầu bằng 'th'."*

---

## 4. Quy tắc quản lý Device Lock khi điều tra & sửa máy (User Invariant)
- **CẤM tự ý mở lock (release lock) các máy đang trong diện sửa/fix:** Khi user yêu cầu "lock máy lại để fix", lease lock trong `C:\Users\Kibe\.codex\device-locks` phải được giữ nguyên (`release_on_terminal=False` hoặc duy trì file lock) cho đến khi toàn bộ quy trình hoàn tất và có xác nhận từ user.
- Tuyệt đối không tự tiện giải phóng lock giữa chừng khiến các batch/cronjob khác can thiệp vào máy đang xử lý.
