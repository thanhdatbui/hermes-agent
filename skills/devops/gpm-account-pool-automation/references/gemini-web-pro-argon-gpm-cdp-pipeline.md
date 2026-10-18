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
  - **Gemini Web StreamGenerate (OmniRoute `:20129`):** Do gửi payload HTTP RPC với `inner[2]` rỗng, máy chủ Google xử lý stateless và **KHÔNG LƯU lịch sử chat vào thanh Recent Chats trên web**.
  - **Gemini 4 Argon Local CDP Daemon (`:20135`):** Vì tương tác trực tiếp trên DOM của Chromium thật tại `https://gemini.google.com/app`, các câu hỏi **ĐƯỢC LƯU LẠI trong thanh Recent Chats** của tài khoản GPM đó. Tài khoản Pro không bị giới hạn số lượng chat, nhưng cần biết điểm khác biệt này để dọn dẹp định kỳ hoặc mở tab Temporary Chat khi cần giấu dấu vết.
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
- **Argon Medium vs Argon High (Tổng kết 10 Hiệp Đấu Thực Chiến 18/10/2026):**
  - **Tỷ số toàn diện:** High thắng 7, Medium thắng 2, Hòa 1.
  - **Hiện tượng Tốc độ & Sức mạnh:**
    - Ở bài toán phức tạp (nhị phân MP4 box, audit ARP subnet), **Argon High phản hồi nhanh gấp 2 đến 3 lần Medium** (H6: 27s vs 51s; H10: 14s vs 48s) nhờ kích hoạt cây tìm kiếm suy luận sâu (Deep Think Tree) đi thẳng vào giải pháp tối ưu, tránh bị backtrack lúng túng.
    - Thời gian phản hồi trung bình giai đoạn 2: High đạt **27.38s**, nhanh hơn Medium (**36.36s**) gần 9 giây.
  - **Khả năng phòng thủ hệ thống:**
    - High tự động bổ sung giao diện chuẩn Python stdlib (`seek`/`read` cho binary stream, cài `__lt__` cho task queue chống lỗi tuple priority, giải thuật DCT 2D tách làm 2 lần 1D $\mathcal{O}(N^3)$).
  - **Khuyến nghị điều phối:**
    - **Worker thi công code khó / giải thuật:** Ưu tiên số 1 là **Argon High** (`reasoning_effort: "high"`).
    - **Tác vụ batch đơn giản / format JSON:** Dùng **Argon Medium** để giữ độ dài output gọn gàng.
- **AGY CLI vs Argon Web Pool (Nguyên nhân chênh lệch năng lực):**
  - `AGY CLI` (3.5s - 5.5s): Nhanh gấp 4-5 lần. Kết nối trực tiếp vào Google Cloud Code IDE engine (`daily-cloudcode-pa.googleapis.com`), được fine-tune chuyên biệt cho SWE (kỹ sư phần mềm) nên phản xạ phòng thủ OS (file lock mode a+b, fsync, zombie process, cắt bỏ token duration) cực kỳ già dơ. **Ưu tiên số 1 cho Worker thi công sửa code O(1) <= 15 dòng**.
  - `Argon Pool` (11s - 20s): Bền bỉ, miễn phí 100% quota IDE, chuyên trị batch lớn, phân tích dữ liệu và chạy thâu đêm.
  - **CẢNH BÁO BẪY KỸ THUẬT VỀ SLOT [79] & SỰ THẬT VỀ 4 ARGON (BÀI HỌC XƯƠNG MÁU 18/10/2026):**
    * Ban đầu có giả định rằng gán `inner[79]` trong `StreamGenerate` sẽ bật được "4 Argon". **ĐÂY LÀ GIẢ THUYẾT SAI / GIẢ CẦY!**
    * Enum `MODE_CATEGORY` của `StreamGenerate` cũ chỉ hỗ trợ: `1=FAST`, `2=THINKING`, `3=PRO`, `4=AUTO`, `5=FAST_DYNAMIC_THINKING`, `6=FLASH_LITE`. Gán `inner[79] = 3` chỉ kích hoạt **Gemini 3.1 Pro**, hoàn toàn KHÔNG PHẢI 4 Argon.
    * **Hiện trường thực tế qua DevTools CDP:** Khi chọn `4 Argon` trên web UI, Google chuyển sang giao thức WebChannel nhị phân hoàn toàn khác: `POST https://geminiweb-pa.clients6.google.com/v1/processSession` (không dùng `StreamGenerate`).
    * **Giải pháp chuẩn để chạy đúng 4 Argon xịn 100% (Phương án B):** Dựng Daemon local (`gemini_argon_server.py`, port `:20135`) kết nối Playwright CDP vào GPM profile Google AI Pro (`dokieu`), giữ tab web `4 Argon` ngầm (offscreen, zero cướp focus), expose API OpenAI-compatible `/v1/chat/completions`. Đã nghiệm thu bằng WinRT OCR đọc đúng text sinh ra trên màn hình.

---

## 7. Cạm Bẫy Treo Tiến Trình AGY CLI Khi Hết Hạn Token & Kỷ Luật Điều Phối

### Cạm bẫy Silent Timeout của Antigravity CLI (`ag_cli.py` / `agy -p`):
- **Hiện tượng:** Khi chạy benchmark hoặc dispatch worker qua `ag_cli.py ask --model gemini-3.8-flash-high`, tiến trình bị treo đơ đúng 120 giây rồi văng timeout, trả về 0 ký tự (`output: empty`).
- **Nguyên nhân gốc rễ & Bẫy đói LRU (The LRU Starvation Trap):**
  - **Tài khoản là độc lập 100%:** 22 profile trong `D:/Taadaa/agy_profiles/` chứa 22 tài khoản Gmail khác nhau (`google_accounts.json`) và 22 bộ OAuth Refresh Token (103 chars) riêng biệt, không phải dùng chung 1 acc.
  - **Bẫy điều phối LRU trong `ag_cli.py`:** Thuật toán chọn profile ưu tiên acc có `last_used` nhỏ nhất. Profile lỗi/chậm (ví dụ `acc_16` gắn proxy Mobi `5121`) có `last_used = 0` nên luôn được xếp lên đầu. Khi bị Timeout (120s), `ag_cli.py` văng ngoại lệ mà KHÔNG cập nhật `last_used` và KHÔNG đưa vào cooldown. Kết quả: các lượt gọi tiếp theo tiếp tục chọn lại đúng profile lỗi đó, gây nghẽn toàn bộ pool khiến tưởng nhầm cả 22 profile đều hỏng.
  - **Khởi động ngầm:** Khi proxy bị chậm hoặc token cần refresh, trong chế độ headless (`-p`) trên Windows với `stdin=subprocess.DEVNULL`, binary Go của Antigravity CLI có thể mất hơn 30s-45s qua proxy 4G. Kiểm tra `cli.log`:
    ```text
    W1018 17:19:52 cache.go:135] Cache(loadCodeAssistResponse): Singleflight refresh failed: error getting token source: You are not logged into Antigravity.
    ```
    (Lưu ý: Dòng "not logged into" ở đầu log là probe ban đầu, sau đó nó tự đọc `oauth_creds.json` và log `Starting experiment refresh after login` -> nếu proxy thông thì vẫn gọi được `streamGenerateContent`).
- **Biện pháp xử lý & Phòng chống:**
  1. **Failover trên Timeout:** Bắt buộc bắt ngoại lệ `subprocess.TimeoutExpired` trong `ag_cli.py` để đánh dấu cooldown tạm thời (ví dụ 300s) cho profile vừa bị timeout, tránh tình trạng LRU starvation kẹt cứng vào 1 acc.
  2. Không để timeout mặc định quá dài (chỉ nên đặt 25s - 35s cho bước ask nhanh).
  3. Khi cần chẩn đoán, đọc trực tiếp `cli.log` và `telemetry.jsonl` để kiểm tra event `dispatch_success` vs `profile_dispatched`.

### Kỷ luật lựa chọn Reasoning Effort cho tác vụ Lập trình:
- **Tuyệt đối không dùng `none` hoặc `low` cho bài toán Code:** Mức suy luận thấp khiến mô hình đoán mò theo xác suất bề mặt, dễ sinh code thiếu khối giải phóng tài nguyên (`finally`), quên xử lý race-condition, hoặc xử lý sai offset nhị phân.
- **Mức `high` (`[[0]]`) là lựa chọn tối ưu:** Trên hạ tầng Google AI Pro, mức `high` không hề chậm (trung bình 15s - 27s), đặc biệt ở các bài toán cấu trúc sâu (nhị phân MP4, xử lý mạng ARP) nó nhanh hơn `medium` gấp 2 - 3 lần nhờ đi thẳng vào giải pháp không bị backtrack. Code sinh ra có đầy đủ type annotations, xử lý toán tử so sánh cho hàng đợi ưu tiên và method stream chuẩn mực.
