# Kỷ luật Chống Báo Cáo Láo Web Login / Registration & Phân Biệt Session DIE vs App Sync

## 1. Bài học xương máu: Bẫy Màn Hình Khách (Guest Mode Trap) & Nút "Đăng nhập"
- **Hiện tượng**: Agent chụp ảnh `chatgpt.com` thấy có ô nhập text ("Bạn đang làm gì vậy?", "Hỏi ChatGPT") liền vội vàng kết luận "Đã đăng nhập/reg thành công và vào trang chủ ChatGPT".
- **Sự thật**: Ở góc trên bên phải màn hình **vẫn còn sờ sờ nút `[Đăng nhập]` (Log in)**! Đây là giao diện Khách vãng lai (Guest Mode / Anonymous Chat) của ChatGPT khi chưa đăng nhập bất kỳ tài khoản nào.
- **KỶ LUẬT NGHIỆM THU WEB LOGIN/REG BẮT BUỘC (ANTI-FALSE-POSITIVE GATE)**:
  1. Tuyệt đối CẤM báo cáo đăng nhập/reg thành công nếu trên màn hình còn xuất hiện các từ: `Đăng nhập`, `Log in`, `Sign in`, `Đăng ký`, `Sign up`, `Bắt đầu`.
  2. Chỉ công nhận ĐÃ ĐĂNG NHẬP THÀNH CÔNG khi thỏa mãn 1 trong 2 điều kiện cứng:
     - **Có Avatar / User Profile**: OCR hoặc XML nhận diện được Avatar người dùng, Tên tài khoản (`luuhuong...`), hoặc email hiển thị trong sidebar/menu tài khoản.
     - **Trích xuất được Token/Session hợp lệ**: Script backend đọc được cookie `__Secure-next-auth.session-token` hoặc trích xuất được `access_token` hợp lệ nạp vào runtime/OmniRoute.
  3. Bất kỳ báo cáo nào vi phạm (còn nút Đăng nhập mà bảo xong) đều bị coi là **BÁO CÁO LÁO / ẢO TƯỞNG**.

---

## 2. Gốc rễ Lỗi Đồng Bộ Gmail App (Android 8 / Samsung S7): Tài Khoản DIE
- **Hiện tượng**: App Gmail trên máy S7 không chịu kéo thư về, kẹt ở màn hình *"Tài khoản chưa được đồng bộ hóa"* hoặc nhảy popup *"Cập nhật thiết bị để đảm bảo an toàn / OsVersionNudgeActivity"*.
- **Cơ chế lỗi**:
  - Khi một tài khoản Google bị khóa/vô hiệu hóa (**DIE**), Google Services trên Android bị văng token (`updateCredentials`).
  - Toàn bộ service đồng bộ nền (`AccountManagerService` & `GoogleAccountAuthenticatorService`) của app Gmail bị treo cứng. Mọi nỗ lực tap nút "Đồng bộ ngay" hoặc swipe refresh cục bộ đều vô nghĩa vì server Google từ chối cấp session cho app.
- **Quy tắc Kiểm tra & Dọn dẹp**:
  1. **Check Live trước khi chạy**: MỌI tác vụ cần Gmail (Reg ChatGPT, đổi Hotmail, lấy OTP) BẮT BUỘC phải gọi `check_gmail_is_live(email)` qua `checkmail.live`. Nếu DIE -> BỎ QUA NGAY, CẤM đâm đầu vào chạy.
  2. **Dọn kép khi phát hiện DIE**: Khi phát hiện Gmail trên máy S7 đã DIE:
     - Gỡ ngay tài khoản khỏi máy Android qua `Cài đặt > Tài khoản > Xóa tài khoản` để giải phóng app Gmail cho các tài khoản LIVE khác.
     - Đánh dấu trạng thái `DIE` trong bảng quản lý Excel (`master_gmail_manager.xlsx`), đồng thời loại bỏ khỏi `gmail_clean_v2.xlsx`.
