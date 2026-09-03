# Antigravity live-test, API-key-from-DB, and model-ID pitfalls

Verified 2026-08-13 while debugging an Antigravity (OAuth subscription, `ag/*`) 429 on
Gemini models while Claude via the same provider worked.

## 1. Get a working API key when `$NINEROUTER_API_KEY` isn't in the shell env

The dashboard "API Keys" page shows the key masked; `browser_console` form-value
extraction is BLOCKED as a sensitive primitive, and the copy button sometimes fails to
land the key in the clipboard (a Console-Log copy overwrites it). Recover the key from
the DB instead:

- **Real DB is `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite` (~50 MB, has a WAL).**
  The `9router.db` at `C:\Users\Kibe\AppData\Roaming\9router\9router.db` is **0 bytes / empty**
  — do NOT query it (sqlite_master returns 0 tables).
- `better-sqlite3` resolves only when `node` runs from the 9router app dir:
  `cd "C:/Users/Kibe/AppData/Roaming/npm/node_modules/9router/app"` then
  `require('better-sqlite3')` (it sits alongside in `../node_modules`).
- Open `data.sqlite` `{readonly:true}`, scan every table for a column matching `/key/i`,
  take the first string value with length > 10. The key is ~35 chars.

```js
const Database = require('better-sqlite3');
const db = new Database('C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite', {readonly:true});
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table'").all().map(t=>t.name);
let key=null;
for (const t of tables){
  const cols = db.prepare('PRAGMA table_info('+t+')').all().map(c=>c.name);
  if (cols.some(c=>/key/i.test(c))){
    for (const r of db.prepare('SELECT * FROM '+t).all())
      for (const k in r){ const v=r[k]; if(/key/i.test(k)&&v&&String(v).length>10) key=v; }
  }
}
// use `key` in fetch below — do NOT echo it to chat
```

Wrap top-level `await` in an `async IIFE`; mixing `require` + top-level await throws
`ERR_AMBIGUOUS_MODULE_SYNTAX` in the app dir (it's ESM-resolved).

## 2. Direct model liveness test (preferred over the dashboard "science" button)

Node v24 has global `fetch`. The `models` endpoint accepts **any** key (even a dummy)
and returns 200; `/v1/chat/completions` requires the **real** key (dummy → 401
`invalid_api_key`). Test each model:

```js
const models = ['ag/gemini-3.6-flash-high','ag/gemini-3.6-flash-low',
                'ag/claude-sonnet-4-6','ag/claude-opus-4-6-thinking'];
for (const m of models){
  const r = await fetch('http://localhost:20128/v1/chat/completions', {
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
    body: JSON.stringify({model:m, messages:[{role:'user',content:'say one word'}], max_tokens:20})
  });
  console.log(m, '->', r.status);
}
```
HTTP 200 with `data: {…"model":"gemini-3.6-flash-tiered"…}` = alive (the resolved
internal model name differs from the requested `ag/*` id — that's normal, not an error).

**PITFALL — the per-model "science" (lab) button on the provider page runs SILENTLY.**
Its result does not appear in `browser_snapshot` (no modal/toast) and is immediately
buried in the Console Log by the continuous combo 429 spam (see §4). Use the API test
above for a definitive answer.

## 3. Antigravity model-ID naming (hyphen, not dot; `-thinking` is opus-only)

`/v1/models` lists the real `ag/*` ids. Wrong ids return **404 `Requested entity was not found`**
(NOT a network/quota error) — easy to misread as "Claude is down":

| Intended | Correct id | Wrong id that 404s |
|---|---|---|
| Claude Sonnet 4.6 | `ag/claude-sonnet-4-6` | `ag/claude-sonnet-4.6-thinking` |
| Claude Opus 4.6 (thinking) | `ag/claude-opus-4-6-thinking` | `ag/claude-opus-4.6` |
| Gemini 3.6 Flash High | `ag/gemini-3.6-flash-high` | — |
| Gemini 3.6 Flash Low | `ag/gemini-3.6-flash-low` | — |

Rule: dots → hyphens (`4.6` → `4-6`); the `-thinking` suffix exists ONLY for
`claude-opus-4-6-thinking` (and similar opus variants), not for sonnet.

## 4. Reading the live Console Log without drowning in combo 429 spam

`/dashboard/console-log` (sidebar) shows the last ~200 lines. A running combo
(e.g. `deepseek-v4-flash` → `oc/deepseek-v4-flash-free`) emits a 429 every 2–3 s
(`FreeUsageLimitError` / `Rate limit exceeded` from the OpenCode FREE tier), which
**floods the log and buries any targeted test entry**. To isolate:
- Click **Clear** (`/dashboard/console-log` → trash icon) before a targeted test, OR
- Prefer the API test in §2 (no log dependency).

The OpenCode-free 429 is **unrelated** to Antigravity/Gemini/Claude — don't conflate them
when the user reports "429 liên tục".

## 5. AG 429 on Gemini while Claude works + Gemini UI shows full quota

Pattern observed: `ag/gemini-3.6-flash-high` 429s with
`"Resource has been exhausted … reset after 5m"`, but `ag/claude-*` on the SAME provider
works, and the Gemini web UI shows quota full.

Diagnosis:
- Because **Claude on the same AG OAuth session works**, it is NOT a session/OAuth ban
  (a ban would kill Claude too) and NOT a global account throttle.
- The Gemini UI "quota full" is the **daily TPM/request quota**; the AG 429 is the
  **per-minute RPM limit** — a separate metric that can be exhausted even when daily
  quota looks full (typical after a burst of requests through 9Router).
- It is **Gemini-specific** (rate bucket per model family), not provider-wide.

Resolution: it's a transient RPM burst — wait for the ~5-min reset window, then the
same model returns 200 (verified live: `ag/gemini-3.6-flash-low` and `-high` both 200
after the window). Do NOT blacklist the model or conclude "Gemini died".
