# CommandCode pricing + cost verification (verified 2026-08-14)

## CRITICAL: 9router's cost is SELF-COMPUTED — never trust it for real spend

`9router` records `usageHistory.cost` by multiplying tokens × its OWN internal
price table. It does **not** know CommandCode's subscription deals, so it
over-reports CommandCode spend by ~10×.

Measured on the same request (7,679 prompt tokens, `deepseek-v4-pro`):
- 9router `usageHistory.cost` = **$0.0035** (WRONG — list-price estimate)
- CommandCode real credit deduction = **$0.0003** (shown on `commandcode.ai/<user>/settings/usage`)

**Rule: to know what a CommandCode request actually costs, read the provider's own
usage page (`commandcode.ai/<user>/settings/usage?limit=100`), NOT 9router's DB.**
9router's cost column is only a proxy-internal accounting number.

## Verified pricing (CommandCode, Go $1/month plan)

- Go = $1/month, $10 credits/month, ~15K requests. 5h limit = $3, weekly = $6.
- Models on Go: DeepSeek V4 Flash + Pro (open models) + GPT-5.6 Luna (premium, "bills from pool").
- **Deal 4× ("credits go up to 4× further") applies ONLY to `deepseek-v4-pro`** — it is
  a permanent 75% off on Pro's list price, NOT on Flash.
- **Deal 4× is plan-dependent (verified on Go $1 only).** Plans page (2026-08-15) shows:
  GO $1: $10 credit → ~$40 Pro usage (4×); MAX 10x $100: $150 credit → ~$600 Pro usage
  (4×); **GOAT $10: $70 credit → only ~$80 Pro usage (~1.14× — 4× deal GONE on GOAT)**.
  GOAT uses per-model allowances ($70 GLM-5.2, $70 Tencent Hy3, $60 Flash, $80 Pro) —
  numbers may be separate pools, not conversion ratios; needs usage-page verification
  before trusting, but as printed GOAT's Pro deal is the weakest.
- List prices (per 1M tokens): Flash = $0.14 in / $0.28 out; Pro = $1.74 in / $0.87 out (before 75% off).
- Pro after 75% off = ~$0.435/1M — but this is STILL 3.1× Flash's list price.

## The conclusion that matters (measured, 12 samples)

Flash is ALWAYS cheaper than Pro, even after Pro's 4× deal, because Flash's list
price is ~12× cheaper than Pro's list price.

A/B same prompt (7,679 prompt tokens, no cache), 4 runs each, read from CommandCode usage page:

| model | completion | real cost |
|---|---|---|
| flash | 300 / 267 / 282 / 281 | $0.000123 / $0.000114 / $0.000118 / $0.000118 |
| pro   | 262 / 300 / 255 / 300 | $0.000311 / $0.000344 / $0.000304 / $0.000344 |

- Flash avg **$0.000118**, Pro avg **$0.000326** → **Pro is 2.76× more expensive**.
- Flash also faster (~4.3s vs ~5.4s).

→ For automation: **use Flash for workers/loops. Use Pro only for reasoning-heavy
planning/audit where quality beats the 2.76× premium.**

## Correct cost-comparison method (avoid the trap that happened)

The earlier mistake: compared Pro (no-cache, 7,679 tokens) against Flash (cache-heavy,
198K-243K tokens) → wrongly concluded "Pro cheaper 3.6×". The fix:
1. Drive the SAME prompt through both models (so prompt tokens match exactly).
2. Interleave A/B runs (F,P,F,P…) to cancel time-of-day noise.
3. Read cost from the provider's own usage page, filtering rows where input tokens
   equal the shared prompt token count.

## CommandCode API / proxy-detection facts

- Endpoint: `https://api.commandcode.ai/alpha/generate`
- Requires header `x-command-code-version: <ver>` (e.g. `0.18.10`); otherwise
  `upgrade_required`.
- Body is NOT plain OpenAI format — needs `memory` + `params` + `config` + `model` +
  `stream` fields (see 9router's `providerRequest` for the exact shape).
- **Proxy detection:** external calls (e.g. 9router) get
  `"Proxy use detected. This endpoint only serves CLI. ... violates the TOS and will
  result in account ban."` → 9router routing through a CommandCode subscription key
  carries ban risk. Deal (4×) is applied by key at CommandCode's billing, so it DOES
  apply to 9router-routed requests too — but proxy use still risks the account.
- CLI is NOT a way around ban: same endpoint + same detect (header + IP + key pattern).
- CommandCode CLI is not installed on this machine (only opencode, 9router, gemini).
