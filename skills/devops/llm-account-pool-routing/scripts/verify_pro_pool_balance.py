#!/usr/bin/env python3
"""
Diagnostic script to audit OmniRoute Pro Pool (:20129)
Checks:
1. Tight priority band (detects priority gap starvation like 13 vs 113)
2. Quota status per Pro account
3. Isolation check: ensures no Restricted/standard-tier accounts have is_active=1
4. Recent call distribution to spot traffic monopoly
"""

import sqlite3
import sys

DB_PATH = "C:/Users/Kibe/.omniroute/storage.sqlite"

def audit_pool():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = con.cursor()

    print("=== 1. AUDIT PRO ACCOUNTS & PRIORITY BAND ===")
    pros = cur.execute("""
        SELECT id, email, priority, is_active, test_status
        FROM provider_connections
        WHERE provider_specific_data LIKE '%Google AI Pro%' AND is_active = 1
        ORDER BY priority ASC
    """).fetchall()

    if not pros:
        print("[-] No active Pro accounts found!")
    else:
        priorities = [p[2] for p in pros if p[2] is not None]
        min_p = min(priorities) if priorities else 0
        max_p = max(priorities) if priorities else 0
        gap = max_p - min_p
        print(f"[+] Total active Pro accounts: {len(pros)}")
        print(f"[+] Priority range: {min_p} -> {max_p} (Spread: {gap})")
        if gap > 15:
            print(f"[!] WARNING: Priority gap is {gap} (>15). Risk of traffic starvation for higher priority numbers!")
        for p in pros:
            # Check remaining quota
            snap = cur.execute("""
                SELECT remaining_percentage, is_exhausted, next_reset_at
                FROM quota_snapshots
                WHERE connection_id = ? AND (window_key = 'gemini-3.8-flash-tiered' OR window_key LIKE '%flash%')
                ORDER BY id DESC LIMIT 1
            """, (p[0],)).fetchone()
            rem = f"{snap[0]:.1f}%" if snap and snap[0] is not None else "N/A"
            reset = snap[2] if snap else "N/A"
            print(f"    - prio={p[2]:<3} | {p[1]:<40} | rem={rem:<6} | reset={reset}")

    print("\n=== 2. ISOLATION CHECK (RESTRICTED ACCOUNTS) ===")
    leaked = cur.execute("""
        SELECT id, email, is_active, test_status
        FROM provider_connections
        WHERE provider = 'antigravity'
          AND (provider_specific_data LIKE '%Restricted%' OR provider_specific_data LIKE '%standard-tier%')
          AND is_active = 1
    """).fetchall()
    if leaked:
        print(f"[!] ALERT: Found {len(leaked)} RESTRICTED accounts with is_active=1:")
        for l in leaked:
            print(f"    - {l[1]} (id: {l[0]})")
    else:
        print("[+] CLEAN: All restricted accounts are properly deactivated (is_active=0).")

    print("\n=== 3. CALL DISTRIBUTION (LAST 15 MINS) ===")
    calls = cur.execute("""
        SELECT account, COUNT(*), SUM(CASE WHEN status=200 THEN 1 ELSE 0 END), SUM(CASE WHEN status!=200 THEN 1 ELSE 0 END)
        FROM call_logs
        WHERE timestamp >= datetime('now', '-15 minutes') AND provider = 'antigravity'
        GROUP BY account
        ORDER BY COUNT(*) DESC
    """).fetchall()
    if not calls:
        print("[*] No calls recorded in the last 15 minutes.")
    else:
        for c in calls:
            print(f"    - {c[0]:<42} | Total: {c[1]:<4} | OK: {c[2]:<4} | Err: {c[3]:<4}")

    con.close()

if __name__ == "__main__":
    audit_pool()
