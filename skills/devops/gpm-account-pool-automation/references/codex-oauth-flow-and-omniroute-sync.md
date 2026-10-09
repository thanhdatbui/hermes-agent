# Codex OAuth Flow via GPM Profiles & OmniRoute (:20129)

## 1. Bản chất kiến trúc: Codex vs ChatGPT-Web
- **Codex**:
  - Dùng cơ chế **OAuth 2.0 PKCE chuẩn developer** (`client_id=app_EMoamEEZ73f0CkXaXp7hrann`, scope `openid profile email offline_access`).
  - Được cấp `accessToken` kèm `refreshToken` quản lý trực tiếp bởi callback server của OmniRoute cổng 1455.
  - Hỗ trợ toàn bộ dòng reasoning / coding models: `cx/gpt-5.6-sol*`, `codex/gpt-5.6-sol*`, `gpt-5.5`, `gpt-5.6-terra-high`.
  - Token chuẩn developer không bị Cloudflare / Web Application Firewall của `chatgpt.com` chặn.
- **ChatGPT-Web**:
  - Dùng session cookie (`__Secure-next-auth.session-token`) cào từ trình duyệt web.
  - Rất dễ bị Cloudflare WAF chặn khi mở nhiều tab, và session cookie chết sau vài ngày nếu không có tương tác trình duyệt.
  - Chỉ hỗ trợ model web thông thường (`gpt-5.6-luna*`, `gpt-4o`).

## 2. Quy trình OAuth Codex tự động (Official Callback Flow)
CẤM lấy accessToken tạm bợ từ `/api/auth/session` của web chatgpt vì đó là JWT ngắn hạn (1-2 tiếng là expire [401 Unauthorized]). Bắt buộc chạy qua callback server của OmniRoute:

1. **Khởi tạo callback server**:
   - Gọi `GET http://127.0.0.1:20129/api/oauth/codex/start-callback-server`.
   - Nhận về `authUrl` (chứa `code_challenge`, `state`, `redirect_uri=http://localhost:1455/auth/callback`).
2. **Khởi động profile GPM**:
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}?win_scale=0.8`.
   - Kết nối Playwright CDP vào `remote_debugging_address`.
3. **Chặn bắt Callback Redirect**:
   - Lắng nghe network event `on("request")`.
   - Khi request URL chứa `localhost:1455/auth/callback` hoặc param `code=`: chuyển tiếp ngay lập tức sang `http://127.0.0.1:1455/auth/callback` để OmniRoute capture mã code.
4. **Tương tác trang Auth OpenAI**:
   - Điều hướng page tới `authUrl`.
   - Điền email nếu hiện form email (`input[type="email"]`).
   - Autofill password / lấy password lưu trong profile nếu hiện form password.
   - Nếu nhảy sang Google SSO:
     - Click div chọn account: `div[role="link"][data-identifier*="<email>"]`.
     - JS click nút Tiếp tục / Continue nếu có consent Google.
   - Nhấn nút cấp quyền OpenAI Codex: `button:has-text("Authorize")`, `button:has-text("Cho phép")`, `button:has-text("Allow")`.
5. **Poll kết quả từ OmniRoute**:
   - Poll `POST http://127.0.0.1:20129/api/oauth/codex/poll-callback` mỗi 3s (timeout 120s).
   - Khi nhận `is_success` và `connectionId`: hoàn tất OAuth Codex, connection tự động chuyển sang `status: active`.
6. **Teardown**:
   - Luôn đóng browser CDP và gọi `GET http://127.0.0.1:19995/api/v3/profiles/stop/{id}` để giải phóng RAM/CPU.

## 3. Pitfalls & Lưu ý sống còn
- **Lọc profile tránh nhầm lẫn**: Khi lọc profile chưa OAuth, chỉ kiểm tra các connection có `provider == 'codex'`. CẤM kiểm tra chung với pool `antigravity` hay `chatgpt-web` vì một email có thể đã có Antigravity nhưng chưa hề có Codex.
- **Tránh race-condition trên cổng 1455**: Khi chạy multi-worker (`worker = 5`), mỗi worker xin `authUrl` riêng nhưng chung callback port 1455. OmniRoute phân biệt session qua param `state` trong URL redirect. Đảm bảo request callback mang đầy đủ param `state` về `127.0.0.1:1455`.
