# Cockpit Tools: Codex Account Proxy & Local Fallback Architecture

## 1. Kiến trúc Fallback Độc lập cho Hermes
Khi OmniRoute (`:20129`) bảo trì hoặc khởi động lại, Cockpit Tools (`cockpit-tools.exe`) có thể đóng vai trò là một túi khí dự phòng (fallback layer) hoàn toàn độc lập chạy trên máy local:
- **Endpoint Local Access**: `http://127.0.0.1:60818/v1/chat/completions` (chuẩn OpenAI Chat Completions & Responses API).
- **Authentication**: Key dạng `agt_codex_<token>` (lưu trong `COCKPIT_API_KEY`).
- **Account Management**: Quản lý nhiều tài khoản Codex (Free / Plus / Team), tự động làm mới OAuth token và xoay tua (account rotation).

---

## 2. Cơ chế Proxy & Fake Fingerprint của Cockpit Tools

### Cạm bẫy IP Mismatch & Single-Proxy Clustering Trap
- **Cạm bẫy IP Mismatch**: Khi nạp tài khoản từ GPM Profile (chạy proxy riêng, VD: Proxy 4G MobiFone `test.taadaa.click:5101`, `5102`), trình duyệt GPM hoàn tất OAuth qua callback `localhost:1455`. Tuy nhiên, Cockpit **CHỈ LƯU TOKEN MÀ KHÔNG TỰ ĐỘNG GÁN PROXY GPM VÀO TÀI KHOẢN**!
- **Hậu quả IP Mismatch**: Khi Cockpit sidecar (`cockpit-cliproxy.exe`) gọi request hoặc refresh token lên `chatgpt.com/backend-api/codex`, nếu app không có egress proxy, request sẽ đi thẳng bằng IP mạng máy host (VD: IP cáp mạng trực tiếp `1.53.55.190` thay vì IP 4G `171.224.136.172`). OpenAI phát hiện đổi IP đột ngột giữa lúc cấp token và lúc dùng -> lập tức thu hồi token:
  ```json
  HTTP 401 Unauthorized
  {"error":{"message":"Encountered invalidated oauth token for user, failing request","type":"authentication_error","code":"auth_unavailable"}}
  ```
- **Cạm bẫy Gom cụm 1 Proxy (Single-Proxy Clustering Trap)**: Tuyệt đối KHÔNG dồn toàn bộ 10 tài khoản free vào chung 1 Global Proxy (hoặc 1 upstream `proxy-url` duy nhất). Nếu toàn bộ traffic của dàn acc free dồn qua 1 IP proxy duy nhất, OpenAI backend sẽ phát hiện bất thường về concurrency/fingerprint và quét ban/revoke chùm toàn bộ dàn acc. Mỗi account bắt buộc phải đi qua đúng proxy gắn liền với profile GPM tương ứng của nó.
- **Giải pháp Routing từng Acc qua Proxy riêng**:
  * **Kiến trúc A (Hermes Provider Fallback Chain)**: Khai báo từng acc thành từng provider độc lập trong `custom_providers` / `fallback_providers`. Mỗi provider bind đúng proxy riêng. Khi acc hiện tại dính HTTP 429 (hết quota), Hermes tự động nhảy sang acc tiếp theo trong chuỗi fallback hoàn toàn tự động mà không cần đổi thủ công.
  * **Kiến trúc B (Dedicated Local Router Adapter)**: Dựng 1 lightweight bridge adapter bind cứng cặp `(Account Token, Dedicated Proxy)` cho từng acc. Router tự động xoay vòng round-robin và tự switch acc khi gặp 429, giữ nguyên 1 endpoint thống nhất cho client.
- **Sidecar Upstream Proxy (`proxy-url`)**: Sidecar `cockpit-cliproxy.exe` đọc `~/.antigravity_cockpit/codex_local_access_sidecar/config.json` và hỗ trợ trường `"proxy-url"` làm upstream proxy chung cho toàn bộ request ra ngoài.
- **Cạm bẫy `PROXY_RESOURCE_INVALID`**: Cockpit Tools KHÔNG nhận raw proxy string trực tiếp vào `egress_proxy_url`. Mọi proxy node phải được đăng ký qua Proxy Engine (Mihomo) trong `codex-proxy-sources.json` với schema hợp lệ (`sourceId`, `itemId`, `parser_version: 1`, `default_invalidated: false`). Nếu inject raw proxy sai format, Cockpit sẽ báo đỏ `PROXY_RESOURCE_INVALID` và dừng toàn bộ API Service (`Stopped`).
- **Kỷ luật kiểm chứng Proxy**: CẤM Agent kết luận "đã bật proxy" chỉ dựa trên việc GPM profile có proxy. BẮT BUỘC kiểm tra thực tế IP egress từ chính tiến trình Cockpit sidecar (`proxy-url` trong sidecar config hoặc Mihomo exit check) trước khi gửi bất kỳ request nào lên OpenAI để chống cháy dàn token.
- **Quy tắc bất di bất dịch**: MỌI tài khoản Codex nạp từ GPM BẮT BUỘC phải gán ngay Proxy tương ứng trong Cockpit trước khi bấm "Add to API Service".
- **Cấu trúc Proxy Egress trong Storage mã hóa của Cockpit**:
  * Cockpit lưu danh mục proxy tại `~/.antigravity_cockpit/codex-proxy-sources.json` (mã hóa AES-256-GCM với key tại `secure-account-storage.key`).
  * Mỗi tài khoản tại `~/.antigravity_cockpit/codex_accounts/<id>.json` mang trường `egress_proxy_url: "cockpit-proxy://<base64>"`.
  * Descriptor base64 chứa: `{"version": 2, "sourceId": "...", "sourceName": "...", "itemId": "...", "outbounds": [{"type": "http", "server": host, "server_port": port, "username": user, "password": pass}]}`.
  * Cạm bẫy `PROXY_RESOURCE_INVALID`: Nếu `sourceId`/`itemId` trong account không khớp với node trong `codex-proxy-sources.json`, hoặc thiếu các trường schema (`parser_version: 1`, `default_invalidated: false`), Cockpit sẽ báo đỏ `PROXY_RESOURCE_INVALID` và dừng toàn bộ API Service (`Stopped`).

### Hai tầng Proxy & Proxy Engine (Mihomo)
1. **Proxy Engine Mihomo (Core bắt buộc)**:
   - Cockpit Tools yêu cầu core **Mihomo 1.19.31** (21.4 MiB) cài trong `~/.antigravity_cockpit/proxy-engine/`.
   - Nếu thiếu Mihomo, Cockpit sẽ báo lỗi `PROXY_ENGINE_MISSING` và Local API trả HTTP 503 `No available account` / `candidates=0`.
   - Cài đặt: Vào tab **Proxies** -> bấm **Download & install** (hoặc import file zip).
2. **Nhập Proxy & Gán theo từng tài khoản (Per-Account Egress Proxy)**:
   - Module Rust: `src-tauri\src\modules\codex_account_proxy.rs`, dữ liệu mã hóa AES-256-GCM lưu tại `~/.antigravity_cockpit/codex-proxy-sources.json`.
   - Thêm proxy node qua nút **Add proxy** (Manual entry hoặc Paste import: `http://user:pass@host:port`).
   - Bấm **Test egress** trên node để xác nhận IP public ra ngoài (`Exit check passed`).
   - Bấm **Assign** -> chọn tài khoản tương ứng trong danh sách để gắn cố định proxy vào tài khoản đó.

---

## 3. Quy trình Chuẩn OAuth Tài khoản Codex qua GPM Profile (Chống Ban & Chống Cháy)
- **TUYỆT ĐỐI CẤM nạp token thủ công vào file JSON**: Cockpit mã hóa state bằng AES-256-GCM và sync với sidecar; nạp file lẻ ngoài giao diện sẽ khiến Cockpit không nhận diện hoặc xóa đè manifest.
- **Vòng đời Listener Port 1455 của Cockpit**:
  * Listener `localhost:1455` **CHỈ MỞ KHI MODAL "Add Account -> OAuth Authorization" ĐANG ACTIVE TRÊN COCKPIT UI**.
  * Nếu Cockpit restart, chuyển tab (sang Antigravity/Relay), hoặc đóng modal, port 1455 tắt ngay (WinError 10061 Refused).
  * Kiểm tra bắt buộc trước khi Playwright auth: `netstat -ano | findstr 1455` phải có `LISTENING`. Nếu mất, phải dùng UI click lại tab Codex -> Add Account -> OAuth Authorization.
- **Quy trình 5 bước OAuth chuẩn native**:
  1. Trong Cockpit Tools: Bấm **Add Account** -> chọn tab **OAuth Authorization**.
  2. Bấm **Refresh Auth Link** (hoặc copy link hiện tại) để sinh URL mới kèm `state` và `code_challenge` còn hạn.
  3. Mở **GPM Profile** tương ứng (profile đã gán proxy sạch của máy đó và kiểm tra còn session ChatGPT sống).
  4. Điều hướng trình duyệt GPM đến `Authorization link` -> chọn tài khoản và bấm **Tiếp tục**.
  5. Trình duyệt tự redirect về callback URL `http://localhost:1455/auth/callback?code=...&state=...`. Listener native của Cockpit trên port 1455 sẽ bắt callback, tự động đổi token và hiển thị "授权成功 / Authorization Successful". Nếu Cockpit UI không tự bắt, paste callback URL vào ô "Manual callback URL" rồi submit.
- **Gộp Tài khoản vào chung 1 Pool qua API Key**:
  * Sau khi OAuth thành công, thẻ tài khoản xuất hiện trong danh sách nhưng mặc định **CHƯA NẰM TRONG API SERVICE**.
  * BẮT BUỘC bấm nút **Add to API Service** trên thẻ tài khoản (nút chuyển thành "Remove from API", số lượng active accounts trong pool tăng lên).
  * Toàn bộ các tài khoản được thêm vào API Service sẽ tự động nằm chung dưới 1 API Key (`agt_codex_...`). Cockpit tự động xoay tua (rotate), load-balance và route từng tài khoản qua đúng proxy riêng đã gán.

---

## 4. Cạm bẫy & Yêu cầu Bắt buộc khi Dùng Dàn Tài khoản FREE

### Cạm bẫy 1: Cờ `restrictFreeAccounts` chặn Local Access API
- **Hiện tượng**: Đã nạp thành công dàn acc Free vào Cockpit, nhưng khi Hermes gọi vào `http://127.0.0.1:60818/v1` thì bị báo lỗi không có tài khoản hợp lệ trong pool hoặc danh sách `accountIds` không chứa acc Free.
- **Nguyên nhân**: Trong `~/.antigravity_cockpit/codex_local_access.json`, cờ `"restrictFreeAccounts"` mặc định được bật là `true`. Cơ chế này của Cockpit tự động lọc bỏ toàn bộ tài khoản có `plan_type: "free"` ra khỏi pool cung cấp cho cổng 60818 (chỉ ưu tiên Plus/Pro).
- **Cách xử lý**:
  - Trong giao diện Cockpit: Vào cài đặt **Codex Local Access** -> Tắt tùy chọn **"Restrict Free Accounts"**.
  - Hoặc sửa trực tiếp trong `~/.antigravity_cockpit/codex_local_access.json`:
    ```json
    "restrictFreeAccounts": false
    ```

### Cạm bẫy 2: Giới hạn Quota tuần của tài khoản Codex Free
- Acc Free trên `chatgpt.com/backend-api/codex` có hạn mức rất hạn chế và cửa sổ reset lên tới 30 ngày / 1 tuần (khi hết sẽ trả về HTTP 429 `usage_limit_reached`).
- Dàn acc Free bắt buộc phải đủ lớn (nhiều acc) và phân bổ đều qua proxy sạch để tránh cạn kiệt đồng loạt trong thời gian ngắn.

### Cạm bẫy 3: Ảo tưởng gọi Model Flagship (gpt-6-sol / gpt-5.6-sol / "sol 6.1") bằng Acc Free & Thực tế Dòng GPT-6
- **Bản chất tên model & Dòng 6.1**: Hoàn toàn **KHÔNG CÓ dòng 6.1** (như `sol 6.1` hay `gpt-6.1`). Mọi chuỗi `6.1` đều là alias tự chế trên 9Router hoặc tên gọi gộp. Gọi `sol 6.1` sẽ trả về `HTTP 404: model sol 6.1 is not available for this API key`.
- **Thực tế các model Codex trên acc Free**:
  - `gpt-6-luna`: **HỖ TRỢ TRÊN ACC FREE** (200 OK, latency cực nhanh ~8-22s, reasoning tokens động 40-270). Đây là model thế hệ 6 xịn nhất acc Free gọi được.
  - `gpt-5.6-terra`: **HỖ TRỢ TRÊN ACC FREE** (200 OK, reasoning sâu ~350 tokens, nhưng latency rất cao ~30-45s và dễ timeout/503 khi context lớn). Không có model nào tên `gpt-6-terra` (trả về 404).
  - `gpt-6-sol` / `gpt-5.6-sol` / `gpt-6-astra`: **CHẶN CỨNG TRÊN ACC FREE** (OpenAI trả về `HTTP 400: {"detail":"The 'gpt-6-sol' model is not supported when using Codex with a ChatGPT account."}`).
- **Hiện tượng đốt quota 4-5% mỗi request**: Request từ coding agent (Hermes/Codex/Claude Code) luôn kèm context/system prompt nặng (18.000 - 26.000 input tokens). Với `gpt-6-luna` / `gpt-5.6-luna`, chi phí token gần như bằng 0 (0% quota). Nhưng với dòng Sol/Astra trước khi bị hard-block, OpenAI áp dụng quota multiplier rất cao, đốt đứt 4% - 5% quota của cả tháng cho 1 câu hỏi đơn lẻ (chỉ 20-25 câu là cháy sạch quota).
- **Hậu quả Token Revocation hàng loạt**: Nếu tài khoản Free xả context nặng liên tục qua proxy, OpenAI backend sẽ thu hồi session ngay lập tức:
  ```json
  HTTP 401 Unauthorized
  {"error":{"message":"Encountered invalidated oauth token for user, failing request","code":"token_revoked"}}
  ```
- **Khác biệt 3 Gateway Local**:
  - **Cockpit (:60818)**: Native Codex pool, chạy trực tiếp `gpt-6-luna` trên acc Free.
  - **OmniRoute (:20129)**: Chưa cắm pool Codex nội bộ, route ra ngoài OpenRouter (bị 402/401 khi hết credit).
  - **9Router (:20128)**: Model `gpt-5.6-luna` chỉ là alias trỏ về Gemini Tiered. Cần add Custom OpenAI Provider trỏ vào `:60818` nếu muốn dùng `gpt-6-luna` thật.

---

## 4. Cấu hình Tích hợp vào Hermes Agent (Coordinator & Worker Fallback)

Cấu hình chuẩn xác trong `~/.hermes/config.yaml` để tự động fallback sang `gpt-6-luna` từ Cockpit khi Gemini / OmniRoute chính gặp lỗi:

```yaml
custom_providers:
  - name: cockpit
    base_url: http://127.0.0.1:60818/v1
    key_env: COCKPIT_API_KEY
    model: gpt-6-luna

fallback_providers:
  - provider: cockpit
    model: gpt-6-luna
    base_url: http://127.0.0.1:60818/v1
    key_env: COCKPIT_API_KEY
  - provider: 9router
    model: omni-worker
    base_url: http://192.168.110.123:20128/v1
    key_env: NINEROUTER_API_KEY
```

**Cơ chế kế thừa của Worker (Subagents)**:
- Subagent dispatch qua `delegate_task` tự động kế thừa `_fallback_chain` từ agent cha (theo `tools/delegate_tool.py`).
- Khi Coordinator cấu hình `fallback_providers` trỏ vào Cockpit `gpt-6-luna`, cả tầng Coordinator lẫn Worker đều được bảo vệ bởi cùng chuỗi fallback này mà không cần cấu hình lặp lại.

