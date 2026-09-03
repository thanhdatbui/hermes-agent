# CommandCode vs OpenCode Go — pricing/quota verified 2026-08-14

Verified from official sources on 2026-08-14 (user was deciding what to buy for farm automation).
All prices USD. VNĐ reference: $1 ≈ 36k.

## CommandCode (commandcode.ai) — commandcode provider `cmc/*` in 9router

Docs URLs (slug-exact, many naive guesses 404):
- Go plan: `https://commandcode.ai/docs/plans/go`
- Pricing+limits+deals: `https://commandcode.ai/docs/resources/pricing-limits`
- Models table: `https://commandcode.ai/models`

### Plans (verified on /pricing + /docs/plans/go)
| Plan | $/mo | Credits/mo | 5h limit | Weekly | Requests |
|---|---|---|---|---|---|
| **Go** | **$1** | $10 | **$3** | **$6** | ~15K |
| GOAT | $10 | $70 | $14 | $35 | ~75K |
| Pro | $20 | $80 | $16 | $40 | — |
| Max 10× | $100 | $150 | $45 | $90 | — |

- Credits NEVER expire; roll over; top-up credits get same deals.
- Limits measured in **credit value**, not request count.

### DeepSeek models on CommandCode (per-token, 75% off already applied)
- **DeepSeek V4 Flash (latest)**: $0.14 in / $0.28 out per 1M. **NO 4× deal.**
- **DeepSeek V4 Pro (latest)**: $0.435 in / $0.87 out per 1M. **HAS the 4× deal** (`deepseek-v4-pro-4x-usage`, Term: **No expiry / permanent**, "DeepSeek has permanently reduced their model prices" — NOT a seasonal promo; contrast Gemini 3.7 Flash which says "through December 31, 2026").

### The 4× deal — exactly what it covers
- **ONLY `deepseek-v4-pro`** gets 4× (credits → $10 credit = $40 effective usage). Flash does NOT.
- Applies on EVERY plan incl. Go $1 (docs: "A $1 Go plan with $10 credits effectively has up to $40 of DeepSeek V4 Pro usage").
- **After 4×, Pro is CHEAPER than Flash**: effective $0.109 in / $0.217 out vs Flash $0.14/$0.28 (~22% cheaper) — AND smarter. Only reason to pick Flash on CommandCode = speed (Flash 3-7s vs Pro slower).
- Verify deal is live = 3 independent sources: (1) /pricing page shows "Permanent deal — credits go up to 4× further ~$40", (2) docs "Term No expiry", (3) 9router usageHistory: real `deepseek/deepseek-v4-pro` cost ~$0.435/1M prompt = discount actually applied (undiscounted would be ~$1.74/1M → 4× the observed cost).

### "No cache" meaning (from docs usage estimates)
- "~60K requests no cache" = per-request ONLY real input tokens (~700-1K), no prompt-cache reads. "~15K with cache" = typical agentic session adds ~42-56K cache-read tokens/request (cache read cheaper but still costs credits). For Hermes automation (short independent prompts, little repetition) ≈ closer to the no-cache 60K figure.

## OpenCode Go (opencode.ai/docs/go/) — free-tier `oc/*` in 9router
- **$5 first month, then $10/month**. Quota: **5h limit $12**, weekly $30, monthly $60.
- Model list incl. DeepSeek V4 Flash, V4 Pro, Hy3, GPT 5.6 Luna, Grok 4.5, GLM-5.x, Kimi K3/K2.7/K2.6, MiMo, MiniMax, Qwen3.x.
- **API endpoints public** (usable from Hermes/9router as custom provider — no app needed):
  - `https://opencode.ai/zen/go/v1/chat/completions` (OpenAI-compatible) for GLM/Kimi/MiMo/Qwen/DeepSeek/Hy3
  - `https://opencode.ai/zen/go/v1/responses` for Grok 4.5 + GPT 5.6 Luna
- Cache hit ~98% claimed is **pattern-dependent**: their per-request estimate for DS V4 Flash = 790 input + **68,000 cached** + 280 output. Only applies to long agentic sessions with repeating context.

## Cache reality for THIS user (measured from agent.log, 2026-08-14)
| model | calls | % calls w/ cache | cache/total_in |
|---|---|---|---|
| deepseek-v4-flash (combo) | 3,562 | 32% | 22% |
| gpt-5.6-sol | 2,102 | 97% | 91% |
| gpt-5.6-luna | 1,603 | 92% | 88% |

User's farm spawns independent worker agents → fresh context each call → **cache benefit largely nullified**. So "98% cache" on OpenCode Go does NOT translate to savings for this workload; per-token price matters more.

## Recommendation given to user (2026-08-14)
- **CommandCode Go $1 = main** (36k VNĐ, has Flash + Pro-4×, no ban risk; buy MULTIPLE accounts to multiply 5h/$3 quota — user confirmed "t mua nhiều acc đc").
- **OpenCode Go $5 first month = backup** (4× bigger 5h quota $12).
- ChatGPT Plus (60k/acc, ~30% ban risk, luna 59s slow) → NOT recommended for automation despite frequent quota resets (~5-day cycles).
- Google Plus 20k/acc → only for claude-sonnet-4-6 when high-reasoning needed (AG ban risk when proxied).
- FB group claim "command code rẻ hơn opencode" = correct for light users; nuance = CommandCode 5h/$3 is tight for heavy automation (multi-account solves it).
