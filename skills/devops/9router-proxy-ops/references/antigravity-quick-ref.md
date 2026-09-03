## Quick Reference: Antigravity Priority Demotion

**Symptom:** `No active credentials for provider: antigravity` (HTTP 404)

**Cause:** All 7 antigravity accounts demoted to priority=9999 due to 429 quota errors.

**Fix:** Run `scripts/fix_antigravity_priority.py` or execute SQL:
```sql
UPDATE providerConnections 
SET priority = json_extract(data, '$.priorityBase'),
    updatedAt = datetime('now')
WHERE provider = 'antigravity' AND priority = 9999;
```

**Verify:** All 7 accounts should have priority = priorityBase (1-7).

**Also check:** `settings.requireLogin = false` in SQLite if remote API access returns "API key required for remote API access".

**Restart:** 9Router server after DB changes.