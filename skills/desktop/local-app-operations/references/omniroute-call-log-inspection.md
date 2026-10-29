# OmniRoute Call Log & Request Artifact Inspection Runbook

## 1. Context & Motivation

When operators or users ask to inspect live OmniRoute traffic ("omnilog 1 req", "xem request log", "kiểm tra payload vừa gửi", "tại sao request chậm/lỗi"):
- Opening the browser UI (`/dashboard/logs`) is slow and can fail (e.g. 500 Internal Server Error when running backend-only build).
- Invoking API endpoints like `/api/logs` via `curl` can be blocked by Coordinator Guard allowlists or require auth headers.
- Blind disk searching via `os.walk` or recursive `glob` violates Coordinator safety invariants.

OmniRoute natively persists all structured call logs and full JSON payload artifacts to local disk. Inspecting SQLite + JSON directly via Python takes <0.1s, operates with zero UI overhead, and provides 100% fidelity.

---

## 2. Storage Layout & Authoritative Paths

- **Data Directory**: `C:\Users\Kibe\.omniroute\`
- **Authoritative Database**: `C:\Users\Kibe\.omniroute\storage.sqlite`
- **Metadata Table**: `call_logs`
- **Artifact Directory**: `C:\Users\Kibe\.omniroute\call_logs\<YYYY-MM-DD>\`
- **Artifact Filename**: `<timestamp>_<call_id>.json` (corresponds directly to `artifact_relpath` in `call_logs`).

### `call_logs` Schema Highlights
| Column | Description |
|---|---|
| `id` | Unique call log identifier (e.g. `1793267360454-fc539d`) |
| `timestamp` | ISO timestamp of the request |
| `method`, `path`, `status` | HTTP method, route (`/v1/chat/completions`), status code (`200`, `503`, `429`) |
| `model`, `requested_model` | Upstream model executed vs model string requested by client |
| `provider`, `account` | Target provider (`antigravity`) and specific account email |
| `connection_id` | Pinned connection UUID |
| `duration` | Total latency in milliseconds |
| `tokens_in`, `tokens_out` | Input prompt tokens and output completion tokens |
| `tokens_cache_read` | Cached tokens read upstream (prefix caching) |
| `tokens_reasoning` | Reasoning / thinking tokens generated |
| `combo_name`, `combo_step_id` | Executing combo and combo step identifier |
| `artifact_relpath` | Relative path to full JSON artifact under `.omniroute\call_logs\` |

---

## 3. O(1) Inspection Recipes

### Recipe A: View Latest Request Summary (One-liner)
```bash
python -c "import sqlite3, json; conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite'); cur = conn.cursor(); cur.execute('PRAGMA table_info(call_logs)'); cols = [c[1] for c in cur.fetchall()]; cur.execute('SELECT * FROM call_logs ORDER BY rowid DESC LIMIT 1'); row = cur.fetchone(); print(json.dumps(dict(zip(cols, row)), indent=2, default=str))"
```

### Recipe B: Inspect Full Payload Artifact (Request & Response Body)
```bash
python -c "import os, sqlite3, json; conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite'); cur = conn.cursor(); cur.execute('SELECT artifact_relpath FROM call_logs ORDER BY rowid DESC LIMIT 1'); relpath = cur.fetchone()[0]; p = os.path.join(r'C:\Users\Kibe\.omniroute\call_logs', relpath); d = json.load(open(p, encoding='utf-8')); print('SUMMARY:', json.dumps(d.get('summary'), indent=2)); req = d.get('requestBody') or {}; print('Msg count:', len(req.get('messages', []))); print('Resp choices:', len(d.get('responseBody', {}).get('choices', [])))"
```

### Recipe C: Filter Recent Errors or Throttled Requests
```bash
python -c "import sqlite3, json; conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite'); cur = conn.cursor(); cur.execute('SELECT id, timestamp, status, model, account, duration, error_summary FROM call_logs WHERE status != 200 ORDER BY rowid DESC LIMIT 10'); print(cur.fetchall())"
```

---

## 4. Diagnostic Interpretation

1. **High Cache Hit Rate (`tokens_cache_read` / `tokens_in` > 80%)**:
   - Normal and desirable for multi-turn sessions. Indicates prefix caching is working.
2. **Account Affinity & Combo Step (`combo_step_id`)**:
   - Confirms whether request went to the expected pool account (e.g. `ag-gemini-pool-3-model-pro-...`) or spilled over due to concurrency saturation.
3. **Duration vs Latency**:
   - `duration` captures end-to-end execution in ms. If duration is long (>15s) with small `tokens_out`, check upstream connection network or Google Cloud Code endpoint throttling.
