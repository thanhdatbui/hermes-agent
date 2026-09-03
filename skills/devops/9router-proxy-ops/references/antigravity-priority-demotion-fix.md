# Antigravity Provider Priority Demotion Fix

## Problem
**"No active credentials for provider: antigravity"** error when trying to use models like `ag/gemini-3.7-flash-high`.

## Root Cause
All 7 antigravity accounts had their `priority` demoted to **9999** due to repeated 429 quota errors. In 9Router, when ALL accounts for a provider have `priority >= 9000`, the auth system treats them as unavailable and returns "No active credentials for provider: antigravity".

### Affected Accounts (all 7)
| Email | Original Priority | Demoted Priority |
|-------|-------------------|------------------|
| thanhdatbui19951@gmail.com | 1 | 9999 |
| jinrakal@gmail.com | 2 | 9999 |
| marcusephillips52sns@gmail.com | 3 | 9999 |
| dinhlan24072000@gmail.com | 4 | 9999 |
| toloan12091999@gmail.com | 5 | 9999 |
| minhan2745@gmail.com | 6 | 9999 |
| dokieu04092004@gmail.com | 7 | 9999 |

## Fix Applied
Reset `priority` back to `priorityBase` value stored in each account's JSON data:

```sql
UPDATE providerConnections 
SET priority = json_extract(data, '$.priorityBase'),
    updatedAt = datetime('now')
WHERE provider = 'antigravity' AND priority = 9999;
```

Result: All 7 accounts restored to priorities 1-7.

## Verification Query
```sql
SELECT id, name, priority, json_extract(data, '$.priorityBase') as priorityBase
FROM providerConnections WHERE provider = 'antigravity';
```

## Prevention
- Monitor 429 rates on antigravity accounts
- Consider adding more antigravity accounts to distribute load
- The `priorityCooldownUntil` field shows when demoted accounts will auto-recover (typically 30 min cooldown)
- Avoid running too many concurrent requests through antigravity at once

## Notes
- Also set `settings.requireLogin = false` in SQLite to allow remote API access (middleware was blocking external curl tests)
- Internal routing (Hermes, other services) works regardless of this middleware setting
- The 9Router server must be restarted after DB changes to pick up new priorities