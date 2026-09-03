# OpenCode Free rate-limit forensics (session evidence, 2026-08-13)

## Verified local implementation

Installed 9Router v0.5.50 contains the OpenCode provider definition:

```js
{
  id: "opencode",
  alias: "oc",
  display: { name: "OpenCode Free" },
  category: "free",
  noAuth: true,
  transport: {
    baseUrl: "https://opencode.ai",
    headers: { "x-opencode-client": "desktop" },
    noAuth: true
  },
  modelsFetcher: {
    url: "https://opencode.ai/zen/v1/models",
    type: "opencode-free"
  }
}
```

The OpenCode adapter builds these outbound headers:

```js
{
  "Content-Type": "application/json",
  Authorization: "Bearer public",
  "x-opencode-client": "desktop",
  Accept: "text/event-stream"
}
```

Therefore the dashboard's **No authentication required** is literal for this route. Do not describe it as a user Console account or as a hidden personal login unless new evidence shows otherwise.

## Request path

```text
OpenCode/Hermes client
  -> local 9Router :20128
  -> selected provider proxy pool (optional)
  -> https://opencode.ai/zen/v1/...
```

A proxy pool changes the outbound egress path, but it does not automatically change the public bearer identity, model-specific bucket, request/token rate, headers, or server-side state. The local 9Router server also derives inbound client IP from the TCP peer and only trusts forwarding headers from a loopback reverse proxy; that is inbound/dashboard handling and is not evidence that the upstream sees the original client IP.

## Safe diagnostic matrix

Probe the exact model routes individually and record HTTP status, error type/message, response `model`, and timestamp:

| Probe | Meaning |
|---|---|
| `oc/deepseek-v4-flash-free` 429 `FreeUsageLimitError` | DeepSeek-free route/bucket currently limited |
| `oc/hy3-free` succeeds | Hy3 route/bucket may be separate and healthy |
| Same route succeeds after egress change | Supports an IP component, but does not prove IP-only limiting |
| Local OpenCode initially succeeds then later limits | Compatible with the same public upstream channel exhausting a time/token bucket; not proof that the local machine is permanently identified |

Use a small request and avoid bulk testing. Do not treat one success or one failure as proof of the quota key. Repeat only when needed, with enough time between probes.

## Conclusions supported by this evidence

- `provider (Console)` in the upstream error is provider-side wording; it does **not** prove that 9Router is checking or forwarding the user's personal Console account.
- OpenCode can enforce a composite limit involving egress IP, public channel/model, token/request rate, headers, and server-side state. The available evidence does not isolate one factor.
- There is no guaranteed legitimate configuration that makes OpenCode Free unlimited. If the user explicitly wants OpenCode Free, answer that goal directly; do not redirect them to adding a paid key or switching providers unless asked.
- Do not provide instructions to spoof device identity, forge trust headers, or evade a provider's free-tier quota. Offer only reset/backoff, lower concurrency, and ordinary provider-supported routes.

## What not to claim

- Do not say “the limit is definitely the shared key of 9Router.” The adapter evidence shows `Bearer public`, not a private account key.
- Do not say “the limit is definitely IP-based” merely because the dashboard mentions proxy pools or because the user uses residential PPPoE.
- Do not say “local OpenCode bypasses the limit” if it only worked before the later bucket was exhausted.
- Do not claim the user's proxy pool IPs are "shared/burned" — this user's pools are their OWN 40+ residential PPPoE IPs.

## Console-log ground truth (session evidence 2026-08-13)

The definitive triage source is `/dashboard/console-log` (or `GET /api/translator/console-logs` with cookie auth), NOT the error banner or `requestDetails`. Sample window on the Admin machine, same model `deepseek-v4-flash-free`, minutes apart, pools rotating per request (random strategy):

```
09:13:03 [PROXY] OPENCODE | deepseek-v4-flash-free | pool=8760... | url=http://khoalee.duckdns.org:16002  → DONE 13767ms
09:13:43 [PROXY] OPENCODE | deepseek-v4-flash-free | pool=3687... | url=http://test.taadaa.click:5102      → ERROR 429 (the ONLY one)
09:14:09 [PROXY] OPENCODE | deepseek-v4-flash-free | pool=8c15... | url=http://khoalee.duckdns.org:16001  → DONE 2556ms
09:14:34 [PROXY] OPENCODE | deepseek-v4-flash-free | pool=e5ff... | url=http://mirotik1.taadaa.click:10004 → proxy fail → fallback DIRECT → DONE 35045ms
09:15:49 ... DONE · 09:17:00 ... DONE · 09:17:13 ... DONE · 09:17:20 ... DONE
```

7× DONE + 1× 429 across different pools on the same model = **time-window burst limit that resets in seconds-minutes**, NOT burned pools / dead IPs / account ban. Rules:

- Count DONE vs 429 over a log window before concluding anything.
- Consistent 429 on one model + OK on another (deepseek-free vs hy3-free) = per-model bucket; hy3 quota is separate (user-confirmed, consistent with live probes).
- Pools rotate per request: round-robin = `(index+1)%len`, random = `Math.random()` — rotation is per-request, NOT per-time-window; request speed does not prevent pool switching.
- Egress = pool IP when a pool is active; the calling machine's own IP is irrelevant (different machine + same pool = same egress = same bucket = same 429). Only `None (direct)` exposes the machine's own IP.
- 9Router retry defaults: `429:{attempts:0,delayMs:0}` (no proxy-layer 429 retry), `502:{attempts:3,delayMs:3000}`, `503:{attempts:3,delayMs:2000}`, `504:{attempts:2,delayMs:3000}`. No pool-level failover for 429 — only `ProxyFetch ... fetch failed` falls back to DIRECT (not to another pool).
- Hermes does the retrying: `conversation_loop.py` honors `Retry-After` (cap 600s) else `jittered_backoff(retry_count, base_delay=2.0, max_delay=60.0)`, up to `agent.api_max_retries` (8 here). Each retry = fresh request → random rotation → different pool automatically. This is the built-in "pool 1 fails → try pool 2" behavior; no extra config needed.

## Combo vs Hermes fallback — choose one, don't stack

9Router combo = proxy-side model chain (set in dashboard `Combo & Vision Adapter`); Hermes `fallback_providers` = client-side chain. If both configure the same chain (deepseek→hy3→luna), a 429 triggers double retry (Hermes retries 8× on the combo name while the combo internally backoffs) → multiplied wait. Decision 2026-08-13: Hermes-side only (user's Hermes is the only client of 9Router for these models).
