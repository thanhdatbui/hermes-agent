# Chẩn đoán sự cố Cascade Failure qua Logs OmniRoute (:20129)

## 1. Bản chất sự cố Cascade (Tràn tầng liên hoàn)
Khi một combo nhiều tầng (như `omni-worker`: Tier 1 AG Gemini Flash -> Tier 2 ChatGPT Web Pool -> Tier 3 OpenCode Free -> Tier 4 AG Claude) chịu tải dồn dập (ví dụ >1.000 req/phút):
- **Tầng 1 (Antigravity Gemini Flash)**: Dễ cạn slot Semaphore (`Semaphore timeout after 30000ms for antigravity:<account_id>`) hoặc dính upstream 429.
- **Tràn sang Tầng 2 (ChatGPT Web)**: Tác vụ agentic (Hermes, Claude CLI, Codex) mang payload lớn (system prompt, tool schemas, context files). Endpoint ChatGPT Web có giới hạn payload nghiêm ngặt -> Dội lỗi **HTTP 413 (Payload Too Large)** hàng loạt, tốn 10-15s upstream per request.
- **Tràn sang Tầng 3 (OpenCode Free)**: OpenCode chặn proxy bên ngoài -> Dội ngay **HTTP 403** (`OpenCode's free tier can only be used from within OpenCode`) và **HTTP 401** (`Model not supported`).
- **Tràn sang Tầng 4 (AG Claude)**: Toàn bộ tải dồn vào các account Claude Sonnet 4.6 vốn rate limit thấp -> Sập hoàn toàn bằng **HTTP 429** / Semaphore timeout 30s.

## 2. Kỹ thuật điều tra nhanh SQLite O(1)
Không cần tải file log text khổng lồ, truy vấn trực tiếp DB SQLite của OmniRoute ở chế độ Read-Only (`mode=ro`):
- Đường dẫn DB runtime chuẩn: `C:\Users\Kibe\.omniroute\storage.sqlite` (URI: `file:C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro`).
- **Bảng `call_logs`**: Chứa toàn bộ request chi tiết của OmniRoute.
  - `status`: HTTP status code (200, 413, 429, 499, 403, 502).
  - `duration`: Thời gian xử lý ms.
  - `error_summary`: Nguyên nhân chi tiết (Semaphore timeout, payload limit, upstream error).
  - `combo_name`, `requested_model`, `provider`, `account`.

### Script thống kê nhanh tình trạng lỗi 5 phút gần nhất:
```python
import sqlite3
con = sqlite3.connect('file:C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cur = con.cursor()
cur.execute('''
    SELECT status, count(*) 
    FROM call_logs 
    WHERE timestamp >= datetime('now', '-5 minutes')
    GROUP BY status
''')
for r in cur.fetchall():
    print(f"Status {r[0]}: {r[1]} requests")
```

### Script truy vết top lỗi và chuỗi cascade:
```python
cur.execute('''
    SELECT combo_name, requested_model, provider, status, error_summary, count(*) 
    FROM call_logs 
    WHERE timestamp >= datetime('now', '-5 minutes') AND status != 200
    GROUP BY combo_name, requested_model, provider, status, error_summary
    ORDER BY count(*) DESC LIMIT 10
''')
for r in cur.fetchall():
    print(r)
```

## 3. Biện pháp xử lý & Phòng vệ (Hard Rules)
1. **Loại bỏ ngay các node chết/chặn proxy**: Các provider như OpenCode Free cấm gọi ngoài client -> Phải disable hoặc xóa khỏi combo cascade, không để request dạt vào gây trễ tích lũy (accumulated latency 10-20s).
2. **Bảo vệ ChatGPT Web Pool khỏi HTTP 413**:
   - ChatGPT Web Pool CHỈ phù hợp cho short prompt, review code diff nhỏ hoặc text translation.
   - Với agentic workload (system prompt dài, file context), bắt buộc bật Context Compression (Caveman / Engine Combos) hoặc không đặt ChatGPT Web làm fallback trực tiếp cho generic worker combo.
3. **Giảm áp lực Semaphore**: Khi thấy hàng loạt lỗi `Semaphore timeout after 30000ms`, nguyên nhân là do client/runner (ví dụ batch từ máy trạm LAN `.119`) gửi request đồng thời mà không có Jitter và Exponential Backoff. Cần điều chỉnh concurrency ở phía client.
