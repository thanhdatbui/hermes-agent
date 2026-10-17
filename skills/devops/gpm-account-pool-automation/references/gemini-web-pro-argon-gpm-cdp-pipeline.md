# Gemini Web Pro Session Extraction, Proxy Binding, and Argon 4 Model Selector

## 1. Bản chất kỹ thuật & Sự khác biệt giữa Antigravity API và Gemini Web

- **Antigravity Provider (`antigravity` / `agy`):** 
  - Gọi qua Google Cloud Code internal API (`daily-cloudcode-pa.googleapis.com`).
  - Dùng OAuth access/refresh token.
  - Bị trừ hạn mức quota IDE của tài khoản Google AI Pro (dù free nhưng có trần tuần/ngày).
- **Gemini Web Provider (`gemini-web`):**
  - Gọi trực tiếp vào giao diện `gemini.google.com/app`.
  - Dùng Cookie phiên duyệt web: `__Secure-1PSID`, `__Secure-1PSIDTS`, `__Secure-1PSIDCC`.
  - Hoàn toàn **FREE 100% quota IDE**, chạy không giới hạn như người dùng gõ web.
  - Trạng thái đăng nhập trong GPM Profile: Phải mở `https://gemini.google.com/app` để sinh đủ bộ 3 cookie `1PSID*`.

---

## 2. Quy trình trích xuất Cookie Pro từ GPM qua CDP (Tự động 100%)

1. **Khởi động GPM Profile có gói Pro:**
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/start/{profile_id}`.
   - Nhận `remote_debugging_address` (e.g. `127.0.0.1:58823`).
2. **Tạo tab mới điều hướng `gemini.google.com/app` qua CDP:**
   - Gửi HTTP `PUT http://{remote_debugging_address}/json/new?https://gemini.google.com/app`.
   - Nhận `webSocketDebuggerUrl`.
3. **Trích xuất Cookie bảo mật bằng WebSocket CDP:**
   - Kết nối raw websocket (kèm `suppress_origin=True` tránh lỗi 403).
   - Gửi lệnh `Storage.getCookies` hoặc `Network.getCookies`.
   - Lọc các cookie thuộc domain `.google.com`:
     - `__Secure-1PSID` (bắt buộc, ~153 ký tự)
     - `__Secure-1PSIDTS` (bắt buộc, ~78 ký tự)
     - `__Secure-1PSIDCC` (~74 ký tự)
   - Ghép thành chuỗi header:
     `cookie_str = "__Secure-1PSID=...; __Secure-1PSIDTS=...; __Secure-1PSIDCC=..."`
4. **Dọn dẹp tiến trình:**
   - Gọi `GET http://127.0.0.1:19995/api/v3/profiles/stop/{profile_id}`.
   - Dùng `psutil` kill sạch tiến trình `gpm_browser_chromium_core.exe` mồ côi để giải phóng khóa file `Cookies` SQLite và RAM.

---

## 3. Gắn Proxy 4G Mobi 1-1 cho Connection trong OmniRoute

Để tránh bị Google phát hiện đổi IP đột ngột (gây checkpoint/out session), connection `gemini-web` trong OmniRoute bắt buộc phải gán đúng proxy 4G tương ứng với profile GPM:
1. **Tạo Connection:**
   - `POST http://127.0.0.1:20129/api/providers`
   - Provider: `"gemini-web"`
   - `apiKey`: `cookie_str`
   - `providerSpecificData`: `{"cookie": cookie_str, "proxy": proxy_url, "tier": "g1-pro-tier", "plan": "Pro"}`
2. **Gán Proxy cố định vào SQLite `storage.sqlite`:**
   - Bảng `proxy_assignments`:
     ```sql
     INSERT INTO proxy_assignments (proxy_id, scope, scope_id, position, created_at, updated_at)
     VALUES (?, "connection", ?, 0, datetime("now"), datetime("now"));
     ```
   - Xác nhận qua endpoint test:
     `POST http://127.0.0.1:20129/api/providers/{id}/test` $\rightarrow$ Trả về `{"valid": true, "diagnosis": {"type": "ok"}}`.

---

## 4. Phát hiện Model "4 Argon" (Gemini 4 Argon) trên Web UI & Cơ chế kích hoạt

### Thực tế DOM trên tài khoản Google AI Pro (`dokieu04092004@gmail.com`):
Khi click mở dropdown chọn model tại góc trên bên trái của `gemini.google.com/app`, menu trả về danh sách model thực tế:
- `3.5 Flash-Lite` (Câu trả lời nhanh nhất)
- `3.8 Flash` (Trợ giúp toàn diện)
- `3.1 Pro` (Suy luận nâng cao)
- **`4 Argon` (Nhiệm vụ phức tạp - MỚI)**
- `Cấp độ tư duy` (Thinking Level / Reasoning control)

### Lỗ hổng của `gemini-web.ts` mặc định & Giải pháp:
- **Lỗ hổng:** `gemini-web.ts` của OmniRoute chỉ vào `gemini.google.com/app` và gõ thẳng vào `.ql-editor`, không chọn model $\rightarrow$ Luôn bị Google mặc định trả lời bằng **Flash**.
- **Giải pháp gọi đúng 4 Argon:**
  1. Click nút Model Switcher (`button[aria-haspopup="menu"]` hoặc text chứa `Gemini Flash`).
  2. Trong menu xổ ra (`div.cdk-overlay-container`), click chọn element chứa text `4 Argon`.
  3. Gõ prompt vào `.ql-editor` và bắt stream response từ `StreamGenerate`.
- **Khuyên dùng:** Sử dụng CDP điều khiển trực tiếp profile GPM có sẵn Proxy 4G và cookies để gọi `4 Argon` làm Worker, vừa giữ nguyên vân tay trình duyệt vừa không phụ thuộc cài đặt Playwright Chromium trên máy host.
