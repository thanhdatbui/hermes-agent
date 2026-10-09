# Telegram Webhook qua Cloudflare Tunnel & Chẩn đoán treo bot 6–10 phút

Tài liệu đúc rút thực chiến giải quyết bài toán Telegram Bot kết nối Hermes Gateway trên môi trường mạng Việt Nam (FPT/Viettel/VNPT) và phân biệt giữa nghẽn mạng vs nghẽn LLM proxy / Event loop.

---

## 1. So sánh cơ chế kết nối Telegram Bot: Polling vs WARP vs Webhook

| Đặc điểm | Long-Polling Direct (Mặc định) | Polling qua WARP SOCKS5 (`127.0.0.1:40000`) | Webhook qua Cloudflare Tunnel (`bot.domain` -> `127.0.0.1:8443`) |
|---|---|---|---|
| **Mô hình** | Client Pull (`getUpdates` socket dài) | Client Pull qua proxy SOCKS5 | Server Push (Telegram bắn HTTP POST về máy) |
| **Hiện tượng treo 5–10 phút** | **Rất nặng.** Nhà mạng VN (đặc biệt FPT) âm thầm ngắt ngắt kết nối TCP nhàn rỗi (Silent TCP Drop mà không gửi TCP RST). Socket rơi vào trạng thái Half-open, bot tưởng kết nối còn sống, đứng im chờ timeout 5–10 phút. | **Giảm nhẹ nhưng vẫn bị.** Mặc dù đổi IP sang Cloudflare, nhưng long-polling vẫn giữ socket dài; jitter hoặc rớt gói UDP của WARP tunnel làm socket stall. | **Triệt tiêu 100%.** Không duy trì socket chờ dài. Telegram server gửi tin trực tiếp tới Cloudflare Edge Singapore (<5ms), chuyển tiếp qua 4 hầm multiplexed HTTP/2 của `cloudflared` về máy local. |
| **Gửi / Nhận Media & Ảnh** | Nhanh (~0.7s/ảnh) | **Rất hay lỗi (`NetworkError`, `ReadTimeout`).** WARP dùng giao thức MASQUE (HTTP/3 trên nền UDP). Nhà mạng bóp gói UDP dung lượng lớn làm nghẽn socket SOCKS5 khi upload/download ảnh. | **Siêu tốc (~0.7s/ảnh).** Nhận tin qua Webhook, còn upload/download media đi thẳng mạng Direct FPT với băng thông tối đa, không chui qua proxy UDP. |

---

## 2. Kiến trúc thiết lập Webhook chuẩn qua Cloudflare Tunnel

### A. Khởi tạo Cloudflare Tunnel
1. Dùng `cloudflared login` ủy quyền domain (ví dụ `taadaa.click`). File cert lưu tại `~/.cloudflared/cert.pem`.
2. Tạo tunnel: `cloudflared tunnel create hermes-bot`.
3. Định tuyến hostname: `cloudflared tunnel route dns hermes-bot bot.taadaa.click`.
4. Cấu hình `~/.cloudflared/config.yml`:
   ```yaml
   tunnel: <TUNNEL_UUID>
   credentials-file: C:\Users\<user>\.cloudflared\<TUNNEL_UUID>.json
   ingress:
     - hostname: bot.taadaa.click
       service: http://127.0.0.1:8443
     - service: http_status:404
   ```
5. Chạy ngầm Windows: Tạo VBScript / Scheduled Task chạy script powershell khởi động `cloudflared tunnel run hermes-bot` khi khởi động máy.

### B. Cấu hình biến môi trường Hermes Gateway (`.env`)
Thêm vào file `.env`:
```bash
TELEGRAM_WEBHOOK=https://bot.taadaa.click/telegram
TELEGRAM_WEBHOOK_PORT=8443
TELEGRAM_WEBHOOK_SECRET=<RANDOM_HEX_64_CHARS>
# Tắt bỏ hoàn toàn TELEGRAM_PROXY để media đi trực tiếp:
# TELEGRAM_PROXY=
```

---

## 3. Bẫy tử huyệt: "Read timeout expired" & Chuỗi phạt Exponential Backoff

### Triệu chứng:
Bot dùng Webhook nhưng thỉnh thoảng user nhắn tin thì bot "im bặt 5–6 phút", sau 6 phút mới đột ngột nhận và trả lời. Trên dashboard LLM proxy (OmniRoute) không hề ghi nhận request nào trong suốt 6 phút đó.

### Nguyên nhân gốc rễ: 
1. **Synchronous Disk I/O trong Event Loop:**
Trong mã nguồn Telegram Adapter (ví dụ `telegram/adapter.py`), khi user gửi ảnh/video/audio:
```python
# Tải dữ liệu async: OK
file_obj = await photo.get_file()
image_bytes = await file_obj.download_as_bytearray()

# BẪY TỬ HUYỆT: Ghi file đồng bộ thẳng trên main thread của asyncio event loop!
cached_path = cache_image_from_bytes(bytes(image_bytes), ext=ext)
```
- Khi máy tính đang bận I/O (chạy batch, quét file, database bận), lệnh ghi file đồng bộ này chặn cứng (`block`) asyncio event loop từ **3 đến 10 giây**.
- Máy chủ web nội bộ (`aiohttp`) không thể xử lý tiếp các HTTP request mới đến cổng 8443.

2. **Outbound Media Download bị ISP bóp (Tử huyệt tắt `TELEGRAM_PROXY`):**
- Khi cấu hình Webhook, Inbound chỉ nhận JSON metadata chứa `file_id`. Để lấy ảnh về máy, Gateway phải gửi **Outbound HTTP GET** tới `https://api.telegram.org/file/bot...`.
- Nếu tắt `TELEGRAM_PROXY` để media đi "Direct FPT", luồng tải ảnh Outbound này lập tức bị nhà mạng FPT bóp socket/drop ngầm (`Primary api.telegram.org path unreachable; fallback IP 149.154.166.110 failed`).
- Luồng tải ảnh bị kẹt socket chờ timeout, giữ chân worker và làm nghẽn tiến trình xử lý request.

3. **Phình file SQLite WAL (`state.db-wal` 4GB) gây Disk I/O Lock:**
- `state.db` của Hermes (11GB+) khi tích tụ file WAL quá lớn (~4GB) sẽ khiến các thao tác ghi bản ghi tin nhắn mới bị nghẽn đĩa (`sqlite3.OperationalError: disk I/O error` hoặc query timeout > 180s).
- Việc ghi synchronous SQLite trong luồng xử lý Webhook làm đóng băng toàn bộ Event Loop của Gateway.

### Hậu quả chuỗi phạt Telegram:
Khi Telegram bắn request tiếp theo tới Webhook mà không nhận được `HTTP 200` trong vòng 5-10 giây do Event Loop bị đóng băng $\rightarrow$ Telegram ghi nhận lỗi:
`"last_error_message": "Read timeout expired"` (kiểm tra qua API `getWebhookInfo`).
- **Cơ chế phạt của Telegram:** Telegram tự động áp dụng **Exponential Backoff**:
  `1s -> 2s -> 5s -> 10s -> 30s -> 60s -> 300s (5 phút) -> 600s (10 phút)`!
- **Hiện tượng "All session dừng gửi request 1 lúc":** 
  - Toàn bộ các session/thread của Hermes Gateway đều bị "đói" tin nhắn vì Telegram ngừng đẩy tin về.
  - Trên Dashboard OmniRoute, toàn bộ traffic LLM đột ngột rơi về 0 suốt 9-10 phút.
  - Khi hết hạn phạt backoff, Telegram xả ồ ạt hàng chục tin nhắn dồn ứ cùng 1 giây $\rightarrow$ Tất cả các session thức dậy và đồng loạt bắn request LLM lên OmniRoute cùng lúc.

### Giải pháp dứt điểm:
1. **Offload I/O media:** Wrap toàn bộ các thao tác ghi đĩa media và convert bytes sang `ThreadPoolExecutor` (`loop.run_in_executor(None, ...)`).
2. **Bảo vệ luồng Outbound Media:** Luồng tải ảnh Outbound không được để drop ngầm; cấu hình DoH hoặc proxy chuyên dụng cho Telegram API endpoints.
3. **Bảo trì `state.db` định kỳ:** Chạy `PRAGMA wal_checkpoint(TRUNCATE)` và VACUUM để không cho file WAL phình quá 100MB, ngăn chặn triệt để Disk I/O block.

---

## 4. Chẩn đoán phân biệt: Nghẽn mạng Telegram vs Nghẽn hàng đợi LLM vs Nghẽn Tool Loop

Khi user phản ánh "Bot bị treo 6–10 phút", điều phối viên BẮT BUỘC kiểm tra đối soát timestamp tại `state.db` trước khi kết luận:

### Bước 1: Tra cứu thời điểm nhận tin tại `state.db`
```sql
SELECT id, session_id, role, timestamp, content 
FROM messages 
WHERE role = 'user' 
ORDER BY id DESC LIMIT 5;
```
- **Kịch bản A (Nghẽn mạng / Webhook Timeout):**
  User gửi lúc 10:00, nhưng bản ghi trong DB có timestamp là 10:06.
  $\rightarrow$ Tin nhắn bị kẹt ở Telegram hoặc Webhook bị phạt backoff do lỗi timeout. Kiểm tra `getWebhookInfo` xem `last_error_message` và `pending_update_count`.
- **Kịch bản B (Treo do LLM Queue hoặc Tool Loop):**
  User gửi lúc 10:00, bản ghi trong DB ghi nhận đúng 10:00 (độ trễ < 0.1s), nhưng bản ghi `assistant` đầu tiên có timestamp là 10:06 hoặc 10:18.
  $\rightarrow$ **Mạng Telegram KHÔNG hề treo!** Nguyên nhân nằm ở:
  1. *Hàng đợi LLM Proxy (OmniRoute):* Khi có 15-20 session chạy song song, `OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT` bị chạm trần, mỗi API call phải xếp hàng 20-30s.
  2. *Chuỗi Tool Call kéo dài (Perceived Freeze):* Coordinator chạy một chuỗi 10-15 tool calls liên tục. Mỗi tool call mất 25s suy nghĩ $\rightarrow 15 \times 25s = 375s$ (~6.2 phút). Trong suốt 6 phút đó bot không emit streaming ra Telegram, người dùng nhìn vào màn hình thấy im bặt tưởng bot treo.

### Quy tắc ứng xử của Coordinator trên kênh Chat:
- Tuyệt đối không tự ý chạy chuỗi dài 10+ tool calls ngầm mà không có feedback.
- Nếu tác vụ tốn thời gian (> 10s), gửi ngay tin phản hồi sơ bộ để người dùng biết bot đang xử lý, tránh gây hiểu lầm là bot bị treo mạng.
