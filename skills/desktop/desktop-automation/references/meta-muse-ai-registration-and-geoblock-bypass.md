# Meta Muse AI / OIDC Registration & Geoblock Bypass Pitfalls

### 1. Phân biệt cơ chế kiểm soát địa lý (Geoblock) giữa các vùng
- **Vùng US (Hoa Kỳ):**
  - Meta áp dụng luật bảo vệ trẻ em nghiêm ngặt: sau khi xác nhận email OTP, luồng đăng ký Meta OIDC kích hoạt **reCAPTCHA Enterprise** và bắt buộc **xác minh độ tuổi (Age Verification)** bằng ảnh selfie khuôn mặt thật (`Tải ảnh selfie xác minh lên`).
  - Nếu đăng ký bằng IP US từ dải hosting/datacenter, sau khi verify sẽ bị đẩy vào màn hình Waitlist (`muse.ai/access`).
- **Vùng Canada (CA):**
  - Không bắt buộc quét selfie hoặc reCAPTCHA hình ảnh phức tạp ở bước đầu.
  - Form chuyển thẳng sang bước điền thông tin cơ bản: Tên, Họ và Ngày sinh (`select` dropdown Day/Month/Year).
  - Yêu cầu ngày sinh: Bắt buộc chọn năm sinh để tuổi $\ge 18$ (ví dụ: sinh năm 1996 - 2005).

### 2. Antifraud & Datacenter IP Pitfall
- Khi bấm nút `Xác nhận` ở bước cuối của form tạo tài khoản Meta, nếu backend trả về lỗi:
  > *"Chúng tôi không thể hoàn tất yêu cầu đó. Hãy thử lại."*
  Nguyên nhân 100% là do IP đang dùng nằm trong danh sách Datacenter/Hosting IP bị Meta chặn ghi nhận tài khoản mới.
- **Lỗi từ chối đăng ký do Email rác (Tempmail Blacklist):**
  - Sử dụng các domain email tạm thời (như `@fextemp.com`, `@yzcalo.com`) sẽ vượt qua được OTP đầu vào nhưng sẽ bị Meta chặn đứng ở bước hoàn tất tạo User: kích hoạt modal dialog `login_registration_rejected_dialog_impression` kèm thông báo:
    > *"Bạn hiện không thể tạo tài khoản mới."*
  - **Khắc phục:** Bắt buộc dùng email thật (Gmail, Hotmail, Outlook) chưa từng đăng ký Meta AI.
- **Quy tắc cách ly sạch Profile & Proxy (Bắt buộc khi đổi acc / thử lại):**
  - Khi một lượt đăng ký bị thất bại (dính checkpoint selfie, OIDC error hoặc bị chặn IP), CẤM TUYỆT ĐỐI tái sử dụng profile GPM cũ.
  - Profile cũ đã lưu cookie rác, local storage, `code_challenge` OIDC hết hạn và fingerprint bị Meta đánh dấu nghi vấn.
  - Bắt buộc tạo **Profile GPM mới toanh + gắn Proxy mới hoàn toàn** để cách ly sạch 100%.
- **Kiên định Geolocation theo chỉ đạo User:**
  - Khi User yêu cầu test/fake IP quốc gia cụ thể (ví dụ Canada), cấm tự ý quay về US hay vị trí khác chỉ vì proxy có sẵn. Phải bám sát vị trí chỉ định.
- **VPN Super di động vs Extension trên GPM:**
  - Ứng dụng "VPN Super" được chia sẻ trong các bài hướng dẫn là app độc quyền di động (iOS / Android APK), không có extension trên Chrome Web Store.
  - Trên trình duyệt GPM (PC), phải dùng các extension VPN tương đương trên Chrome Web Store (như Touch VPN, Hotspot Shield) hoặc VPN cấp hệ điều hành, hoặc thao tác trực tiếp trên điện thoại.
- **Lưu ý về Hotmail Farm trong GPM:**
  - Các profile GPM nuôi nick của Farm thường trỏ qua proxy nội bộ (`192.168.110.2:200xx`), session Outlook web thường hết hạn (`NO_TOKEN`), không thể tự động hứng OTP qua web trừ khi có token Graph API hoặc đăng nhập trực tiếp.

### 3. Tương tác form Muse AI & Meta Checkpoint qua Playwright CDP
- **Input Email / Tên / Ngày sinh:** Các input trên giao diện Next.js / Tailwind của Muse AI (`input[data-slot="input"]`) thường bị chặn sự kiện khi dùng `fill()` trực tiếp nếu chưa có focus chuột hoặc click trúng toạ độ thực.
- **Kỹ thuật tương tác chuẩn:**
  1. Xác định toạ độ input qua `getBoundingClientRect()`.
  2. Dùng `page.mouse.click(x, y)` để kích hoạt focus và layout thật.
  3. Dùng `page.keyboard.type(text, delay=50)` để mô phỏng gõ phím của người dùng.
  4. Submit form bằng `page.keyboard.press('Enter')` hoặc click toạ độ tâm của nút bấm `button[type="submit"]`.

### 4. Xử lý Input File Selfie tự động
- Khi gặp màn hình yêu cầu nộp ảnh selfie xác minh danh tính/độ tuổi (`Tải ảnh selfie xác minh lên`):
  - File input ẩn: `input[type="file"][accept*="image"]`.
  - Nạp ảnh tự động: `page.locator('input[type="file"]').first.set_input_files('<path_to_clean_avatar.jpg>')`.
  - Ảnh selfie phải rõ ngũ quan, 1 người duy nhất, ánh sáng tốt, tuổi trưởng thành $\ge 18$.
  - Sau khi nộp ảnh selfie, đợi Meta backend quét thẩm định (3–5s) trước khi bấm `Tiếp tục`.
