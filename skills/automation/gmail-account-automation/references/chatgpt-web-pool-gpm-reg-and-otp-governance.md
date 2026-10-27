# ChatGPT Web Pool GPM Registration & OTP Automation Governance

## 1. Bản Chất Kho Tài Khoản Hotmail Trên Farm
- **Mail mua sẵn (Purchased Hotmail):** Hoàn toàn KHÔNG CÓ "script reg Hotmail" trên farm. Toàn bộ Hotmail là mail mua sẵn theo lô từ nhà cung cấp.
- **Tên file lịch sử:** File lưu trữ tên là `gmail_clean_v2.xlsx` (tồn tại ở cả `D:\OneDrive\TaadaaData\kibe\` và `admin\`), nhưng thực tế dữ liệu bên trong là 100% tài khoản Hotmail mua sẵn.
- **Cấu trúc trường:** Mỗi dòng lưu: Cột 2 (Email), Cột 3 (Mật khẩu mail gốc), Cột 9 (Microsoft Graph refresh_token), Cột 10 (Graph client_id).
- **Phân rã Pipeline:**
  1. `HOTMAIL_LOGIN`: Đăng nhập mail mua sẵn vào GPM profile bằng mật khẩu mail gốc.
  2. `CHATGPT_REG`: Mở profile GPM đã login mail để tiến hành đăng ký tài khoản ChatGPT mới.

---

## 2. Ý Nghĩa Màn Hình `/about-you` ("Bạn bao nhiêu tuổi?")
- **Dấu hiệu New Signup Flow:** Màn hình hỏi Họ Tên (`input[name="name"]`) và Tuổi (`input[name="age"]`) / Ngày sinh là bước Onboarding bắt buộc của **luồng tạo tài khoản mới lần đầu**.
- **Chống ngộ nhận trạng thái:** Khi điền email mà OpenAI chuyển sang trang `/about-you`, chứng minh tài khoản này **chưa từng hoàn tất đăng ký ChatGPT trước đây**, bất kể trong telemetry hay state file của supervisor trước đó có ghi nhận stage `DONE` hay `chatgpt_registered_at`.
- **Tự động xử lý Onboarding:** Điền Tên ("Chau Ta"), Tuổi ("25") hoặc ngày sinh, submit nút "Tiếp tục" / "Bắt đầu" và chờ điều hướng sang `chatgpt.com` để trích xuất cookie `__Secure-next-auth.session-token`.

---

## 3. Chống Báo Cáo Ảo (Exit Code & Supervisor Gate)
- **Cấm Exit Code 0 khi Thất Bại:** Script đăng ký (`chatgpt_gpm_direct_reg.py`) CẤM TUYỆT ĐỐI `return 0` khi danh sách ứng viên rỗng hoặc khi đăng ký thất bại (`FAIL_PASSWORD_NOT_FOUND`, `FAIL_OTP_TIMEOUT`, `FAIL_WRONG_OTP`...).
- **Chỉ Exit Code 0 khi SUCCESS:** Script chỉ được trả về `0` khi tài khoản thực sự đăng ký thành công và có session thật. Bất kỳ trường hợp nào khác bắt buộc trả về `1` để supervisor không bao giờ đánh dấu hoàn thành ảo.

---

## 4. Zero-Footprint Password & Excel Persistence
- **Cấm tuyệt đối Pattern tĩnh / Brand Footprint:** CẤM dùng hậu tố cố định như `@Taadaa2026` để kéo dài mật khẩu $\ge 12$ ký tự. Hệ thống fraud detection của OpenAI sẽ quét pattern chuỗi tĩnh và trảm liên đới toàn bộ cụm tài khoản farm.
- **Salt ngẫu nhiên độc nhất per-account:** Sử dụng hàm băm hoặc bộ sinh salt ngẫu nhiên riêng biệt cho từng email (kết hợp chữ hoa, chữ thường, số, ký tự đặc biệt `@, #, $, %, !, &, *`). Đảm bảo không tài khoản nào có pattern giống nhau.
- **Bắt buộc lưu vào Excel (Persistence):** Khi sinh xong mật khẩu ngẫu nhiên cho nick nào, bắt buộc ghi đè cập nhật ngay vào cột `PASS CHATGPT` (cột L / cột 11) của cả 2 file:
  - `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx`
  - `D:\OneDrive\TaadaaData\admin\taikhoan_dat_v2_updated .xlsx`

---

## 5. Bẫy Selector OTP Trên `auth.openai.com/email-verification`
- **Bẫy ô Readonly Email:** Trên trang nhập OTP của OpenAI, phía trên các ô nhập mã có một trường hiển thị email dạng `<input readonly type="text" placeholder="Địa chỉ email">`.
- **Lỗi Locator:** Nếu selector tìm input có chứa `input[type="text"]`, Playwright sẽ chọn trúng ô readonly này, gây ra lỗi `element is not editable` và timeout 30 giây khi gọi `.fill(otp)`.
- **Selector chuẩn xác:** Bắt buộc dùng:
  ```python
  code_inp = page.locator('input[name="code"], input#code, input[inputmode="numeric"]:not([readonly])').first
  ```
  Hoặc kiểm tra 6 ô digit: `input[data-index], input.code-input, input[aria-label*="digit"]`.

---

## 6. Pre-Validate Microsoft Graph Token
- **Kiểm tra trước khi mở Browser:** Khởi động trình duyệt GPM tiêu tốn nhiều RAM/CPU và dễ làm treo máy nếu chạy đồng loạt. Trước khi mở profile, BẮT BUỘC thực hiện 1 HTTP POST nhanh để xác thực refresh_token:
  ```python
  requests.post(
      "https://login.microsoftonline.com/common/oauth2/v2.0/token",
      data={
          "client_id": cid,
          "grant_type": "refresh_token",
          "refresh_token": tok,
          "scope": "https://graph.microsoft.com/Mail.Read offline_access",
      },
      timeout=8,
  )
  ```
- **Fail-Fast:** Nếu status != 200 (token hết hạn AADSTS70000 hoặc revoke), bỏ qua ngay lập tức để tiết kiệm tài nguyên.

---

## 7. Trần Phủ Proxy Cho ChatGPT-Web Pool
- **Định mức:** Cố định trần $\ge 2$ tài khoản active / IP (port proxy).
- **Đối soát Dynamic:** Trước khi chạy reg cho một port, kiểm tra bảng `proxy_assignments` trong `C:/Users/Kibe/.omniroute/storage.sqlite`. Nếu port đã có đủ $\ge 2$ tài khoản active thì bỏ qua chuyển sang port khác.
- **Phủ toàn diện:** Bao gồm 38 cổng MobiProxy 4G (`5101–5138`) và 35 cổng MikroTik (`10001–10035`).
