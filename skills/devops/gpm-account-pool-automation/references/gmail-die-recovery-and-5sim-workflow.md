# Quy Trình Cứu Gmail DIE / Checkpoint Phone & Thuê SIM 5sim Bền Vững

## 1. Bản Chất Các Dạng Checkpoint Phone Google
Khi tài khoản Gmail bị gắn cờ DIE hoặc dính checkpoint xác minh trên môi trường mới (GPM, Playwright CDP):

1. **Google báo "Không tìm thấy tài khoản" (Account Not Found)**:
   - Tài khoản đã bị Google purge/xóa vĩnh viễn khỏi server. Không thể khôi phục bằng số điện thoại hay SIM.
2. **Google hỏi "Xác nhận số điện thoại khôi phục của bạn" (Confirm recovery phone)**:
   - Google CHỈ dùng số điện thoại như câu hỏi bảo mật (Security Question).
   - KHÔNG bắt nhận tin nhắn SMS. Chỉ cần nhập đúng chuỗi số cũ đã lưu trong sổ cái Excel (ví dụ `0929212741`) là Google đối soát khớp và chuyển tiếp.
3. **Google yêu cầu "Nhận mã xác minh tại số ••••••••XX" (SMS to existing phone)**:
   - Nếu SIM cũ đang giữ: bấm nhận mã SMS hoặc cuộc gọi để nhập OTP.
   - Nếu nhập thử mã hoặc gửi SMS quá nhiều lần trong thời gian ngắn, Google sẽ kích hoạt rate-limit: `"Bạn đã thử quá nhiều lần. Vui lòng thử lại sau"`.
   - **Xử lý Rate-limit**: Đưa tài khoản vào `cooldown_7days` (tối thiểu 48h - 7 ngày), đóng profile không probe liên tục để tránh ăn hard ban.
4. **Google yêu cầu "Nhập số điện thoại để nhận tin nhắn mã xác minh" (Anti-bot checkpoint)**:
   - Màn hình thông báo: *"Google sẽ lưu trữ và chỉ sử dụng số điện thoại này cho mục đích bảo mật"*.
   - Cho phép nhập MỘT SỐ ĐIỆN THOẠI MỚI BẤT KỲ (dùng được SIM thuê 5sim).

---

## 2. Quy Trình Thuê Số 5sim & Gỡ Số Sau Khi Cứu (Zero SIM Dependency)
Khi dùng dịch vụ OTP ảo (như 5sim, sản phẩm `google`, quốc gia `vietnam` giá ~$0.18):
- **Vấn đề**: SIM thuê qua dịch vụ là số tạm thời 1 lần. Nếu để nguyên số đó làm Recovery Phone, sau này Google hỏi lại sẽ mất tài khoản vĩnh viễn.
- **Quy trình 4 bước chuẩn**:
  1. **Bước 1 (Unlock)**: Thuê số từ API 5sim -> Điền vào form Google -> Lấy OTP SMS -> Đăng nhập thành công vào Google Account.
  2. **Bước 2 (Đặt Giáp 2FA TOTP NGAY LẬP TỨC)**:
     - Truy cập ngay `https://myaccount.google.com/signinoptions/twosv`.
     - Bật tính năng **Ứng dụng xác thực (Authenticator App / TOTP)**.
     - Sao lưu Secret Key Base32 vào cột `2FA_Secret` trong Master Excel.
  3. **Bước 3 (Gỡ / Xóa số điện thoại 5sim)**:
     - Truy cập `https://myaccount.google.com/signinoptions/rescuephone` hoặc `myaccount.google.com/phone`.
     - Bấm biểu tượng Thùng rác để xóa số SIM tạm. Khi Google yêu cầu xác minh danh tính để xóa số, nhập mã TOTP vừa tạo ở Bước 2.
  4. **Bước 4 (Cập nhật Sổ Cái Excel)**:
     - Cập nhật Secret 2FA, đưa tài khoản từ sheet `Gmail_DIE_Archive` trở lại sheet `LIVE` (`Master_All`, `Kibe_Farm_S7`), xóa bỏ hoàn toàn phụ thuộc vào SIM vật lý.

---

## 3. Quy Tắc Giữ Profile GPM (Không Tự Ý Đóng Trình Duyệt)
- **Pitfall**: Agent sau khi tự động điền Email, Password, và SĐT đến màn hình chờ OTP lại gọi `browser.close()` hoặc đóng profile GPM.
- **Hậu quả**: Khi User định cầm điện thoại lấy mã nhập vào thì cửa sổ trình duyệt đã bị tắt, làm phiên đăng nhập bị hủy bỏ và dễ dính rate-limit Google.
- **Invariant**:
  - Khi script automation dẫn dắt luồng đăng nhập đến màn hình **Chờ OTP / Nhập Code**, BẮT BUỘC giữ nguyên cửa sổ trình duyệt mở trên màn hình (`disconnect()` CDP thay vì `close()`).
  - Chụp ảnh màn hình lưu `debug_screenshots/` và thông báo rõ tên Profile GPM đang mở để User tương tác trực tiếp.

---

## 4. Quản Lý Sổ Cái Excel Khi Gmail DIE
- Tuyệt đối KHÔNG xóa dòng dữ liệu khỏi `master_gmail_manager.xlsx`.
- Duy trì sheet riêng **`Gmail_DIE_Archive`** chứa toàn bộ tài khoản DIE kèm 16 cột thông tin gốc (Email, Password, Recovery Email, 2FA, SĐT đã ver, ChatGPT_Reg, Profile GPM).
- Dữ liệu tài khoản ChatGPT / Codex tạo bằng Email/Password độc lập với Google Auth — ngay cả khi Gmail bị Google khóa, tài khoản ChatGPT vẫn có thể login độc lập bằng Email + Password đó trừ khi sử dụng Google SSO.
