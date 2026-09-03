# commandcode ("cmc/deepseek/deepseek-v4-flash") via 9router — "weird error" diagnosis

Verified 2026-08-13 when the user reported "command code qua 9router bị trả lỗi gì lạ lắm".
Root cause was NOT commandcode — it was the combo fallback chain + a dead proxy pool.

## 1. Isolate: commandcode itself is HEALTHY

`cmc/deepseek/deepseek-v4-flash` (provider `commandcode`) returns **HTTP 200** both with
`stream:false` and `stream:true` + heavy payload. Verified live twice:

```js
const r = await fetch('http://localhost:20128/v1/chat/completions', {
  method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},
  body: JSON.stringify({model:'cmc/deepseek/deepseek-v4-flash', stream:true,
    messages:[{role:'user',content:'Explain recursion in 2 sentences.'}], max_tokens:200})
});
// 200, ~2.4s, 45 chunks, finish_reason:"stop"  ← route is fine
```

So if the user "calls commandcode" and gets an error, EITHER they're calling it **through the
`deepseek-v4-flash` combo** (and seeing the combo's upstream errors), OR the error is
combo/proxy-layer, not commandcode.

## 2. The "weird error" = combo fallback chain (live 2026-08-13)

Combo `deepseek-v4-flash` now resolves to **4 models** (verified in Console Log: `Trying model N/4`):
`oc/deepseek-v4-flash-free` -> `oc/hy3-free` -> `cmc/deepseek/deepseek-v4-flash` -> (4th, `cx/gpt-5.6-luna` or `cx/gpt-5.6-sol`).
The errors the user sees come from models 1-2, not commandcode (model 3):

| # | Model | Live result | Symptom user perceives |
|---|---|---|---|
| 1 | `oc/deepseek-v4-flash-free` | X **429** `FreeUsageLimitError` (every ~2s) | "429 liên tục" |
| 2 | `oc/hy3-free` | X **502 `fetch connect timeout`** after **~249s (4 min) HANG** | the "lạ" one - a 502 after 4 minutes |
| 3 | `cmc/deepseek/deepseek-v4-flash` | OK 200 (only reached AFTER the 4-min hy3 hang) | actually serves, but only after a long wait |
| 4 | `cx/gpt-5.6-luna`/`sol` | (fallback if cmc also fails) | - |

**PITFALL - `oc/hy3-free` is a 4-minute trap.** It does NOT fail fast; it hangs ~249s then
returns `502 [502]: fetch connect timeout Error: fetch connect timeout`. If hy3-free sits at
position 2 of the combo, EVERY request waits ~4 minutes before falling through to commandcode.
If the user's client has a shorter timeout, they see a client-side timeout/error that *looks*
like a commandcode failure but is really the hy3-free hang upstream.

Fix options:
- Move `cmc/deepseek/deepseek-v4-flash` to **position 1** (or position 2 after `oc/deepseek-v4-flash-free`)
  so the working model is reached without the 4-min hy3 wait.
- Remove `oc/hy3-free` from the combo (or push it to the very end) until its upstream is fixed.
- Use the dashboard API (cookie auth) to edit the combo - see `references/dashboard-api-and-combos.md`.

## 3. Dead Proxy Pool diagnostic (root of `[ProxyFetch] Proxy failed`)

Recurring log line: `[ProxyFetch] Proxy failed, falling back to direct: fetch connect timeout`
(appears 2-3x per combo cycle). Confirm the cause on the **Proxy Pools** page
(`/dashboard/proxy-pools`, sidebar):

- 42 pools listed, **all `active`** but **`Last tested: Never`**, type **`unknown`**, **`0 bound`**.
- These pools were never connectivity-tested -> 9Router cannot connect through any of them ->
  it falls back to **direct** (which works). The proxy pool being dead is NOT fatal (direct works),
  but it adds the `ProxyFetch failed` noise and a small latency hit on every request.

The error string `fetch connect timeout` with NO upstream URL in the message = the **proxy itself**
is unreachable (egress connect timeout), distinct from a provider 429/502. Don't conflate the two.

Fix: either add working proxies (then test them so `Last tested` updates) or accept direct mode
(the fallback already works). Buried/never-tested pools just mean "proxy layer unused."

## 4. Quick triage checklist when user says "command code lỗi lạ"

1. Test `cmc/deepseek/deepseek-v4-flash` directly (S1) - if 200, commandcode is fine.
2. Open Console Log, **Clear** it, then trigger one combo call; read the chain (S2) - count which
   model actually errors (usually oc-free 429 / hy3-free 502-timeout, NOT cmc).
3. Check Proxy Pools page (S3) - 42 "never tested" pools => dead proxy layer, benign fallback to direct.
4. Conclude: the "weird error" is almost always the **hy3-free 249s hang** + **opencode-free 429**
   in the combo, plus the dead proxy pool noise - none of it is commandcode logic.
