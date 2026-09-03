# 9Router update & auto-restart mechanics (verified 2026-08-15, v0.5.50)

## How 9router starts on this machine

- `Startup\9router.vbs` → `npm\9router.cmd --bg`
- `9router.cmd` `--bg` branch runs `node server.js` inside an **infinite `:loop`**
  with a **30s** `timeout` between restarts (raised from 2s on 2026-08-15 so the
  in-UI updater's 3–15s wait finds the port free and npm doesn't race file locks;
  applies from the NEXT start of the loop); stdout/stderr appended to
  `%APPDATA%\9router\logs\server.log`.
- Consequence: the app always comes back on its own after a crash (2s delay).

## What the in-UI updater does (app/src/lib/updater/updater.js)

1. Spawns a detached updater process (survives app exit) serving status on :20129.
2. Waits for app port :20128 to free: min 3s hard delay, polls up to max 15s.
3. Runs `npm i -g 9router --prefer-online`, retry ×3 with 5s delay.
4. Relaunches app **only if** env `UPDATER_RELAUNCH=1` + `UPDATER_RELAUNCH_CMD`
   were set at app start. Plain `9router.cmd --bg` does NOT set them — but the
   `:loop` restarts the app anyway.

## The race that makes UI updates flaky on Windows

- Loop now restarts app after ~30s; updater's patience is only 3–15s → app stays
  down across the npm install window (no EBUSY race).
- Old behavior (2s restart) made `npm i -g` hit EBUSY file-lock
  (node.exe holding files) → install fails → retries → may end up still on old
  version while UI claims an attempt.
- **Manual update is the reliable path:**
  1. `taskkill /f /im node.exe` (only when nothing else on the box needs node)
  2. `npm i -g 9router@latest`
  3. `C:\Users\Kibe\AppData\Roaming\npm\9router.cmd --bg`
- Don't update mid-live-batch: Hermes loses :20128 for ~1–2 min and requests
  fail/retry during that window. Once the port is back, Hermes works again —
  **no gateway restart needed**.

## Error classifier (0.5.50) — what triggers fallback/backoff

Trigger list (status or message):
- status: 400, 401, 402, 403, 404, 406, 429, 500, 502, 503, 504
- message contains: `no credentials`, `request not allowed`, `improperly formed
  request`, `rate limit`, `too many requests`, `quota exceeded`, `capacity`,
  `overloaded`

Behavior:
- Backoff: base 2000ms → max 300000ms (maxLevel 15) for rate-limit-class errors.
- Cooldown 120s for 401/402/403/404.
- **NO auto-disable of a dead account** — it keeps retrying forever (every ≤5 min).

## The 524 gap (why "Gateway request failed" sticks)

- `statusCode 524` / `"Invalid error response format: Gateway request failed"` is
  NOT in the trigger list → no combo/account fallback → error passes straight to
  the caller (Hermes sees `[CommandCode error: ... 524 ... isRetryable:true]`).
- CommandCode's `isRetryable:true` flag is never read by 9router.
- 524 is a Cloudflare timeout on CommandCode's side (their server hung), not an
  account problem → switching account/connection does NOT help.
- **PATCHED 2026-08-15 on this machine** (0.5.50 & 0.5.55 both lack it upstream):
  `{status:524,cooldownMs:15e3},{status:529,cooldownMs:15e3}` added to the
  trigger list in 35 build files → combo skips to next model ~15s after 524/529.
  Details + re-patch after every npm update:
  `references/commandcode-524-fallback-patch.md`.
