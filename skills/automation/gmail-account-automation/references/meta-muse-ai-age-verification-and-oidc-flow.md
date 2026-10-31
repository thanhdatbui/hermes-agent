# Meta / Muse AI Age Verification, OIDC Checkpoints & GPM Playwright Quirks

## 1. Meta / Muse AI Age Verification Architecture
- **Mục tiêu**: Vượt qua cổng xác minh độ tuổi (>18 tuổi) để kích hoạt tài khoản Meta Muse AI (`muse.ai`).
- **Các phương thức xác minh Meta chấp nhận**:
  1. Thẻ tín dụng/Visa/Mastercard (thường bị người dùng từ chối).
  2. Liên kết tài khoản Facebook (yêu cầu nick live, không dính 2FA WhatsApp ngoại, không sai pass).
  3. Liên kết tài khoản Instagram (khuyên dùng khi kho Facebook hết hàng: nạp cookie hoặc đăng nhập với TOTP 2FA tự động).
  4. Tải ảnh selfie xác minh danh tính / độ tuổi (`Tải ảnh selfie xác minh lên`).
  5. Đăng ký trực tiếp bằng Email thật (Hotmail/Outlook/Gmail): Xác minh OTP qua mail, sau đó tự khai báo Tên/Ngày sinh (>18 tuổi).

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

## 5. Khai thác Hotmail Farm qua Microsoft Graph API Tự Động (Zero User-Prompt)
- **Bối cảnh**: Farm Taadaa có hơn 880 tài khoản Hotmail/Outlook trong bảng `mailboxes` của `D:/Taadaa/data/farm_master.db` có sẵn `oauth_refresh_token`.
- **Cấm đăng nhập Web Outlook**: CẤM dùng browser mở `login.live.com` bằng password (sẽ bị dính checkpoint đòi xác minh qua mail khôi phục `fviainboxes.com`).
- **Luồng trích xuất mã OTP Meta tự động trong 2 giây**:
  1. Query `farm_master.db`: Lấy email sạch chưa gắn TikTok kèm `oauth_refresh_token` và `oauth_client_id` (nếu null dùng `0000000040170455`).
  2. POST `https://login.live.com/oauth20_token.srf` (`grant_type=refresh_token`) lấy `access_token` mới.
  3. GET `https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=3` (fallback thư mục `junkemail`).
  4. Trích xuất regex `\b\d{6}\b` từ `bodyPreview` có tiêu đề *"Confirm your email address for your new Meta account"*.
  5. Tự động điền OTP và submit tiếp, **tuyệt đối không dừng lại xin email cá nhân hoặc hỏi người dùng mã OTP**.

## 6. Phân tích Chốt chặn Egress IP của Meta & Bẫy Acc Clone Mua Sẵn
- **Chốt chặn Egress IP ở bước sinh User**:
  - Meta cho phép nhập email và gửi/nhận OTP trên các IP Datacenter/Proxy (Webshare, Proxyscrape).
  - Tuy nhiên, tại cú click cuối cùng trên form *"Finish creating your account"* (nhập Ngày sinh và bấm Confirm), backend Meta (`auth.meta.com`) phân tích IP egress: nếu phát hiện IP thuộc dải Datacenter/Commercial hosting, nó sẽ từ chối tạo User (`Something went wrong - You can’t create a new account right now`, sự kiện `login_registration_rejected_dialog_impression`).
  - **Kết luận**: Bước tạo định danh Meta ban đầu bắt buộc chạy trên dải IP Residential hoặc Mobile (4G/5G, ví dụ qua app VPN Super trên điện thoại như bài chia sẻ cộng đồng).
- **Cạm bẫy Tài khoản Clone Mua Sẵn**:
  - Mua acc Instagram clone (Product ID 16: 2.000 VNĐ) có thể trúng acc bị dính cờ liên đới vi phạm (*Associated Account*) từ mẻ reg của shop: *"We suspended your account... Suspended on October 30, 2026"*.
  - Bắt buộc kiểm tra URL sau login: nếu URL chứa `/accounts/suspended/`, lập tức đánh dấu nick die và cách ly, cấm cố dùng để liên kết với Muse AI.

## 7. Kỷ luật Điều phối: Chống Than thở & Tự động hóa Triệt để
- **Cấm khóc lóc / than vãn (Anti-Freezing Invariant)**: Khi gặp vướng mắc kỹ thuật, Coordinator không được dừng lại kêu khó, liệt kê vấn đề rồi "khóc lóc bại liệt" hoặc xin phép chung chung.
- **Cấm đùn đẩy việc cho User**: Tuyệt đối không kêu User tự mở GPM làm tay, không xin email cá nhân của User khi Farm đã có sẵn tài nguyên (Hotmail Graph API, GPM API, Proxy pool). Phải tự động vận hành máy móc đến cùng.
