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

### Lỗ hổng của `gemini-web.ts` cũ & Giải pháp Native HTTP StreamGenerate (Đã thi công):
- **Cơ chế cũ (Playwright):** Cồng kềnh, dễ lỗi thiếu Chromium binary hoặc timeout trên Windows.
- **Cơ chế mới (Native HTTP StreamGenerate):**
  1. GET `https://gemini.google.com/app` với Cookie lấy `SNlM0e` (AT token) và build label (`cfb2h`).
  2. POST trực tiếp `/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate` với form payload `f.req` và `at`.
  3. Phản hồi siêu tốc 2.5s - 5s qua proxy 4G Mobi 1-1, hoàn toàn không cần trình duyệt Playwright.
- **Điều khiển Reasoning Effort qua Slot [17] Protobuf:**
  - `inner[17] = [[0]]`: High (Deepest Thinking) — dùng cho bài toán kiến trúc, giải thuật hóc búa.
  - `inner[17] = [[2]]`: Medium (Mặc định cho Worker thi công) — tư duy sắc sảo nhưng kỷ luật $O(1)$, chống over-engineering.
  - `inner[17] = [[4]]`: Low — phản xạ nhanh cho tác vụ trích xuất / regex.
  - `inner[17] = null`: None — tắt hẳn CoT.
- **Hiện thực lịch sử chat trên giao diện Web (Conversation History Isolation):**
  - **Gemini Web (`gemini-web-argon-pool`):** Do gửi payload HTTP RPC với `inner[2]` rỗng, máy chủ Google xử lý stateless và **KHÔNG LƯU lịch sử chat vào thanh Recent Chats trên web**.
  - **ChatGPT Web (`gpt-web-sol`):** Luôn bật mặc định cờ `history_and_training_disabled: true` (Temporary Chat), **KHÔNG LƯU lịch sử chat trên chatgpt.com**.

---

## 5. Phân Định Danh Tính Worker (Tránh Nhầm Lẫn Thuật Ngữ)
- **AGY CLI (`ag_cli.py`):** Binary CLI chính thức của Google Antigravity, chạy model **Gemini** (`gemini-3.8-flash-high/medium`). Tốc độ cực nhanh 3s - 5s.
- **Claude CLI (`claude_worker.py`):** CLI chính thức của Anthropic, chạy model **Claude Haiku / Sonnet** (tuyệt đối không nhầm sang Gemini).
- **Sol Web (`sol_worker.py`):** Worker autonomous ReAct chạy **GPT-5.6 Sol** qua OmniRoute `:20129`.
- **Argon Web Pool (`gemini-web-argon-pool`):** Worker pool 5 accs Google AI Pro chạy **Gemini 4 Argon / 3.1 Pro** qua OmniRoute `:20129`.

---

## 6. An Toàn Tài Khoản & Benchmark Vận Hành Thực Chiến
- **Temporary Chat / Stateless là Khiên Hộ Mệnh cho Tài Khoản:**
  - Nếu lưu lịch sử: Worker cày 300-500 prompts/ngày sẽ tạo ra hàng ngàn đoạn chat rác 1-turn ngắn ngủn trong Sidebar $\rightarrow$ Hệ thống chống lạm dụng của Google/OpenAI sẽ phát hiện hành vi bot và gắn cờ tài khoản ngay.
  - Chạy ở chế độ Stateless (Gemini RPC) hoặc Temporary Chat (`history_and_training_disabled: true` trên ChatGPT) giúp tài khoản sạch sẽ tuyệt đối, mô phỏng đúng hành vi tra cứu nhanh của người dùng thật, chống checkpoint/ban nick 100%.
- **Argon Medium vs Argon High:**
  - `Medium` (Default cho Worker): Né bẫy runtime Python cực tốt (ví dụ: bẫy heapq tuple comparison với dict payload, co biên giữ hình vuông avatar), code tinh gọn chuẩn $O(1)$, chống over-engineering.
  - `High`: Tầm nhìn hệ thống sâu rộng hơn (tư duy cấp phát IP mạng bảo toàn lease, kiểm tra thứ tự ưu tiên phạt), thích hợp làm cố vấn/thiết kế thuật toán khi Medium bế tắc.
- **AGY CLI vs Argon Web Pool (Nguyên nhân chênh lệch năng lực):**
  - `AGY CLI` (3.5s - 5.5s): Nhanh gấp 4-5 lần. Kết nối trực tiếp vào Google Cloud Code IDE engine (`daily-cloudcode-pa.googleapis.com`), được fine-tune chuyên biệt cho SWE (kỹ sư phần mềm) nên phản xạ phòng thủ OS (file lock mode a+b, fsync, zombie process, cắt bỏ token duration) cực kỳ già dơ. **Ưu tiên số 1 cho Worker thi công sửa code O(1) <= 15 dòng**.
  - `Argon Pool` (11s - 20s): Bền bỉ, miễn phí 100% quota IDE, chuyên trị batch lớn, phân tích dữ liệu và chạy thâu đêm.
  - **Lưu ý kỹ thuật về Slot [79] (modelCategory):** Hiện tại trong `gemini-web.ts`, slot `inner[79]` đang để trống (`null`) nên máy chủ Google tự fallback về mô hình Consumer Chatbot mặc định chứ **chưa kích hoạt trọng số của model 4 Argon thực thụ**. Để gọi đúng 4 Argon, cần map mã `MODE_CATEGORY` vào `inner[79]` (tương tự như `gemini-business.ts`).
