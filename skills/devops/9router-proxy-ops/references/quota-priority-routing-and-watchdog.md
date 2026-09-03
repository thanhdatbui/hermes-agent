# 9Router Quota Priority Routing & Watchdog Architecture

## Architecture Overview
In 9Router (`:20128`), multi-account load balancing selects active connections ordered by `priority ASC` (lower number = higher priority).

### 1. Account-Level Priority Routing by Quota (Sticky & Rotation Lifecycle)
Rather than auto-disabling exhausted accounts or applying per-model lockouts (`modelLock_*`), accounts remain active (`isActive = 1`) and follow a sticky rotation lifecycle:
- **Sticky Single-Account In-Use (Priority 1..99):** The top-priority account is used **exclusively** for all incoming requests. As quota depletes (> 0%), its priority is **NOT** modified or swapped so requests stay locked to that single account.
- **Exhaustion Demotion (0% Quota / 429):** When an account hits 0% quota or receives a 429 upstream error, it is demoted to `priority: 9999` (bottom of queue). 9Router immediately falls through to the next active account (`priority: 2, 3...`).
- **Quota Recovery Promotion (> 0% Quota):** When an account's quota resets/recovers (remaining > 0%) and its current priority is `9999`, it is promoted to `priority: 100`. This places it at the tail of the available pool waiting in line, ensuring it **does not interrupt or preempt the account currently in active use**, while remaining ahead of any exhausted `9999` accounts.
- **Antigravity:** Quota evaluation checks remaining percentage of Gemini models.
- **Codex:** Quota evaluation checks remaining percentage across Codex quota metrics.

### 2. Server-Side Real-Time Auto-Demotion (`.next-cli-build/server/chunks/2283.js`)
Client-side quota refresh only syncs when the dashboard is opened. To ensure real-time failover during live traffic:
- In `server/chunks/2283.js` inside error fallback function `l(a, b, c, e=null, j=null, k=null)` (where `a` = connectionId, `b` = status code, `c` = error body):
  ```javascript
  if (429 === Number(b) || String(c || "").toLowerCase().includes("quota")) {
    try {
      await (0, d.updateProviderConnection)(a, {
        priority: 9999,
        updatedAt: new Date().toISOString(),
      });
    } catch (e) {}
  }
  ```
- This ensures that when an in-flight request hits 429, the exhausted account immediately drops to `#9999` in SQLite, and the next incoming request automatically selects the next available account (`priority: 2, 3...`) with zero user intervention.

### 3. Client Quota Page Bundle Patch (`dashboard/quota/page-*.js`)
In `.next-cli-build/static/chunks/app/(dashboard)/dashboard/quota/page-*.js`:
- `E0(quotas, provider)`: Returns `true` if exhausted (remaining <= 0), `false` if has quota (> 0), or `null` if no quota metrics.
  - If `provider === 'antigravity'`: filters specifically for `gemini` models.
  - If `provider === 'codex'` or others: checks across active quota entries.
- In `eB(e, t)` (quota refresh callback):
  - If exhausted (`E0 === true`): `PUT /api/providers/:id` with `{ priority: 9999 }`.
  - If recovered (`E0 === false`): queries current priority via `GET /api/providers/:id`; if `priority >= 9999`, executes `PUT /api/providers/:id` with `{ priority: 100 }`. If priority is already < 9999 (currently in active rotation), leaves it untouched.

### 4. Server-Side Model Lock & Cooldown Suppression
9Router server builds (`.next-cli-build/server/chunks/*.js` and `server/app/api/**/route.js`) contain duplicate error classifier modules (`12557`):
- `function j(a, b)`: Selector predicate checking `modelLock_<model>` or `modelLock___all`. Must return `false` to prevent excluding accounts on 429.
- `function l(a, b)`: Lock generator function. Must return `{}` (noop) to prevent saving cooldown timestamps.

### 5. PowerShell Watchdog & `quota_manager.py` Pitfall
**Critical Pitfall:** `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1` runs a 10s supervisory loop.
- It previously executed `C:\Users\Kibe\AppData\Roaming\9router\quota_manager.py`, which inspected `errorCode == 429` / `lastError` and wrote `modelLock_gemini_*` directly into SQLite `providerConnections.data` and `kv (scope='quota_cooldown')`.
- Even if server bundle code is patched, the watchdog will continuously re-inject `modelLock_*` every 10s unless:
  1. The watchdog call in `9router_watchdog.ps1` is removed.
  2. `quota_manager.py` `run()` is set to return 0 (disabled).
  3. The watchdog PowerShell process is restarted to load the updated script.
  4. Existing `modelLock_*` entries in `providerConnections.data` and `kv` rows with `scope='quota_cooldown'` are cleaned up via SQLite.

### 6. Verification Checklist
- `SELECT email, isActive, priority, data FROM providerConnections WHERE provider IN ('antigravity', 'codex') ORDER BY priority;`
- Ensure `modelLock_*` is empty for all accounts.
- Ensure all accounts have `isActive = 1`.
- Verify port `20128` listener is running and watchdog supervisor is active without invoking `quota_manager.py`.
