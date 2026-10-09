# Kỷ Luật Đăng Ký ChatGPT & Phân Biệt Tài Khoản Farm (Bài Học Thực Chiến 19/09/2026)

## 1. INVARIANT BẮT BUỘC: ĐĂNG KÝ CHATGPT BẰNG DIRECT EMAIL OTP
- **CẤM TUYỆT ĐỐI**: Không bao giờ bấm nút "Continue with Google" / "Tiếp tục bằng Google" (Google SSO).
  - *Hậu quả khi dùng Google SSO*: Làm dính checkpoint xác minh danh tính tài khoản trên điện thoại, kích hoạt cơ chế chặn của OpenAI ("Chúng tôi đã gặp sự cố khi đăng nhập cho bạn, vui lòng tạm dừng một lát và thử lại sau"), phá vỡ tính độc lập của tài khoản farm.
- **QUY TRÌNH BẮT BUỘC**:
  1. Nhập email trực tiếp vào ô `Email address` (Tọa độ fallback trên màn hình Samsung S7 1080x1920: `540, 1280`).
  2. Bấm nút `Tiếp tục` (Tọa độ fallback: `540, 1485`).
  3. Nếu xuất hiện popup gợi ý tài khoản Google của trình duyệt Chrome ("Tiếp tục bằng tài khoản của..."): BẮT BUỘC bấm `[Bỏ qua]` / `[Hủy]` (tọa độ fallback: `540, 1780`), TUYỆT ĐỐI KHÔNG bấm chọn tài khoản Google.
  4. Mở app Gmail bốc mã OTP 6 số (`\d{6}`). Nếu app Gmail hiện popup chưa bật tự động đồng bộ: Bấm `[Đồng bộ ngay]` (tọa độ `540, 970`), chờ 3 giây rồi mới vuốt làm mới hòm thư.
  5. Quay lại Chrome điền OTP vào ô `(540, 1100)` $\rightarrow$ Vượt qua onboarding giọng nói `(540, 1780)` $\rightarrow$ Hoàn tất.

---

## 2. NHẬN DIỆN KẾT QUẢ NGHIỆM THU THẬT SỰ TRÊN WEB CHATGPT
- **CẤM BÁO CÁO ẢO KHI TRANG CÒN NÚT "ĐĂNG NHẬP"**:
  - Nếu góc trên bên phải trang `chatgpt.com` vẫn còn nút đen **`[Đăng nhập]`**: Đây là phiên khách (Guest), hoàn toàn CHƯA đăng ký hay đăng nhập thành công.
  - **DẤU HIỆU NGHIỆM THU ĐẠT CHUẨN**:
    * Nút `[Đăng nhập]` biến mất hoàn toàn.
    * Xuất hiện nút **`+ Nâng cấp gói`** (*Upgrade plan*) ở góc trên bên phải.
    * Xuất hiện các ô tính năng của tài khoản active: *"Tạo ảnh hoặc hình dán"*, *"Viết hoặc chỉnh sửa"*, *"Hỏi bất kỳ điều gì"*.

---

## 3. CHECK-LIVE GMAIL VÀ DỌN RÁC TÀI KHOẢN DIE TRÊN ĐIỆN THOẠI
- Trước khi chạy bất kỳ luồng nào (Reg ChatGPT, nuôi nick, bốc 2FA), BẮT BUỘC check-live Gmail qua `check_gmail_live_fast.py`.
- Nếu tài khoản Google bị **DIE / Vô hiệu hóa**:
  - Google Services trên máy Samsung S7 (Android 8) sẽ văng session, kích hoạt màn hình chặn `OsVersionNudgeActivity` ("Hãy cập nhật thiết bị để đảm bảo an toàn...") và làm **đình trệ toàn bộ chức năng đồng bộ của app Gmail**.
  - Xử lý: Phải gỡ tài khoản DIE khỏi máy ngay lập tức, đưa tài khoản LIVE chuẩn vào thì app Gmail trên điện thoại mới tải được thư mới bình thường.

---

## 4. TÍCH HỢP VÀO WATCHDOG GPM CA TỐI
- **Đánh dấu CHATGPT_READY**: Khi một nick hoàn tất tạo tài khoản ChatGPT, tự động ghi nhận cờ `CHATGPT_READY` vào Cột 14 (*Ghi Chú*) của `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`).
- **Ưu tiên số 1 (Priority Boost)**: Watchdog login GPM ca tối (`post_evening_gpm_login_watchdog.py`) ưu tiên bốc các tài khoản có cờ `CHATGPT_READY` lên login trước để bốc OAuth/Session Token nạp vào OmniRoute ngay trong đêm.
- **Bỏ ép buộc 2FA**: User đã bỏ quy định bắt buộc phải có 2FA mới được login GPM, các tài khoản chưa 2FA vẫn được đưa vào ứng viên login bình thường.
