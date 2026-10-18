# FastMCP Production Hardening, Nginx Proxy Invariants & Evaluator Audit

Comprehensive reference for deploying FastMCP (Python) servers into live production behind Nginx reverse proxies, handling security settings, avoiding 421/403 errors, and engineering robust technical specification evaluators for public procurement.

---

## 1. FastMCP DNS Rebinding & Real-Domain 421 Trap

### Root Cause
FastMCP (Anthropic official Python SDK `mcp.server.fastmcp`) includes built-in DNS Rebinding Protection via `TransportSecuritySettings`. By default:
- `enable_dns_rebinding_protection = True`
- `allowed_hosts = []` (only `localhost` / `127.0.0.1` are permitted implicitly)

When a FastMCP server is deployed behind a real domain (e.g. `https://doravo.net/mcp`), requests carry `Host: doravo.net`. The FastMCP middleware detects an untrusted Host header and immediately aborts the connection with:
```http
HTTP/1.1 421 Misdirected Request
Content-Length: 19

Invalid Host header
```

### The Fix
Explicitly configure `TransportSecuritySettings` on server initialization:
```python
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings

sec = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
    allowed_hosts=["doravo.net", "www.doravo.net", "localhost", "127.0.0.1"],
    allowed_origins=["*"]
)
mcp = FastMCP("YCCMED Bidding Assistant", transport_security=sec)
```
*Note:* In Nginx, if passing the host header, ensure `proxy_set_header Host $host;` or `proxy_set_header Host localhost;` is consistent with the allowed hosts list.

---

## 2. Nginx Reverse Proxy: The Prefix vs Regex Priority Trap (403 Forbidden)

### The Pitfall
In monolithic web configs (like WordPress, ShopClone, or PHP apps), security configurations frequently include regex location blocks to deny access to sensitive files:
```nginx
location ~ /\.(?!well-known).* { deny all; }
location ~* \.(env|sql|sqlite|db|log|sh)$ { deny all; }
```
In Nginx request matching order:
1. Exact matches (`=`)
2. Preferential prefix matches (`^~`)
3. **Regular expressions** (`~` and `~*`)
4. Standard prefix matches (`location /mcp { ... }`)

If `/mcp` is defined as a standard prefix `location /mcp { ... }`, any trailing path, parameter, or nested matching can fall into higher-priority regex blocks, returning `403 Forbidden` (`access forbidden by rule`).

### The Invariant: Use `^~` Modifier
Always declare MCP proxy locations with `^~`:
```nginx
location ^~ /mcp {
    proxy_pass http://127.0.0.1:8100;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection '';
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding off;
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;
}

location = /.well-known/oauth-authorization-server {
    proxy_pass http://127.0.0.1:8100/.well-known/oauth-authorization-server;
    proxy_set_header Host $host;
}
```
`^~` tells Nginx: *If this prefix matches, immediately stop checking regular expressions!*

---

## 3. Procurement Specification Evaluator: The False-FIT / False-UNFIT Hazards

When developing rule-based technical evaluators for tender dossiers (e.g. Trocar, medical devices):

### A. Word-Boundary Hazards (False UNFIT)
- **Sub-string collision:** Checking `"8mm" in text` matches `"Trocar 18mm"`, incorrectly classifying an 18mm package as UNFIT.
- **Rule:** Always use negative lookbehind and word boundaries:
  ```python
  re.search(r"(?<!\d)8\s*mm\b", text_lower)
  ```

### B. Negation Clauses in Dossiers (False UNFIT)
- Bidding documents often include negative requirements, such as:
  *"Hệ thống phẫu thuật nội soi thông thường, không yêu cầu robot"*
  *"Không dùng trocar có lưỡi dao"*
- A naive check for `"robot" in text` will trigger an UNFIT verdict, reversing the legal intent of the document.
- **Rule:** Check for negation prefixes within a 25-character window preceding the keyword:
  ```python
  def _is_negated_keyword(text: str, keyword_pattern: str) -> bool:
      for m in re.finditer(keyword_pattern, text):
          prefix = text[max(0, m.start() - 30):m.start()].strip()
          if re.search(r"(không|chẳng|ko|khg)\s+(yêu cầu|sử dụng|dùng|phải|cần)?\s*$", prefix):
              continue
          return False
      return True
  ```

### C. The Blind-FIT Trap: Require `NEEDS_REVIEW`
- When a bidding document contains only general terms (e.g., *"Mua sắm Trocar nội soi"*) without specifying sizes (5mm, 10mm, 12mm, 15mm), an evaluator must **never** return `FIT` with a recommendation of all 4 models.
- "Absence of disqualifying keywords" is NOT proof of compatibility.
- **Rule:** If no sizes or specific technical parameters are matched, return:
  - `status: "NEEDS_REVIEW"`
  - `reason: "Hồ sơ thầu chưa nêu rõ kích cỡ hoặc thông số kỹ thuật chi tiết. Cần kiểm tra file chương kỹ thuật (E-HSMT)."`
  - `matched_models: list(YCCMED_MODELS.values())` (provisional candidates only).

---

## 4. Date Normalization & Cache Freshness Transparency

### A. Date Parsing for SQLite Ordering
- Vietnamese government portals return dates formatted as `DD/MM/YYYY` or `DD/MM/YYYY HH:mm`.
- SQLite `ORDER BY deadline_date` performs lexicographical text sorting: `"01/12/2026"` will sort before `"02/01/2026"`.
- **Rule:** Convert all incoming dates to ISO-8601 (`YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`) before `upsert_tender()`.

### B. Dynamic Expiry Gate
- Do not rely solely on the crawler's boolean `is_open` flag. If crawler sync pauses, an expired tender will permanently appear "open".
- **Rule:** Filter dynamically in SQLite queries:
  ```sql
  WHERE is_open = 1 AND (deadline_date IS NULL OR deadline_date >= date('now'))
  ```

### C. Data Freshness SLA (`data_as_of`)
- All MCP tools returned to ChatGPT must include the timestamp of the latest cache sync (`data_as_of` or `updated_at`).
- Provide a dedicated diagnostic tool:
  ```python
  @mcp.tool()
  def get_cache_status() -> str:
      """Kiểm tra tình trạng đồng bộ dữ liệu: tổng số gói thầu trong cache và thời điểm cập nhật mới nhất."""
  ```
  This allows ChatGPT to alert the user if data is stale (> 6-12 hours).

---

## 5. Multi-Lot (Phân Lô) Specification Isolation

### The Hazard
Vietnamese hospital tenders frequently group multiple procurement lots into a single tender package (TBMT / YCBG):
- *Lô 1:* Trocar nội soi 5mm, 10mm, 12mm (dùng một lần, thân ren không dao).
- *Lô 2:* Dụng cụ phẫu thuật Robot / Trocar 8mm chuyên dụng.
- *Lô 3:* Lưỡi dao mổ / Dao cắt nội soi.

If the MCP evaluator blindly concatenates the entire tender document (`text = " ".join([title, category, raw_json])`), disqualifying keywords (`robot`, `8mm`, `lưỡi dao`) from Lot 2 or Lot 3 will falsely trigger an **UNFIT** verdict for Lot 1.

### The Invariant
1. Parse the structured JSON payload rather than dumping raw JSON text into the evaluator:
   ```python
   raw_str = tender.get("raw_json") or ""
   specs_text = ""
   try:
       raw_obj = json.loads(raw_str)
       if isinstance(raw_obj, dict):
           specs_text = str(raw_obj.get("technical_specs") or raw_obj.get("note") or "")
       else:
           specs_text = raw_str
   except Exception:
       specs_text = raw_str

   text = f"{tender.get('title') or ''} {tender.get('category') or ''} {specs_text}".strip()
   ```
2. When parsing multi-lot tenders, isolate per-lot line items so each lot receives an independent compatibility assessment.

---

## 6. SQLite WAL Mode Synchronization Trap (Live Database Upload to VPS)

### The Pitfall
When synchronizing or updating an SQLite database (`bidding_cache.db`) on a production VPS where the FastMCP service is running with WAL mode enabled (`PRAGMA journal_mode=WAL;`):
- Active connections maintain uncommitted pages and index shared memory in companion files: `bidding_cache.db-wal` and `bidding_cache.db-shm`.
- If an agent simply copies the new `bidding_cache.db` file over SFTP without stopping the service or removing `-wal`/`-shm`, SQLite continues serving cached pages from the old `-wal` file!
- **Symptom:** Local database has 117 records, but querying the VPS database returns `COUNT(*) = 1` or stale records.

### The Invariant: Clean-Cut Sync Protocol
1. **On Source Machine (Flush WAL):**
   ```python
   conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
   conn.close()
   ```
2. **On VPS (Atomic Swap):**
   ```bash
   systemctl stop doravo-mcp
   rm -f /opt/doravo-mcp/mcp_server/bidding_cache.db*
   ```
3. **Upload & Restart:**
   - Upload fresh `bidding_cache.db`.
   - Start the service: `systemctl start doravo-mcp`
   - Immediately verify live count:
     ```bash
     /opt/doravo-mcp/venv/bin/python3 -c "import sqlite3; conn=sqlite3.connect('/opt/doravo-mcp/mcp_server/bidding_cache.db'); print('Count:', conn.execute('SELECT COUNT(*) FROM tenders').fetchone()[0])"
     ```

---

## 7. Null-Safe Ingestion & Resilient Sync Invariants

### A. The `data.get("scope", "")` Null Trap
In SQLite schemas defining `scope TEXT NOT NULL`, python's `dict.get("scope", "Trong nước")` only provides the default if the key `"scope"` is **missing**. If the scraper produces `{"scope": null}`, `get()` returns `None`, violating the SQLite constraint:
```text
sqlite3.IntegrityError: NOT NULL constraint failed: tenders.scope
```
- **Rule:** Always use `or` fallback:
  ```python
  scope = data.get("scope") or "Trong nước"
  ```

### B. Missing Primary Key (`bid_code`) Guard
Never allow records with null or blank primary keys into the upsert pipeline:
```python
bid_code = data.get("bid_code")
if not bid_code or not str(bid_code).strip():
    return
```

### C. Fault-Tolerant Bulk Sync
In `sync_adapter.py`, wrap individual record upserts in `try/except Exception` so that a single corrupted line in a 500-line historical JSONL crawler dump never aborts the remaining 499 records. Log the skipped count and continue.
