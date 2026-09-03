# Multi-account round-robin, proxy pools, and provider-risk analysis

Use this note when evaluating whether adding subscription/OAuth accounts or proxies will improve 9Router reliability.

## Separate three mechanisms

1. **Account selection**: multiple connections for one provider. `round-robin` spreads requests; `fill-first` prioritizes one connection. A sticky limit may keep several consecutive calls on one account before rotating.
2. **Error fallback**: provider errors mark an account/model unavailable for a cooldown and retry another available connection. This is not the same as proactive round-robin.
3. **Connection proxy**: proxy pool assignment is stored per connection and resolved separately from account selection. Enabling round-robin accounts does not automatically assign distinct proxies.

Always inspect the implementation matching the installed 9Router version/tag; routing semantics change. For 0.5.50, `src/sse/services/auth.js` selected the least-recently-used available account under round-robin, honored a sticky call count, and then resolved that connection's proxy config. `open-sse/services/accountFallback.js` classified errors/cooldowns.

## What extra accounts can and cannot do

Under ideal even distribution, N healthy accounts reduce request share to roughly `1/N` per account and multiply aggregate quota only if each account has an independent allowance. This helps capacity and account-local rate limits.

It does **not** prove lower suspension risk. Provider enforcement may also use request/client fingerprints, endpoint/project identity, IP/ASN, device/OAuth patterns, payment/account provenance, linked-account behavior, or terms compliance. Correlated 403/429 errors across accounts with quota remaining—especially when the official app still works—point to transport/fingerprint/router behavior rather than insufficient account count.

9Router/Antigravity public incidents have shown client-fingerprint mismatches where the same account worked in the official IDE but failed through routed requests. Treat issue reports as evidence of possible mechanisms, not a universal ban probability.

## Decision procedure before buying accounts

1. Add and test the legitimate accounts already owned.
2. Enable account round-robin with a small sticky limit and record per-request connection ID, status, model, and quota state.
3. Keep proxy assignment unchanged during the account-only experiment; changing both variables destroys attribution.
4. Classify failures:
   - account-local quota follows one connection -> more independent quota may help;
   - all connections fail together while official client works -> investigate router fingerprint/translation/project path;
   - auth/recovery/provenance failure -> replacement accounts may share the same risk.
5. Buy more only for measured capacity demand, not as a claimed ban-prevention guarantee.
6. Prefer official API/team/project products for sustained automated scale.

## Safety boundary

Do not advise proxy rotation, fingerprint spoofing, fake accounts, or multi-account pools as ways to evade enforcement. Proxy pools are legitimate for network routing and isolation, but they can add inconsistent-location signals and are not proof of safety. Quote no ban-risk percentage without provider-specific measured evidence.

## Verification checklist

- installed 9Router version and matching source tag;
- provider strategy (`round-robin` vs `fill-first`);
- sticky limit;
- number of active connections and their independent quota state;
- per-connection proxy binding (or explicit none);
- request-to-connection evidence;
- official-client control test;
- whether failures are account-local or correlated across the pool.

## Operational: round-robin vs sequential, and handling a quota-dead account (verified 2026-08-15, v0.5.50 source)

**Round-robin vs sequential — which is riskier:** with CommandCode's proxy-detection already
threatening bans, prefer **no round-robin** (fill-first/sticky, run one account at a time).
Rotating accounts in a fixed cycle from one client/fingerprint looks like a farm pattern;
sequential use keeps rotation signals minimal. Change only ONE variable at a time
(accounts OR proxies, never both) to keep attribution clean.
Prompt Caching: Gemini/Antigravity server-side caching (>85-95% hit rate) requires sequential
conversations on the SAME account. Round-robin invalidates cache across requests, causing massive
latency (TTFT jumps from 1.5s to 15s+) and wasting input token quota.

**Quota-dead accounts — 9router retries FOREVER, no auto-disable, timing hard-coded:**
Error classifier lives in `app/.next-cli-build/server/app/api/models/route.js` (module 3662):
- Text matches `"rate limit"`/`"too many requests"`/`"quota exceeded"`/`"capacity"`/`"overloaded"`
  + HTTP 429 → exponential backoff `{base:2e3, max:3e5, maxLevel:15}` = 2s base → max **5 min** gap.
- HTTP 401/402/403/404 → fixed cooldown **120s** (`cooldownMs:12e4`); `"no credentials"`/`"improperly
  formed request"` → 120s; `"request not allowed"` → 5s.
- **No UI/config to change backoff timing** — it is compiled into the build.
- Consequence: a quota-exhausted account is probed every ≤5 min forever (~300 useless requests/day),
  each one a proxy "touch" toward the provider → extra ban signal + wasted fallback latency.

**Auto Quota Manager Fix (Implemented):**
- Integrated helper: `%APPDATA%\9router\quota_manager.py` executed by `9router_watchdog.ps1`.
- On 429 quota exhaustion: automatically updates `isActive = 0` in SQLite (`providerConnections`) and records timestamp into `kv` table (`scope='quota_cooldown'`).
- Auto-recovery: Re-enables account (`isActive = 1`, clears 429 errorCode & modelLock) after **5 hours** cooldown window (matching Google AI rolling quota reset).

## 524 fallback gap — "stuck on error" diagnosis (verified 2026-08-15, v0.5.50)

CommandCode error `{"type":"server_error","message":"Invalid error response format: Gateway request
failed","statusCode":524,"isRetryable":true}` is a Cloudflare timeout = **CommandCode server-side
overload, not an account/quota issue**. 9router's classifier matches neither the status list
(400/401/402/403/404/406/429/500/502/503/504) nor any text pattern → **no fallback, no retry — the
error passes straight through to the client** (Hermes shows it raw; the combo does NOT skip to the
next model/account). 9router also ignores upstream's `isRetryable` field — it only trusts its own
hard-coded classifier. Consequences: switching/disabling accounts does NOT help (server-side);
workaround = retry the request manually after a few seconds, or update 9router (0.5.55+ banner)
in case the classifier gained 5xx/524 handling. When diagnosing "combo stuck on error", grep the
built `app/.next-cli-build/server/app/api/combos/[id]/route.js` (module 3662) for the error message
before assuming account problems.
