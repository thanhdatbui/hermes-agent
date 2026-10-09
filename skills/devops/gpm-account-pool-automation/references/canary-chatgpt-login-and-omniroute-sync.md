# Canary ChatGPT Login + OAuth OmniRoute Execution Guide

## Mục đích & Ngữ cảnh
Quy trình canary / batch kết nối profile GPM (đã đăng nhập Google Session) để đăng nhập ChatGPT và đồng bộ OAuth Token vào OmniRoute (port 20129) cho cả 2 provider: `codex` và `chatgpt-web`.

## Nguyên tắc Vận hành (Scope & Budget Guardrails)
1. **Tuần tự từng Profile**:
   - Không chạy song song để tránh tranh chấp CDP port hoặc quá tải proxy.
   - Mỗi account gồm 4 bước chuẩn xác: Start profile -> Login ChatGPT via Google SSO -> Xử lý onboarding / main chat check -> Trích xuất token & sync OmniRoute.
2. **Fail-Fast**:
   - Nếu <= 3 iterations phát hiện Google session chết (đòi mật khẩu không có trong scope) hoặc proxy timeout: Abort ngay lập tức acc đó, gọi `profiles/stop/{id}`, ghi log báo anchor / đề xuất contract, chuyển sang acc tiếp theo. Cấm đốt budget công cụ mò tìm file tài khoản.
3. **Tiết kiệm Tool Call Budget**:
   - Gom toàn bộ logic vào 1 runner script duy nhất (ví dụ: `scripts/canary_chatgpt_3accs.py`).
   - Kiểm tra `py_compile` trước khi thực thi để tránh syntax error giữa chừng.

## Các bước chuẩn trong Runner Script

### B1. Khởi động Profile GPM & Kết nối CDP
- `GET http://127.0.0.1:19995/api/v3/profiles/start/{id}?win_scale=0.8`
- Lấy `remote_debugging_address`.
- Sleep 2.5s + retry `connect_over_cdp` tối đa 5 lần.

### B2. Điều hướng & Google SSO Login
- Điều hướng tới `https://chatgpt.com/auth/login` (timeout <= 25s).
- Dismiss Cookie Banner:
  - Selector: `button:has-text("Chấp nhận tất cả")`, `button:has-text("Accept all")`.
- Click `Continue with Google` / `Tiếp tục với Google`:
  - Selector: `button:has-text("Continue with Google")`, `button:has-text("Tiếp tục với Google")`.
- Kiểm tra tab context:
  - Nếu Google mở ở popup hoặc tab riêng (`accounts.google.com`), switch page/context tới tab đó.
  - Tìm và click đúng tài khoản email target (`[data-email="{email}"]`, `div:has-text("{email}")`).
  - Nếu có màn hình Consent: click `Continue` / `Tiếp tục` / `Cho phép` / `Allow`.
- Nếu phát hiện `account_deactivated` hoặc tài khoản bị vô hiệu hóa -> FAIL-FAST, dừng profile, chuyển acc tiếp theo.

### B3. Redirect & Onboarding Verification
- Chờ redirect về `chatgpt.com` hoặc `openai.com`.
- Xử lý màn hình Onboarding (nếu xuất hiện form `about-you` / "Bạn bao nhiêu tuổi?"):
  - Họ tên: điền tên trích xuất từ prefix email hoặc họ tên chuẩn.
  - Tuổi: điền giá trị 25 (hoặc ngày tháng năm sinh nếu form dạng DD/MM/YYYY).
  - Click `Tiếp tục` / `Continue`.
- Xác nhận vào giao diện chính:
  - Kiểm tra body chứa `'Hôm nay bạn muốn làm gì'` / `'Đoạn chat mới'` / `'New chat'` hoặc selector `#prompt-textarea`.

### B4. OAuth OmniRoute Sync & Screenshot Nghiệm thu
1. **Codex OAuth Token**:
   - Mở `https://chatgpt.com/api/auth/session` trên context của profile.
   - Trích xuất `accessToken` (bắt buộc `startswith('ey')` và `len > 50`).
   - Gửi `POST http://127.0.0.1:20129/api/oauth/codex/import-token` với payload `{"accessToken": token, "name": "<email> (<Name>)"}`.
   - Ghi lại `conn_id` trả về.
2. **ChatGPT-Web Session Token**:
   - Trích xuất cookie `__Secure-next-auth.session-token` từ domain `https://chatgpt.com` (gộp các chunk `.0`, `.1` nếu có).
   - Kiểm tra `GET http://127.0.0.1:20129/api/providers` xem connection đã tồn tại chưa:
     - Nếu đã có: `PUT http://127.0.0.1:20129/api/providers/{conn_id}` với `apiKey: session_token`.
     - Nếu chưa: `POST http://127.0.0.1:20129/api/providers` với `provider: "chatgpt-web"`, `apiKey: session_token`.
3. **Nghiệm thu**:
   - Chụp ảnh full màn hình nghiệm thu: `debug_screenshots/chatgpt_<email>_verified.png`.
   - Gọi `http://127.0.0.1:19995/api/v3/profiles/stop/{id}` để giải phóng tài nguyên.
