# GPM Profile Reuse Discipline & Proxy Invariant

## 1. CẤM TỰ Ý TẠO PROFILE RÁC (PROFILE REUSE FIRST)
- Khi có task cần trình duyệt để đăng nhập, nhận mail, bypass OTP hay làm nhiệm vụ web, **BẮT BUỘC** tìm kiếm và tái sử dụng profile có sẵn trong hệ thống GPMLogin (`GET /api/v3/profiles?search=...`).
- Tuyệt đối **CẤM** tự ý gọi `POST /api/v3/profiles/create` để đẻ profile mới không có trong danh mục quản lý của farm, gây rác database GPM và làm loãng pool tài khoản.

## 2. KỶ LUẬT PROXY INVARIANT CHO GPM & TRÌNH DUYỆT (CHỐNG LỘ IP HOST)
- Mọi tài khoản trong farm (Gmail, Hotmail, TikTok, AWS, ChatGPT...) **BẮT BUỘC** phải chạy qua Proxy riêng được gán (dải proxy di động Mobi/Mirotik).
- **CẤM TUYỆT ĐỐI** mở profile trình duyệt chạy bằng IP trực tiếp của máy host (Kibe) để test, đăng ký hay truy cập dịch vụ bên ngoài. Lộ IP gốc của host sẽ kích hoạt cơ chế liên đới cấm hàng loạt tài khoản trên cùng dải IP.
- Trước khi thực hiện bất kỳ thao tác nhạy cảm nào trong profile, **BẮT BUỘC** kiểm tra IP thực tế qua request nội bộ (`https://api.ipify.org?format=json`) để bảo đảm IP đang dùng khớp chính xác với dải proxy được cấp.

## 3. GPM BROWSER CORE RESOURCE & VERSION VALIDATION
- Lỗi `"Yêu cầu cập trình duyệt [Chromium] [142]"`:
  * Nguyên nhân: Do GPM Local API kiểm tra manifest/version file trong thư mục core (`gpm_browser_chromium_core_142\version`). Nếu lệch giữa `1.0` và `1.1` hoặc app GPM chưa xác thực gói tài nguyên gốc với server, API sẽ từ chối `profiles/start`.
  * Không cố tạo profile với core cũ hơn (139/137) vì GPM có rule chặn downgrade từ 137 trở lên (`"Do not downgrade from version 137"`).
  * Kiểm tra đúng file `version` trong thư mục core và dùng chức năng đồng bộ tài nguyên của app GPM nếu bị lệch build.

## 4. CƠ CHẾ ĐIỀU KHIỂN FORM REACT / RECAPTCHA TRÊN GPM CDP
- Trên các trang single-page dùng React (như AWS Console Signup, Google Signin):
  * Thuộc tính `value` của input nếu chỉ gán trực tiếp `input.value = '...'` sẽ không trigger state của React/AWSUI, dẫn đến lỗi validation (`An email address is required`).
  * Bắt buộc dùng `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value)` kết hợp dispatch đủ 3 sự kiện: `input`, `change`, `blur`.
  * Khi xuất hiện iframe bảo mật (`threat-mitigation.aws.amazon.com` hoặc reCAPTCHA), đây là checkpoint tương tác người dùng — chụp ảnh xác nhận và báo user can thiệp giải captcha bằng tay trên màn hình.
