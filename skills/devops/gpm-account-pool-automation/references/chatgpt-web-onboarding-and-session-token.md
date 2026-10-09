# ChatGPT Web & OpenAI OAuth Onboarding via GPM CDP (2026-09-14)

## 1. Bản chất & Sự khác biệt
- **Token chuẩn (Auth session-token)**: Bắt đầu bằng `eyJhbG...` (JWT auth token chính thức).
- **Token khách (Anon / Guest cookie)**: Thường có tiền tố `__Secure-next-auth...` hoặc cookie tạm. Khi mở `chatgpt.com` bằng profile này, trên màn hình vẫn còn nút "Đăng nhập" / "Đăng ký" (14 nút đăng nhập).
- **Quy tắc nghiệm thu login thành công**:
  1. `context.cookies()` trích xuất `__Secure-next-auth.session-token` phải có dạng `eyJhbG...`.
  2. Trên trang `https://chatgpt.com/`, số lượng nút `button:has-text("Log in"), button:has-text("Đăng nhập")` phải bằng **0**.

## 2. Các cạm bẫy giao diện OpenAI Onboarding (`/about-you`)
Khi đăng nhập tài khoản mới bằng Google SSO, OpenAI chuyển hướng về `https://auth.openai.com/about-you`:

### Cạm bẫy 1: DateField tiếng Việt mặc định năm 2026
- OpenAI dùng component `react-aria-DateField` lấy ngày hệ thống hiện tại (ví dụ: `14/09/2026`).
- Nếu không xóa năm `2026`, tuổi = 0 (< 13 tuổi), OpenAI báo đỏ: *"Chúng tôi không thể tạo tài khoản với thông tin đó"*.
- **Cách xử lý**:
  - Click vào từng ô `div[data-type="day"]`, `div[data-type="month"]`, `div[data-type="year"]`.
  - Bắt buộc bấm `Control+A` trước khi gõ để ghi đè số cũ.
  - Năm sinh phải điền trong khoảng **1996 – 2002** (24 – 30 tuổi hợp lệ).

### Cạm bẫy 2: Form bắt nhập số tuổi trực tiếp (`input[name="age"]`)
- Một số giao diện hiển thị ô nhập tuổi dạng số (`<input name="age" type="number">`).
- **Cách xử lý**: Kiểm tra nếu có `input[name="age"]`, click force, `Control+A` và gõ tuổi ngẫu nhiên `22 - 28`. Tránh nhầm lẫn giữa datefield và age input khiến form bị bỏ trống.

### Cạm bẫy 3: Màn hình "Phiên của bạn đã kết thúc" (`https://auth.openai.com/u/login`)
- **Triệu chứng**: Giao diện tối giản hiện logo OpenAI, tiêu đề: *"Phiên của bạn đã kết thúc"* / *"Your session has ended"*, bên dưới có nút đen `[Đăng nhập]`.
- **Nguyên nhân**: Request xác thực bị timeout, token exchange bị chậm, hoặc người dùng ngâm trang quá lâu.
- **Cách xử lý**: Tự động click vào nút `button:has-text("Đăng nhập"), a:has-text("Đăng nhập")` để quay lại luồng login bình thường.

## 3. Quản lý tiến trình & Tránh tràn Taskbar
- **Giới hạn luồng**: Chỉ chạy tối đa **2–3 workers** song song. Dồn quá nhiều worker trên cùng dải IP proxy sẽ kích hoạt Cloudflare WAF hoặc lỗi `token_exchange_failed` từ OpenAI.
- **Dọn dẹp sau mỗi profile**:
  1. Gọi API stop: `GET http://127.0.0.1:19995/api/v3/profiles/stop/{id}`.
  2. Quét diệt tiến trình `chrome.exe` mồ côi theo `profile_path` để tránh treo tràn thanh Taskbar:
  ```python
  import psutil
  for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
      try:
          cmd = ' '.join(p.info.get('cmdline') or [])
          exe = p.info.get('exe') or ''
          if 'chrome.exe' in p.info.get('name', '').lower() and 'gpm_browser' in exe.lower():
              if p_path in cmd:
                  p.kill()
      except Exception:
          pass
  ```
