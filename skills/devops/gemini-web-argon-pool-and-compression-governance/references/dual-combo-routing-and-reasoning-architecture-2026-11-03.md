# Dual-Combo Routing & Reasoning Architecture: `gemini-web` vs `gemini-web-argon-pool` (2026-11-03)

## 1. Hiện Tượng Hai Combo Song Song Trên OmniRoute (`:20129`)
Trên OmniRoute tồn tại 2 combo cùng trỏ vào backend Google Gemini Web (Argon Pro):
- **`gemini-web`**: Ban đầu khởi tạo phục vụ Compression Engine và role Planner (`gate_b_planner.py`), cấu hình sẵn 20 accounts Google AI Pro.
- **`gemini-web-argon-pool`**: Phục vụ Tier 1 Worker thi công (`gemini_web_worker.py`) và Hội đồng Cố vấn (`consult_advisor.py`). Trước ngày 03/11/2026 chỉ có 15 accounts do sót bước đồng bộ khi scale-up đợt 20 acc.

## 2. Kiểm Chứng Hiện Trường Về "Reasoning" & "Role Plan"
1. **Không có thinking / reasoning parameter truyền vào:**
   - Cả `gate_b_planner.py` (Role Plan) và `gemini_web_worker.py` (Worker), `consult_advisor.py` (Advisor) đều gửi payload thuần OpenAI format (`model`, `messages`, `temperature: 0.1` hoặc `stream: True`).
   - Hoàn toàn KHÔNG truyền bất kỳ trường `thinking`, `reasoning_effort` hay thinking budget nào sang OmniRoute.
2. **Bản chất TO (Output Tokens) trên Dashboard:**
   - Web interface của Gemini (Argon) không tách riêng luồng `reasoning_content` như các API Thinking thương mại (DeepSeek/o1).
   - TO hiển thị trên Dashboard là toàn bộ phần text trả lời hoặc patch diff sinh ra.
   - Các lượt TO = 0 là các lượt tóm tắt nén context một chiều hoặc các lượt request dính timeout proxy 4G.

## 3. Quy Trình Đồng Bộ CSDL OmniRoute (`storage.sqlite`)
Khi mở rộng tài khoản cho Pool Gemini Web, BẮT BUỘC cập nhật đồng thời cả 2 Combo trong bảng `combos`:
```python
import sqlite3, json

conn = sqlite3.connect(r'C:/Users/Kibe/.omniroute/storage.sqlite')
c = conn.cursor()

# Lấy models từ combo chuẩn 20 acc
row = c.execute("SELECT data FROM combos WHERE name='gemini-web'").fetchone()
data_20 = json.loads(row[0])
models = data_20.get('models', [])

# Đồng bộ sang gemini-web-argon-pool
row_dst = c.execute("SELECT data FROM combos WHERE name='gemini-web-argon-pool'").fetchone()
data_dst = json.loads(row_dst[0])
data_dst['models'] = models
data_dst['description'] = 'Gemini Web 4 Argon Pool (20 Google AI Pro Accounts)'

c.execute("UPDATE combos SET data = ?, updated_at = datetime('now') WHERE name = 'gemini-web-argon-pool'", (json.dumps(data_dst),))
conn.commit()
conn.close()
```
Đảm bảo cả 2 combo luôn cùng số lượng models (20 acc) và cùng strategy (`cache-optimized`).
