# Antigravity & Codex Quota Priority & UI Ordering Architecture

## 1. Antigravity Dual Quota Architecture
Antigravity accounts in 9Router track two independent quota pools:
1. **Google Gemini Pool**: `gemini-3.7-flash-*`, `gemini-3.6-flash-*`, `gemini-3.5-flash-*`, `gemini-3.1-pro-*` (typically reset on a multi-day rolling cycle, e.g. 3-4 days).
2. **Anthropic & OpenAI Pool**: `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium` (typically reset on a short cycle, e.g. 3-5 hours).

### Quota Exhaustion Detection (`E0` in client)
* In the quota dashboard client (`dashboard/quota/page-*.js`), `E0(quotas, 'antigravity')` isolates Gemini models:
  ```javascript
  if ('antigravity' === p) {
    let r = t.filter(e => String(e?.modelKey || e?.name || '').toLowerCase().includes('gemini'));
    if (r.length > 0) t = r;
  }
  ```
* When all Gemini quotas have `remainingPercentage <= 0` or `used >= total`, `E0` evaluates to `true` (exhausted).
* When exhausted, the client calls `PUT /api/providers/:id` with `{ priority: 9999 }`.
* When restored, it updates `{ priority: 100 }`.

## 2. Quota Tracker UI Card Sorting vs. DB Priority
The order of account cards on `http://localhost:20128/dashboard/quota` depends on UI filters:
* **`Expiring first` Toggle**:
  Sorts cards by `min(resetAt)` across ALL models on the account:
  ```javascript
  let s = e => {
    let r = (t[e.id]?.quotas || []).map(e => e.resetAt ? new Date(e.resetAt).getTime() : Infinity).filter(e => Number.isFinite(e));
    return r.length > 0 ? Math.min(...r) : Infinity;
  };
  ```
  * *Pitfall*: An account with 0% Gemini (resets in 4 days) and 97% Claude (resets in 3h 30m) will have `min(resetAt) = 3h 30m`. It will appear before an account whose Gemini resets in 3h 50m, even though its Gemini quota is dead.
* **Default Mode (No filter)**: Displays providers grouped by provider type and connection creation order.

## 3. Server-side Request Selection & Reordering
* **Account Selection (`2283.js`)**: Sorted by `(a.priority || 999) - (b.priority || 999)`.
* **Sequential Reordering Pitfall (`4884.js` & `middleware.js` in `l(a, b)` / `reorderProviderConnections`)**:
  When `reorderProviderConnections` or priority updates run, the default sequential renumbering was:
  ```javascript
  // OLD problematic behavior:
  c.forEach((b, idx) => a.run("UPDATE providerConnections SET priority = ? WHERE id = ?", [idx + 1, b.id]));
  ```
  This turned `9999` into `5` or `6`.
  * **Fix / Patch Applied**: Keep priority `>= 9000` untouched during sequential re-indexing:
  ```javascript
  c.forEach((b, c) => {
    let p = (b.priority >= 9000) ? b.priority : (c + 1);
    a.run("UPDATE providerConnections SET priority = ? WHERE id = ?", [p, b.id]);
  });
  ```
* **Quota Tracker Default Card Sorting Patch**:
  Patched client `page-*.js` to sort cards by ascending priority `(a.priority || 999) - (b.priority || 999)` when `Expiring first` is turned OFF.
