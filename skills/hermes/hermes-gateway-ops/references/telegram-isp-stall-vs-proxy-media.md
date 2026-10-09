# Telegram Gateway: ISP Silent TCP Stall vs. Proxy Media Bottleneck

## 1. Hiện tượng & Vòng luẩn quẩn (The Seesaw Dilemma)

Khi vận hành Hermes Telegram Gateway trên các đường truyền mạng gia đình/doanh nghiệp tại Việt Nam (đặc biệt là mạng FPT, Viettel), thường xuất hiện vòng luẩn quẩn:

| Trạng thái | Cơ chế kết nối | Triệu chứng thực tế |
|---|---|---|
| **BẬT Proxy / WARP SOCKS5 (`127.0.0.1:40000`)** | Toàn bộ traffic Telegram (cả tin nhắn polling lẫn media) chui qua cổng SOCKS5 | Bot nhận tin nhắn tương đối ổn định, ít bị treo, **NHƯNG gửi/nhận ảnh rất hay lỗi** (`NetworkError`, `httpcore.ProxyError: Host unreachable`, `ReadTimeout`). |
| **TẮT Proxy (Direct FPT)** | Toàn bộ traffic đi trực tiếp qua card mạng host tới dải IP `api.telegram.org` | **Gửi/nhận ảnh siêu mượt (< 1s)**, **NHƯNG bot cứ lâu lâu lại bị treo cứng 5-10 phút** liên tục trong ngày mà không rõ lý do. |

### 🚨 Cảnh báo sai lầm kinh điển (Anti-Pattern):
Một agent ở session trước thấy bot lỗi tải ảnh -> lập tức khuyên người dùng: *"Tắt `TELEGRAM_PROXY` đi để gửi ảnh được"*.
Hành động này là **"chữa cháy một đầu nhưng làm bùng cháy đầu kia"**: giải quyết được việc tải ảnh tức thời nhưng lại ném bot trở về đúng cái bẫy drop socket ngầm của nhà mạng, khiến bot bị câm nín 5-10 phút định kỳ.

---

## 2. Bản chất kỹ thuật cốt lõi (Root Cause)

### A. Tại sao TẮT Proxy lại bị treo đúng 5-10 phút? (Silent TCP Stall)
1. **Cơ chế Long-Polling (`getUpdates`):** Bot Telegram mở một kết nối HTTPS/TCP kéo dài tới máy chủ Telegram API (đặt tại Singapore DC5, dải IP `149.154.160.0/20`) để chờ tin nhắn mới.
2. **Silent Drop từ ISP:** Tường lửa/hệ thống quản lý lưu lượng (DPI) của ISP (FPT) định kỳ bóp hoặc âm thầm ngắt các luồng TCP quốc tế mở lâu mà **không gửi gói `TCP RST` hay `TCP FIN`** để báo đóng kết nối.
3. **Half-Open Socket:** Phía client Python của Hermes vẫn nghĩ socket còn sống nên tiếp tục chờ trong vô vọng.
4. **Socket Read Timeout (300s - 600s):** Phải sau đúng 5 đến 10 phút chạm trần timeout của tầng socket TCP OS, client mới phát hiện kết nối đã chết, ngắt kết nối cũ và reconnect lại. Khi reconnect thành công, toàn bộ tin nhắn người dùng gửi trong 10 phút đó sẽ bị bung dồn về máy cùng một giây (*burst arrival*).

### B. Tại sao BẬT WARP SOCKS5 lại bị lỗi gửi/nhận ảnh?
1. **Giao thức MASQUE (HTTP/3 over UDP):** Cloudflare WARP phiên bản mới mặc định sử dụng giao thức MASQUE chạy trên nền HTTP/3 UDP. Các nhà mạng VN bóp lưu lượng UDP quốc tế dung lượng lớn rất gắt gao. Khi truyền gói media nhị phân nặng (ảnh JPEG/PNG, video, file APK) qua tunnel UDP, tỷ lệ mất gói tăng vọt khiến kết nối SOCKS5 bị reset hoặc đứt nửa chừng (`httpcore.ProxyError: Proxy Server could not connect: Host unreachable`).
2. **Kiến trúc HTTPXRequest trong `adapter.py`:**
   - Trong `plugins/platforms/telegram/adapter.py`, có 2 đối tượng HTTP client:
     - `get_updates_request`: Luồng chạy vòng lặp long-polling `getUpdates`.
     - `request`: Luồng thực hiện các API call thông thường (`sendMessage`, `sendPhoto`, và `get_file() -> download_as_bytearray()`).
   - Khi cấu hình `TELEGRAM_PROXY` chung, cả hai luồng đều bị ép đi qua proxy. Luồng tải ảnh với các khối binary nặng làm nghẽn pool proxy hoặc văng timeout khi proxy bị chập chờn.

---

## 3. Ba giải pháp xử lý dứt điểm

### 🌟 Giải pháp 1: Tách luồng "Polling đi WARP – Media đi Direct" (Khuyến nghị cao)
Tận dụng ưu điểm lớn nhất của cả hai đường truyền:
- **Luồng Polling (`get_updates_request`):** Bắt buộc đi qua WARP SOCKS5 (`127.0.0.1:40000`) hoặc Viettel Proxy. Vì gói tin polling chỉ là vài byte text nhẹ, proxy cân 24/7 không bao giờ lo bị FPT bóp socket ngầm $\rightarrow$ **Triệt tiêu 100% việc treo bot 5-10 phút**.
- **Luồng Request/Media (`request`):** Đi thẳng Direct FPT (hoặc direct + DoH IPs). Direct FPT tải file ảnh/video từ Telegram cực nhanh (chỉ mất ~0.7s) và không bao giờ bị nghẽn cổng proxy nội bộ.

*Cách triển khai trong `adapter.py`:*
```python
# get_updates_request dùng proxy WARP/Viettel để chống drop socket:
get_updates_request = HTTPXRequest(**request_kwargs, proxy=proxy_url, httpx_kwargs=_with_limits())

# request gửi tin nhắn & tải media đi Direct FPT để đạt tốc độ tối đa:
request = HTTPXRequest(**request_kwargs, httpx_kwargs=_with_limits())
```

---

### 🌟 Giải pháp 2: Chuyển sang Telegram Webhook qua Cloudflare Tunnel (`cloudflared`) [Triệt để 100%]
Đây là giải pháp triệt để nhất về mặt mạng, giải quyết tận gốc lý do **tại sao ngay cả khi dùng WARP thỉnh thoảng vẫn bị treo**:

#### A. Tại sao dùng WARP "đỡ hơn nhưng thỉnh thoảng vẫn bị treo"?
- Bản chất WARP vẫn là Long-Polling: Client trên máy vẫn phải duy trì 1 socket TCP mở dài (`getUpdates`) chui qua hầm WARP.
- WARP chạy giao thức MASQUE (HTTP/3 over UDP). Tuyến cáp FPT quốc tế khi có sự cố chập chờn sẽ gây jitter / rớt gói UDP, hoặc khi WARP tự động xoay key / reconnect, socket long-poll bên trong bị khựng (TCP Stall) và rơi vào trạng thái *Half-open socket* cho đến khi timeout vài phút.

#### B. Tại sao Webhook qua Cloudflare Tunnel không bao giờ bị treo?
1. **Đảo ngược chiều nhận tin (Push thay vì Poll):** Bot không bao giờ ngâm bất kỳ kết nối TCP nào từ máy ra quốc tế. Khi có tin nhắn, máy chủ Telegram tại Singapore bắn thẳng HTTP POST qua Cloudflare Edge Singapore (< 5ms).
2. **Đường hầm đa tuyến (Multiplexed 4-path Tunnel):** `cloudflared` trên host duy trì đồng thời 4 kết nối song song tới 2 datacenter Cloudflare khác nhau (HKG, SIN). Tuyến này suy hao thì tuyến kia lập tức gánh trong mili-giây.
3. **Ảnh & File đi Direct FPT:** Bot tải hoặc gửi ảnh/file qua mạng Direct cực nhanh (~0.7s), không bao giờ bị nghẽn proxy hay lỗi `NetworkError`.

#### C. Hướng dẫn triển khai từng bước (Production-Ready)
1. **Cấu hình trên Cloudflare Dashboard (Zero Trust):**
   - Vào [one.dash.cloudflare.com](https://one.dash.cloudflare.com/) -> **Networks** -> **Tunnels** -> **Create a tunnel** (chọn *Cloudflared*).
   - Đặt tên tunnel (vd: `hermes-bot`) -> Lưu.
   - Chọn OS **Windows**, copy chuỗi Token (`eyJh...`).
   - Sang tab **Public Hostname**:
     * **Subdomain:** `bot` (hoặc tên tùy chọn, ví dụ `bot.taadaa.click`)
     * **Domain:** chọn domain quản lý trên Cloudflare (ví dụ `taadaa.click`)
     * **Path:** để trống
     * **Service:** Type chọn `HTTP`, URL điền `127.0.0.1:8443`
     * Lưu hostname.

2. **Cài đặt Windows Service cho `cloudflared` trên máy host:**
   Mở terminal / cmd với quyền Administrator:
   ```cmd
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" service install <TOKEN_CLOUDFLARE>
   ```
   Service `cloudflared` sẽ tự động khởi chạy và chạy ngầm cùng Windows (tốn ~20MB RAM, 0% CPU).

3. **Cấu hình Hermes Gateway (`%LOCALAPPDATA%\hermes\.env`):**
   ```env
   # TELEGRAM WEBHOOK CONFIG
   TELEGRAM_WEBHOOK_URL=https://bot.taadaa.click/telegram
   TELEGRAM_WEBHOOK_PORT=8443
   TELEGRAM_WEBHOOK_SECRET=<tao_chuoi_hex_ngau_nhien_32_bytes>
   ```
   *(Tạo secret bằng lệnh bash: `openssl rand -hex 32` hoặc Python: `python -c "import secrets; print(secrets.token_hex(32))"`).*

   > 🚨 **BẮT BUỘC BẢO MẬT (HARD INVARIANT):** `TELEGRAM_WEBHOOK_SECRET` là BẮT BUỘC trong mã nguồn Hermes (`adapter.py:3567-3578`). Nếu thiếu secret token, Hermes Gateway sẽ ném `RuntimeError` và từ chối khởi động nhằm ngăn chặn tấn công giả mạo webhook (GHSA-3vpc-7q5r-276h).

4. **Khởi động lại Gateway & Nghiệm thu:**
   - Khởi động lại Gateway (qua `delayed-restart.ps1` hoặc PowerShell ngoài).
   - Kiểm tra trạng thái Webhook đã đăng ký với Telegram:
     ```python
     import urllib.request, json
     # Kiểm tra getWebhookInfo
     token = "<TELEGRAM_BOT_TOKEN>"
     url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
     with urllib.request.urlopen(url) as resp:
         print(json.loads(resp.read().decode()))
     ```
   - Tiêu chí chuẩn: `url` trỏ đúng `https://bot.taadaa.click/telegram`, `has_custom_certificate: false`, `pending_update_count: 0`. Tin nhắn phản hồi lập tức < 100ms.

---

### 🌟 Giải pháp 3: Tinh chỉnh WARP Tunnel Protocol & Timeout
Nếu bắt buộc phải chạy toàn bộ qua Cloudflare WARP:
1. **Chuyển Tunnel Protocol sang WireGuard:**
   ```bash
   "C:\Program Files\Cloudflare\Cloudflare WARP\warp-cli.exe" tunnel protocol set wireguard
   ```
   WireGuard xử lý phân mảnh gói tin và tải file lớn ổn định hơn MASQUE HTTP/3 UDP trên mạng ISP VN.
2. **Nâng Timeout trong `.env`:**
   ```bash
   HERMES_TELEGRAM_HTTP_POOL_SIZE=1024
   HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30.0
   HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=15.0
   HERMES_TELEGRAM_HTTP_READ_TIMEOUT=60.0
   HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=60.0
   ```

#### 💡 Mẹo Vượt Form Thẻ Tín Dụng Cloudflare Dashboard bằng CLI Login (`cert.pem`)
Khi đăng ký Cloudflare Zero Trust trên giao diện Web, hệ thống thường bắt điền thẻ thanh toán (Credit Card / PayPal) ngay cả với gói Free $0.
**Cách vượt qua hoàn toàn:**
1. Chạy lệnh đăng nhập qua CLI:
   ```cmd
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel login
   ```
2. Mở đường link đăng nhập trả về (`https://dash.cloudflare.com/argotunnel?aud=...`) trên trình duyệt đã đăng nhập Cloudflare.
3. Chọn domain của bạn (ví dụ `taadaa.click`) và bấm **Authorize**. Chứng chỉ sẽ tự động tải về `%USERPROFILE%\.cloudflared\cert.pem` mà KHÔNG yêu cầu nhập thẻ!
4. Sau đó tạo tunnel và định tuyến bình thường:
   ```cmd
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel create hermes-bot
   "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel route dns hermes-bot bot.taadaa.click
   ```

---

## 4. Bẫy Chẩn Đoán Treo 2 Tầng (Two-Layer Freeze: Network Stall vs. OmniRoute Admission Queue)

### 🚨 Vấn đề thường gặp: "Đã bật Webhook nhưng bot vẫn bị im lặng/treo 5-10 phút?"
Khi người dùng báo bot bị "treo 6-10 phút", đa số agent vội vàng kết luận là:
- Mạng Telegram bị đứt.
- Gateway process bị crash.
- Cấu hình Webhook bị lỗi.

**NHƯNG THỰC TẾ CÓ 2 TẦNG NGHẼN HOÀN TOÀN ĐỘC LẬP:**

```
[User Telegram] ──> [Telegram Server] ──(Tầng 1: Network/Webhook)──> [Hermes Gateway]
                                                                            │
                                                                  (Tầng 2: LLM API)
                                                                            ▼
                                                                  [OmniRoute :20129]
                                                                  (Admission Queue)
```

### A. Phân định O(1) nguồn gốc gây treo
1. **Kiểm tra Tầng 1 (Mạng Telegram / Webhook):**
   - Truy vấn SQLite `state.db`:
     ```sql
     SELECT id, timestamp, content FROM messages WHERE role='user' ORDER BY id DESC LIMIT 5;
     ```
   - Đối chiếu `timestamp` nhận tin với giờ người dùng bấm gửi trên Telegram:
     - **Nếu tin nhắn đã vào `state.db` ngay lập tức:** Tầng mạng Telegram & Webhook hoạt động HOÀN HẢO. Không có hiện tượng stall hay drop socket!
     - **Nếu tin nhắn bị trễ nhiều phút:** Tầng 1 bị nghẽn (do Long-polling stall).

2. **Kiểm tra Tầng 2 (Hàng đợi OmniRoute Admission Queue):**
   - Đo độ trễ `/api/health`:
     ```bash
     curl -s http://127.0.0.1:20129/api/health -o /dev/null -w "OmniRoute health: %{http_code} in %{time_total}s\n"
     ```
     - Bình thường: ~5ms - 15ms.
     - Dấu hiệu quá tải / kẹt hàng đợi: **3s - 5s+**.
   - Kiểm tra số lượng session song song đang nã vào OmniRoute:
     ```python
     # Đếm session active trong 1 giờ gần nhất
     SELECT count(DISTINCT session_id) FROM messages WHERE timestamp > (strftime('%s', 'now') - 3600);
     ```
     Nếu có 15-35 session chạy song song (do nhiều subagent, farm background cron, hoặc session mồ côi từ ngày trước bị leak).

### B. Cơ chế nghẽn của OmniRoute (`OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`)
- OmniRoute có cơ chế bảo vệ chống sập tài nguyên bằng biến `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT` (mặc định là `9`).
- Khi các background session gửi các context cực nặng (50k, 160k, 250k tokens), 9 slot này bị chiếm trọn 100%.
- Tin nhắn mới của người dùng (từ chat Telegram) khi được Gateway gửi sang OmniRoute sẽ bị đẩy vào **Hàng đợi Admission (Admission Queue)** chờ slot rảnh.
- Thời gian chờ trong hàng đợi có thể lên tới 120s hoặc nhiều phút nếu các context nặng đang streaming.
- **Hậu quả:** Người dùng thấy bot không typing, không trả lời suốt 5-10 phút — tạo cảm giác y hệt như mạng bị treo!

### C. Quy trình khắc phục dứt điểm Tầng 2:
1. **Nâng trần Heavy In-Flight cho OmniRoute:**
   - Trong `omniroute_watchdog.ps1` (hoặc biến môi trường của OmniRoute):
     ```powershell
     $env:OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT = 24
     $env:OMNIROUTE_SKIP_DB_HEALTHCHECK = "1"
     ```
     *(Máy host 64GB RAM với 30GB+ free hoàn toàn an toàn khi chạy 24+ heavy stream song song).*
2. **Khởi động lại OmniRoute via Watchdog:**
   - Restart tiến trình node của OmniRoute để nạp biến môi trường mới.
   - Verify: `/api/health` trở lại ~5ms.
3. **Dọn dẹp các tiến trình zombie / session mồ côi:**
   - Quét các tiến trình Python chạy nền lặp vô tận từ các ngày cũ (`os.walk` quét đĩa, test loop...) đang liên tục bắn API.
   - Dùng script dọn lock và kill các worker đã cạn deadline: `reap-dead-owner-locks.py`.

### D. 🚨 Tử Huyệt: Tuyệt Đối Cấm Tự Ý Coi "Session Cũ = Session Rác" (User Active Multi-Day Workspaces)
- **User Frustration Signal:** *"vấn đề các session đó tao vẫn chưa làm xong mà???"*
- **Thực tế kiến trúc:** Người dùng phân tách và điều phối công việc qua nhiều **Telegram Forum Topics / Groups** khác nhau (Topic Farm Alert, Topic Review Code, Topic ChatGPT Web, Topic Avatar Watchdog...).
- Nhiều quy trình và task lớn kéo dài liên tục 2–3 ngày qua nhiều phiên làm việc.
- **BẤT BIẾN:** CẤM TUYỆT ĐỐI Agent tự ý coi các session khởi tạo từ 1–2 ngày trước là "session mồ côi / zombie / rác" rồi vội vàng đòi kill hoặc dọn sạch. Mọi hành động can thiệp vào session đang chạy đều phải có sự chỉ định đích danh từ User!

### E. 🚨 Tử Huyệt: Chuỗi Tool Call Tuần Tự Trong Bóng Tối (Dark Tool Loops in Coordinator Turn)
- **Cơ chế gây hiểu lầm treo bot:**
  Khi OmniRoute đang gánh nhiều session song song, latency mỗi lượt gọi LLM (`omni-worker`) tăng lên **20s – 25s/call** (thay vì 1s – 2s).
  - Nếu Coordinator ở session chat chính thực thi một chuỗi 10–15 tool calls tuần tự trong 1 turn:
    $$15 \text{ tool calls} \times 22\text{s/call} = 330\text{s} \approx 5.5 \text{ phút!}$$
  - Telegram Bot API không stream từng tool call về màn hình chat của người dùng.
  - Người dùng nhìn từ client Telegram thấy bot **im bặt suốt 5–6 phút** $\rightarrow$ Người dùng khẳng định chắc nịch là bot lại bị treo mạng!
- **Kỷ luật Coordinator tại Session Chat Trực Tiếp:**
  1. Giữ các turn chat trực tiếp O(1), tối đa 1–2 tool calls focused.
  2. Tuyệt đối không tự ý chạy các vòng lặp tool probe/quét lê thê nhiều bước liên tiếp trong session chat chính.
  3. Mọi tác vụ chẩn đoán sâu hoặc quét nhiều bước: BẮT BUỘC dispatch worker subagent qua `delegate_task` để chạy ngầm, Coordinator lập tức trả lời ngay trạng thái tiếp nhận cho User.

### F. 💡 Bẫy Cloudflare Error 1010 ("Browser Integrity Check") trên Webhook URL
- Khi kiểm tra webhook endpoint `https://bot.taadaa.click/telegram` bằng `curl` thô hoặc script Python không kèm header User-Agent: Cloudflare WAF sẽ chặn họng và trả về `HTTP 403 Forbidden` (`error code: 1010`).
- **Thực tế:** Máy chủ Telegram Bot API gửi request với User-Agent chuẩn `TelegramBot (like TwitterBot)`, Cloudflare cho phép đi qua và trả về HTTP 200 OK.
- Khi probe test webhook qua curl/Python từ terminal host, BẮT BUỘC đính kèm header:
  ```bash
  curl -s -X POST https://bot.taadaa.click/telegram -H "User-Agent: TelegramBot (like TwitterBot)" -H "Content-Type: application/json" -H "X-Telegram-Bot-Api-Secret-Token: <SECRET>" -d '{"update_id": 1}'
  ```
