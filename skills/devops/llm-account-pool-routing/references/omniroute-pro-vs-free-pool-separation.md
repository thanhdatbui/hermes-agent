# Tiered Sub-Combos: Gemini Pro Primary vs Free Fallback Separation

Tài liệu này ghi lại kiến trúc chuẩn để phân tầng ưu tiên tuyệt đối tài khoản trả phí (Google AI Pro / `g1-pro-tier`) trước tài khoản miễn phí (`free-tier` / `standard-tier`) trong hệ thống OmniRoute.

---

## 1. Vấn đề kiến trúc (The Mixed-Pool Starvation Problem)

Khi một combo (ví dụ `ag-gemini-pool-3`) gộp chung cả tài khoản Pro và tài khoản Free vào một danh sách phẳng và chạy `strategy: "round-robin"`:
- Thuật toán Round-Robin duyệt tuần tự qua từng connection (`[0] -> [1] -> ... -> [N]`).
- Do số lượng tài khoản Free thường áp đảo tài khoản Pro (ví dụ: 16 Pro vs 87 Free = 84% Free), phần lớn các request (8-9/10 request) sẽ rơi vào tài khoản Free ngay từ đầu lượt, dù dàn Pro đang còn 100% quota và rảnh rỗi.
- Khi các tài khoản Free cạn quota sau 10-15 phút dồn tải, router phải liên tục xử lý lỗi 429 và failover, làm tăng latency và nguy cơ sập luồng.

---

## 2. Kiến trúc giải pháp chuẩn (2-Tier Flat Priority trong omni-worker)

Tránh bẫy lồng 3 cấp (`omni-worker` -> `ag-gemini-pool-3` -> `ag-gemini-pro-pool`), ta thiết kế **Priority 5 tầng phẳng** trực tiếp trong `omni-worker`:

```text
omni-worker (Strategy: priority, nestedComboMode: "execute")
├── Tier 1: ag-gemini-pool-3 (Strategy: round-robin, GỒM ĐÚNG 16 ACC PRO)
│     └── Ưu tiên 100% traffic vào đây, xoay tua đều giữa các acc Pro, bảo tồn Prompt Cache
│
├── Tier 2: ag-gemini-free-pool (Strategy: round-robin, GỒM TOÀN BỘ 87 ACC FREE/STANDARD)
│     └── Lưới cứu hộ: Chỉ nhận request khi toàn bộ 16 acc Pro cạn quota tuần hoặc dính 429/bận concurrency
│
├── Tier 3: chatgpt-web-pool (Strategy: round-robin, 12-16 live accounts Web ChatGPT)
│     └── Fallback sang ChatGPT Web
│
├── Tier 4: omni-free (Strategy: round-robin)
│     └── Safety net model Free ngoài (Muse Spark, MiMo, Laguna...)
│
└── Tier 5: ag-claude (Strategy: round-robin, Claude Sonnet 4.6)
      └── Fallback cuối cùng
```

---

## 3. Quy trình cấu hình & Xác minh O(1)

### Bước 1: Phân loại tài khoản từ SQLite (`~/.omniroute/storage.sqlite`)
```python
import sqlite3, json

con = sqlite3.connect("C:/Users/Kibe/.omniroute/storage.sqlite")
cur = con.cursor()
cur.execute("SELECT id, email, is_active, provider_specific_data FROM provider_connections WHERE provider='antigravity' AND is_active=1")

pro_cids = []
free_cids = []

for cid, email, is_active, psd in cur.fetchall():
    d = json.loads(psd) if psd else {}
    tier = str(d.get('tier') or d.get('tierId') or '')
    plan = str(d.get('plan') or '')
    if tier == 'g1-pro-tier' or plan == 'Pro':
        pro_cids.append((cid, email))
    else:
        free_cids.append((cid, email))
```

### Bước 2: Cập nhật REST API `:20129`
1. `PUT /api/combos/<id_ag_gemini_pool_3>`:
   - `strategy`: `"round-robin"`
   - `models`: Đúng 16 model connection của 16 acc Pro.
   - `config`: `stickyRoundRobinLimit: 1`, `disableSessionStickiness: false`, `disablePromptCacheAffinity: false`.
2. `POST /api/combos` (hoặc `PUT` nếu đã có `ag-gemini-free-pool`):
   - `name`: `"ag-gemini-free-pool"`
   - `strategy`: `"round-robin"`
   - `models`: Toàn bộ model connection của 87 acc Free/Standard.
   - `config`: `stickyRoundRobinLimit: 1`, `disableSessionStickiness: false`.
3. `PUT /api/combos/<id_omni_worker>`:
   - `strategy`: `"priority"`
   - `config.nestedComboMode`: `"execute"`
   - `models`: 5 tầng combo-ref (`ag-gemini-pool-3` -> `ag-gemini-free-pool` -> `chatgpt-web-pool` -> `omni-free` -> `ag-claude`).

### Bước 3: Đồng bộ Backup & Test Gate
- Dump toàn bộ trạng thái API về file backup:
  `D:/Taadaa/AI-Tools/tools/omniroute/combos_backup.json`
- Chạy test suite xác nhận 5/5 PASSED:
  ```bash
  python -m pytest "D:/Taadaa/AI-Tools/tests/test_omniroute_combos.py" -v
  ```
- Gửi probe inference và kiểm tra `call_logs` xác nhận request ăn thẳng vào tài khoản Pro.
