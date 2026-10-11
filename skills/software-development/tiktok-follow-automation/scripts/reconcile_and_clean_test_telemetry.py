#!/usr/bin/env python3
"""
scripts/reconcile_and_clean_test_telemetry.py
Audit and safely purge test or duplicate session telemetry from session_account_actions
and cleanly recalculate daily_account_actions in tiktok_tracker.db.

Usage:
    python scripts/reconcile_and_clean_test_telemetry.py [--db D:/Taadaa/data/tiktok_tracker.db] [--date YYYY-MM-DD] [--fix]
"""

import argparse
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

STANDARD_SESSION_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}_ca\d+_phien\d+$")

def audit_sessions(db_path: str, target_date: str = None) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    query = "SELECT DISTINCT session_key, target_date FROM session_account_actions"
    params = []
    if target_date:
        query += " WHERE target_date = ?"
        params.append(target_date)
    query += " ORDER BY target_date DESC"
    
    rows = cur.execute(query, params).fetchall()
    conn.close()

    anomalous = []
    for s_key, t_date in rows:
        if not STANDARD_SESSION_REGEX.match(s_key):
            anomalous.append((s_key, t_date))
    return anomalous

def clean_and_rebuild(db_path: str, target_date: str = None, dry_run: bool = True):
    anomalous = audit_sessions(db_path, target_date)
    if not anomalous:
        print("[INFO] No anomalous or test session keys found.")
        return 0

    print(f"[FOUND] {len(anomalous)} anomalous session key(s):")
    for s_key, t_date in anomalous:
        print(f"  - Session: {s_key} (Date: {t_date})")

    if dry_run:
        print("\n[DRY RUN] Run with --fix to purge these sessions and rebuild daily_account_actions.")
        return len(anomalous)

    # Backup DB first
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.bak_{ts}"
    shutil.copy2(db_path, backup_path)
    print(f"[BACKUP] Created database backup: {backup_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    anomalous_keys = [s[0] for s in anomalous]
    placeholders = ",".join(["?"] * len(anomalous_keys))
    
    # 1. Delete anomalous records from session_account_actions
    cur.execute(f"DELETE FROM session_account_actions WHERE session_key IN ({placeholders})", anomalous_keys)
    deleted_rows = cur.rowcount
    print(f"[PURGE] Deleted {deleted_rows} row(s) from session_account_actions.")

    # 2. Re-aggregate daily_account_actions for affected dates
    affected_dates = sorted(set(s[1] for s in anomalous))
    for d in affected_dates:
        cur.execute("DELETE FROM daily_account_actions WHERE target_date = ?", (d,))
        cur.execute("""
            INSERT INTO daily_account_actions (target_date, username, may, internal_follows, updated_at)
            SELECT target_date, username, MAX(may), SUM(internal_follows), MAX(updated_at)
            FROM session_account_actions
            WHERE target_date = ?
            GROUP BY target_date, username
        """, (d,))
        rebuilt = cur.rowcount
        print(f"[REBUILD] Date {d}: rebuilt {rebuilt} account row(s) in daily_account_actions.")

    conn.commit()
    conn.close()
    print("[DONE] Telemetry purged and daily table recalculated successfully.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit and clean test session telemetry.")
    parser.add_argument("--db", default="D:/Taadaa/data/tiktok_tracker.db", help="Path to tiktok_tracker.db")
    parser.add_argument("--date", default=None, help="Specific target date (YYYY-MM-DD)")
    parser.add_argument("--fix", action="store_true", help="Apply cleanup and rebuild (destructive with backup)")
    args = parser.parse_args()

    sys.exit(clean_and_rebuild(args.db, args.date, dry_run=not args.fix))
