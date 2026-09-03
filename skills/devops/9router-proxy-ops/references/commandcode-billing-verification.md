# CommandCode billing verification through 9Router

Use this when comparing CommandCode models or investigating quota burn. 9Router is a transport/aggregator; its local `usageHistory.cost` is an estimate from its own price table and may not include subscription discounts.

## Evidence hierarchy

1. **CommandCode's own Usage/Billing page** — authoritative for credits actually charged.
2. Request token counts/model/timestamps in 9Router — use to identify matching upstream rows.
3. 9Router's local `cost` — diagnostic estimate only, never proof of billed credits.

## Fair A/B procedure

1. Run alternating requests (A/B/A/B) with the exact same prompt, `max_tokens`, mode, and route.
2. Record model, prompt tokens, output tokens, latency, and exact local timestamp.
3. In CommandCode Usage, match rows by timestamp + model + input/output token counts.
4. Compare at least 4 rows/model. Keep output-token counts similar; do not compare a no-cache short request against a cache-heavy long session.
5. Report mean and sample spread. State whether the result is billed credits, local estimate, or latency.

Verified session example (2026-08-14; historical, re-test if pricing changes): same 7,679-input-token prompt, four samples each:

- V4 Flash credits: 0.000123, 0.000114, 0.000118, 0.000118; mean ≈ $0.000118.
- V4 Pro credits: 0.000311, 0.000344, 0.000304, 0.000344; mean ≈ $0.000326.
- Under that live plan/deal, Pro cost ≈ 2.76× Flash. The advertised 4× deal meant Pro credits stretched relative to its own reference rate; it did **not** mean Pro was 4× cheaper than Flash.

## Cache interpretation

- "No cache" is a request scenario, not a declaration that a provider has no caching.
- Cache hit depends heavily on repeated prompt prefixes. Independent spawned agents often share less reusable conversation prefix than a long-lived agent session.
- Provider marketing estimates (for example a 98% cache-hit workload) are workload assumptions, not guarantees for Hermes.
- Do not infer cache ratios from aggregate provider totals. Use explicit cache-read/write token fields when available; otherwise label the estimate uncertain.

## Quota semantics

- A shared account/window quota affects every model billed from that same pool. Switching Flash → Pro does not rescue a depleted CommandCode account.
- Pro is a **quality escalation while quota remains**. A quota fallback must use another healthy account/pool/provider.
- Multiple-account or proxy rotation can violate provider terms. Do not recommend evasion or present account rotation as ban-safe; use provider-supported credential pools/team plans where available.

## Request inspection warning

A direct malformed/unsupported call to CommandCode's CLI-only endpoint can return a proxy-use warning. That response proves the endpoint rejected that request; it does not by itself prove all 9Router traffic has identical billing or ban treatment. Ground claims in matched upstream usage rows and provider policy.