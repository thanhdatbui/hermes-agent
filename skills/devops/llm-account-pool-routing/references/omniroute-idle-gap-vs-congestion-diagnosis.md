# Runbook: Chẩn đoán Stale Dashboard / Idle Gap vs Nghẽn Router OmniRoute (:20129)

## 1. Hiện tượng thường gặp
- Người dùng xem Dashboard `/dashboard/logs` trên mobile hoặc web thấy request gần nhất kết thúc cách đó vài phút (ví dụ: hiện tại 22:42 nhưng dòng trên cùng là 22:38).
- Dấu hiệu trực quan dễ gây hiểu lầm: Cột Time đứng yên, không nhảy log mới -> Người dùng nghĩ **"Router bị nghẽn / treo / dừng nhận request"**.

---

## 2. Bản chất kỹ thuật & 2 kịch bản phân biệt
Bảng Request Log của OmniRoute hoạt động theo cơ chế **Event-driven / Polling hiển thị lịch sử request thực tế**:
- Nếu **Client / Worker không gửi request nào** trong khoảng nghỉ (idle gap giữa các batch), bảng log sẽ đứng yên ở request cuối cùng của batch trước.
- Cần phân biệt rạch ròi 2 kịch bản:

| Chỉ số / Hiện trường | Kịch bản A: Idle Gap giữa các Batch (Bình thường) | Kịch bản B: Router Treo / Nghẽn Event Loop (Sự cố) |
| :--- | :--- | :--- |
| **`/api/health`** | 200 OK ngay lập tức (0ms - 5ms) | Timeout (>15s), ECONNREFUSED, hoặc 500/503 |
| **In-flight / Active Requests** | 0 req (hoặc chỉ 1 vài req nội bộ) | Hàng chục req `status: 0, active: true` kéo dài >30s-60s |
| **Traffic trong DB (`call_logs`)** | Trong khoảng N phút nghi vấn, `count(*) = 0` (Client không bắn vào) | `count(*) > 0` nhưng toàn bộ dính `429 Semaphore timeout 30s` hoặc `499 Client disconnected` |
| **Watchdog Log** | Không có failure counter hoặc restart | Liên tục ghi nhận `health check failed (N/8)` hoặc restart tiến trình |

---

## 3. Quy trình chẩn đoán O(1) chuẩn xác

### Bước 1: Kiểm tra nhanh Liveness của Router
```bash
curl -s -w "\nHTTP: %{http_code} | Time: %{time_total}s\n" http://127.0.0.1:20129/api/health
```

### Bước 2: Kiểm tra Active In-Flight Requests
Gọi API call-logs lọc active entries:
```bash
curl -s "http://127.0.0.1:20129/api/usage/call-logs?limit=10" | python -c "
import sys, json
logs = json.load(sys.stdin)
active = [l for l in logs if l.get('active')]
print(f'Active in-flight: {len(active)}')
for a in active:
    print(' -', a.get('account'), a.get('model'), f\"{a.get('duration')}ms\")
"
```

### Bước 3: Đối soát Traffic theo từng phút trong SQLite `storage.sqlite`
Truy vấn trực tiếp `call_logs` (dùng URI `mode=ro` an toàn):
```python
import sqlite3, datetime

conn = sqlite3.connect('file:/C:/Users/Kibe/.omniroute/storage.sqlite?mode=ro', uri=True)
cur = conn.cursor()
# Lọc 30-60 phút gần nhất
cur.execute('''
    SELECT strftime('%Y-%m-%d %H:%M', timestamp) as minute_utc, count(*), 
           sum(case when status = 200 then 1 else 0 end) as ok_count,
           sum(case when status >= 400 then 1 else 0 end) as err_count,
           avg(duration) as avg_dur
    FROM call_logs
    WHERE timestamp >= datetime('now', '-60 minutes')
    GROUP BY minute_utc
    ORDER BY minute_utc ASC
''')
rows = cur.fetchall()
print('Phút (Local) | Total | 200 OK | Lỗi | Latency TB')
for r in rows:
    dt = datetime.datetime.strptime(r[0], '%Y-%m-%d %H:%M') + datetime.timedelta(hours=7)
    print(f"{dt.strftime('%H:%M')} | Total: {r[1]:2d} | OK: {r[2]:2d} | Err: {r[3]:2d} | Latency: {int(r[4] or 0)}ms")
```

---

## 4. Kết luận & Báo cáo với User
- Nếu `count = 0` trong khoảng thời gian user thắc mắc: Khẳng định rõ ràng **"Khoảng nghỉ tự nhiên (idle gap) của worker/client giữa các batch"**, không phải lỗi hệ thống hay nghẽn server.
- Nêu rõ mốc thời gian batch trước kết thúc và mốc thời gian batch tiếp theo bắt đầu để user an tâm.
