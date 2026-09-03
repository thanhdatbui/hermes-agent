# Codex profile fallback via 9router + app-default recipe (verified 2026-08-07)

Two ways to make a 9router-served model (e.g. `cmc/deepseek/deepseek-v4-flash`) usable
by Codex, plus the traps.

## The wiring facts

- Base `~/.codex/config.toml` defines `[model_providers.9router]`:
  `base_url = "http://localhost:20128/v1"`, `env_key = "NINEROUTER_API_KEY"`,
  `wire_api = "responses"` (Responses API — the only wire Codex supports).
  A legacy `[model_providers.omni]` with identical values also exists.
- 9router `combos` DB table maps friendly ids → upstream ids:
  - `deepseek-v4-flash` → `["cmc/deepseek/deepseek-v4-flash"]`
  - `deepseek-v4-pro` → `["cmc/deepseek/deepseek-v4-pro"]`
  - `deepseek-v4-pro-max` → `["ds/deepseek-v4-pro-max"]`
  - `opencode-free` → `["oc/deepseek-v4-flash-free","oc/mimo-v2.5-free", ...]`
- Both the combo id (`deepseek-v4-flash`) and the full id (`cmc/deepseek/deepseek-v4-flash`)
  answer POST `/v1/responses` with `{"model":"deepseek/deepseek-v4-flash", ...}` — the
  translate layer rewrites the model string but the request works.

## Path A — profile fallback (CLI only; app ignores profiles)

`~/.codex/deepseek-test.config.toml`:
```toml
model = "deepseek-v4-flash"
model_provider = "9router"
model_reasoning_effort = "high"
```
Run: `codex exec -p deepseek-test --sandbox read-only "Reply exactly DEEPSEEK_VERIFY_OK"`
→ exit 0, header prints `model: deepseek-v4-flash / provider: 9router`, replies.

## Path B — app default (VERIFIED recipe; this is what "set for the app" means)

Edit the **base** `~/.codex/config.toml` (the desktop app reads this; it ignores profiles):
```toml
model = "deepseek-v4-flash"
model_provider = "omni"        # omni ≡ 9router
```
Backup → edit → **restart the app**. Verify with `codex exec` and NO `-p`/`-c`
overrides — that is exactly what the app reads. Verified 2026-08-07: run header
`model: deepseek-v4-flash / provider: omni`, `APP_DS_OK`, exit 0.

## ⚠️ The `codex/`-prefix 401 trap (the reason Path B breaks gpt-5.6-luna)

With a custom provider active, Codex rewrites **OpenAI-registry** model ids with a
`codex/` prefix. `model="gpt-5.6-luna"` + `model_provider="omni"` → request id
`codex/gpt-5.6-luna` → 9router:
```
401 Unauthorized: [codex/gpt-5.6-luna] [401]: {
  "error": { "message": "Your authentication token has been invalidated. ...",
  url: http://localhost:20128/v1/responses
```
Misleading: NOT an auth problem. 9router simply doesn't know id `codex/gpt-5.6-luna`
(it doesn't strip the `codex/` prefix). Non-OpenAI ids (`deepseek-v4-flash`, `cmc/*`,
`oc/*`) are sent verbatim → work fine.

Consequences:
- App default deepseek → `model_provider = "omni"` fine.
- Need gpt-5.6-luna as app default + deepseek fallback → KEEP `model_provider = "openai"`
  and use Path A (`-p`/`-c`) for the fallback. Do NOT switch the app provider.

## Codex has NO native model fallback

`developers.openai.com/codex/config-reference` contains no `model_fallback` /
`fallback_models` key. All "fallback" entries are MCP OAuth auth fallback or
`project_doc_fallback_filenames`. `notice.hide_rate_limit_model_nudge` only controls
an in-app *suggestion* to switch models. Quota fallback must be orchestrated
(profile or `-c` override), not configured.

## `[tui.model_availability_nux]` is NOT a registry

Entries (`"deepseek-v4-flash" = 1`) are NUX "seen" markers. Adding entries there does
NOT make a model appear in the picker. Picker list = Codex's OpenAI registry + the
active provider's `/v1/models` (which fails to decode — see below — so router models
may not show; setting `model =` in config is the reliable path).

## Benign warnings (do not chase)

- `Model metadata for 'deepseek-v4-flash' not found. Defaulting to fallback metadata`
  → run still works.
- `codex_models_manager ... failed to refresh available models: missing field 'models'`
  → 9router `/v1/models` returns OpenAI list shape `{"object":"list","data":[...]}`,
  Codex expects `{"models":[...]}`. Cosmetic refresh error; `exec` runs fine.

## Workflow lesson (user correction 2026-08-07)

User asked "set model deepseek-v4-flash from provider cmc via 9router as a usable
model in the Codex app" — that means **base config**, NOT a CLI profile. Building a
profile first and reporting it as done is off-target: the app ignores profiles. When
the request says "app", edit base `config.toml` and verify via `codex exec` with no
overrides.

## Probe recipe (read-only)

```bash
curl -s -X POST http://127.0.0.1:20128/v1/responses \
  -H "Authorization: Bearer $NINEROUTER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"deepseek-v4-flash","input":"reply exactly: OK","max_output_tokens":20}'
```
Expect `"object":"response"`, `"status":"completed"`, `resp_...` id.
