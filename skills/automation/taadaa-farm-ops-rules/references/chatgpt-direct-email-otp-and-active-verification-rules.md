# Quy chuẩn Vận hành Reg ChatGPT trên Samsung S7 & Invariant Bắt buộc (19/09/2026)

## 1. INVARIANT TỐI CAO: BẮT BUỘC DIRECT EMAIL OTP, CẤM GOOGLE SSO
- **Quy tắc tuyệt đối**: Mọi quy trình đăng ký/liên kết ChatGPT trên thiết bị S7 BẮT BUỘC dùng phương thức **Direct Email OTP** (điền email vào ô `Email address` -> bấm `Tiếp tục` -> nhận mã OTP 6 số từ hòm thư -> điền OTP hoàn tất).
- **CẤM TUYỆT ĐỐI**: Bấm "Continue with Google" / Google SSO:
  - Google SSO trên Android WebView khiến Google kích hoạt checkpoint danh tính (`OsVersionNudgeActivity` hoặc `challenge/pwd`).
  - OpenAI gắn cờ session mismatch và trả về lỗi: *"Chúng tôi đã gặp sự cố khi đăng nhập cho bạn, vui lòng tạm dừng một lát và thử lại sau."*
  - Làm hỏng tính độc lập của tài khoản farm.
- **Xử lý popup gợi ý của Chrome**: Nếu Chrome bật popup "Đăng nhập bằng Google", "Tiếp tục bằng tài khoản của...", script BẮT BUỘC bấm `[Bỏ qua]` / `[Hủy]` (fallback tọa độ `540, 1780`), KHÔNG BAO GIỜ chạm vào tài khoản Google.

## 2. QUY CHUẨN NGHIỆM THU CHATGPT ACTIVE (CHỐNG BÁO LÁO / FALSE-POSITIVE)
- **Dấu hiệu CHƯA ĐĂNG NHẬP / CHƯA REG THÀNH CÔNG**:
  - Ở góc trên bên phải màn hình `chatgpt.com` **vẫn còn nút màu đen `[Đăng nhập]`**.
  - Đây là trạng thái khách vãng lai (Guest Mode). Báo cáo thành công khi còn nút này là BÁO CÁO LÁO.
- **Dấu hiệu ĐÃ LIÊN KẾT / ĐĂNG NHẬP THÀNH CÔNG 100%**:
  - Nút `[Đăng nhập]` biến mất hoàn toàn.
  - Xuất hiện nút **`+ Nâng cấp gói`** (*Upgrade plan*) hoặc avatar/icon profile tài khoản.
  - Giao diện lộ rõ các prompt gợi ý của tài khoản đã active: *"Tạo ảnh hoặc hình dán"*, *"Viết hoặc chỉnh sửa"*, *"Hỏi bất kỳ điều gì"*.
  - Bắt buộc kiểm tra OCR có chuỗi `Nâng cấp gói` hoặc trích xuất được Session/Access Token.

## 3. LỖI GMAIL DIE LÀM KẸT ĐỒNG BỘ APP GMAIL TRÊN ANDROID 8 (S7)
- **Hiện tượng**: App Gmail trên S7 hiện popup *"Tài khoản chưa được đồng bộ hóa. Hãy nhấn Đồng bộ ngay..."* hoặc Google chặn màn hình `OsVersionNudgeActivity` (*"Hãy cập nhật thiết bị để đảm bảo an toàn..."*).
- **Nguyên nhân gốc rễ**: Khi trên máy S7 có 1 tài khoản Gmail bị **DIE** (Vô hiệu hóa), Google Play Services trên Android 8 bị crash session xác thực, làm đóng băng toàn bộ background push sync của app Gmail.
- **Giải pháp xử lý**:
  1. Luôn chạy `check_gmail_is_live(email)` qua proxy của máy trước khi gọi runner.
  2. Dọn gỡ sạch tài khoản DIE ra khỏi Cài đặt S7 (`dumpsys account` -> gỡ tài khoản DIE).
  3. Khi chỉ còn tài khoản LIVE chuẩn, app Gmail sẽ tải thư bình thường mà không bị kẹt màn hình update OS.

## 4. QUY TẮC PHÂN BỔ TÀI KHOẢN & ƯU TIÊN GPM ĐÊM
- Các tài khoản đã reg ChatGPT thành công trên S7 cần được đánh dấu flag `CHATGPT_READY` trong `master_gmail_manager.xlsx` (Cột 14 - Ghi Chú).
- Script watchdog ca tối (`post_evening_gpm_login_watchdog.py`) ưu tiên bốc các tài khoản có flag `CHATGPT_READY` lên đầu danh sách nạp proxy để lấy OAuth token nạp OmniRoute/OpenAI pool trước.
