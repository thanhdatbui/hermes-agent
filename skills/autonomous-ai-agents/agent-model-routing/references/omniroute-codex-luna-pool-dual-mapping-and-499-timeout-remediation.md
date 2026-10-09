# OmniRoute Codex Luna Pool Dual-Mapping & 499 Timeout Remediation (2026-09-29)

## 1. Bản chất sự cố
Trong quá trình vận hành điều phối giữa Hermes Coordinator và Worker Subagents qua OmniRoute proxy (:20129), hai vấn đề nghiêm trọng xuất hiện:
1. **Lỗi 499 Client Closed Request hàng loạt ở mốc 45s**: Log OmniRoute xuất hiện dày đặc các request thất bại với status `499` sau đúng `45.021ms`, `46.346ms`, `47.022ms`.
2. **Model Downgrade âm thầm từ High xuống Medium**: Mặc dù Hermes cấu hình `delegation.model: cx/gpt-5.6-luna-high`, nhưng request thực tế upstream lại bị hạ xuống `codex/gpt-5.6-luna-medium`.

## 2. Nguyên nhân kỹ thuật gốc rễ (Root Cause)
Khi kiểm tra bảng `combos` trong database SQLite của OmniRoute (`~/.omniroute/storage.sqlite`):
1. **Tồn tại 2 combo song song không đồng bộ**:
   - `codex-luna-pool` (tạo 15:22 ngày 22/09): Cấu hình `targetTimeoutMs: 45000` (45 giây).
   - `codex-luna` (tạo 17:07 ngày 22/09): Cấu hình `targetTimeoutMs: 90000` (90 giây).
2. **Lỗi tham chiếu lồng (Nested Combo Reference Trap)**:
   - Combo tổng cấp hệ thống `omni-worker` ở Tier 3 lại trỏ cứng vào `codex-luna-pool` (bản cũ 45s), thay vì `codex-luna` (bản mới 90s).
   - Khi GPT-5.6 Luna High thực hiện reasoning (sinh 1.000–3.000 thinking tokens ngầm), thời gian xử lý thường vượt qua 45s. Ngay khi chạm mốc 45.000ms, OmniRoute chủ động ngắt kết nối upstream và đóng kết nối HTTP với status `499`.
3. **Gán cứng chuỗi model version cũ**:
   - Toàn bộ 20 connection accounts của Codex CLI bên trong cả hai combo đều khai báo `model: "codex/gpt-5.6-luna-medium"` từ thời điểm thiết lập ban đầu (trước giải đấu Tournament 15 trận chốt Luna High vô địch 462đ).

## 3. Quy trình khắc phục chuẩn (Remediation Recipe)
Cập nhật trực tiếp vào database `storage.sqlite` của OmniRoute:

```python
import sqlite3, json

db_path = "C:/Users/Kibe/.omniroute/storage.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

combos_to_update = ["codex-luna-pool", "codex-luna"]

for cname in combos_to_update:
    c.execute("SELECT id, data FROM combos WHERE name=?", (cname,))
    cid, data_str = c.fetchone()
    data = json.loads(data_str)
    
    # 1. Nâng targetTimeoutMs lên >= 90.000 ms
    data["config"]["targetTimeoutMs"] = 90000
    
    # 2. Đồng bộ toàn bộ connection accounts sang bản High
    for m in data.get("models", []):
        if "medium" in m.get("model", ""):
            m["model"] = "codex/gpt-5.6-luna-high"
            
    c.execute("UPDATE combos SET data=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?", 
              (json.dumps(data), cid))

conn.commit()
conn.close()
```

## 4. Xác minh thực nghiệm (On-the-wire Proof)
Bắn test request vào endpoint `http://localhost:20129/v1/chat/completions` với `model: "codex-luna-pool"`:
- Status: `200 OK`.
- Thời gian: 4.93s.
- Log record tại `call_logs`: `requested_model: codex/gpt-5.6-luna-high`, `actual_model: gpt-5.6-luna-high`, `provider: codex`.
