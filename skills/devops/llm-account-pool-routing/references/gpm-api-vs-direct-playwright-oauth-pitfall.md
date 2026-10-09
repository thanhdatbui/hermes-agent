# Pitfalls: Phân biệt GPM API CDP và Playwright Persistent Context khi thực hiện Google OAuth SSO

## 1. Nguyên lý phân tách
- Trong hệ thống pool LLM (OmniRoute, Antigravity, ChatGPT-Web, Codex), các tài khoản Google/ChatGPT bắt buộc phải giữ độ tin cậy tự nhiên (trust score).
- **GPM Local API v3 (`port 19995`) + CDP:** 
  - Khởi động qua `GET /api/v3/profiles/start/{id}`.
  - Được engine của GPMLogin (`gpmdriver.exe`, native DLL injection) bọc lớp chống phát hiện tự động hóa (anti-detect, mask canvas/webgl/audio/navigator).
  - Playwright chỉ kết nối thụ động qua `connect_over_cdp` -> Google cho phép đăng nhập và hoàn tất OAuth Consent (`Continue with Google`).
- **Playwright `launch_persistent_context` trực tiếp:**
  - CẤM DÙNG để thực hiện luồng Google SSO / OAuth liên kết OpenAI / Antigravity.
  - Bất kể thêm cờ stealth args (`--disable-blink-features=AutomationControlled`), Google Identity Services sẽ phát hiện trình duyệt automation và chặn tại URL:
    `https://accounts.google.com/v3/signin/rejected` (*"Trình duyệt hoặc ứng dụng này có thể không an toàn"*).

## 2. Xử lý lỗi GPM API `Yêu cầu cập trình duyệt [Chromium] [XXX]`
- Khi API trả về lỗi này, không tự ý bypass sang persistent context.
- Đây là trạng thái app GPM chờ người dùng bấm xác nhận tải/cập nhật lõi browser trên giao diện GUI.
- Phải mở khóa app trên GUI trước để API `/profiles/start/{id}` trả về `remote_debugging_address`, sau đó CDP mới vào thao tác.
