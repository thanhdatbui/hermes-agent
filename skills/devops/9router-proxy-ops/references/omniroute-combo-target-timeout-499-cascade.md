# OmniRoute Incident Runbook: Combo Target Timeout (targetTimeoutMs) & False HTTP 499 Cascade

## 1. Hiện tượng & Triệu chứng
- Trên Dashboard OmniRoute (`:20129/dashboard/logs`), xuất hiện hàng loạt request báo lỗi **`499 Request aborted`** hoặc **`[499] Client disconnected`**.
- Các request con đều có icon mũi tên rẽ nhánh (`↳`), tạo thành chuỗi retry/failover từ 5–10 accounts liên tiếp (`failed · 5 at...` hoặc `failed · 10 at...`), cuối cùng sụp đổ thành **`HTTP 503 ALL_TARGETS_SKIPPED`**.
- Tài khoản upstream (Antigravity Google Pro, Claude, Codex...) kiểm tra quota vẫn còn 100%, không hề dính `429 RESOURCE_EXHAUSTED`.

## 2. Cơ chế gây lỗi trong Code OmniRoute

### A. Timer nội bộ trong `targetTimeoutRunner.ts`
Trong `open-sse/services/combo/targetTimeoutRunner.ts`:
- Mỗi target trong combo được bọc bởi `effectiveTimeoutMs` (lấy từ `config.targetTimeoutMs` của combo).
- Nếu request vượt quá `effectiveTimeoutMs`, timer nội bộ sẽ nổ:
  ```typescript
  timeoutController.abort(new Error(COMBO_PER_MODEL_TIMEOUT_REASON));
  ```

### B. Phân loại nhầm thành 499 trong `chatCore.ts`
Trong `open-sse/handlers/chatCore.ts`:
- Khi fetch upstream bị `timeoutController.abort()`, nó ném ra `AbortError`.
- Hàm `isLocalStreamLifecycleError(error)` đánh giá `errName === "AbortError"` là `true`.
- `chatCore` coi đây là client tự hủy kết nối (`isRequestAborted = true`) và ghi vào DB `call_logs`:
  ```typescript
  status: 499,
  error_summary: "Request aborted"
  ```
- **Hệ quả tương quan:** Hầu như toàn bộ request 499 do nguyên nhân này đều có `duration` tập trung chính xác quanh mốc `targetTimeoutMs` (ví dụ: `29.700ms - 31.000ms` khi timeout là 30s).

### C. Hiệu ứng Domino Failover
- Khi target 1 bị abort ở mốc 30s, Combo router (`combo.ts` hoặc `runtimeUnits.ts`) coi target đó thất bại và chuyển tiếp sang target 2 trong pool.
- Target 2 nhận cùng payload nặng (ví dụ: ảnh Vision base64 >70k chars, prompt ngữ cảnh lớn cần 35-50s) lại chạy tới đúng giây thứ 30 và bị chém thành 499.
- Vòng lặp kéo dài qua 8–10 tài khoản, tiêu tốn 4–5 phút và cuối cùng kích hoạt `COMBO_LOOP_SAFETY_TIMEOUT_MS` hoặc cạn attempt budget -> trả về **503 Service Temporarily Unavailable**.

## 3. Quy trình Chẩn đoán O(1)
Chạy truy vấn SQLite phân tích thời lượng của các lỗi 499:
```python
import sqlite3

conn = sqlite3.connect(r'C:/Users/Kibe/.omniroute/storage.sqlite')
cur = conn.cursor()
cur.execute('''
    SELECT count(*), avg(duration), min(duration), max(duration)
    FROM call_logs
    WHERE status = 499 AND timestamp >= datetime('now', '-2 hours')
''')
print('499 stats in last 2h:', cur.fetchone())

# Kiểm tra phân bố quanh mốc 30s
cur.execute('''
    SELECT count(*) FROM call_logs
    WHERE status = 499 AND duration BETWEEN 29000 AND 32000
''')
print('499 clustered at ~30s:', cur.fetchone()[0])
conn.close()
```
Nếu đại đa số lỗi 499 có duration ~30.000ms -> 100% là do `targetTimeoutMs` bị bóp quá ngắn.

## 4. Khắc phục Live qua Management REST API (Zero Downtime)
Tuyệt đối không cần restart tiến trình OmniRoute. Cập nhật `targetTimeoutMs` lên **`60000` (60 giây)** qua REST API:

```python
import json, urllib.request

def fix_combo_timeout(combo_id, new_timeout_ms=60000):
    url = f'http://127.0.0.1:20129/api/combos/{combo_id}'
    with urllib.request.urlopen(url) as resp:
        current = json.loads(resp.read().decode())
    
    config = current.get('config', {})
    config['targetTimeoutMs'] = new_timeout_ms
    
    payload = {
        'name': current['name'],
        'description': current.get('description'),
        'strategy': current.get('strategy'),
        'models': current.get('models'),
        'config': config,
        'isActive': current.get('isActive', True)
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"Updated {res['name']}: targetTimeoutMs = {res['config']['targetTimeoutMs']}")

# Cập nhật cả combo con (ag-gemini-pool-3) và combo cha (omni-worker)
fix_combo_timeout('22975610-b162-41b9-b6b3-30be076265bd', 60000) # ag-gemini-pool-3
fix_combo_timeout('c8122fc4-66d8-418d-a765-2a00251b4eb5', 60000) # omni-worker
```

### Tại sao không cần restart OmniRoute?
Hàm `updateCombo` trong `src/lib/db/combos.ts` gọi `invalidateDbCache("combos")` ngay khi ghi DB thành công. Cache RAM được giải phóng và request tiếp theo sẽ tự động nạp cấu hình 60s mới ngay lập tức.
