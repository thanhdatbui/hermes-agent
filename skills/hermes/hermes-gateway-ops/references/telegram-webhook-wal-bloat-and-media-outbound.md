# Telegram Webhook Backoff, SQLite WAL Bloat & Outbound Media Quirks

## 1. Triệu chứng nghẽn đồng loạt (Stall Symptoms)
- Tất cả các session / subagent dường như "dừng gửi request lên LLM router (OmniRoute/9router) cùng một lúc".
- Dashboard OmniRoute không nhận thêm request, trong khi server LLM vẫn trả lời `healthcheck: 200 OK`.
- User gửi tin nhắn qua Telegram nhưng bot không phản hồi suốt 5–15 phút, sau đó đột ngột nhận 1 cục hàng đợi tin nhắn dồn về trong cùng 1 giây.

## 2. Chuỗi nguyên nhân gốc rễ (Root Cause Chain)
1. **SQLite WAL Bloat (`state.db-wal`):**
   - SQLite mặc định chạy checkpoint PASSIVE, không tự động thu nhỏ file `-wal` nếu có nhiều connection mở đọc/ghi.
   - Khi file `state.db-wal` phình to (> 3GB), các lệnh truy vấn/ghi session của Hermes Gateway bị giật cục, dính lỗi `sqlite3.OperationalError: disk I/O error` hoặc lock kéo dài > 180s.
2. **Telegram Webhook "Read timeout expired" & Backoff Penalty:**
   - Cổng webhook (ví dụ Cloudflare Tunnel -> `http://127.0.0.1:8443/telegram`) bị nghẽn Event Loop do disk lock / download treo, không kịp trả HTTP 200 cho Telegram Server trong vòng 5 giây.
   - Telegram Server ghi nhận lỗi `Read timeout expired` hoặc `502 Bad Gateway` và kích hoạt **Exponential Backoff**: tạm ngưng đẩy tin nhắn mới sang máy chủ trong 5–10 phút trước khi retry.
3. **Outbound Media (Tải ảnh/Voice) qua mạng trực tiếp (Direct ISP):**
   - Webhook chỉ nhận metadata JSON (`file_id`).
   - Ngay sau đó Gateway phải gọi ngược ra `api.telegram.org/file/bot...` để tải binary ảnh.
   - Nếu `TELEGRAM_PROXY` bị tắt, luồng tải ảnh đi qua mạng trực tiếp (FPT/VNPT) dễ bị bóp packet, rơi vào fallback loop `Primary api.telegram.org path unreachable -> sticky fallback IP -> failed`, gây block event loop.

## 3. Quy trình chẩn đoán O(1)
```bash
# 1. Kiểm tra kích thước WAL
ls -lh ~/AppData/Local/hermes/state.db*

# 2. Kiểm tra lỗi Webhook trực tiếp từ Telegram Server
python -c "
import urllib.request, json
with open('C:/Users/Kibe/AppData/Local/hermes/.env') as f:
    token = [line.split('=', 1)[1].strip() for line in f if line.startswith('TELEGRAM_BOT_TOKEN=')][0]
r = urllib.request.urlopen(f'https://api.telegram.org/bot{token}/getWebhookInfo')
print(json.dumps(r.json(), indent=2))
"

# 3. Kiểm tra độ trễ phản hồi Webhook nội bộ
curl -i http://127.0.0.1:8443/telegram
```

## 4. Biện pháp khắc phục & Phòng ngừa
1. **Khẩn cấp (Hotfix):**
   ```python
   import sqlite3
   conn = sqlite3.connect(r'C:\Users\Kibe\AppData\Local\hermes\state.db', timeout=10.0)
   conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
   conn.close()
   ```
2. **Tự động hóa qua Watchdog (`hermes_stale_watchdog.py`):**
   - Giám sát định kỳ: nếu `state.db-wal` > 50 MB, tự động gọi `PRAGMA wal_checkpoint(TRUNCATE)` với timeout ngắn (10s).
   - Ghi telemetry có cấu trúc ra `logs/wal_maintenance.jsonl`, ghi cảnh báo ra `stderr`, tuyệt đối giữ `stdout` rỗng (0 byte) để tránh spam alert.
