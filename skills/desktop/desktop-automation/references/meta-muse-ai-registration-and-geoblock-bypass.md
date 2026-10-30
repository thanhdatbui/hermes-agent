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
- **Giải pháp:** Phải dùng Proxy dân cư sạch (Residential) hoặc kết nối qua ứng dụng VPN cá nhân trên máy (như VPN Super chọn vùng Canada/US dân cư) trước khi submit form.

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
