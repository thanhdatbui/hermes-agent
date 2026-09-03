#!/usr/bin/env python3
"""
Fix antigravity provider priority demotion in 9Router.

When all antigravity accounts have priority >= 9000 (demoted due to 429 quota),
the error "No active credentials for provider: antigravity" occurs.

This script resets priority back to priorityBase for all demoted antigravity accounts.
"""

import sqlite3
import os
import sys


def fix_antigravity_priority(db_path: str) -> int:
    """Reset priority for demoted antigravity accounts."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("""
        SELECT id, name, priority, json_extract(data, '$.priorityBase') as priorityBase
        FROM providerConnections 
        WHERE provider = 'antigravity' AND priority = 9999
    """)
    demoted = cursor.fetchall()
    
    if not demoted:
        print("No demoted antigravity accounts found.")
        return 0
    
    print(f"Found {len(demoted)} demoted antigravity accounts:")
    for row in demoted:
        print(f"  {row[1]}: priority={row[2]}, priorityBase={row[3]}")
    
    # Fix: reset priority to priorityBase
    cursor.execute("""
        UPDATE providerConnections 
        SET priority = json_extract(data, '$.priorityBase'),
            updatedAt = datetime('now')
        WHERE provider = 'antigravity' AND priority = 9999
    """)
    rows_updated = cursor.rowcount
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT id, name, priority, json_extract(data, '$.priorityBase') as priorityBase
        FROM providerConnections WHERE provider = 'antigravity'
    """)
    all_accounts = cursor.fetchall()
    
    print(f"\nUpdated {rows_updated} accounts. Current state:")
    for row in all_accounts:
        status = "✓" if row[2] == row[3] else "✗"
        print(f"  {status} {row[1]}: priority={row[2]}, priorityBase={row[3]}")
    
    conn.close()
    return rows_updated


if __name__ == "__main__":
    # Default 9Router DB path on Windows
    appdata = os.environ.get('APPDATA', '')
    db_path = os.path.join(appdata, '9router', 'db', 'data.sqlite')
    
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        sys.exit(1)
    
    print(f"Using database: {db_path}")
    rows = fix_antigravity_priority(db_path)
    
    if rows > 0:
        print(f"\n✓ Fixed {rows} antigravity account(s). Restart 9Router to apply changes.")
    else:
        print("\nNo changes needed.")