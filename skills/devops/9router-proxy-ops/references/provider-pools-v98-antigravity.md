# Provider pools: v98 (`v98/`) and Antigravity (`ag/`) — verified 2026-08-07

## v98 — OpenAI-compatible reseller (v98store.com)
- Connection: `providerConnections` row `provider='openai-compatible-chat-f1892574-...'`, name `v98-opus`, prefix **`v98`**, `baseUrl https://v98store.com/v1`, apiKey `sk-eyB...`. Model IDs live in `kv` as `openai-compatible-chat-f1892574-...|<model>|llm`.
- `v98/<model>` is a direct provider route (slash = bypasses combos). Works in combo chains too (combo `deepseek-v4-flash` now has 10 v98 models after cmc + oc).
- **LLM chat models that WORK as fallback (batch-tested 8-way parallel, max_tokens 8):**
  `deepseek-v3` (5.5s), `deepseek-v3.1` (5.7s), `deepseek-v4-flash-0731` (11.9s), `glm-5` (5.7s), `gpt-4o-mini` (1.7s), `gpt-5-nano` (2.3s), `gpt-5.4-mini` (2.2s), `kimi-k2` (4.1s), `qwen3-max` (3.0s), `qwen3.5-plus` (9.7s).
- **FAIL / not for chat fallback:**
  - `mj_custom_zoom`, `mj_modal`, `mj_variation`, `mj_reroll`, `mj_blend`, `mj_describe`, `mj_edits`, `mj_upload`, `mj_video` → Midjourney **image** models, not LLMs — user tested `mj_custom_zoom` and it failed. Never add `mj_*` to a chat combo.
  - `claude-opus-4-8`, `claude-sonnet-4-5-20250929` → **timeout 25s** in parallel batch (user says claude-opus-4-8 works when tested alone — likely concurrency-sensitive; if added to a chain, put LAST so a slow timeout doesn't stall the chain).
  - `deepseek-chat` 503, `deepseek-reasoner` 429, `glm-4.5-air` 429, `glm-4.5-flash` 500, `deepseek-v3-1-think-*` (untested but think-variants risky).
- **Pitfall — "tắt cmc" ≠ provider off:** there are TWO commandcode connections (`'xxx'` isActive=0, `'thanhdatbui19951'` isActive=1). Toggling ONE connection off in the UI leaves the provider alive → model 1 still succeeds → fallback chain never advances. To force fallback to oc/v98, disable ALL connections for the provider (or delete the account row) — check `providerConnections.isActive` for every row of that provider.

## Antigravity (`ag/`) — OAuth subscription provider, BAN RISK
- Dashboard: `Providers > Antigravity`, 9router shows a **Risk Notice**: "uses a subscription/OAuth session not officially licensed for proxy/router use. Account may be restricted or banned."
- **Requires `+ Add Connection` (OAuth login, e.g. Google `thanhdatbui19951@gmail.com`) before use.** With 0 connections, any `ag/<model>` request → `404 {"error":{"message":"No active credentials for provider: antigravity"}}`, console log `[AUTH] No credentials for antigravity`.
- Model IDs: `ag/gemini-3.6-flash-high|medium|low`, `ag/gemini-3.5-flash-*`, `ag/gemini-3-flash-agent`, `ag/gemini-pro-agent`, `ag/claude-sonnet-4-6`, `ag/claude-opus-4-6-thinking`, `ag/gpt-oss-120b-medium`.
- **Works (tested):** `ag/gemini-3.6-flash-high` text → 200 "Hi there!" 3.7s; **image input works** (1x1 PNG test → correct color description, ~3.7s). So it's a legit vision-capable provider, NOT quota-limited like gemini API free tier.
- **User decision 2026-08-07:** use only as BACKUP vision, minimize usage (ban fear). Main vision = `oc/mimo-v2.5-free`; combo `vision-gemini` = `["ag/gemini-3.6-flash-high"]` created for on-demand gemini vision. Hermes `auxiliary.vision.model` stays `oc/mimo-v2.5-free`.
- Note: `mimo-free`/`mmf` provider alias exists in chunk 55330 model map (`new x.Yh`), distinct from `oc/mimo-v2.5-free`.

## Hermes config final state (2026-08-07, after this session)
- `model.default: deepseek-v4-flash` (combo name!) + `custom_providers.1.model: deepseek-v4-flash`; provider `models:` block lists `deepseek-v4-flash`/`deepseek-v4-pro` (combo names).
- `fallback_providers: [oc/deepseek-v4-flash-free]` only — gemini REMOVED (user: "dùng 1 tầng của 9router là đủ, đằng nào cũng phải mở 9router").
- `auxiliary.vision.model: oc/mimo-v2.5-free`; `agent.reasoning_overrides: {oc/deepseek-v4-flash-free: high}`.
- Backups: `config.yaml.bak-combo-20260807-121924`, `config.yaml.bak-nogemini-20260807-*`.
