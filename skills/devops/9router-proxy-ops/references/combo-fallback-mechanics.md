# Combo fallback mechanics — decompiled (verified 2026-08-14)

Root-cause work for "vẫn để opencode lên đầu nhưng fail nó nhảy qua cái khác liền".
Decompiled from `C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\.next-cli-build\server\chunks\*.js`.

## Source map (where the logic lives)

| Chunk | Module | What |
|---|---|---|
| `8910.js` (16KB) | module 18910, export `Pr` | combo resolution **loop**: `Trying model N/M` → call → `succeeded`/`failed, trying next`; also fusion path |
| `112.js` (19KB) | — | combo **caller**: logs `Combo "X" with N models (strategy: Y, sticky: Z)`; reads `settings.comboStrategy` + `comboStickyRoundRobinLimit`; also capacity-adapter routing + account rotation |
| `3350.js` / `6832.js` (identical) | module 12557 `hk`, module 3662 `t2`/`EQ` | fallback decision table |
| `3212.js` (10KB) | — | per-connection fallback (`shouldFallback` from `d.vk`) |
| `app/src/` | — | ONLY CLI UI (terminalUI.js, cli/api/client.js 30s timeout) — proxy logic is NOT here |

`src/` is a red herring for proxy logic. Grep the `.next-cli-build/server/chunks/` files instead.
Python reading these files: **use Windows paths** (`C:\Users\...`), MSYS `/c/Users/...` paths fail in `python -c`.

## The fallback decision — `hk(status, errorMessage)` ALWAYS falls back

module 12557 in `3350.js`:

```js
function e(a, b, c = 0) {   // a=status, b=error message, c=backoffLevel
  let f = (b ? (typeof b === "string" ? b : JSON.stringify(b)) : "").toLowerCase();
  for (let b of d.t2)       // d = module 3662, t2 = pattern table
    if (b.text && f.includes(b.text) || b.status && b.status === a) {
      if (b.backoff) { ... return {shouldFallback: !0, cooldownMs: fn, newBackoffLevel: ...}; }
      return {shouldFallback: !0, cooldownMs: b.cooldownMs};
    }
  return {shouldFallback: !0, cooldownMs: d.wf};   // default ALSO falls back
}
```

**There is NO branch returning `shouldFallback: false`.** Every status/error → fallback to next combo model.
`t2` table (module 3662): `{text:"no credentials",cooldownMs:12e4}`, `{text:"request not allowed",5e3}`,
`{text:"improperly formed request",12e4}`, `{text:"rate limit",backoff:true}`, `{text:"too many requests",backoff:true}`,
`{text:"quota exceeded",backoff:true}`, `{text:"capacity",backoff:true}`, `{text:"overloaded",backoff:true}`,
`{status:401|402|403|404,cooldownMs:12e4}`, `{status:429,backoff:true}`. Backoff = exponential: base 2s, max 300s, maxLevel 15 (`EQ`).

`cooldownMs` is only actually *waited* for **502/503/504** (`j>0 && j<=5000 && (503||502||504) → await setTimeout`).
429/401/403 → no wait, next model tried immediately.

**524/529 PATCH (2026-08-15, vendor build):** added
`{status:524,cooldownMs:15e3},{status:529,cooldownMs:15e3}` to the `t2` table
(35 files, backups `.bak-524patch`). Default branch already falls back on any
status, but 524/529 otherwise mark the account `testStatus:unavailable` + 30-min
`modelLock_` → combo skips that acc/model long-term. The patch gives 524/529 a
short 15s cooldown instead. **MẤT khi `npm i -g 9router`** — re-patch:
`references/commandcode-524-fallback-patch.md`.

## Combo loop (module 18910 in 8910.js)

```js
for (let b = 0; b < o.length; b++) {
  let e = o[b];
  g.info("COMBO", `Trying model ${b+1}/${o.length}: ${e}`);
  try {
    let b = await c(a, e);
    if (b.ok) return g.info("COMBO", `Model ${e} succeeded`), b;
    ... parse error message + retryAfter ...
    let {shouldFallback:i, cooldownMs:j} = (0,d.hk)(b.status, f);
    if (!i) return ..."failed (no fallback)"...;   // unreachable in practice
    ... wait only for 502/503/504 ...
    g.warn("COMBO", `Model ${e} failed, trying next`, {status:b.status});  // → b++ → next model
  } catch ...
}
// exhausted → "All models failed" with the LAST error message + status
```

## Sticky / strategy semantics (from profile page UI text + 112.js)

- `settings.comboStrategy`: `"fallback"` (default) | `"round-robin"` | `"fusion"`.
- UI text (authoritative): **`"round-robin"===comboStrategy ? "Combos rotate after N calls per model" : "Combos always start with their first model."`**
- `settings.comboStickyRoundRobinLimit` (default 1, UI min 1 max 100, label "Calls per combo model before switching"): **only meaningful for round-robin**. With `fallback`, every request starts at model 1 — sticky does NOT remember a previous failure.
- Both keys are PATCHable: `PATCH /api/settings` with `{"comboStickyRoundRobinLimit": N}` / `{"comboStrategy": "round-robin"}` (cookie auth). Changing them triggers combo reload (`UP()`).

## The real reason "fail không nhảy liền" (4-min stalls)

Decompiled code says fallback ALWAYS advances. `server.log` confirms it works:
`Trying model 1/4`=1562, `2/4`=1405, `3/4`=388 (fallback fires constantly when head models fail).

The observed ~257-283s (≈4.3 min) fixed latency is **NOT** 9router waiting — it's **Hermes retry storm**:
1. Combo head models are all the SAME free ecosystem (`oc/deepseek-v4-flash-free` 429 + `oc/hy3-free` 502) → whole chain head fails → 9router returns 429 to Hermes.
2. Hermes `api_max_retries: 8` + `jittered_backoff` (2s→60s) retries up to 8×.
3. **Each Hermes retry is a NEW request → combo resets to model 1** (`strategy: fallback` always starts at model 1) → 429 again → loop. 8 × (chain walk + backoff) ≈ 4 minutes.
4. `[AUTH] ... locked modelLock_<model> for 1800s [429]` — 9router also locks the model 30 min after 429, but that only skips it on *later* requests; the current retry still hits it.

**Fix directions (combo-level):**
- Model 2 right after the free head MUST be a **different provider pool** (e.g. `cmc/deepseek/deepseek-v4-flash`), not another free model — so a free-tier outage falls straight to commandcode instead of failing the whole chain.
- Keep free models OUT of positions 2-3 when they share the upstream quota bucket (hy3-free 502s while deepseek-free 429s = same ecosystem outage).
- Reduce Hermes `agent.api_max_retries` (8 → 2-3) — the combo already falls back; Hermes retrying 8× multiplies the stall.
- User's own fix on 2026-08-14 09:46: put `cmc` FIRST → 968 requests, 0 opencode hits, med latency 6.3s vs 24.7s (oc-first). That is the "fast" config; "oc-first but fail fast" = the chain above + retries=2-3.

## server.log — the FULL persistent log (key discovery)

`C:\Users\Kibe\AppData\Roaming\9router\logs\server.log` (5MB+, keeps days of history) contains EVERYTHING the console-log API truncates (console-log API = last ~200 lines only). Same `[COMBO] ...` / `[PROXY] ...` / `[AUTH] ...` lines, timestamps = local VN time. This is the go-to source for combo fallback forensics across time windows:
- `grep -E "Trying model [0-9]+/[0-9]+" server.log | sort | uniq -c | sort -rn` → fallback frequency per position.
- `grep -E "COMBO.*(failed|trying next|no fallback)" server.log` → failure reasons per model.
- Interleaved `Trying model 1/12` twice in the same second = two DIFFERENT requests (Hermes retry), NOT one request re-trying model 1.
