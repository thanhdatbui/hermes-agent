# OmniRoute Provider Bulk-Toggle Incident & Cluster 503 Upstream Diagnosis

## 1. Incident Signatures: UI Bulk-Toggle vs Automation Test Isolation Timeout (Dual Causality)

When multiple LLM accounts in a provider pool (e.g. Antigravity Pro accounts in `ag-gemini-pool-3`) suddenly become inactive simultaneously, causing widespread `HTTP 503` upstream failures:

There are TWO distinct mechanisms that produce identical audit log footprints (20–30 simultaneous deactivations from `127.0.0.1`):

### Mechanism A: Automation Shell Timeout in `isolated_chat_test` (CRITICAL ROOT CAUSE)
- **The Code**: Scripts designed to test a single account in isolation (e.g. `isolated_chat_test` in `vm_rescue_lib.py`) iterate over all active connections, set them `isActive: False`, enable only the target account, and attempt to restore them in a `try...finally` block:
  ```python
  active_before = [c["id"] for c in conns if c.get("isActive")]
  try:
      for cid in active_before:
          set_active(cid, False)
      set_active(connection_id, True)
      # perform test HTTP call...
  finally:
      set_active(connection_id, False)
      for cid in active_before:
          set_active(cid, True)
  ```
- **The Fatal Flaw (Subprocess Hard-Kill / SIGKILL)**: When an agent or operator runs this script inside a shell/terminal with an execution timeout (e.g. `terminal(timeout=35)`):
  1. The script deactivates all 30 active accounts via `PUT /api/providers/<id> { isActive: false }`.
  2. If the upstream provider request stalls or times out (e.g. Google Cloud Code API latency), the outer terminal runner forcibly terminates the process (`exit code 124` / `taskkill /F`).
  3. **Python's `finally:` block NEVER executes on SIGKILL**.
  4. The target account or the entire fleet remains permanently trapped in `isActive: False` in the database!
- **Signature of `isolated_chat_test`**:
  * First wave (e.g. 08:24:40 `True -> False` followed by 08:25:01 `False -> True`): a successful test run that restored state.
  * Second wave (e.g. 08:25:30 `True -> False` with NO restore): a second test run that stalled and was killed by timeout, leaving the pool dead.
  * Recent terminal history contains calls to `isolated_chat_test` or rescue scripts that exited with `code 124`.

### Mechanism B: UI Master Toggle / Touch Collision on `/dashboard/providers`
- **Root Cause**: On the OmniRoute `/dashboard/providers` page, each provider group card (such as the Antigravity IDE / OAuth card rendered by `HighlightableProviderCard`) has a master toggle switch.
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
- **Accidental Trigger / Touch Target Hazard**:
  * In `ProviderCard.tsx`, the entire card is wrapped in `<Link href="/dashboard/providers/${providerId}">`. Inside the card, the master toggle is nested directly in `<div onClick={handleToggle}><Toggle size="xs" checked={!allDisabled} /></div>`.
  * **Zero Confirmation Modal**: Unlike destructive actions, bulk toggling has no confirmation prompt.
  * **Touch/Click Target Collision**: On mobile devices (iOS Safari, Android Chrome) or desktop viewports, touches can easily hit the `size="xs"` toggle hit-box or trigger touch event bubbling.
  * **Operator Perceptions**: Operators will firmly state *"I never touched or disabled those accounts!"* — verify whether Mechanism A (subagent/script timeout) occurred in the session before accusing operator touch errors!

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
| Signature | Cause | How to Distinguish |
|---|---|---|
| 20-30 rows within 1-2s, `actor: "admin"`, `changedFields: ["isActive"]`, IP `127.0.0.1` | **Automation Test Isolation Timeout (`isolated_chat_test`)** | Check recent terminal/session logs for `isolated_chat_test` or rescue scripts that exited with `code 124` (SIGKILL). Script disabled fleet and died before `finally:` ran. |
| 20-30 rows within 1-2s, `actor: "admin"`, `changedFields: ["isActive"]`, IP LAN/mobile | **UI Master Toggle on `/dashboard/providers`** | Check client IP (e.g. `192.168.110.25`), no terminal test scripts active at that timestamp. Accidental touch/tap on card toggle. |
| Single row, `action: "provider.credentials.updated"`, IP from specific tool | Targeted script or single card toggle | Normal per-account toggle |
| `testStatus: "expired"`, `lastErrorType: "unrecoverable_refresh_error"` | True OAuth token revocation by Google upstream | Upstream token revoked, needs re-auth |
| `actor: "system"`, `action: "provider.warning"` | Runtime health check / admission error | Internal proxy warning |

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
