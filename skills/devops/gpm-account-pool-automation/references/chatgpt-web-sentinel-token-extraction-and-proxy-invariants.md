# ChatGPT-Web Pool Rescue, Sentinel Bypass & Proxy Invariants

## 1. Bản chất sự cố Sentinel PoW (HTTP 401 trên /backend-api/sentinel/chat-requirements/prepare)
Khi upstream OpenAI cập nhật web client, OmniRoute executor `chatgpt-web.ts` bị lỗi `SENTINEL_BLOCKED` vì 2 nguyên nhân cốt lõi:
1. **Lệch OAI_CLIENT_VERSION & OAI_CLIENT_BUILD_NUMBER:** Header gửi lên không khớp với phiên bản live trên HTML `https://chatgpt.com`.
2. **OpenAI bỏ Webpack scripts, chuyển sang `<link rel="modulepreload">`:**
   - Hàm `fetchDpl()` cũ tìm thẻ `<script src="...">` Webpack chunk để lấy path asset client.
   - Khi không tìm thấy, `fetchDpl()` fallback tự tạo tên file JS ngẫu nhiên (`webpack-${randomHex(16)}.js`).
   - OpenAI kiểm tra file này không tồn tại trên CDN (`/cdn/assets/...`) và trả về `HTTP 401 Unauthorized`.
   - **Cách vá đúng:** Đổi regex sang bắt `<link rel="modulepreload" href="([^"]+/entry\.client-[^"]+\.js)">`, fallback về asset hash đang hoạt động (ví dụ `/cdn/assets/entry.client-go4vy0y8.js`).

## 2. Invariant Trích xuất Session Token ChatGPT từ Context Trình duyệt
- **CẤM TUYỆT ĐỐI** kiểm tra token chỉ bằng tiền tố `value.startswith("eyJhbG")`:
  - Trang đăng nhập `auth.openai.com` tự sinh nhiều cookie tạm thời (như `oai-did`, `auth0`, `__cf_bm`) có value dạng JWT (`eyJhbG...`) ngay cả khi **CHƯA ĐĂNG NHẬP**.
  - Script nếu chỉ check `eyJhbG` sẽ ngộ nhận tài khoản đã đăng nhập, nạp cookie rác vào DB dẫn đến OmniRoute báo `401 Unauthorized (re-paste your __Secure-next-auth.session-token)`.
- **ĐIỀU KIỆN TIÊN QUYẾT BẮT BUỘC:** Cookie đăng nhập của ChatGPT Web **bắt buộc phải có tên chứa `session-token`**:
  ```python
  has_session = any("session-token" in (c.get("name") or "") for c in all_cookies)
  ```
  Session token hợp lệ thường có độ dài chuỗi cookie > 8.000 ký tự (bao gồm cookie chunk `.0`, `.1`).

## 3. Invariant Khớp Proxy Mobi Farm (test.taadaa.click)
- Mỗi port Mobi `5101..5138` có username tương ứng theo số port:
  - Port `5101` $\rightarrow$ user `mobi1`
  - Port `5104` $\rightarrow$ user `mobi4`
  - Port `5128` $\rightarrow$ user `mobi28`
  - Password chung: `TaadaaMobi#2026!`
- **CẤM** gán cứng user `mobi28` cho tất cả các port. Khi gửi sai user, proxy trả về `HTTP 407 Proxy Authentication Required`, OmniRoute kích hoạt `[Proxy Fast-Fail] Proxy unreachable` và đánh rớt tài khoản ngay lập tức.
- Trong GPM SQLite (`profile_data.db`), proxy được lưu tại trường `Proxy` (chữ P hoa) trong `JsonData`, dạng `test.taadaa.click:51XX:mobiXX:TaadaaMobi#2026!`.

## 4. Invariant Model Slug Cho Tài Khoản Free
- Tài khoản ChatGPT Free **KHÔNG HỖ TRỢ** model `gpt-5.6-sol-high` hay `gpt-5-6` trực tiếp qua API web (OpenAI trả về `404 Model not found`).
- Tài khoản Free chỉ nhận:
  - Model slug: `auto` (hoặc `gpt-5.6-luna-free` trong OmniRoute mapping).
  - Có thể kèm `system_hints: ["reason"]` nếu muốn bật suy luận (`gpt-5.6-luna-free-thinking`).
- Trong bảng `combos` (`chatgpt-web-pool`), các entries dành cho tài khoản Free **bắt buộc phải đặt `model = "chatgpt-web/auto"`**.

## 5. Quy trình Nạp & Nghiệm thu Pool Chuẩn (Zero-Failure)
1. **Khởi động GPM Profile** qua GPM Local API (`/api/v3/profiles/start/{id}`).
2. **Mở https://chatgpt.com/**, nếu gặp màn hình đăng nhập thì bấm "Continue with Google" $\rightarrow$ chọn email tương ứng $\rightarrow$ chấp thuận Consent $\rightarrow$ submit age nếu có form onboarding.
3. **Chờ redirect về https://chatgpt.com/** và xác nhận `any("session-token" in c["name"] for c in context.cookies())`.
4. **Chụp ảnh Gate 6**, soi mắt OCR xác nhận giao diện ChatGPT chào mừng người dùng thực tế.
5. **Ghi vào `storage.sqlite`:**
   - Cập nhật `provider_connections` (`is_active = 1`).
   - Cập nhật `proxy_assignments` đúng proxy 1-1 (scope `account`).
   - Cập nhật combo `chatgpt-web-pool` với model `chatgpt-web/auto`.
6. **Reload OmniRoute** (kill process node để watchdog khởi động lại, xóa cache in-memory).
7. **Canary Probe:** Gửi POST tới `http://127.0.0.1:20129/v1/chat/completions` với `model: "chatgpt-web-pool"`, xác nhận trả lời HTTP 200 trong vòng < 30s.
