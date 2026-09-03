# Antigravity quota priority routing

## User policy

Use the simple account-priority policy. Do **not** auto-disable accounts and do **not** auto-lock models:

- Ranking is based specifically on **remaining Gemini quota**, not on whether the account has any unrelated quota such as Claude Sonnet.
- More remaining Gemini quota means a better account priority. Less remaining Gemini quota is pushed later. 9Router sorts ascending: lower `priority` wins.
- Keep every Antigravity account `isActive=true`. A quota refresh must never send `isActive:false`.
- Priority is account-level only. It does not guarantee that a Gemini request will avoid an account whose Gemini quota is exhausted but whose other model quota remains. Do not claim model-specific exclusion.
- Do not create, extend, or restore `modelLock_<model>` entries from quota refresh, 429 handling, or a watchdog. The operator chooses a different model when the available Gemini pool is exhausted.

## Ranking implementation

Antigravity quota rows normally contain `modelKey`, `used`, `total`, `remainingPercentage`, and `resetAt`. Select rows whose model key/name contains `gemini` and whose `total > 0`.

- Prefer `remainingPercentage`.
- Fall back to `remaining / total * 100`.
- Fall back to `(total - used) / total * 100`.
- Clamp each value to 0–100 and average the known Gemini rows for that account.
- Convert the score to priority with a descending-quota mapping such as `100000 - round(averageRemainingPercentage)`. Preserve a deterministic tie-break/order through the normal provider API.
- If no valid Gemini quota row exists, do not overwrite a previously known priority based on fabricated data; surface the refresh error or keep the existing order.

## Investigation and implementation recipe

1. Inspect the **served** installation, not only source. This installation may have no source repository; the runtime is commonly under `app/.next-cli-build/`.
2. Trace the whole path before editing: quota response → dashboard refresh handler → `PUT /api/providers/:id` priority update → provider selector → any server-side lock writer → external watchdog/scripts.
3. Search all `server/app/**/*.js` and `server/chunks/**/*.js`. Next.js route bundles can contain duplicate copies of the quota-lock helper; patching one shared chunk is insufficient.
4. Remove quota-refresh writes that set `isActive:false`. Replace the old group-only priority (`1` versus `9999`) with a Gemini remaining-quota ranking.
5. Disable every external auto-lock path. On Windows, inspect `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1` and `quota_manager.py`; the watchdog may call the manager every 10 seconds even when the Node bundle has been patched. Backup first, remove the watchdog call, and make the manager a no-op if it is retained for compatibility.
6. Remove stale `modelLock_*` fields only after stopping/isolating the writer, and remove only the scoped stale cooldown records. Keep `isActive=1`; make a DB backup before any direct SQLite cleanup.
7. Restart the actual supervisor/process so edited bundles are loaded. Verify the port and PID, then wait through at least one watchdog interval before checking the DB again.
8. Run `node --check` on every edited served bundle and `python -m py_compile` on any Python manager. Verify all of: priority ordering, all accounts active, no `modelLock_*` fields, no remaining watchdog manager call, and no lock regeneration after the observation window.

## Pitfalls and evidence gates

- A UI switch showing active/inactive is account state, not proof of model routing.
- A dashboard showing 0% does not prove a model lock exists; inspect the DB and server bundles.
- Patching only `server/chunks/2283.js` (or one route) is incomplete because settings, combo, usage, and translator route bundles can embed their own helper copy.
- Removing DB locks while the old watchdog is still alive is ineffective: the manager will recreate them on its next tick. Stop the writer first.
- A process restart can appear successful while the wrapper does not relaunch the listener. Confirm `netstat -ano` shows `0.0.0.0:20128 LISTENING` and identify the Node PID.
- Do not report “Gemini is routed only to accounts with Gemini quota” for account-level priority. The truthful claim is “accounts with more remaining Gemini quota are preferred.”

## Session-specific reference

The verified Windows paths, duplicate-bundle pattern, cleanup commands, and evidence from the August 2026 incident are documented in `references/antigravity-quota-priority-routing.md` itself; keep this file updated when the installed 9Router layout changes.
