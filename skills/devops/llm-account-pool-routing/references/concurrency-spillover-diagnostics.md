# Concurrency Spillover Diagnostics for OmniRoute Priority Pools

## Pattern Observed: Priority Account Concurrency Spillover to Failing Accounts

When a priority-ordered pool has accounts with `max_concurrent` caps, high concurrency on early-priority accounts (P1–P14) causes spillover to later-priority accounts (P15–P18). If those later accounts have credential failures (403/revoked tokens), the entire pool reports "No active credentials" 404/502 errors even though early accounts are healthy.

### Diagnostic Query: Full Account Health + Concurrency State

```python
import sqlite3
conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute('''
  SELECT name, priority, is_active, test_status, error_code, last_error, last_error_at, last_error_type,
         backoff_level, rate_limited_until, last_used_at, max_concurrent, expires_at
  FROM provider_connections
  WHERE provider = 'antigravity'
  ORDER BY priority ASC
''')
for row in cursor.fetchall():
    print(row)
```

### Key Columns to Inspect

| Column | Purpose |
|--------|---------|
| `max_concurrent` | Capacity ceiling per account (8 for Pro, 3 for Starter) |
| `last_used_at` | Last successful inference call timestamp |
| `consecutive_use_count` | Sequential dispatches without rotation |
| `expires_at` | OAuth token expiry (critical for 403 diagnosis) |
| `backoff_level` / `rate_limited_until` | Active backoff state |

### Spillover Detection Logic

1. Count accounts with `last_used_at` within last N minutes → active concurrency
2. If active concurrency ≥ sum of `max_concurrent` for P1–P14 → spillover to P15+
3. Check P15+ for `test_status != 'active'` OR `expires_at` near/past now OR 403 in recent `call_logs`

### Remediation Options

| Option | When |
|--------|------|
| Re-login failing accounts (P15+) | Token revoked/expired (403 `invalid_grant`) |
| Temporarily `is_active = 0` for failing accounts | Need immediate stop to 404 pool errors |
| Increase `max_concurrent` on P1–P14 | If capacity genuinely insufficient |
| Add more healthy priority accounts | Long-term fix |

### Evidence from This Session (2026-09-03)

- P1–P14: `max_concurrent = 8`, healthy tokens, serving 200
- P15 (`phungthibichngoc`): 8, but 403 errors in logs
- P16 (`lamngocdiep`): 8, 403 errors
- P17 (`lequynh27032002`): 8, 403 errors
- P18 (`brittanysbarnes`): 3 (Starter), no recent errors

Pool errors: "No active credentials for provider: antigravity (+7/+9/+10 more)" = router tried all 18 accounts, all failed (because P1–P14 busy, P15–P17 failing, P18 alone insufficient).