# Hot-Session ChatGPT-Web OAuth Hook via Active Google Session

## 1. Bối cảnh & Nguyên lý hoạt động
Khi chạy pipeline OAuth Antigravity trên browser profile GPM (`run_oauth_s7_pipeline.py`), trình duyệt đã hoàn tất đăng nhập Google đầy đủ (vượt qua Google prompt/2FA). Thay vì mở session mới hoặc login thủ công, ta tận dụng ngay browser context đang "nóng" (active Google session) để điều hướng trực tiếp sang ChatGPT qua luồng Google Direct Social Login:

`https://chatgpt.com/auth/login_with?callback_path=%2F&connection=google-oauth2&screen_hint=login_or_signup&ext-web-mobile-direct-social-login=true`

## 2. Kiến trúc Module `src/chatgpt_hot_oauth.py`
Hàm chính: `trigger_hot_chatgpt_oauth(page, context, email: str, mid: int, port: int, p_res: dict) -> bool`

Các bước thực hiện:
1. **Navigate & Handshake**: Điều hướng tới endpoint login direct Google OAuth.
2. **Auto-handling Popups & Forms**:
   - Tự động điền form "About you" (name, age) nếu xuất hiện tài khoản mới.
   - Click nút "Tiếp tục" / "Cho phép" nếu có màn hình consent.
   - Chọn đúng email nếu xuất hiện Google Account Chooser.
3. **Cookie Extraction**:
   - Trích xuất toàn bộ cookies của domain `https://chatgpt.com` từ Playwright context.
   - Định dạng chuỗi cookie `k1=v1; k2=v2; ...`.
   - Kiểm tra ngưỡng cookie hợp lệ (>= 15 cookies).
4. **OmniRoute Ingestion & Combo Update**:
   - Gửi validate tới OmniRoute: `POST /api/providers/validate` với `{"provider": "chatgpt-web", "apiKey": cg_cookie_str}`.
   - Đăng ký connection: `POST /api/providers/connections`.
   - Gán proxy tương ứng cổng máy vào connection mới (`PUT /api/settings/proxies/assignments`).
   - Mở SQLite DB `storage.sqlite`, trích xuất combo `chatgpt-web-pool`, tự động append connection model mới (`chatgpt-web/gpt-5.6-sol-high`) vào pool nếu chưa tồn tại.

## 3. Hook trong Pipeline (`run_oauth_s7_pipeline.py`)
- Import an toàn trong block `try...except`:
  ```python
  try:
      from chatgpt_hot_oauth import trigger_hot_chatgpt_oauth
  except Exception:
      trigger_hot_chatgpt_oauth = None
  ```
- Kích hoạt ngay sau bước `sync-models`:
  ```python
  if trigger_hot_chatgpt_oauth:
      trigger_hot_chatgpt_oauth(page, context, email, mid, port, p_res)
  ```
- Hoàn toàn non-blocking đối với Antigravity: nếu ChatGPT hot OAuth gặp lỗi/timeout, nó ghi warning log và trả về `False`, không làm gián đoạn pipeline chính.
