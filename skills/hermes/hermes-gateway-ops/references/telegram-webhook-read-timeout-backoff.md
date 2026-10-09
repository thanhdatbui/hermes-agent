# Chẩn đoán và xử lý nghẽn Telegram Webhook: Telegram Read Timeout Expired qua Cloudflare Tunnel & Heartbeat Debounce

## Triệu chứng thực tế
1. Bot Telegram im lặng suốt nhiều phút (ví dụ 4-15 phút) dù User liên tục gửi tin nhắn ở nhiều topic/chat.
2. Dashboard proxy LLM (OmniRoute, 9Router) đứng im, không phát sinh bất kỳ request LLM nào trong suốt khoảng thời gian đó.
3. Bất thình lình, bot bùng nổ nhận dồn dập hàng loạt tin nhắn cùng một giây (`Flushing text batch ... inbound message: ...`).
4. Kiểm tra lệnh terminal hoặc tiến trình nền không thấy có process nào bị treo (các lệnh vẫn xong trong 0.8s - 2s).

## Cách kiểm tra và bằng chứng hiện trường

### 1. Kiểm tra trạng thái Webhook trực tiếp từ Telegram Bot API
Chạy probe lệnh gọi thẳng Telegram endpoint `getWebhookInfo`:
```bash
python -c "
import urllib.request, json
# Token lấy từ C:/Users/Kibe/AppData/Local/hermes/.env (TELEGRAM_BOT_TOKEN)
token = 'YOUR_BOT_TOKEN'
res = json.loads(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getWebhookInfo').read())
print(res['result'])
"
```

**Bằng chứng phát hiện:**
```json
{
  "url": "https://bot.taadaa.click/telegram",
  "has_custom_certificate": false,
  "pending_update_count": 0,
  "last_error_date": 1790545993,
  "last_error_message": "Read timeout expired",
  "max_connections": 40
}
```
* `last_error_message`: `Read timeout expired` chứng minh chính máy chủ Telegram đã chủ động ngắt kết nối do không nhận được phản hồi HTTP `200 OK` kịp thời từ webhook server.
* `last_error_date`: Thời điểm xảy ra lỗi khớp chính xác với thời gian bot bắt đầu im lặng.

### 2. Nguyên nhân gốc rễ (Root Cause)
1. **Kiến trúc Webhook qua Cloudflare Tunnel**:
   - `Telegram Servers` -> `https://bot.taadaa.click/telegram` (Cloudflare) -> `cloudflared` (tunnel) -> `http://127.0.0.1:8443` (Hermes Gateway).
2. **Nghẽn Event Loop / Blocking Request**:
   - Khi Hermes Gateway đang bận xử lý đồng thời nhiều session nặng (chạy subagent, giải mã file lớn, turn context bloat), handler webhook trên port `8443` bị delay.
   - Máy chủ Telegram đặt ngưỡng timeout trả về HTTP response rất nghiêm ngặt (khoảng 10–20 giây). Nếu gateway không trả về `200 OK` kịp thời, Telegram coi như delivery thất bại.
3. **Cơ chế Telegram Backoff Exponential**:
   - Sau khi dính `Read timeout expired`, Telegram tự động tạm dừng gửi tiếp các bản tin mới trong hàng đợi (backoff 5–15 phút).
   - Mọi tin nhắn user nhắn trong lúc này bị ứ đọng lại trên máy chủ Telegram.
   - Khi hết chu kỳ backoff, Telegram thử retry lại -> toàn bộ tin nhắn tồn đọng bị dội về cùng một thời điểm.

## Quy tắc xử lý và phòng chống tái phát

1. **Phân biệt rạch ròi Chiều Inbound vs Outbound**:
   - **Chiều Outbound (Hermes -> api.telegram.org)**: Cần `TELEGRAM_PROXY=socks5://127.0.0.1:40000` (qua Cloudflare WARP local proxy) để vượt qua DPI / packet drop của nhà mạng Việt Nam. Nếu tắt proxy, gateway sẽ dính cảnh báo fallback IP và stall socket khi gửi tin.
   - **Chiều Inbound (Telegram -> Webhook 8443)**: Lỗi `Read timeout expired` thuộc về chiều này. Bật `TELEGRAM_PROXY` **không** sửa được lỗi này nếu Webhook handler trả response chậm.
   - Khi WARP daemon bị disconnect ngầm, log sẽ xuất hiện: `httpx.ProxyError: Proxy Server could not connect: Host unreachable`.
2. **Kỷ luật Gateway Webhook Handler (Nếu giữ Webhook)**:
   - Webhook server phải trả về `HTTP 200 OK` ngay lập tức (< 0.1s - 0.2s) cho Telegram ngay khi nhận payload JSON, sau đó mới đẩy message vào hàng đợi background asyncio queue để agent xử lý.
   - Tuyệt đối cấm chờ LLM, database, hoặc subprocess trước khi trả 200.
3. **Phương án Tối ưu: Chuyển sang Long Polling qua SOCKS5 WARP**:
   - Đối với hệ thống Single-instance Agent / Phone farm: Bỏ/comment `TELEGRAM_WEBHOOK_URL` trong `.env`, giữ `TELEGRAM_PROXY=socks5://127.0.0.1:40000`.
   - **Bắt buộc gọi deleteWebhook**: Trước khi chạy polling, gọi `curl -x socks5://127.0.0.1:40000 https://api.telegram.org/bot<token>/deleteWebhook?drop_pending_updates=false` để xóa webhook trên server Telegram (tránh lỗi xung đột 409).
   - **Ưu điểm**: Triệt tiêu hoàn toàn `Read timeout expired`, không có rủi ro bị Telegram phạt backoff 5-15 phút, bot chủ động pull updates qua WARP cực kỳ bền vững.
4. **CẠM BẪY CHẾT NGƯỜI: Scheme `socks5://` vs `socks5h://` trên HTTPX 0.27.2**:
   - Nhiều tài liệu/LLM (kể cả Claude Code CLI) khuyên đổi sang `socks5h://` để phân giải DNS tại proxy.
   - **CẢNH BÁO FATAL CRASH**: Hermes venv hiện cài `httpx 0.27.2`. Bản này **chưa hỗ trợ `socks5h://`** (chỉ có từ `httpx 0.28+`). Nếu cấu hình `TELEGRAM_PROXY=socks5h://...`, Telegram Gateway sẽ crash-loop với lỗi `ValueError: Unknown scheme for proxy URL URL('socks5h://...')`.
   - **BẮT BUỘC DÙNG**: `TELEGRAM_PROXY=socks5://127.0.0.1:40000`. Thư viện `socksio` đi kèm `httpx` đã tự động xử lý chuyển tiếp hostname an toàn sang WARP daemon để phân giải, không lo rò rỉ hay đầu độc DNS.
5. **KỶ LUẬT LƯU CẤU HÌNH VÀO REPO (CHỐNG LƯU VÀO MEMORY)**:
   - Theo chỉ đạo của User: CẤM lưu các quy tắc mạng, scheme proxy, timeout guard vào `memory` cá nhân.
   - Mọi quy chuẩn kỹ thuật bắt buộc phải được commit trực tiếp vào Git Repository (`D:/Taadaa/tools/GATEWAY_INVARIANTS.md`, `D:/Taadaa/PROJECT_RULES.md`).
6. **KỶ LUẬT CLOSEOUT GATE CHO TÀI LIỆU QUY CHUẨN (CONTRACT TEST REQUIREMENT)**:
   - Khi commit tài liệu Invariants/Policy vào repo, Sol Auditor (`closeout_gate.py`) sẽ thẳng tay REJECT (`0/25` Test Evidence, điểm < 50) nếu diff chỉ có text Markdown thuần túy mà không có code hay bằng chứng kiểm chứng.
   - **BẮT BUỘC**: Luôn tạo kèm một bộ Contract Test (ví dụ `tests/test_gateway_invariants.py`) để kiểm tra tự động:
     * File `.env` runtime có tuân thủ đúng config (proxy scheme, disabled webhook).
     * Hook guard (`guard_broad_grep.py`) thực thi chặn đúng ma trận timeout (missing, >60s, invalid, valid).
     * File audit log JSONL (`guard_scan_audit.jsonl`) được ghi nhận đầy đủ schema 8 trường.
7. **CẠM BẪY POLLING: Heartbeat Probe Quá Nhạy Tự Sát (Self-inflicted Polling Teardown & Event Loop Freeze)**:
   - **Hiện tượng**: Sau khi chuyển sang Polling, thỉnh thoảng bot vẫn im lặng 5–10 phút và Dashboard OmniRoute không có request nào (ví dụ mốc 05:34–05:39 sáng hoặc 11:38–11:49 trưa).
   - **Bản chất nguyên nhân kép**:
     1. *Thông số .env cũ quá khắc nghiệt*: `HERMES_TELEGRAM_HEARTBEAT_INTERVAL=15` (15s spam probe 1 lần) và `HERMES_TELEGRAM_HEARTBEAT_TIMEOUT=10.0` (chỉ cho chờ 10s). Khi gateway có nhiều active agents (9–11 agents) chạy nặng hoặc WARP micro-jitter, probe `bot.get_me()` bị nghẽn nhẹ >10s.
     2. *Code adapter.py cũ KHÔNG CÓ DEBOUNCE*: Chỉ cần probe fail **1 lần duy nhất**, bot đã lập tức ra lệnh **STOP toàn bộ tiến trình Polling** và rơi vào thang exponential reconnect backoff: 5s -> 10s -> 20s -> 40s -> 60s. Hậu quả là bot rơi vào "cơn động kinh" tự ngắt kết nối liên tục (6 lần trong 10 phút), ngừng kéo tin nhắn từ Telegram.
     3. *Thiếu `httpx.ProxyError` trong failover*: Trong `telegram_network.py`, hàm `_is_retryable_connect_error` chỉ bắt `ConnectTimeout, ConnectError` mà bỏ quên `ProxyError`. Khi WARP port 40000 chập chờn 1s, nó quăng lỗi crash poller thay vì failover sang direct fallback.
   - **Giải pháp dứt điểm 4 lớp (Đã nghiệm thu qua Claude CLI & Sol Auditor)**:
     * **Lớp 1: Cấu hình .env**:
       ```env
       HERMES_TELEGRAM_HEARTBEAT_INTERVAL=180   # 3 phút mới probe 1 lần (thay vì 15s)
       HERMES_TELEGRAM_HEARTBEAT_TIMEOUT=45.0   # Chờ tối đa 45s (thay vì 10s)
       HERMES_TELEGRAM_HTTP_READ_TIMEOUT=45.0   # Nâng trần read timeout lên 45s
       ```
     * **Lớp 2: Code `adapter.py` — Debounce 3 lần + Adaptive Fast Retry 15s**:
       ```python
       while True:
           try:
               # Adaptive cadence: lúc bình thường 180s, khi đang có lỗi probe lại sau 15s
               sleep_s = 15 if getattr(self, "_polling_heartbeat_fail_count", 0) > 0 else HEARTBEAT_INTERVAL
               await asyncio.sleep(sleep_s)
               ...
               await asyncio.wait_for(bot.get_me(), PROBE_TIMEOUT)
               self._polling_heartbeat_fail_count = 0  # Reset khi thành công
           except (asyncio.TimeoutError, OSError) as probe_err:
               self._polling_heartbeat_fail_count = getattr(self, "_polling_heartbeat_fail_count", 0) + 1
               if self._polling_heartbeat_fail_count >= 3:
                   self._polling_heartbeat_fail_count = 0
                   self._schedule_polling_recovery(probe_err, reason="heartbeat probe (3 consecutive failures)")
               else:
                   logger.warning("[%s] Telegram heartbeat probe transient failure (%d/3): %s", self.name, self._polling_heartbeat_fail_count, probe_err)
       ```
       *Lợi ích*: Khi mạng gián đoạn thật, sau 3 lần x 15s = 45s bot đã phát hiện và reconnect ngay, không bị ngâm 9-10 phút.
     * **Lớp 3: Code `telegram_network.py` — Bổ sung ProxyError vào retryable**:
       ```python
       def _is_retryable_connect_error(exc: Exception) -> bool:
           return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.ProxyError))
       ```
     * **Lớp 4: Telemetry Audit Logging**:
       Tự động ghi nhận sự kiện `POLLING_RECOVERY_SCHEDULED` vào `D:/Taadaa/runtime/audit_logs/telegram_gateway_audit.jsonl` có config qua `TELEGRAM_AUDIT_LOG_DIR` và log debug khi lỗi I/O (không swallow exception).
8. **Cạm bẫy Giao thức WARP Tunnel (MASQUE vs WireGuard)**:
   - `warp-cli` mặc định dùng MASQUE (HTTP/3 over UDP). Trên hạ tầng ISP Việt Nam (Viettel/VNPT), phiên NAT UDP thường bị router bóp hoặc timeout sau 3-5 phút, gây ra micro-drop ngắt quãng.
   - Cần cẩn trọng khi gõ `warp-cli tunnel protocol set WireGuard`: lệnh này sẽ vô tình reset mode từ `WarpProxy` (chỉ mở port 40000) về full-tunnel `Warp` (khiến port 40000 ngừng listen).
   - **Lệnh chuẩn để giữ chắc port 40000**:
     ```powershell
     warp-cli mode proxy
     warp-cli proxy port 40000
     warp-cli connect
     ```
     Sau đó verify bằng: `curl -x socks5://127.0.0.1:40000 https://api.telegram.org` (trả về HTTP 302 là thông).
9. **Kinh nghiệm pass Closeout Gate cho async loop test**:
   - Khi viết test mock cho method loop tạo background task (`loop.create_task(coroutine)`), bắt buộc phải mock coroutine target hoặc await coroutine để tránh `RuntimeWarning: coroutine was never awaited`.
   - Sử dụng fixture `tmp_path` để cô lập file audit log, không để lại rác trên filesystem CI.
10. **Hiện tượng Treo Turn do Tải Media/Ảnh từ Telegram CDN (`NetworkError` / CDN Timeout)**:
   - **Triệu chứng**: User gửi ảnh chụp màn hình qua Telegram, bot im lặng 5–7 phút mới phản hồi. Trong tin nhắn dispatch đến agent xuất hiện thông báo:
     `[The user attempted to send a photo but it could not be downloaded (NetworkError); they have been asked to retry.]`
   - **Nguyên nhân gốc rễ**: Trong `adapter.py` (`_handle_media_message`), Gateway gọi `photo.get_file()` rồi `file_obj.download_as_bytearray()`. Khi CDN file của Telegram (`api.telegram.org/file/bot...`) bị nghẽn băng thông quốc tế hoặc proxy WARP micro-stall, request tải file nhị phân bị ngâm đến kịch trần read timeout. Trong suốt thời gian tải media thất bại, Gateway chưa dispatch message event cho agent, khiến user lầm tưởng cả bot hay model LLM bị treo.
   - **Phân biệt với lỗi sập Model / OmniRoute**:
     * Kiểm tra `/api/health` trên port `:20129` và đuôi file `omniroute-stdout.log`. Nếu OmniRoute trả về HTTP 200 OK trong 0.007s và log stream model vẫn `succeeded` đều đặn trong 5–10s, thì 100% không phải lỗi model mà là do Telegram CDN download timeout.
   - **Quy tắc vận hành**: Hướng dẫn user gửi lại ảnh hoặc gửi dạng Document file; nếu mạng chập chờn kéo dài, cần tinh chỉnh timeout tải media trong `adapter.py` để fail-fast (< 20s) và báo user gửi lại thay vì ngâm event loop cả chục phút.
