# CommandCode proxy block + deal 4× reality + cache patterns (verified 2026-08-14)

## 1. CommandCode API blocks proxying — ban risk via 9router

Direct-call `https://api.commandcode.ai/alpha/generate` with the Bearer key (from 9router
`providerConnections` table, `data.apiKey`, ~92-93 chars):

1. First error without proper headers:
   `{"error":{"code":"upgrade_required","message":"Your Command Code CLI is out of date. Run
   \`cmd update\` or \`npm i -g command-code\` to upgrade.","minVersion":"0.18.10"}}`
   → needs header `x-command-code-version: 0.18.10` (or newer). Other headers
   (`x-client-version`, `User-Agent`, `x-command-code-client`) do NOT work.
2. With version header + minimal body → `BAD_REQUEST`: expects full CLI body shape
   (`memory`, `params`, `config`, `thinking`, `reasoning_effort`, `model`, `stream`).
   Copy the shape from 9router's `requestDetails.providerRequest` (that's the exact body
   9router sends — it mocks the CLI, including `x-cli-environment: cli` header).
3. With correct body → `{"success":false,"error":{"code":"BAD_REQUEST","status":400,
   "message":"Proxy use detected. This endpoint only serves CLI. Use Command Code provider
   API instead. Continued proxying of your subscription violates the TOS and will result in
   account ban.","docs":"https://commandcode.ai/docs/reference/errors/bad_request"}}`

**Consequence:** the 9router `cmc/*` route is proxying your CommandCode subscription key —
CommandCode detects it and threatens account ban. No safe multi-account/fake-proxy path
exists. Team seats (`Team Pro $40/seat`, pooled credits, "billed per seat") are the only
sanctioned multi-user route. CLI cannot multi-account either (1 auth = 1 acc, re-login per
switch) and fake-proxy via CLI is detected server-side the same way.

## 2. Deal 4× (DeepSeek V4 Pro) — real, permanent, per-key, but NOT enough to beat Flash

- Docs (`commandcode.ai/docs/plans/go` + `/docs/resources/pricing-limits`): "permanent
  deal", "no expiry", "permanently 75% off" — because DeepSeek permanently cut list prices
  ($1.74 → $0.435/1M input). "Credits stretch 4× on DeepSeek V4 Pro" applies on Go $1 plan:
  $10 credits → ~$40 effective usage on Pro.
- Deal applied **per subscription key at billing time** — CommandCode's own usage page
  (`commandcode.ai/<user>/settings/usage`) shows it even for requests that arrived via
  9router. The usage page is the source of truth; 9router's DB is not.
- Flash has NO 4× deal — only Pro. Flash is cheap natively ($0.14/1M input).
- Measured 8-sample A/B (same 7,679-token prompt, interleaved F/P/F/P..., CommandCode usage
  page costs): Flash ≈ $0.000118/req, Pro ≈ $0.000326/req → **Pro is 2.76× Flash after the
  deal**, because Flash list price is already 12× cheaper than Pro's original.
- Speed (same bench): Flash ~4.3s, Pro ~5.4s.
- **Decision for automation:** Flash wins on price AND speed. Pro only when quality matters
  (plan/audit/reasoning). "4× cheaper" means "4× further than Pro's own list price" — NOT
  "cheaper than Flash".
- CommandCode Go $1 plan: $10 credits/mo, 5h limit $3, weekly $6, ~15K req (cache) / ~60K
  req (no-cache) for Flash. OpenCode Go: $5 first month → $10/mo, 5h $12, weekly $30,
  monthly $60 — bigger quota windows but 5-10× pricier subscription.

## 3. Fair cost A/B methodology (anti-pattern found)

- Bug hit: comparing a **no-cache Pro request (7,679 tokens)** against **cache-heavy Flash
  requests (198K-243K tokens)** made Pro look 3.6× CHEAPER — completely wrong. Cache reads
  are ~10× cheaper than input tokens, so per-token rates diverge wildly across cache states.
- Correct method:
  1. Same prompt every call → identical prompt_tokens (7,679 in the test).
  2. Interleave models (F,P,F,P...) to cancel time-of-day noise.
  3. Run 4+ samples per model.
  4. Read costs from CommandCode usage page (never 9router DB). Ask user to screenshot the
     page; `vision_analyze` extracts exact cost rows (works well on the dark table).
- 9router requestDetails truncates `request`/`providerRequest` to `_preview`/`_originalSize`
  (~460K chars original) — cannot read full body from DB; the `_originalSize` field confirms
  Hermes sends its full system prompt + history per call.

## 4. Cache reality for spawn-agent automation (user's own usageHistory)

- Spawn-agent pattern (each worker = fresh context): deepseek combo had only **22% of input
  tokens as cache** (32% of calls had cache). Long-lived sessions (sol/luna) hit **88-91%**
  cache. → "98% cache hit" marketing (OpenCode Go) barely applies to spawn-agent automation;
  per-token price matters more than cache ratio for this pattern.

## 5. Quota burn diagnosis (why "flash is still expensive")

- User's CommandCode Go burned $9.77/$10 monthly. Root cause was NOT flash price — it was
  **context bloat**: 2,033 flash requests/day × avg 195K prompt tokens = 396M tokens/day.
  Distribution: 49% of requests 200-400K, 45% 100-200K. Hermes sessions grew to ~192-195K
  tokens before compression (ctx 1M + threshold 0.3 → compresses at ~300K... but sessions ran
  at ~193K/call continuously).
- **Auxiliary compression used the SESSION's model** when `compression.model` unset
  ("auto"): session on sol → compressed with sol; on luna → luna. Those are the expensive
  codex models → $626/day (91% of spend) went to sol/luna compression calls.
- Fix: `hermes config set compression.model deepseek-v4-flash` + `compression.provider
  custom:9router` + `delegation.model deepseek-v4-flash` → compression & workers use Flash.
- **Compression model resolution** (source `agent/auxiliary_client.py` line ~5978
  `_resolve_task_provider_model`): priority = explicit args > config file
  (`auxiliary.<task>.model` / `compression.model`) > "auto" (inherit session model).
  → Setting `compression.model` is GLOBAL and WINS over session model; "auto" means session
  model. Config change applies without /new for compression + delegation; only the session's
  own default model needs /new.
- Feasibility check (`agent/conversation_compression.py` `check_compression_model_feasibility`)
  requires aux compression model context window ≥ main model's compression threshold. Flash
  ctx 1M is fine for all.
