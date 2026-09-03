# Quy tắc đặt tên Việt hóa, ưu tiên Graph API & Chạy Batch Song Song (2026-08-18)

### 1. Quy tắc chạy batch song song (Parallel execution)
- Khi user yêu cầu "chạy reg các máy X, Y, Z", phải kích hoạt chạy batch song song toàn bộ các máy mục tiêu thông qua `_run_all_targets.py --full-scope-takeover`.
- **Tuyệt đối KHÔNG chờ hay dừng các máy khác vì 1 máy bị lỗi.** Các máy độc lập về thiết bị và tài khoản, máy nào lỗi thì dừng ghi nhận màn hình lỗi máy đó, các máy còn lại vẫn phải chạy tiếp cho xong.

### 2. Ưu tiên Microsoft Graph API cho Hotmail (Loại 2 có token)
- Mailbox Hotmail/Outlook có `refresh_token` trong `gmail_clean_v2.xlsx` phải ưu tiên 100% đọc OTP / Magic Link qua Graph API trên PC.
- Chỉ mở app Outlook trên thiết bị Android khi mailbox không có token trong file hoặc Graph API trả về rỗng sau timeout.
- Tránh mở app Outlook vì:
  1. Dễ bấm nhầm mail xác minh cũ từ hôm trước.
  2. Khi mở link xác minh dễ bị kẹt dialog chọn trình duyệt ("Mở bằng") hoặc popup Privacy của Google Chrome ("Quyền riêng tư nâng cao trong quảng cáo").

### 3. Đặt Tên hiển thị và Biệt danh (@handle) chế kiểu Việt Nam
- **Tên hiển thị (Display Name):**
  - Rút gọn phần đầu email, đối chiếu bảng âm gần tiếng Việt (ví dụ: `Gaye...` → Gia, `Lilyan...` → Linh, `Debi...` → Diệp, `Daunte...` → Đan, `Steven...` → Thịnh).
  - Nếu không khớp bảng âm, chọn ngẫu nhiên từ danh sách tên Việt phổ biến (*Minh, Linh, Hà, An, Chi, Lan, Hân, Vy, Khoa, Nam, Tuấn, Dũng, Phong, Huy, Hoàng, Thảo, Trang, Mai, Quỳnh, Hương, Ngọc...*).
- **Biệt danh / Handle (@username):**
  - Tạo dạng `ten_viet + so_duoi` (ví dụ: `gia4667`, `linh_271`, `dan.2198`, `an_9104`...).
  - Hạn chế tối đa việc giữ nguyên chuỗi ký tự tiếng nước ngoài dài dòng từ email gốc.

### 4. Tự đọc ảnh (Vision analyze) trước khi gửi cho user
- Khi chụp màn hình lỗi và gửi cho user, agent phải tự chạy vision để soi kỹ các thành phần trên ảnh (nút bấm, text điều khoản, popup che...) trước khi báo cáo.
- Không gửi ảnh suông mà không đọc, dẫn đến việc không phát hiện ra click nhầm vào text disclaimer/điều khoản thay vì nút "Tiếp tục".
