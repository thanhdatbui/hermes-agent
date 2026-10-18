# Automated Crawler Ingest & VPS Atomic SQLite Sync Pipeline

Patterns, safety invariants, and operational guidelines for connecting local residential crawlers (Chrome CDP / VNEPS) to cloud FastMCP SQLite caches via atomic swaps and integrity checks.

---

## 1. Problem Statement & Architecture

In Decoupled CQRS architectures for public procurement (VNEPS Mua Sắm Công):
- The crawler operates on a local residential machine to bypass WAF, SSL DH_KEY_TOO_SMALL, and Keycloak bot-detection.
- The query daemon (FastMCP) runs on a cloud VPS serving remote SSE requests to ChatGPT / Antigravity in $< 0.2\text{s}$.
- **The Core Risk:** How to update the SQLite database on the cloud VPS continuously without:
  1. Corrupting live connections (`sqlite3.OperationalError: database is locked` or stale WAL pages).
  2. Overwriting production data with an incomplete/empty scrape (crawler failure wiping DB).
  3. Experiencing extended downtime during sync.

---

## 2. Invariant 1: Local Safe Snapshot via SQLite Backup API

Never perform a raw file copy of an active SQLite database in WAL mode (`bidding_cache.db`). Copying without flushing or mid-transaction leaves companion `-wal` and `-shm` files inconsistent, resulting in corrupted snapshots or stale reads.

```python
import sqlite3, os, hashlib

def create_safe_snapshot(src_db_path: str, dst_snapshot_path: str) -> dict:
    if not os.path.exists(src_db_path):
        raise FileNotFoundError(f"Source DB missing: {src_db_path}")

    # 1. Truncate WAL to write all transactions into main DB
    src_conn = sqlite3.connect(src_db_path)
    try:
        src_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    except sqlite3.Error:
        pass

    # 2. Use SQLite Backup API to create a consistent, standalone clone
    dst_conn = sqlite3.connect(dst_snapshot_path)
    with dst_conn:
        src_conn.backup(dst_conn)
    src_conn.close()

    # 3. Convert snapshot journal mode to DELETE (removes WAL dependency completely)
    dst_conn.execute("PRAGMA journal_mode=DELETE;")
    cur = dst_conn.cursor()
    cur.execute("PRAGMA integrity_check;")
    if cur.fetchone()[0] != "ok":
        dst_conn.close()
        raise ValueError("Snapshot integrity check failed!")

    cur.execute("SELECT COUNT(*) FROM tenders;")
    count = cur.fetchone()[0]
    dst_conn.close()

    # 4. Calculate local SHA256 checksum
    hasher = hashlib.sha256()
    with open(dst_snapshot_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    
    return {
        "path": dst_snapshot_path,
        "sha256": hasher.hexdigest(),
        "row_count": count,
        "status": "ok"
    }
```

---

## 3. Invariant 2: Row Count Guard & Staging Integrity Check

Before performing any destructive swap on the VPS, enforce an absolute guard check: **The incoming snapshot row count must be $\ge$ the existing row count on VPS**.

- If the crawler encountered a portal error, network glitch, or parser selector change and only scraped 5 tenders, it MUST NOT overwrite the production database containing 117 tenders.

```python
# Query current production row count on VPS before uploading
cmd_count = (
    '/opt/doravo-mcp/venv/bin/python3 -c "'
    'import sqlite3, os; '
    'print(sqlite3.connect(\'/opt/doravo-mcp/mcp_server/bidding_cache.db\').execute(\'SELECT COUNT(*) FROM tenders\').fetchone()[0] '
    'if os.path.exists(\'/opt/doravo-mcp/mcp_server/bidding_cache.db\') else 0)"'
)
vps_count = int(ssh_exec(cmd_count).strip() or "0")

if local_snapshot_count < vps_count:
    raise ValueError(
        f"Row count guard trip: Snapshot ({local_snapshot_count}) < VPS current ({vps_count})! Aborting sync."
    )
```

---

## 4. Invariant 3: Atomic Swap with Automatic Rollback

1. **Upload to Staging:** SFTP file to `/opt/doravo-mcp/mcp_server/bidding_cache.db.staging`.
2. **Verify Remote Checksum:** Run `sha256sum` on VPS staging file and match against local SHA256. If mismatch, `rm -f staging` and abort.
3. **Execute Atomic Swap:**
   ```bash
   systemctl stop doravo-mcp && \
   cp -f /opt/doravo-mcp/mcp_server/bidding_cache.db /opt/doravo-mcp/mcp_server/bidding_cache.db.prev 2>/dev/null || true; \
   mv -f /opt/doravo-mcp/mcp_server/bidding_cache.db.staging /opt/doravo-mcp/mcp_server/bidding_cache.db && \
   rm -f /opt/doravo-mcp/mcp_server/bidding_cache.db-wal /opt/doravo-mcp/mcp_server/bidding_cache.db-shm && \
   systemctl start doravo-mcp && sleep 4
   ```
4. **Post-Swap Health Verification & Rollback:**
   - Probe internal Uvicorn endpoint: `curl -s -i http://127.0.0.1:8100/health`.
   - If response does not contain `200 OK`:
     ```bash
     cp -f /opt/doravo-mcp/mcp_server/bidding_cache.db.prev /opt/doravo-mcp/mcp_server/bidding_cache.db && \
     systemctl restart doravo-mcp
     ```
     Raise exception to notify operator of rollback.

---

## 5. Operational Verification via Antigravity CLI

After every pipeline run, verify through external remote MCP call (simulating ChatGPT):
```bash
agy mcp add yccmed_remote https://doravo.net/mcp
```
Run `get_cache_status` to confirm:
- `total_tenders` reflects expected row count.
- `data_as_of` timestamp is updated to current UTC ISO time.
