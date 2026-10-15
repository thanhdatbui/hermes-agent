# OmniRoute Blank Dashboard Recovery (Backend-Only Build Override)

## 1. Symptom & Triage
- **Symptom:** Accessing `http://127.0.0.1:20129/dashboard` or `http://localhost:20129` results in a completely blank white screen (`empty page`).
- **Deceptive Health:** `http://127.0.0.1:20129/api/health` returns `{"status":"ok"}` (HTTP 200) and proxy routing (`/v1/chat/completions`) continues to work normally.
- **CRITICAL ANTI-PATTERN:** Never tell the user that "OmniRoute does not have a dashboard" or redirect them to 9Router on port `:20128`. Port `:20128` (9Router) and port `:20129` (OmniRoute) are distinct services; OmniRoute has its own comprehensive Next.js v3.8.x management dashboard.

## 2. Root Cause
- In `C:\Users\Kibe\OmniRoute`, `.build/next/` was built using `npm run build:backend` (`OMNIROUTE_BUILD_BACKEND_ONLY=1`) via `scripts/build/backendOnlyPages.mjs`.
- In `backendOnlyPages.mjs`, all ~126 App Router dashboard pages, templates, and layouts are stubbed out with `BackendOnlyPageStub` returning `null` inside a minimal `<html><body></body></html>`.
- This typically happens after an agent executes a backend code edit (e.g. `[L2-surgery]` on `chatgpt-web.ts`) and runs `build:backend` to save compile time, unwittingly overwriting `.build/next/` with headless stubs.

## 3. Recovery Procedure
To restore the full dashboard UI without losing any runtime configuration:

1. **Rebuild Full Next.js UI:**
   In `C:\Users\Kibe\OmniRoute`, run the isolated build script without backend-only environment flags:
   ```bash
   node scripts/build/build-next-isolated.mjs
   ```
   *(Ensure `OMNIROUTE_BUILD_BACKEND_ONLY` and `OMNIROUTE_BUILD_PROFILE` are unset. Compilation takes ~2–4 minutes).*

2. **Trigger Watchdog Reload via Process Termination:**
   Terminate the active PID holding port 20129:
   ```powershell
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 20129 -State Listen).OwningProcess -Force
   ```
   `omniroute_watchdog.ps1` will detect the port closure within 15s and relaunch OmniRoute with the new full build.

3. **Verify Health & UI:**
   - Wait ~15–20s for health check:
     ```bash
     curl -s http://127.0.0.1:20129/api/health
     ```
   - Navigate browser to `http://127.0.0.1:20129/dashboard` and confirm title `OmniRoute — AI Gateway for Multi-Provider LLMs` and the Provider Topology / Recent Requests table render properly.

## 4. Persistent Data Safety
- Rebuilding `.build/next/` only touches ephemeral compiled static assets.
- All persistent configuration in `C:\Users\Kibe\.omniroute\storage.sqlite` (180+ connections, 16 combos including `chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`, 5 API keys, proxy pool allocations) and `C:\Users\Kibe\AppData\Roaming\omniroute\server.env` are completely independent and remain 100% intact.
