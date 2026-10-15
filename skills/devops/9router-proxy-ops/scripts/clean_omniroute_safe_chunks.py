"""Chunked safe cleaner for OmniRoute SQLite database bloat.
Deletes records in small batches by PK/rowid to avoid locking SQLite and choking the NodeJS Event Loop.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta, timezone

DB_PATH = r"C:\Users\Kibe\.omniroute\storage.sqlite"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def clean() -> None:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cur = conn.cursor()

    # 1. Clean quota_snapshots (> 2 days old)
    log("Cleaning quota_snapshots older than 2 days...")
    t0 = time.time()
    cur.execute("SELECT id FROM quota_snapshots WHERE created_at < datetime('now', '-2 days') ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        max_id = row[0]
        deleted_qs = 0
        while True:
            cur.execute("SELECT id FROM quota_snapshots WHERE id <= ? ORDER BY id ASC LIMIT 1 OFFSET 25000", (max_id,))
            next_row = cur.fetchone()
            chunk_bound = next_row[0] if next_row else max_id
            with conn:
                cur.execute("DELETE FROM quota_snapshots WHERE id <= ?", (chunk_bound,))
                cnt = cur.rowcount
            deleted_qs += cnt
            if chunk_bound >= max_id or cnt == 0:
                break
            time.sleep(0.05)
        log(f"Cleaned {deleted_qs} rows from quota_snapshots in {round(time.time() - t0, 2)}s")
    else:
        log("No stale quota_snapshots found.")

    # 2. Clean xp_audit_log (> 3 days old)
    log("Cleaning xp_audit_log older than 3 days...")
    t0 = time.time()
    cur.execute("SELECT id FROM xp_audit_log WHERE created_at < datetime('now', '-3 days') ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row:
        max_id = row[0]
        deleted_xp = 0
        while True:
            cur.execute("SELECT id FROM xp_audit_log WHERE id <= ? ORDER BY id ASC LIMIT 1 OFFSET 25000", (max_id,))
            next_row = cur.fetchone()
            chunk_bound = next_row[0] if next_row else max_id
            with conn:
                cur.execute("DELETE FROM xp_audit_log WHERE id <= ?", (chunk_bound,))
                cnt = cur.rowcount
            deleted_xp += cnt
            if chunk_bound >= max_id or cnt == 0:
                break
            time.sleep(0.05)
        log(f"Cleaned {deleted_xp} rows from xp_audit_log in {round(time.time() - t0, 2)}s")
    else:
        log("No stale xp_audit_log found.")

    # 3. Clean call_logs (> 3 days old)
    log("Cleaning call_logs older than 3 days...")
    t0 = time.time()
    with conn:
        cur.execute("DELETE FROM call_logs WHERE timestamp < datetime('now', '-3 days')")
        cnt = cur.rowcount
    log(f"Cleaned {cnt} rows from call_logs in {round(time.time() - t0, 2)}s")

    # 4. Clean conversation_turn_nodes (> 5 days old)
    cutoff_5d = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    log(f"Cleaning conversation_turn_nodes older than 5 days ({cutoff_5d})...")
    t0 = time.time()

    cur.execute("SELECT MIN(rowid), MAX(rowid) FROM conversation_turn_nodes")
    min_r, max_r = cur.fetchone()
    if min_r and max_r:
        low, high = min_r, max_r
        target_rowid = min_r
        while low <= high:
            mid = (low + high) // 2
            cur.execute(
                "SELECT last_seen_at FROM conversation_turn_nodes WHERE rowid >= ? ORDER BY rowid ASC LIMIT 1",
                (mid,),
            )
            r = cur.fetchone()
            if not r:
                high = mid - 1
                continue
            if r[0] < cutoff_5d:
                target_rowid = mid
                low = mid + 1
            else:
                high = mid - 1

        log(f"Target rowid for 5d cutoff: {target_rowid} (current min: {min_r})")
        deleted_turns = 0
        curr = min_r
        while curr <= target_rowid:
            batch_end = min(curr + 20000, target_rowid)
            with conn:
                cur.execute("DELETE FROM conversation_turn_nodes WHERE rowid <= ?", (batch_end,))
                cnt = cur.rowcount
            deleted_turns += cnt
            log(f"  Turn nodes deleted so far: {deleted_turns} (up to rowid {batch_end})")
            curr = batch_end + 1
            time.sleep(0.1)
        log(f"Cleaned {deleted_turns} rows from conversation_turn_nodes in {round(time.time() - t0, 2)}s")

    # 5. Clean agentic_conversations (> 5 days old)
    log("Cleaning agentic_conversations older than 5 days...")
    t0 = time.time()
    with conn:
        cur.execute("DELETE FROM agentic_conversations WHERE last_seen_at < ?", (cutoff_5d,))
        cnt = cur.rowcount
    log(f"Cleaned {cnt} rows from agentic_conversations in {round(time.time() - t0, 2)}s")

    # 6. Checkpoint WAL and optimize
    log("Running PRAGMA wal_checkpoint(PASSIVE)...")
    cur.execute("PRAGMA wal_checkpoint(PASSIVE);")
    log(f"Checkpoint result: {cur.fetchall()}")

    log("Running PRAGMA optimize...")
    cur.execute("PRAGMA optimize;")

    # 7. Check current freelist count
    cur.execute("PRAGMA freelist_count;")
    freelist = cur.fetchone()[0]
    cur.execute("PRAGMA page_count;")
    page_count = cur.fetchone()[0]
    log(
        f"Done! Freelist pages: {freelist}/{page_count} (~{round(freelist * 4096 / 1024 / 1024, 1)} MB reusable free space)"
    )

    conn.close()


if __name__ == "__main__":
    clean()
