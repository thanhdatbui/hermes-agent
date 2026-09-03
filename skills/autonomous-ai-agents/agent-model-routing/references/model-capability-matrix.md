# Model capability matrix (verified 2026-08-05, this machine; refreshed 2026-08-06)

Live probe results — re-verify before relying (credentials/quota change over time).

## 9router `http://127.0.0.1:20128/v1` (chat_completions, NINEROUTER_API_KEY)

| model | result |
|---|---|
| `deepseek-v4-pro` (cmc/deepseek/deepseek-v4-pro) | ✅ works (same-provider model swap OK for Hermes subagents; re-verified 2026-08-06 via curl chat/completions — returns `model: deepseek/deepseek-v4-pro`, reasoning_content present) |
| `gpt-5.6-luna` (codex) | 401 token_invalidated — GPT models not provisioned on 9router yet; adding GPT creds enables them |
| `freemodel/gpt-5.6-luna` | 401 insufficient balance |
| `gc/gemini-*` (prefix `gc/`) | 403 quota reset — WRONG prefix for this setup |
| `gemini/gemini-3.6-flash` | ✅ text OK + **VISION OK** (see below) |
| `gemini/gemini-3.1-pro-preview` | ✅ text OK; vision needs real-size image |
| `gemini/gemini-2.5-pro` | ✅ text OK; ❌ vision 400 "Unable to process input image" |
| `gemini/gemini-3.6-flash(high)` (with suffix) | ❌ 400 — the `(high)` suffix is DISPLAY-ONLY in the dashboard; never pass it as the model name |
| `v98/qwen3-vl-plus`, `v98/gpt-5.1-codex` | respond but deny image input — NOT real vision |

### Vision via 9router Gemini — WORKS (verified 2026-08-05)

- `gemini/gemini-3.6-flash` accepts real image input and answers correctly (test: solid-color 64x64 PNG → "Xanh"/"Cam"/"Tím").
- **Pitfall**: tiny test PNGs (2x2 / 8x8 px) get rejected by 9router with `400 "Unable to process input image. Please retry"` — this is a size problem, NOT a vision-capability problem. Use ≥ ~64x64 px images (or a real screenshot) when probing.
- `gemini/gemini-2.5-pro` via 9router fails on image input even at real size — prefer `gemini/gemini-3.6-flash` for vision.

### Hermes `auxiliary.vision` recipe (DeepSeek coordinator → Gemini vision fallback)

```yaml
auxiliary:
  vision:
    provider: custom
    base_url: http://127.0.0.1:20128/v1
    model: gemini/gemini-3.6-flash
    # api key comes from NINEROUTER_API_KEY env automatically (no api_key field needed)
```

- Set ONLY via `hermes config set auxiliary.vision.<key> <value>` — the agent is BLOCKED from writing `config.yaml` directly (security guard: "Agent cannot modify security-sensitive configuration").
- After setting, DeepSeek (text-only main model) auto-falls back to the configured vision model when an image arrives; the analysis text is returned to the main model.
- Verify E2E: `async_call_llm(task='vision', messages=[...image_url...])` reads the config (task='vision' is REQUIRED — omitting it uses the main model and the call reports "cannot see image" even though the vision path works), or `vision_analyze_tool(image_url=<file>, user_prompt=...)`.
- Takes effect after app restart / new session.

## 9router dashboard (operational)

- URL `http://127.0.0.1:20128` → login (password user-provided, currently `123456`). Providers page: `/dashboard/providers`; **Gemini provider = `/dashboard/providers/gemini`** (NOT `/gemini-cli` — that is the separate "Gemini CLI" OAuth provider).
- Gemini provider shows 2 API-key connections + "Available Models" list (Gemini 3.6 Flash, 3.5 Flash Lite, 3.1 Pro Preview, 3.1 Flash Lite Preview, 3 Flash Preview, 2.5 Pro, 2.5 Flash, 2.5 Flash Lite, Gemma 4 31B IT). Each row's `(high)` = thinking-level display suffix, not part of the model ID.
- The chat/audit model used by `invoke-gemini-9router-audit.ps1` (`gemini/gemini-3.6-flash`) is the SAME model now used for vision — one model, two uses.

## cockpit `http://localhost:60818/v1` (codex_responses, COCKPIT_API_KEY, `custom_providers.cockpit`)

- `POST /v1/responses` model `gpt-5.6-luna` + `reasoning.effort=max` → `status: completed` ✅
- Models: gpt-5.6-luna / sol / terra, gpt-5.5, gpt-5.4(-mini), gpt-5.3-codex, GPT Image 2, codex-auto-review
- This is the ONLY Hermes path to Luna/Sol/Terra: `delegation.provider: cockpit`, `delegation.model: gpt-5.6-luna`, `delegation.reasoning_effort: max`

## Hermes subagent model limits (0.20.0 confirmed at source)

- `delegate_task` has NO per-task model param — one `delegation.*` config applies to ALL subagents, or they inherit the parent model.
- `_MODEL_HIDDEN_TASK_FIELDS = {acp_command, acp_args}` only — not model.
- Different model in a subagent works ONLY within the same provider (e.g. 9router flash → pro). Cross-provider (Gemini/Claude/Command Code) subagents: not possible → use CLI wrappers (`invoke-*.ps1`).
