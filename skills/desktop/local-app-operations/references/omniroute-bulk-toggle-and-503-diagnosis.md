# OmniRoute Provider Bulk-Toggle Incident & Cluster 503 Upstream Diagnosis

## 1. Incident Signature & Root Cause

When multiple LLM accounts in a provider pool (e.g. Antigravity Pro accounts in `ag-gemini-pool-3`) suddenly become inactive simultaneously, causing widespread `HTTP 503` upstream failures:

- **Root Cause (UI Master Toggle)**: On the OmniRoute `/dashboard/providers` page, each provider group card (such as the Antigravity IDE / OAuth card rendered by `HighlightableProviderCard`) has a master toggle switch.
- **Mechanism**: Toggling this master switch triggers `handleToggleProvider(providerId, toggleAuthType, active)` in `src/app/(dashboard)/dashboard/providers/page.tsx`:
  ```typescript
  const providerConns = connections.filter(matchesToggle);
  await Promise.allSettled(
    providerConns.map((c) =>
      fetch(`/api/providers/${c.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isActive: newActive }),
      })
    )
  );
  ```
  This fires parallel `PUT /api/providers/<id>` updates across **all** connections for that provider, flipping 20–30 accounts in under 1 second.
- **Accidental Trigger**: Operators clicking the provider card or testing toggles can inadvertently turn off the entire fleet instead of a single connection.

---

## 2. Audit Log Forensics (`storage.sqlite`)

Do NOT guess whether accounts died from OAuth token revocation (`invalid_grant`), cron jobs, or UI actions. Inspect the authoritative SQLite database:

- **Database path**: `C:\Users\Kibe\.omniroute\storage.sqlite`
- **Audit Table**: `audit_log` (columns: `id`, `timestamp`, `action`, `actor`, `details`, `ip_address`)

### Investigation Query
```python
import sqlite3, json

conn = sqlite3.connect(r'C:\Users\Kibe\.omniroute\storage.sqlite')
c = conn.cursor()
c.execute('''
    SELECT id, timestamp, action, actor, ip_address, details 
    FROM audit_log 
    WHERE action = 'provider.credentials.updated' 
    ORDER BY id DESC LIMIT 50
''')
for r in c.fetchall():
    d = json.loads(r[5])
    print(r[0], r[1], r[3], r[4], d.get('before', {}).get('name'), d.get('changedFields'), d.get('before', {}).get('isActive'), '->', d.get('after', {}).get('isActive'))
conn.close()
```

### Forensic Signatures
| Signature | Cause |
|---|---|
| 20-30 rows within 1-2 seconds, `actor: "admin"`, `changedFields: ["isActive"]`, IP `127.0.0.1` or LAN | **UI Master Toggle on `/dashboard/providers`** |
| Single row, `action: "provider.credentials.updated"`, IP from specific tool | Targeted script or single card toggle |
| `testStatus: "expired"`, `lastErrorType: "unrecoverable_refresh_error"` | True OAuth token revocation by Google upstream |
| `actor: "system"`, `action: "provider.warning"` | Runtime health check / admission error |

---

## 3. Why 503 Cascades Occur After Fleet Inactivation

1. **Target Starvation**: Combo models (e.g. `ag-gemini-pool-3`) distribute traffic across pinned `connectionId` targets. When 16+ accounts are inactive, remaining accounts quickly hit concurrency caps (`maxConcurrent`).
2. **Heavy Payload Queue Saturation**: Heavy agent requests (200k–300k prompt tokens) consume the global admission budget (`OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT`). Inbound requests queue up; if queue time exceeds `OMNIROUTE_CHAT_ADMISSION_QUEUE_MS` (120s), OmniRoute returns `503`.
3. **Proxy Fast-Fail**: If local proxy ports (`http://test.taadaa.click:<port>`) drop or return 407/timeout, OmniRoute logs `[Proxy Fast-Fail] Proxy unreachable: ...` and fails closed immediately, reporting `503` upstream.

---

## 4. Instant O(1) Fleet Remediation

To immediately restore all Pro accounts without clicking dozens of cards in the UI:

```python
import requests

r = requests.get('http://127.0.0.1:20129/api/providers').json()
conns = [c for c in r.get('connections', []) if c.get('provider') == 'antigravity']
pro_accs = [c for c in conns if 'pro' in str((c.get('providerSpecificData') or {}).get('tier') or '').lower()]

inactive_pro = [c for c in pro_accs if not c.get('isActive')]
print(f'Re-activating {len(inactive_pro)} Pro accounts...')

for c in inactive_pro:
    cid = c['id']
    email = c.get('email') or c.get('name')
    res = requests.put(f'http://127.0.0.1:20129/api/providers/{cid}', json={'isActive': True}, timeout=10)
    print(f'  {email} -> {res.status_code}')
```

Verify restoration:
1. Check active count: `requests.get('http://127.0.0.1:20129/api/providers')` -> confirms `Total Pro == Active Pro`.
2. Canary request: send a lightweight request to `http://127.0.0.1:20129/v1/chat/completions` with the target combo alias (`ag-gemini-pool-3`) to confirm 200 OK.
