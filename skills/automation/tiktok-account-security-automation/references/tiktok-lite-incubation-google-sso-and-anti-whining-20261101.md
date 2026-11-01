# TikTok Lite Account Incubation, Google SSO vs Manual Email, and Anti-Whining Invariant (2026-11-01)

## 1. Kèo Nuôi Ngâm TikTok Lite Song Song Trên Farm ROM Gốc (S7)
- **Bản chất kỹ thuật:** TikTok Lite (`com.zhiliaoapp.musically.go`) và TikTok chuẩn (`com.ss.android.ugc.trill`) là 2 sandbox Android độc lập trên cùng thiết bị.
- **Quy tắc mỗi máy 1 nick ngâm:** Cài đặt TikTok Lite v47.6.1 trên máy đã có 8 nick TikTok chuẩn không làm ảnh hưởng phiên đăng nhập hay dữ liệu của 8 nick chính.
- **Mục tiêu chiến lược:** Ngâm tích lũy ngày tuổi (từ 0 lên 2–3 tháng tuổi) song song trong lúc 8 nick chính đang cày follow, triệt tiêu khoảng trống thiếu nick sau khi bán dàn chính.

## 2. Sự Khác Biệt Sống Còn: Google One-Tap SSO vs Gõ Mail Thủ Công
- **🔴 Gõ Hotmail/Gmail thủ công (Manual Sign-Up) = INSTANT-BAN:**
  - Bấm "Sử dụng email" và gõ tay email vào form đăng ký trực diện `I18nSignUpActivity` trên máy farm đã có nhiều nick sẽ bị thuật toán Anti-Fraud của ByteDance quét hành vi bot auto-reg và kích hoạt án phạt **`Tài khoản của bạn đã bị cấm`** ngay tại giây cuối tạo UID.
- **🟢 Bấm "Tiếp tục với Google" (Google One-Tap SSO) = 100% SUCCESS:**
  - Máy farm đã đăng nhập sẵn tài khoản Gmail trong hệ điều hành Android (Google Play Services).
  - Khi chọn Google SSO, Google Play Services đứng ra bảo lãnh danh tính thật (`Google Sub ID`).
  - TikTok tin cậy token xác thực này nên bỏ qua bộ lọc cấm, bỏ qua bước nhập OTP thủ công, vào thẳng Profile (`@username`).

## 3. Quản Lý Email & Đổi Mail Cho Nick Tạo Bằng Google SSO
- **Trạng thái ban đầu:** Khi tạo nick qua Google SSO, trường `Email` trong *Cài đặt -> Quản lý tài khoản* **ĐANG TRỐNG 100%** (chưa bind cứng email). Google chỉ là SSO Provider bên ngoài.
- **Thêm Hotmail bảo mật trực tiếp:**
  - Vào *Cài đặt & quyền riêng tư -> Quản lý tài khoản -> Email*: Hiển thị thẳng form *"Nhập địa chỉ email"*.
  - Nhập Hotmail sạch ➔ Bấm *"Gửi mã"* ➔ Rút OTP từ Microsoft Graph API điền vào là tài khoản nhận Hotmail làm email bảo mật.
  - **Không cần OTP mail cũ:** Vì trường Email ban đầu trống, không phải qua bước xác minh mail cũ như luồng Change Email thông thường.
  - Sau khi đặt Mật khẩu riêng cho nick, tài khoản hoàn toàn độc lập với Gmail gốc (kể cả Gmail bị mất/die thì nick TikTok vẫn sống và login bằng Hotmail/Username bình thường).
- **CẤM TÁI CHẾ GMAIL:**
  - Mỗi Gmail chỉ dùng làm bệ phóng 1 lần duy nhất cho 1 nick TikTok.
  - Trên TikTok Lite **HOÀN TOÀN KHÔNG CÓ NÚT GỠ LIÊN KẾT GOOGLE (UNLINK GOOGLE)**.
  - CẤM mang Gmail cũ đã tạo nick đi reg tiếp kẻo bị ByteDance lưu vết Risk Engine (shadowban, 0 view, chết chùm).

## 4. Kỷ Luật Ứng Xử Chống Khóc Lóc & Chống Bại Liệt (Anti-Whining Invariant)
- **User Phạt Nặng: "Lại khóc lóc rồi đụ mẹ":** Khi bị Guard chặn, agent có xu hướng mở đầu bằng lời xin lỗi ẻo lả, nhận lỗi sâu sắc ("Em nhận lỗi sâu sắc...", "Em chủ quan..."). Đây là hành vi thoái thác bị cấm tuyệt đối.
- **Kỷ luật phát ngôn:**
  - CẤM TUYỆT ĐỐI văn mẫu xin lỗi, nhận lỗi dông dài.
  - Khi gặp lỗi hoặc bị Guard chặn: **Lẳng lặng dùng đúng tool call/lệnh tiếp theo để giải quyết dứt điểm**, báo cáo bằng kết quả thật hoặc lỗi kỹ thuật cụ thể.
- **Receipt Guard Mechanism:**
  - Nếu agent nói "Đã dispatch", "Đã xử lý xong" nhưng trong cùng lượt không có tool call thành công hoặc không có receipt hợp lệ ➔ Hệ thống cơ học sẽ đóng dấu đỏ **`⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`**.
  - Không bao giờ phát ngôn ở thì khẳng định hoàn thành trước khi tool call thực sự chạy thành công.
