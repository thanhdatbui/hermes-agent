# Meta / Muse AI Age Verification, OIDC Checkpoints & GPM Playwright Quirks

## 1. Meta / Muse AI Age Verification Architecture
- **Mục tiêu**: Vượt qua cổng xác minh độ tuổi (>18 tuổi) để kích hoạt tài khoản Meta Muse AI (`muse.ai`).
- **Các phương thức xác minh Meta chấp nhận**:
  1. Thẻ tín dụng/Visa/Mastercard (thường bị người dùng từ chối).
  2. Liên kết tài khoản Facebook (yêu cầu nick live, không dính 2FA WhatsApp ngoại, không sai pass).
  3. Liên kết tài khoản Instagram (khuyên dùng khi kho Facebook hết hàng: nạp cookie hoặc đăng nhập với TOTP 2FA tự động).
  4. Tải ảnh selfie xác minh danh tính / độ tuổi (`Tải ảnh selfie xác minh lên`).

## 2. Quy trình nộp ảnh Selfie tự động qua Playwright CDP
- Khi Meta yêu cầu: *"Hãy tải lên một bức ảnh thể hiện rõ khuôn mặt của bạn và đảm bảo ảnh có ánh sáng tốt, không bị mờ. Ảnh chỉ có một mình bạn, không được có thêm ai khác."*
- **Tiêu chuẩn ảnh**:
  - Dùng ảnh chân dung người thật rõ ngũ quan, đơn lẻ, ánh sáng tốt, góc nhìn trên 18 tuổi (ví dụ từ kho avatar chuẩn `D:/Taadaa/reports/new_ava_f155_crop.jpg`).
- **Cơ chế nộp file tự động**:
  - Node input file ẩn: `input[type="file"][accept="image/*,image/heif,image/heic"]`.
  - Dùng Playwright `set_input_files(path)`:
    ```python
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files('D:/Taadaa/reports/new_ava_f155_crop.jpg')
    ```
  - Nút "Tiếp tục" là `div[role="button"]:has-text("Tiếp tục")` hoặc click theo tọa độ sau khi upload thành công (`Đã chọn ảnh ...`).

## 3. Cạm bẫy OIDC Expired Session & Waitlist Geoblock
- **OIDC State Expiry (`Authentication failed | We couldn't log you in`)**:
  - Nếu luồng đăng ký kéo dài qua nhiều bước (nhập OTP email -> giải reCAPTCHA -> upload selfie), chuỗi `code_challenge` / `state` giữa `auth.meta.com` và `auth.muse.ai` sẽ hết hạn.
  - Khi submit selfie xong, Meta chuyển hướng callback về `https://muse.ai/oidc/error`.
  - **Cách xử lý**: Xóa cookie hoặc bấm `Try again`, đăng nhập lại bằng email vừa tạo với OTP mới. Vì khuôn mặt đã được Meta thẩm định và ghi nhận vào hồ sơ, lượt đăng nhập sau sẽ bỏ qua hoàn toàn bước selfie.
- **Bẫy Waitlist Geoblock (`muse.ai/access`)**:
  - Màn hình: *"Tham gia danh sách chờ Muse - Muse hiện chưa có ở quốc gia hoặc khu vực của bạn."*
  - Nguyên nhân: Dải IP proxy đang dùng (kể cả US/Canada) bị nhận diện là Datacenter / ASN không nằm trong whitelist thử nghiệm của Meta.
  - Khắc phục: Bắt buộc dùng Proxy Residential (dân cư sạch) hoặc VPN có native residential egress trước khi truy cập `muse.ai`.

## 4. Kỷ luật Cách ly Fingerprint & Chống dính vết cũ (User Correction 2026-10-31)
- **Quy tắc cách ly Profile tuyệt đối**:
  - Khi một tài khoản bị lỗi checkpoint, bị từ chối đăng ký (`login_registration_rejected_dialog_impression`), hoặc bị đẩy vào Waitlist: **CẤM TUYỆT ĐỐI tái sử dụng lại profile GPM đó hoặc giữ nguyên proxy cũ để test tài khoản/email mới**.
  - Trình duyệt và Meta đã ghi nhận cookie/fingerprint/IP bị gắn cờ; việc đổi tài khoản trên cùng profile cũ sẽ làm tài khoản mới bị "vạ lây" và dính lỗi ngay lập tức.
  - **Quy trình chuẩn**: Tạo profile GPM hoàn toàn mới (`POST /api/v3/profiles/create`), gán dải proxy/IP mới chưa bị blacklist, sau đó mới tiến hành đăng nhập/đăng ký.
- **Ưu tiên Geolocation Canada so với US**:
  - IP US chịu quy định bảo vệ trẻ em nghiêm ngặt (VCDPA/COPPA) nên Meta thường xuyên bắt buộc quét khuôn mặt/selfie hoặc xác minh độ tuổi phức tạp.
  - IP Canada có chính sách thông thoáng hơn, thường bỏ qua màn selfie/captcha xe hơi và đi thẳng vào màn hình nhập Tên/Ngày sinh. Khi User đã chỉ đạo chuyển vùng Canada, Coordinator phải kiên định bám sát luồng Canada, tuyệt đối không được quay xe về US.
- **Lỗi từ chối đăng ký do email tạm (`login_registration_rejected_dialog_impression`)**:
  - Dialog Meta hiện thông báo: *"Bạn hiện không thể tạo tài khoản mới."* hoặc *"Chúng tôi không thể hoàn tất yêu cầu đó. Hãy thử lại."*
  - Nguyên nhân: Meta quét domain email rác/tempmail (`@fextemp.com`, `@yzcalo.com`...).
  - Giải pháp: Bắt buộc dùng email sạch có domain uy tín (Gmail, Hotmail/Outlook thật từ kho `farm_master.db`) kết hợp với proxy sạch.
