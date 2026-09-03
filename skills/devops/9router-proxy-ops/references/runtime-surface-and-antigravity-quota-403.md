# Runtime surface and Antigravity quota-403 recovery

## Trigger
Use this when the 9Router/Antigravity dashboard shows `403`, `Antigravity upstream error`, or a quota warning while the user says quota remains available.

## Evidence-first sequence

1. Identify the actual installed runtime, not a neighboring checkout:
   - `netstat -ano` for `20128`, `20129`, and any dashboard port.
   - process command line and parent watchdog for the PID bound to `20128`.
   - `GET /api/health` and `GET /api/version` on `20128`.
2. Inspect the installed version and registry before updating. If `/api/version` says the installed version equals `latestVersion` and npm has no newer version, do not perform a blind package upgrade.
3. Keep `20128` (installed 9Router) separate from `20129` (OmniRoute dev/source server). Source tests are evidence about the source build, not the production runtime.
4. Classify the failure:
   - quota exhaustion: normally `429` or explicit `quota reached`, `quota exhausted`, `RESOURCE_EXHAUSTED`, etc.;
   - quota-monitor access issue: `403` from the usage/catalog RPC can coexist with healthy chat;
   - auth/project issue: refresh may succeed while the selected Cloud Code project lacks invocation permission.
5. Test a real usage endpoint and model discovery for one affected connection, plus the provider connection test. Do not expose access/refresh tokens. A valid usage response with nonzero remaining quota and model discovery HTTP 200 proves the screenshot was stale/transient or monitor-specific.

## Safe runtime patch pattern

Only patch the installed bundle if the exact stale literal and a verified replacement are known from the current source/runtime comparison:

1. Create a timestamped backup outside the build output or alongside it.
2. Require exactly one match per intended bundle; abort on zero or multiple matches.
3. Patch only the endpoint literal or similarly narrow target. Do not replace the whole build with a dev build.
4. Run `node --check` on every changed JavaScript bundle.
5. Restart only the 9Router process bound to `20128`; leave `20129` and unrelated services alone.
6. Wait for the watchdog to restore the port, then verify `/api/health` and `/api/version` are HTTP 200. Verify the changed literal is present and the old literal is absent.
7. Report backup path, changed files, version, health result, and what was deliberately not changed.

## Antigravity-specific finding

The older 9Router quota code used only `https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels`. The newer source used `daily-cloudcode-pa.googleapis.com` plus fallback hosts. In the investigated case, changing the installed quota-monitor bundle's `quotaApiUrl` to `https://daily-cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels` restored the current host path; chat/OAuth credentials and quota state were not reset.

This is a runtime workaround, not a general guarantee that every 403 is host-related. If the real usage endpoint or connection probe also fails, capture the response body and distinguish `PERMISSION_DENIED`, `SERVICE_DISABLED`, stale project ID, geo restriction, and token revocation before changing account/project settings.

## Do not do

- Do not ban/disable an account for a quota-monitor 403.
- Do not reset quota, reconnect OAuth, or clear cooldowns before proving exhaustion or expired state.
- Do not edit the OmniRoute source checkout when the request targets the running 9Router app.
- Do not claim a package update when the installed version is already latest.
- Do not trust a stale dashboard port (for example `2029`) without checking the live listener.
