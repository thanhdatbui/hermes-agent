# DeepSeek reasoning — Hermes→9Router→commandcode resolution chain

Verified on Hermes v0.18.2 + 9router v0.5.50 (2026-08-06). Code locations are inside `C:\Users\Kibe\AppData\Local\hermes\hermes-agent\`.

## Hermes side

1. Config: `agent.reasoning_effort: max`, `agent.reasoning_overrides: {gemini/gemini-3.6-flash: high}`, `model.default: cmc/deepseek/deepseek-v4-flash` (no suffix).
2. `hermes_constants.py:999 resolve_reasoning_config(cfg, model)` — single chokepoint. Priority: per-model `reasoning_overrides` → global `reasoning_effort`. For our model: `{'enabled': True, 'effort': 'max'}`.
   - `parse_reasoning_effort_for_model` (line 835) rejects efforts not in `reasoning_efforts_for_model` → `DEEPSEEK_V4_REASONING_EFFORTS = ("low", "high", "max")` (line 802). So `max` passes, `medium`/`auto` → None → provider default.
3. `run_agent.py:5411 _supports_reasoning_extra_body()` — True for provider `custom`/`custom:9router` when base_url host is localhost/127.0.0.1 port **20128** AND model starts with `cmc/deepseek/`, `ds/deepseek-`, `deepseek-v4-`.
4. `agent/transports/chat_completions.py` `build_kwargs` — custom providers have **no provider profile** (`get_provider_profile` returns None), so the legacy flag path runs:
   - line 472-481: if `supports_reasoning and not is_lmstudio` → `extra_body["reasoning"] = {"enabled": True, "effort": <effort>}` (default "medium" if unset).
   - line 501-502: `api_kwargs["extra_body"] = extra_body`.
   - OpenAI SDK (`_base_client.py:1994`) merges `extra_body` into the JSON body via `extra_json` — so `reasoning` really hits the wire.
5. `reasoning_config` is resolved at session/agent init and on fallback swap (`agent_runtime_helpers.py`, `chat_completion_helpers.py:1680-1700`). Config changes after session start do NOT re-resolve → need a new session.

## 9Router side (bundle code, `.next-cli-build/server/chunks/`)

- `sS(body)` (chunk 8499.js, module 52136) reads effort from translated body: `output_config.effort` → `thinking.type`/`budget_tokens` → `reasoning_effort` / `reasoning.effort` → `thinkingConfig`/`generationConfig.thinkingConfig` → `enable_thinking`. Returns `{mode: none|auto|budget|level}`.
- `fmtThink(mode)` (chunk 1829.js) prints: none→"off", auto→"auto", budget→"Nk", level→level string.
- commandcode transformer (chunk 318.js, class `A` extends base `H`): `transformRequest` only sets `stream=!0`, body otherwise passed through unchanged. No effort rewriting.
- Model-name suffix `(high)`/`(max)` is parsed by `nF()` (module 52136) into `{mode:"level"}` **only for routing** — but the raw model string (with parens) is sent upstream, and commandcode rejects it: `403 Model/provider not recognized: anthropic:deepseek/deepseek-v4-flash(max)`.

## Diagnosis recipe: "why does console log say THINK:auto"

- `THINK:auto` = translated body had **no** effort param (or `"auto"` explicitly). It is NOT the model auto-selecting.
- Causes: (a) request from a session started before `reasoning_effort` was set; (b) effort set to something outside DeepSeek's `(low, high, max)` so Hermes dropped it; (c) request bypassed the reasoning-capable gate (wrong base_url port / non-deepseek model name).
- Fix: `hermes config set agent.reasoning_effort max` + `/new` session; verify via a fresh Console Log line showing `THINK:max`.

## DB forensics

`%APPDATA%\9router\db\data.sqlite`:
- `requestDetails` — per-request: id like `2026-08-06T11:13:40.276Z-5v8jhl-deepseek-deepseek-v4-flash`, timestamp, provider, model, connectionId, status, data JSON (`request`/`providerRequest`/`providerResponse`/`response`, each truncated to 200-char `_preview`).
- `usageHistory`, `usageDaily`, `providerConnections`, `apiKeys`, `combos`.
- curl probes from the terminal do NOT get recorded in requestDetails (only real app traffic seems to land there).
