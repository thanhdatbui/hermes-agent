# ChatGPT S7 Registration & GPM Watchdog Discipline (2026-09-19)

## 1. KHÓA CỨNG INVARIANT: CẤM GOOGLE SSO
- **Quy tắc bất di bất dịch**: Đăng ký ChatGPT trên thiết bị S7 **100% BẮT BUỘC dùng Direct Email OTP** (Nhập email vào ô `Email address` -> Bấm `Tiếp tục` -> Bốc mã OTP 6 số từ hòm thư).
- **CẤM TUYỆT ĐỐI**: Không bao giờ bấm vào nút "Continue with Google" hoặc chọn bất kỳ tài khoản Google SSO nào.
- **Xử lý popup Google Account Chooser của Chrome**: Khi Chrome tự động nhảy popup "Tiếp tục bằng tài khoản của..." / "Đăng nhập bằng Google", BẮT BUỘC tap nút `[Bỏ qua]` / `[Hủy]` (fallback tọa độ `540, 1780`) để đóng popup, tuyệt đối không tap chọn tài khoản.
- **Lý do kỹ thuật**: Google SSO trên Webview S7 sẽ kích hoạt reCAPTCHA, checkpoint xác minh danh tính và bị OpenAI chặn với lỗi *"Chúng tôi đã gặp sự cố khi đăng nhập cho bạn"*.

## 2. CHỐNG BÁO CÁO LÁO NGHIỆM THU CHATGPT
- **Chỉ coi là đăng ký / đăng nhập thành công khi**:
  1. Màn hình **ĐÃ MẤT HOÀN TOÀN NÚT `[Đăng nhập]`**.
  2. Xuất hiện nút **`+ Nâng cấp gói`** (Upgrade plan) ở góc trên bên phải hoặc avatar tài khoản.
  3. Mở thanh menu / drawer thấy đúng email/tên tài khoản đang active.
- **CẤM**: Thấy màn hình chào *"Bạn đang làm gì vậy? / Hỏi ChatGPT"* mà ở góc trên vẫn còn nút `[Đăng nhập]` -> Đây là trang khách (Guest state), CHƯA đăng ký / chưa login! Báo cáo thành công ở trạng thái này là BÁO CÁO LÁO.

## 3. CHECK LIVE GMAIL & XỬ LÝ DIE TRÊN S7
- Trước khi chạy reg/link ChatGPT, BẮT BUỘC gọi `check_gmail_is_live(email)` qua proxy của máy.
- **Tài khoản DIE trên S7**: Khi 1 tài khoản Google bị DIE, Google Services sẽ văng session, kích hoạt màn hình chặn `OsVersionNudgeActivity` ("Hãy cập nhật thiết bị để đảm bảo an toàn...") và pause toàn bộ dịch vụ đồng bộ của app Gmail.
- **Cách xử lý**: Gỡ sạch tài khoản DIE khỏi `Cài đặt Android -> Cloud và Tài khoản -> Google`, app Gmail của các nick LIVE còn lại sẽ lập tức thông suốt và kéo được thư OTP.

## 4. TỌA ĐỘ CHUẨN S7 (1080x1920 PORTRAIT) TRÊN CHROME CHATGPT
- Khóa cứng chống xoay ngang (`accelerometer_rotation = 0`, `user_rotation = 0`).
- Popup Cookie: `(540, 1780)` (nút Chấp nhận tất cả).
- Ô nhập Email address: `(540, 1280)`.
- Nút Tiếp tục (Continue): `(540, 1485)` hoặc `(540, 1500)`.
- Popup Voice Onboarding ("Làm quen với Giọng nói"): `(540, 1780)`.
- Nút `[Đồng bộ ngay]` trong Gmail: `(540, 970)` hoặc `(322, 992)`.

## 5. QUY TẮC ĐƯA LÊN GPM (NGÂM ĐỦ 7 NGÀY & ƯU TIÊN CHATGPT)
- **Đánh dấu flag**: Khi reg ChatGPT thành công, ghi nhận cờ `CHATGPT_READY` vào Cột 14 (*Ghi Chú*) của `master_gmail_manager.xlsx`.
- **Van chặn 7 ngày**: BẮT BUỘC ngâm đủ $\ge 7\text{ ngày}$ kể từ ngày tạo/cập nhật (Cột 15). Acc mới reg dưới 7 ngày dù đã có ChatGPT cũng CẤM đem lên GPM login để tránh dính checkpoint thiết bị lạ của Google.
- **Priority Boost**: Khi đã đủ $\ge 7\text{ ngày}$ và đã có profile GPM, các acc có cờ `CHATGPT_READY` được gán `priority = 1`, watchdog GPM ca tối ưu tiên bốc trước để nạp token vào OmniRoute.
