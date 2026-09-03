# 9Router update + auto-restart mechanics (verified 2026-08-15)

## Updater flow (UI "Update" button) — read from `app/src/lib/updater/updater.js`

1. UI spawns a **detached** updater process (survives app death) exposing status on `:20129`.
2. Updater **waits for the app to exit** before running npm (Windows file-lock): hard min 3s,
   polls `:20128` until free, gives up at 15s and runs anyway (`proceeding anyway` → EBUSY risk).
3. Runs `npm i -g 9router --prefer-online`, retries up to 3× (5s apart).
4. `relaunchApp()` runs ONLY if the app was started with env `UPDATER_RELAUNCH=1` +
   `UPDATER_RELAUNCH_CMD` set. A manual/normal start does NOT set these → **app does not
   relaunch itself**; whatever wrapper the user uses must bring it back.

## User's auto-restart wrapper (this machine)

`C:\Users\Kibe\AppData\Roaming\npm\9router.cmd` (`--bg` mode) runs an infinite loop:

```bat
:loop
"C:\Program Files\nodejs\node.exe" --dns-result-order=ipv4first --max-old-space-size=6144 server.js >> "%APPDATA%\9router\logs\server.log" 2>&1
timeout /t 30 /nobreak >nul
goto loop
```

- Started at login via `Startup\9router.vbs` → `9router.cmd --bg` (window hidden, port 20128,
  host 0.0.0.0).
- **2026-08-15: raised `timeout` from 2s → 30s.** Reason: with 2s, the loop restarted the app
  ~8s before the updater's 3–15s port-free window expired → updater saw port busy, ran npm
  anyway → EBUSY/install-fail during UI update. 30s > 15s gives npm a clean window; app comes
  back on its own afterwards.
- A running loop keeps the OLD timeout until the wrapper is restarted — editing the .cmd only
  affects the NEXT launch.

## Update = planned downtime; don't do it mid-batch

- Update kills the app → `:20128` dead → every Hermes request through `custom:9router` fails
  (~30–60s+ depending on npm). Sessions recover automatically once the port is back; no
  gateway restart needed. Still: never update while farm batches / live sessions are running.

## 0.5.55 does NOT fix the 524 fallback gap (verified by diff)

- Published 2026-08-14. Error classifier byte-identical to 0.5.50
  (`app/.next-cli-build/server/app/api/combos/[id]/route.js` + chunk copies):
  same `base:2e3, max:3e5, maxLevel:15`, same status list
  (401/402/403/404/429 + text patterns `rate limit|too many requests|quota exceeded|capacity|overloaded`).
- No 524 / generic `>=500` handling → CommandCode 524 (`Invalid error response format:
  Gateway request failed`, Cloudflare timeout on their side) still does NOT trigger combo/account
  fallback. 9router also ignores the upstream `isRetryable: true` field.
- **PATCHED LOCALLY 2026-08-15** (see `references/commandcode-524-fallback-patch.md`):
  524/529 added to the trigger list in 35 build files → combo skips to next model.
  The patch lives in `node_modules` → **re-apply after every `npm i -g 9router` update.**
- **Before the patch existed**, the workaround was manual retry (524 is CommandCode-side
  overload, not the account — switching accounts does not help).

## How to re-verify a future version

```bash
npm pack 9router@<ver> --silent && tar -xzf 9router-<ver>.tgz
# diff the classifier between installed and packed:
#   app/.next-cli-build/server/app/api/combos/[id]/route.js
# grep for: base:2e3,max:3e5,maxLevel:15  |  status:401,cooldownMs:12e4  |  text:"quota exceeded",backoff:!0
grep -rn "524" package/app/.next-cli-build/server/chunks/ | grep -iv "524288\|buffer\|byteLength"
```

There is no CHANGELOG in the npm package/README — version diffs must be read from the
bundled `.next-cli-build` code.
