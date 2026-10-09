# OmniRoute Proxy Assignment & Static Binding Invariants

## Core Principles
1. **Never Confuse 9Router (:20128) vs OmniRoute (:20129)**
   - Hermes primary provider `omni` connects to OmniRoute (:20129).
   - Old accounts removed from OmniRoute might still exist in 9Router DB (`C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`).
   - ALWAYS verify the running service endpoint before stating account presence.

2. **Static Binding (Fail-Closed Architecture)**
   - In OmniRoute, `proxy_assignments` statically binds accounts to specific proxy registry entries (`scope='account'`).
   - `PROXY_FAIL_OPEN=false` and `OMNIROUTE_CONTROL_PLANE_PROXY_DIRECT_FALLBACK=false` are strictly enforced.
   - When a proxy goes down (e.g. power outage on Mobi 4G farm `test.taadaa.click`), accounts statically assigned to that proxy TIMEOUT and FAIL CLOSED.
   - OmniRoute NEVER randomly re-assigns or falls back to another proxy pool (e.g., MikroTik) for those accounts.

3. **Multi-Account Pool Traffic Flow During Outages**
   - If user asks why Google/Antigravity traffic is still flowing when one proxy pool is down:
     Check active accounts assigned to OTHER unaffected pools (e.g., MikroTik `10001..10035` or direct connections).
   - Trace exact connection IDs via `open-sse` / `/api/providers` and `proxy_assignments`.
   - Distinguish clearly between Pro tier accounts (`g1-pro-tier`) and Free tier accounts. Never claim traffic is routing through unassigned/free accounts without verifying the exact connection ID in `combos` and `proxy_assignments`.
