# Kiến trúc Pool Phân Tách giữa Antigravity vs Codex vs ChatGPT-Web trên OmniRoute (Port 20129)

## 1. Sự thật kiến trúc phân tầng các Pool tài khoản

Nhiều trường hợp người vận hành lầm tưởng "đã OAuth cả đống account thì pool nào cũng có sẵn tài khoản". Thực tế trên OmniRoute, tài khoản được phân lập hoàn toàn theo `provider`:

| Provider | Mục đích / Model phục vụ | Nguồn tài khoản | Tình trạng thực tế |
| :--- | :--- | :--- | :--- |
| **`antigravity`** | Phục vụ Google Gemini & Claude Opus Thinking (`ag-opus-pool`, `ag-gemini-pool-3`) | 81 Google Accounts (đăng nhập Google OAuth qua Playwright) | **81 acc LIVE**, chạy cực khỏe, không bị chết |
| **`codex`** | Phục vụ lập trình chuyên sâu (`gpt-5.6-terra-high`, `gpt-5.6-sol`, `gpt-5.5`) | OAuth Developer Flow (`authUrl` callback port 1455) | **Chỉ có 1 acc chính** (`~/.codex/auth.json`), các acc web import bị expired |
| **`chatgpt-web`** | Phục vụ chat web & gọi chéo được cả Terra/Sol/Luna | Session token từ `chatgpt.com/api/auth/session` | **5 acc LIVE**, token sống bền nhiều ngày |

---

## 2. Nguyên nhân sâu xa của lỗi `503 Unavailable (reset after 700h+)`

- **Hiện tượng**: Gọi combo `review` (hoặc `gpt-5.6-terra-high`) trả về `503 Unavailable (reset after 701h 35m)`.
- **Nguyên nhân cốt lõi**:
  - Combo `review` đặt `codex/gpt-5.6-terra-high` ở Tier 1.
  - Người dùng tưởng rằng 80+ tài khoản đã OAuth sẽ cùng gánh tải cho combo này. Nhưng thực tế 80+ acc đó nằm ở pool **`antigravity`** (chỉ gánh cho Tier 2: `ag-opus-pool`).
  - Toàn bộ pool **`codex`** ở Tier 1 chỉ có duy nhất 1 connection sống (`Codex Session ~/.codex/auth.json`).
  - Khi người dùng gọi review liên tục suốt ngày, OmniRoute dồn 100% request vào đúng 1 tài khoản đó -> tài khoản bị OpenAI bóp rate-limit/hết hạn ngạch tháng cứng (700h+).

---

## 3. Khả năng gọi chéo Model của ChatGPT-Web

Thực nghiệm đo đạc thực tế ngày 13/09/2026 trên OmniRoute 20129:
- `chatgpt-web/gpt-5.6-terra-high`: **HTTP 200 OK** (phản hồi chuẩn xác, hỗ trợ reasoning).
- `chatgpt-web/gpt-5.6-sol`: **HTTP 200 OK** (sinh code chuẩn).
- `chatgpt-web/gpt-5.6-luna-free-thinking`: **HTTP 200 OK** (giải thuật toán min-heap tối ưu).

**Chiến lược giải quyết**:
1. Đưa `chatgpt-web` vào làm tier fallback hoặc san tải song song trong combo `review` để tránh dồn toàn bộ tải vào 1 connection Codex duy nhất.
2. Nạp hàng loạt tài khoản Google sang pool `chatgpt-web` (bằng cách lấy session token web) vì vừa né được Phone Checkpoint của OAuth Codex, vừa không bị áp hạn ngạch tháng 503.

---

## 4. Cạm bẫy Token khi nạp `chatgpt-web` & Ảo giác đọc Log Request

### Cạm bẫy định dạng Token (JWT vs Session Cookie & Chunked Cookies):
- Provider `chatgpt-web` trong OmniRoute dùng endpoint trao đổi session `/api/auth/session`, do đó trường API Key **bắt buộc phải là cookie `__Secure-next-auth.session-token`** (hoặc chuỗi cookie chứa cookie này).
- **Lỗi 1 (JWT Header / Trích xuất nhầm)**: Copy nhầm JWT Bearer / ID token (bắt đầu bằng `eyJhbGci...`) từ request header hay localStorage thay vì cookie.
- **Lỗi 2 (Bẫy Chunked Cookies > 4KB)**:
  - Khi cookie phiên của NextAuth vượt quá 4096 bytes, máy chủ tự động chia thành các chunk: `__Secure-next-auth.session-token.0` và `__Secure-next-auth.session-token.1`.
  - Các script trích xuất tự động qua Playwright CDP thường duyệt `for ck in context.cookies(): if 'session-token' in ck['name']: break`.
  - Hậu quả: Vòng lặp dừng ngay ở chunk `.0`, chỉ lấy giá trị cụt (bắt đầu bằng `eyJhbGci...`) và bỏ quên chunk `.1` cùng tên cookie. Khi đẩy lên OmniRoute, chuỗi này bị wrap sai format và OpenAI trả về lỗi `401.0`:
    `[401]: ChatGPT auth failed — re-paste your __Secure-next-auth.session-token cookie from chatgpt.com.`
  - **Định dạng chuẩn bắt buộc nạp vào OmniRoute apiKey**:
    `__Secure-next-auth.session-token.0=<chunk0>; __Secure-next-auth.session-token.1=<chunk1>`

### Kỹ thuật trích xuất Cookie Offline từ GPM Profile (Zero-UI, Không cần mở Chrome):
Khi cần sửa hàng loạt tài khoản lỗi 401 mà không muốn khởi động profile làm phiền màn hình hay dính reCAPTCHA:
1. Xác định `profile_path` qua GPM API: `GET http://127.0.0.1:19995/api/v3/profiles/{id}`.
2. Thư mục profile nằm tại: `~\AppData\Local\Programs\GPMLogin\profile\<profile_path>`.
3. Khóa giải mã nằm ở `Local State`: giải mã qua DPAPI (`win32crypt.CryptUnprotectData`).
4. Database cookie nằm tại `Default/Network/Cookies`: truy vấn bảng `cookies` với `name LIKE '%session-token%'`.
5. **Đặc thù Chromium v130+**: Chuỗi giải mã bằng AESGCM chứa header nhị phân 32 bytes (`dec[32:]` mới là chuỗi text cookie thực sự).
6. Ghép toàn bộ chunk theo thứ tự: `; `.join(f"{name}={val}") rồi gọi `PUT http://127.0.0.1:20129/api/providers/{conn_id}` với `apiKey: full_cookie` và `isActive: true`.
7. Kiểm tra live bằng chat completion thật: `POST /v1/chat/completions` với `model: chatgpt-web/gpt-5.6-luna-free`.

### Ảo giác đọc Log Request (Failover Cascade Illusion):
- Khi có request model (ví dụ `gpt-5.6-luna-free`), OmniRoute duyệt qua danh sách connection: nếu các account đầu danh sách bị 401, router failover lần lượt cho đến khi gặp account sống đầu tiên (trả về 200 `[healed]`).
- **Ngay khi 1 account trả về 200, chuỗi failover lập tức dừng lại.** Tất cả các account khỏe mạnh xếp sau đó hoàn toàn KHÔNG được gọi đến trong request đó.
- **Hệ quả phân tích**: Nhìn vào bảng log request của 1 lần gọi sẽ thấy một loạt 401 và duy nhất 1 account 200, dẫn đến kết luận sai lệch là "cả pool chỉ có đúng 1 acc sống".
- **Kỷ luật chẩn đoán đúng**:
  1. Kiểm tra các dòng log của sự kiện `connection-test` (OmniRoute test độc lập từng account).
  2. Hoặc query trực tiếp bảng `provider_connections` trong `storage.sqlite` để xem trường `test_status` và `error_code` của từng connection.
  - *Lưu ý vị trí DB SQLite*: Trên Windows, database hoạt động thực tế nằm tại `~/.omniroute/storage.sqlite` (`C:\Users\Kibe\.omniroute\storage.sqlite` do `getLegacyDotDataDir()` giữ legacy dir), file ở root repo `C:\Users\Kibe\OmniRoute\storage.sqlite` thường là file rỗng (0 bytes).
  - *Phân biệt 401 Session Expired vs Hết Quota trong pool chatgpt-web*:
    - **401 Unauthorized**: Session cookie hết hạn (`ChatGPT session expired — log into chatgpt.com and copy a fresh cookie`), hoàn toàn KHÔNG PHẢI hết quota. Router tự động failover sang acc kế tiếp.
    - **Hết Quota / Rate limit thực tế**: Thường trả về HTTP **`502 Bad Gateway`** kèm `[502]: You've hit your limit. Please try again later.` (khi gọi model Pro vượt trần account free) hoặc HTTP **`429`**. Cần tra cứu bảng `call_logs` trong `storage.sqlite` để phân định chính xác.
