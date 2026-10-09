# Case Study: On-Device OAuth Warmup & Anti-False-Positive Discipline (15/09/2026)

## 1. Bối cảnh & Vấn đề
- Hệ thống cần warmup cho tài khoản Gmail mới tạo trên Samsung S7 (Android 8.0) nhằm tăng trust, tránh bị Google checkpoint đòi SMS.
- Ban đầu dùng script newsletter (Cooperpress, NodeWeekly) gửi HTTP POST trực tiếp: Hệ thống báo 200 OK nhưng thực chất là trang Cloudflare Turnstile bot protection chặn request -> **Báo cáo ảo (false positive)**, hộp thư Gmail không hề nhận được thư.
- Ý tưởng dùng SMTP nội bộ (từ tài khoản chính của farm gửi thư sang acc mới) bị bác bỏ: Google Anti-Abuse AI phát hiện ngay hành vi "Farm cluster inter-linking" vì tài khoản vừa sinh ra 5 phút không thể có người thật nào biết để gửi thư đến.

## 2. Giải pháp: Hook Google OAuth Đăng Ký Dịch Vụ Thật (ChatGPT) On-Device
- Đăng ký ChatGPT trực tiếp trên S7 thông qua Google OAuth ("Continue with Google") ngay sau khi reg Gmail:
  1. Google & OpenAI gửi ngay email bảo mật xác nhận liên kết tài khoản (`Bạn đã chia sẻ dữ liệu với OpenAI`) vào hộp thư -> Inbound mail từ corporate uy tín, trust tăng mạnh tự nhiên.
  2. Fingerprint thiết bị và IP 4G trùng khớp 100% với phiên tạo tài khoản.

## 3. Các cạm bẫy kỹ thuật & Cách khắc phục trên Android S7 cũ
1. **Lỗi ký tự đặc biệt (`!`) khi gõ qua ADB**:
   - Mật khẩu có chứa dấu chấm than (ví dụ `Kha!594Apex`) nếu bắn qua `input text` hoặc không escape chuẩn trong shell bash sẽ bị nuốt hoặc biến thành `\!`, dẫn đến báo sai mật khẩu trên Google.
   - **Khắc phục**: Dùng hàm `human_type` chuyên dụng gửi từng ký tự có escape `\$&*();'"<>|~^!?`.
2. **Bắt nhầm email ở tiêu đề trang nhập mật khẩu**:
   - Trên trang `accounts.google.com/v3/signin/challenge/pwd`, Google vẫn in text email mục tiêu ở phần header.
   - Nếu điều kiện tìm kiếm email (`find_node_in_xml(xml, email)`) chạy trước kiểm tra mật khẩu, script sẽ bấm liên tục vào tiêu đề và không bao giờ nhập mật khẩu.
   - **Khắc phục**: Bắt buộc ưu tiên kiểm tra `challenge/pwd` trước `Account Chooser`.
3. **Dialog hệ thống của Chrome che khuất**:
   - Khi bấm "Tiếp tục với Google", Chrome trên Android 8.0 có thể bật popup: *"Đăng nhập vào Chrome - sử dụng dấu trang..."*.
   - **Khắc phục**: Tự động phát hiện text "Đăng nhập vào Chrome" và tap nút "Bỏ qua" / "Skip" ở đáy màn hình.
4. **Bàn phím ảo che mất nút hành động**:
   - Sau khi nhập tuổi trên trang `auth.openai.com/about-you`, bàn phím ảo che mất nút "Tiếp tục".
   - **Khắc phục**: Sau khi gõ số tuổi, gửi phím Back (`keyevent 4`) hoặc tap nhẹ lên header an toàn để ẩn bàn phím rồi mới tap nút Tiếp tục.
5. **Rào cản reCAPTCHA Google khi chạy hàng loạt**:
   - Khi chạy batch mở Chrome liên kết OAuth trên nhiều máy S7 cùng dải IP/cụm farm, Google có thể kích hoạt cơ chế phòng vệ `accounts.google.com/v3/signin/challenge/recaptcha` ("Xác minh danh tính của bạn - Xác nhận bạn không phải là rô-bốt").
   - **Kỷ luật xử lý**: Không cố click mù quáng hay bypass captcha phức tạp làm treo máy; hook phải nhận diện URL/text `challenge/recaptcha`, fail-fast với status `FAILED_AT_RECAPTCHA_CHALLENGE`, chụp ảnh hiện trường, đóng Chrome và nhả máy về Home sạch sẽ.

## 5. Tối ưu thực thi Runner: Gom Batch & Chạy Trực Tiếp
- **Bẫy lãng phí tool calls**: Khi nhận yêu cầu chạy lại hoặc kích hoạt hook cho danh sách nhiều máy (ví dụ M01, M02, M42, M65), không nên tốn nhiều turn gọi lệnh shell đơn lẻ (như thăm dò ADB path, scan từng thư mục, đọc từng đoạn log, chạy từng máy ở turn riêng lẻ). Chia lẻ turn dễ chạm giới hạn tool-calling iteration limit của coordinator agent trước khi kịp chạy máy thứ hai.
- **Mẫu Runner trực tiếp (1-shot Execution)**: Tạo một runner script duy nhất import trực tiếp `hook_chatgpt_register` và `gmail_reg_v10` từ repo `D:/Taadaa/register gmail`, lặp qua toàn bộ danh sách targets, bắt `try...finally` đảm bảo chụp ảnh nghiệm thu và nhấn phím Home (`keyevent 3`), lưu screenshot và kết quả JSON để trả kết quả trọn vẹn trong một phiên.

## 6. Kỹ thuật điều khiển Samsung S7 & Cạm bẫy UI Automator Dump
- **Lỗi `uiautomator dump` bị OS kill**: Trên Samsung S7 (Android 8.0, RAM giới hạn), khi Chrome đang chạy nặng hoặc render webview, lệnh raw shell `adb exec-out uiautomator dump /sdcard/...` thường xuyên bị OS OOM-killer bắn hạ (`Killed`, `cat: No such file or directory`).
  - **Khắc phục**: Luôn dùng hàm helper `get_ui_xml(device_id)` trong `gmail_reg_v10` (tận dụng `atx-agent` port 7912 hoặc cơ chế fallback an toàn), không gọi raw `uiautomator dump` thủ công.
- **Bẫy trang trắng / Timeout khi mở direct link ChatGPT**: Khi mở `https://chatgpt.com/auth/login?screen_hint=signup`, nếu mạng 4G/Wi-Fi nghẽn hoặc gặp Cloudflare challenge, Chrome chỉ giữ URL thanh địa chỉ mà không render ô input email. Runner phải fail-fast với status `FAILED_AT_EMAIL_SUBMIT` (`EMAIL_SUBMIT_TIMEOUT`), chụp ảnh màn hình hiện trường và không treo luồng.

## 4. Kỷ luật chống báo láo (Anti-False-Positive Gate)
- **CẤM TUYỆT ĐỐI**: Vòng lặp `for/while` hết thời gian mà tự động trôi xuống cuối hàm return `success: True`.
- **BẮT BUỘC**:
  - Mọi bước chuyển trạng thái (Google click -> Chooser -> Password -> Consent -> About-You -> ChatGPT) phải verify rành mạch qua XML/URL.
  - Thất bại ở bước nào phải lập tức return `{"success": False, "status": "FAILED_AT_<STEP>"}` kèm screenshot hiện trường.
  - Chỉ return `success: True` khi giao diện thực sự rời khỏi các trang auth/cookie và render thành công khung chat hoặc URL `chatgpt.com`.
  - Báo cáo kết quả phải đi kèm nghiệm thu hòm thư thật (kéo sync Gmail app và chụp ảnh thư xác nhận `MEDIA:...`).
