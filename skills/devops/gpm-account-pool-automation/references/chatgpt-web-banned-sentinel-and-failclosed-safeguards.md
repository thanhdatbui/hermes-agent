# Banned / Suspended Account Diagnostics in ChatGPT Web Pool & Fail-Closed Protection

## 1. Cơ chế phát hiện và chẩn đoán tài khoản die/banned

### Sentinel / Turnstile Block (HTTP 403)
Khi OmniRoute kết nối tới ChatGPT Web pool gặp lỗi:
```text
ChatGPT blocked the request (Sentinel/Turnstile required). Try again later or open chatgpt.com in a browser to refresh state.
```
- **Bản chất**: Đây là lớp Cloudflare Turnstile / OpenAI Sentinel bot detection chặn request tự động từ backend proxy. 
- **Nguyên nhân tiềm ẩn**:
  - Tần suất request hoặc concurrency quá cao dồn lên cùng 1 session Web (`maxConcurrent` không được giới hạn).
  - Proxy bị dính blacklist IP của Cloudflare/OpenAI.
  - Sử dụng fail-open proxy khiến IP thật của host bị lộ và bị cắm cờ hàng loạt.
- **Phân biệt với Account Deleted / Disabled**:
  - `Sentinel/Turnstile 403`: Session token (`oai-did` / cookie) bị từ chối ở tầng network gateway. Tài khoản chưa chắc đã bị xóa/khóa vĩnh viễn. Cần mở browser thật trên profile GPM tương ứng để vượt challenge thủ công nếu cần hồi phục.
  - `Account Deleted / Disabled`: Khi đăng nhập vào auth.openai.com báo *"Lỗi xác thực: Bạn không có tài khoản vì tài khoản đã bị xóa hoặc vô hiệu hóa"*. Đây là án phạt cấp tài khoản (Account-level Ban), không thể khôi phục.

## 2. Hard Invariants & Fail-Closed Safeguards

### Invariant 1: CẤM TUYỆT ĐỐI Google SSO khi OAuth Codex
- Khi chạy OAuth Codex cho các profile GPM đã reg ChatGPT, tuyệt đối **KHÔNG ĐƯỢC bấm nút "Continue with Google"** hoặc chọn tài khoản qua Google Account Chooser.
- Bắt buộc **100% sử dụng session ChatGPT sẵn có** trong profile.
- Nếu mở OAuth mà trang rơi vào `auth.openai.com/log-in` hoặc Guest Mode (`Log in / Sign up`):
  -> **FAIL-CLOSED NGAY LẬP TỨC**: Đánh dấu profile thiếu session, loại khỏi hàng đợi chạy Codex. CẤM cố tình click Google SSO để đăng nhập vòng qua.

### Invariant 2: CẤM Direct-IP Fallback (Proxy Fail-Closed)
- Thiết lập bắt buộc trong `.env` và launcher của OmniRoute:
  ```env
  PROXY_FAIL_OPEN=false
  OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=false
  ```
- Khi proxy gặp lỗi kết nối hoặc timeout: Phải ngắt kết nối và trả lỗi ngay lập tức (`fail-closed`).
- Tuyệt đối cấm fallback về IP trực tiếp của máy chủ, tránh làm lộ địa chỉ IP thật và gây ban hàng loạt tài khoản trong pool.

### Invariant 3: Dọn dẹp Chromium Process Leak trong GPM Automation
- Khi viết script tự động hóa GPM sử dụng Playwright qua CDP (`connect_over_cdp`):
- Trong khối `finally:`, bắt buộc đóng theo thứ tự:
  1. `for context in browser.contexts: context.close()`
  2. `browser.close()`
  3. Gọi API GPM stop: `GET /api/v3/profiles/stop/{profile_id}`
- Nếu chỉ gọi API stop mà không đóng browser Playwright, các tiến trình `chrome.exe` con sẽ bị rò rỉ (leak), tích tụ hàng chục process mồ côi trên Taskbar/RAM gây nghẽn toàn bộ hệ thống.
