# GPM Profile Third-Party Service Login: ChatGPT via Google OAuth

Quy trình tự động hóa đăng nhập và tạo tài khoản ChatGPT (OpenAI) bằng tài khoản Google đã có sẵn phiên đăng nhập (session/cookies) trên GPMLogin profile qua Playwright CDP.

---

## 1. Bản chất Kỹ thuật & Bối cảnh
- Các GPM profile sau khi hoàn thành login Gmail (`run_oauth_s7_pipeline.py` hoặc `relogin_and_add_omniroute.py`) đã lưu đầy đủ Google session cookies trong Chrome user data directory.
- Khi người dùng muốn tạo/đăng nhập tài khoản dịch vụ AI bên thứ ba (ChatGPT, Claude, Poe...), việc dùng trực tiếp "Continue with Google" sẽ kế thừa session có sẵn, không yêu cầu nhập lại password Gmail và không kích hoạt lại Google Prompt / 2FA trên điện thoại.
- Proxy kết nối: Sử dụng chính proxy gán cho GPM profile (MobiProxy 4G `test.taadaa.click:5101..5138` hoặc MikroTik/Singbox). Proxy Việt Nam residential/mobile cho phép truy cập `chatgpt.com` bình thường (`HTTP 200 OK`, không bị chặn IP).

---

## 2. Quy trình Thực thi Chuẩn (Playwright CDP)

### Bước 1: Khởi động GPM Profile qua Local API v3
```python
import requests

GPM_API = "http://127.0.0.1:19995/api/v3"
res = requests.get(f"{GPM_API}/profiles/start/{profile_id}").json()
if not res.get("success"):
    raise RuntimeError(f"Cannot start GPM profile {profile_id}: {res}")

remote_addr = res["data"].get("remote_debugging_address") or res["data"].get("RemoteDebuggingAddress")
```

### Bước 2: Kết nối Playwright CDP
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://{remote_addr}")
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.set_default_timeout(30000)
```

### Bước 3: Điều hướng & Click "Continue with Google"
1. Truy cập `https://chatgpt.com` hoặc `https://chatgpt.com/auth/login`.
2. Kiểm tra nếu đã login sẵn (xuất hiện prompt box `#prompt-textarea` hoặc chat URL): ghi nhận thành công ngay.
3. Nếu ở Landing page: Click nút "Log in" (`[data-testid="login-button"]` hoặc `button:has-text("Log in")` / `button:has-text("Đăng nhập")`).
4. Tại trang xác thực OpenAI (`auth.openai.com` / `auth0.openai.com`):
   - Tìm và click nút "Continue with Google" (`button[data-provider="google"]` hoặc `button:has-text("Google")`).

### Bước 4: Xử lý Google Account Chooser & Consent
- Do trình duyệt đã login Google, Google chuyển hướng đến trang chọn tài khoản:
  - Selector: `div[data-identifier="{email}"]` hoặc `div[data-email="{email}"]` hoặc click vào dòng tài khoản tương ứng.
  - Nếu xuất hiện màn hình xác nhận chia sẻ thông tin với OpenAI: Click "Continue" / "Tiếp tục" / "Confirm".

### Bước 4b: Google Checkpoint "Không thể xác minh danh tính" (CRITICAL 2026-09-13)
- **Triệu chứng**: Khi click "Continue with Google", thay vì hiện Account Chooser hoặc redirect thành công, Google chuyển hướng đến trang `https://accounts.google.com/v3/signin/rejected` hoặc hiển thị thông báo:
  `"Chúng tôi không thể xác minh danh tính của bạn... Hãy đảm bảo rằng những thiết bị bạn thường dùng để đăng nhập đã được bật và có kết nối mạng"` hoặc rớt về `/signin/identifier` đòi nhập lại mật khẩu.
- **Nguyên nhân**:
  1. Profile GPM chưa thực sự có session Google hợp lệ (profile mới tạo, cookies rỗng).
  2. Google phát hiện IP proxy lạ/mới hoặc hành vi tự động hóa bất thường từ ứng dụng bên thứ 3 (OAuth client OpenAI `799222349882-...`), kích hoạt security challenge.
- **Xử lý chuẩn & Fail-Fast**:
  - Không click lặp lại mù quáng gây circuit breaker.
  - Dùng selector kiểm tra nhanh xem URL có chứa `/signin/rejected`, `/signin/identifier` hoặc nội dung trang chứa "không thể xác minh danh tính" / "couldn't verify".
  - Nếu phát hiện: Đánh dấu trạng thái `GOOGLE_IDENTITY_CHECKPOINT`, chụp screenshot lưu debug, tắt profile và bỏ qua tài khoản đó ngay lập tức để không lãng phí iterations.
  - Tuyệt đối phân loại nhóm profile: Chỉ chạy batch với những profile thuộc group đã verified live session (Group 10), loại trừ các profile mới chưa warmup hoặc profile văng Google session.

### Bước 5: Xử lý Onboarding & Checkpoint của ChatGPT
1. **Thông tin cá nhân (Tell us about you)**:
   - ChatGPT yêu cầu họ tên và ngày sinh (Birthday) để đảm bảo độ tuổi $\ge 18$.
   - Điền ngày sinh hợp lệ (ví dụ: `15/08/1998`), bấm "Continue" / "Tiếp tục".
   - **Pitfall nút Tiếp tục bị disabled**: Nút `Tiếp tục` / `Continue` có thể ở trạng thái disabled khi form chưa nhập đủ. BẮT BUỘC kiểm tra `is_enabled()` hoặc selector `button:has-text("Tiếp tục"):not([disabled])` trước khi click để tránh timeout 30s gây văng worker.
2. **Cloudflare Turnstile**:
   - Chờ Cloudflare tự giải trong 3–5 giây. Nếu có checkbox xác minh "Verify you are human", click frame/checkbox.
3. **Yêu cầu xác minh SĐT (Phone Verification)**:
   - Nếu OpenAI kích hoạt cờ rủi ro và bắt xác minh số điện thoại:
   - Chụp ảnh màn hình lưu vào `D:/Taadaa/GPM auto/debug_screenshots/chatgpt_phone_req_<email>.png`.
   - Đánh dấu trạng thái `PHONE_VERIFICATION_REQUIRED`, kết thúc phiên duyệt của tài khoản này, KHÔNG treo script.

### Bước 6: Nghiệm thu & Chụp bằng chứng
- Khi xuất hiện giao diện chính của ChatGPT (ô nhập prompt hoặc URL `https://chatgpt.com/`):
  - Chụp ảnh toàn trang: `D:/Taadaa/GPM auto/debug_screenshots/chatgpt_success_<email>.png`.
  - Luôn gọi `requests.get(f"{GPM_API}/profiles/stop/{profile_id}")` trong khối `finally` để giải phóng tài nguyên.
  - Báo cáo kết quả kèm `MEDIA:<path_anh>` theo chuẩn Gate 6.

---

## 3. Pitfalls & Lưu ý Sống còn
1. **Quản lý Process GPM**: Không mở cùng lúc quá nhiều profile GPM gây quá tải CPU/RAM; nên tuần tự hoặc tối đa 2 profile song song.
2. **Bash Special Chars trong Proxy**: Mật khẩu proxy MobiProxy có ký tự `#` và `!` (`mobiN:TaadaaMobi#2026!`). Trong shell hoặc command line, BẮT BUỘC dùng single quotes `'...'` để tránh bash xem `#` là comment và `!` là history expansion.
3. **Fail-Fast**: Nếu sau 30 giây không thể vượt qua Cloudflare hoặc bị kẹt selector không xác định, chụp màn hình debug ngay và chuyển sang tài khoản kế tiếp.
