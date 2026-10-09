# TikTok Passwordless Signup, OTP-Only Login & Profile UI Navigation Pitfalls

## 1. Bản chất Tỷ lệ Pass Ảo vs Pass Thật khi Reg TikTok

- **Cơ chế phân luồng của TikTok**: Khi đăng ký tài khoản TikTok bằng Email/Hotmail, hệ thống TikTok phân luồng dựa trên đánh giá rủi ro thiết bị:
  - Một số tài khoản bắt buộc đi qua màn hình nhập/tạo mật khẩu.
  - Một số tài khoản bypass hoàn toàn màn hình mật khẩu, đưa thẳng người dùng vào màn hình chính hoặc trang cá nhân.
- **User Invariant (Kỷ luật bảo vệ dữ liệu farm)**:
  - **CẤM TUYỆT ĐỐI** tự sinh mật khẩu giả/ảo (random string) ghi vào Cột D (PASS TikTok) của Excel khi flow reg không yêu cầu tạo mật khẩu.
  - Tài khoản không có màn hình nhập pass thì **BẮT BUỘC để trống Cột D** (chuẩn tài khoản Passwordless).
  - Thử mật khẩu ảo vào app TikTok sẽ kích hoạt cảnh báo bảo mật *"Sai tài khoản hoặc mật khẩu. Còn 1 lần nhập. Hãy thử lại"* và có nguy cơ khóa tài khoản vĩnh viễn.

---

## 2. Luồng Đăng nhập `--otp-only` & Fallback Quên Mật Khẩu

- **Cờ `--otp-only`**: Tích hợp trong `tiktok_login_v1.py` dùng khi giải cứu tài khoản passwordless hoặc tài khoản nghi ngờ pass ảo:
  - Ép `login_target = account["login_email"]` (bỏ qua ID + pass tĩnh).
  - Không tự động bấm link "Đăng nhập bằng mật khẩu".
- **Xử lý Màn hình Mật khẩu (Password Screen Fallback)**:
  - Khi TikTok mở màn hình *"Nhập mật khẩu"* mà không có link *"Đăng nhập bằng mã"*:
  - **Kỹ thuật**: Tự động tìm và bấm link **"Quên mật khẩu?"** (`#ldh` hoặc text `"Quên mật khẩu?"` / `"Forgot password?"`) ➔ bấm chọn **"Email"**.
  - TikTok sẽ gửi mã OTP 6 số về hòm thư Hotmail (đọc tức thời qua Microsoft Graph API).
  - Nạp mã OTP ➔ TikTok mở màn hình tạo mật khẩu mới ➔ điền mật khẩu chính thức ➔ nạp pass mới vào Excel Cột D.

---

## 3. Các Bẫy Giao diện Profile & Switcher trên TikTok v30+ (Galaxy S7)

1. **Lọc Bỏ Thông Báo Thanh Trạng Thái (Notification Bar)**:
   - Hàm `is_auth_landing_screen` không được quét thô toàn bộ XML, vì Android SystemUI thường chứa thông báo: *"Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập"*, *"Tín hiệu điện thoại"*... chứa từ khóa "đăng nhập", "điện thoại" dẫn đến nhận diện nhầm Profile thành màn hình Login.
   - **Giải pháp**: Chỉ quét các node có `package == "com.ss.android.ugc.trill"` hoặc `class` thuộc TikTok.
2. **Anchor Switcher Căn Lề Trái Layout Mới**:
   - Trên TikTok v30+, display name và username trên Profile nằm căn lề trái với bounds `[36, 280]...`, mang resource id:
     - `t7l`: Display name (ví dụ: `Mai Giang1`).
     - `t3y`: Username / handle (ví dụ: `@guadazvvrn5`).
   - Bắt buộc thêm `"t7l"` và `"t3y"` vào danh sách markers của `_try_open_account_dropdown_once` trong `social_reg_v1.py` để tap mở switcher bottom sheet chỉ sau 1 lượt.
3. **Bẫy Huy Hiệu Từ Thiện Gây Vòng Lặp Thoát App (Infinite Bounce Loop)**:
   - Các profile có gắn quỹ từ thiện (ví dụ: *"Đang hỗ trợ: International Animal Rescue"*) chứa chuỗi `supporting:` và resource id `alb`.
   - Hàm `dismiss_profile_overlays` nếu thấy `supporting:` sẽ tưởng nhầm là bottom sheet modal quyên góp và bấm phím Back (`keyevent 4`) để đóng.
   - Hậu quả: Bấm Back trên trang cá nhân cá nhân sẽ thoát TikTok ra Launcher Android, gây vòng lặp relaunch liên tục.
   - **Bản vá**: Bắt buộc bọc điều kiện `not _is_personal_profile_screen_xml(xml)` trước khi xử lý `supporting:`.
4. **Bẫy Popup Tạo Nhật Ký (Story Prompt Sheet)**:
   - Xuất hiện với tiêu đề: *"Hiển thị với follower trong 24 giờ"* hoặc *"Bạn có chuyện gì?"*.
   - Nút X đóng popup có `content-desc="close"` (chữ thường).
   - Dismiss bằng cách tìm `"close"` hoặc gửi lệnh `keyevent 4` (Back).
