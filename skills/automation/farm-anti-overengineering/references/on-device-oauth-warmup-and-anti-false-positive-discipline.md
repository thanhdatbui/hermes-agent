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

## 5. Kỷ luật chống báo láo (Anti-False-Positive Gate)
- **CẤM TUYỆT ĐỐI**: Vòng lặp `for/while` hết thời gian mà tự động trôi xuống cuối hàm return `success: True`.
- **BẮT BUỘC**:
  - Mọi bước chuyển trạng thái (Google click -> Chooser -> Password -> Consent -> About-You -> ChatGPT) phải verify rành mạch qua XML/URL.
  - Thất bại ở bước nào phải lập tức return `{"success": False, "status": "FAILED_AT_<STEP>"}` kèm screenshot hiện trường.
  - Chỉ return `success: True` khi giao diện thực sự rời khỏi các trang auth/cookie và render thành công khung chat hoặc URL `chatgpt.com`.
  - Báo cáo kết quả phải đi kèm nghiệm thu hòm thư thật (kéo sync Gmail app và chụp ảnh thư xác nhận `MEDIA:...`).
