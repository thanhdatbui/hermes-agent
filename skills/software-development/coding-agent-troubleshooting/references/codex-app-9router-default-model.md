# Codex desktop app → 9Router-served model (deepseek-v4-flash) — full recipe

Session: 2026-08-07 (user asked to "set model deepseek v4 flash from provider cmc via 9router as a usable model in the Codex app UI").

## ⚠️ TL;DR — this does NOT work for the desktop app UI (superseded 2026-08-07 evening)

Editing the base `~/.codex/config.toml` does NOT make `deepseek-v4-flash` appear
in the desktop dropdown, and it silently switches the default model for ALL new
chats (even when the user selects GPT in the dropdown). The user demanded a full
revert. Full story + rules: see the "Desktop-app default — CORRECTED recipe" block
in SKILL.md. The one-line answer below is the mechanism, NOT a recommendation.

## Evidence chain (all verified live)

| Check | Result |
|---|---|
| 9router `combos` DB has `deepseek-v4-flash` → `["cmc/deepseek/deepseek-v4-flash"]` | ✅ |
| `/v1/responses` probe `{"model":"deepseek-v4-flash",...}` → `resp_...` completed | ✅ |
| `/v1/models` lists `deepseek-v4-flash` (combo) + `cmc/deepseek/deepseek-v4-flash` + `deepseek-v4-pro` | ✅ |
| `codex exec -p deepseek-test` (profile) → `model: deepseek-v4-flash / provider: 9router`, replies | ✅ |
| `codex exec` with base config `deepseek-v4-flash`+`omni`, NO overrides → `model: deepseek-v4-flash / provider: omni`, `APP_DS_OK`, exit 0 | ✅ |
| `codex exec` base `gpt-5.6-luna`+`omni` → 401 `codex/gpt-5.6-luna` | ❌ (the trap) |

## Pitfall: the `codex/` prefix 401

With `model_provider = "omni"` (custom provider), Codex rewrites **OpenAI-registry** model ids with a `codex/` prefix:

```
ERROR: unexpected status 401 Unauthorized: [codex/gpt-5.6-luna] [401]: {
  "error": { "message": "Your authentication token has been invalidated. ...",
  url: http://localhost:20128/v1/responses
```

The message is misleading — it's NOT a token/auth problem. 9router doesn't know id `codex/gpt-5.6-luna` (it only handles plain ids/combo names). Non-OpenAI ids (`deepseek-v4-flash`, `cmc/deepseek/...`, `oc/...`) are sent verbatim and work.

Rule of thumb:
- App default = deepseek/other-9router model → `model_provider = "omni"` is fine.
- App default = gpt-5.6-luna + occasional deepseek fallback → keep `model_provider = "openai"`, fall back via `-c`/profile.

## Benign noise (do NOT chase)

```
warning: Model metadata for `deepseek-v4-flash` not found. Defaulting to fallback metadata
ERROR codex_models_manager::manager: failed to refresh available models:
  missing field `models` at line 1 column 158518; body: {"object":"list","data":[...]}
```
- The `missing field 'models'` error: 9router `/v1/models` returns the OpenAI **list** shape `{"object":"list","data":[...]}`; Codex expects Responses shape `{"models":[...]}`. Refresh fails, but the run proceeds. Cosmetic.
- `Model metadata not found` = the model isn't in Codex's hardcoded registry; fallback metadata is used. Benign.

## `[tui.model_availability_nux]` is NOT a registry

Entries like `"deepseek-v4-flash" = 1` are NUX "already seen" markers. Do NOT add entries there expecting the model to appear. The picker list comes from Codex's OpenAI registry + the active provider's `/v1/models` (which, per above, fails to decode — so router models may not show even with the right provider; selecting via `model =` in config is the reliable path).

## No native model fallback

`developers.openai.com/codex/config-reference` has no `model_fallback`/`fallback_models` key. Every "fallback" hit is MCP OAuth (`mcp_servers.<id>.auth`) or `project_doc_fallback_filenames`. Closest is `notice.hide_rate_limit_model_nudge` (app suggests switching models on rate limit; never auto-switches). Quota fallback must be orchestrated externally (profile / `-c` route).

## Ad-hoc verification pattern (used; passed 11/11)

Script under `%TEMP%` with `hermes-verify-` prefix, `tempfile.TemporaryDirectory` for the git cwd, `tomllib` to validate the config, then:

```python
r = subprocess.run(["codex","exec","--sandbox","read-only",
    "Reply exactly with the single token APP_DS_OK and nothing else."],
    cwd=td, capture_output=True, text=True, timeout=180)
out = (r.stdout or "") + (r.stderr or "")
assert r.returncode == 0 and "model: deepseek-v4-flash" in out \
   and "provider: omni" in out and "APP_DS_OK" in out
```

Checks: TOML valid / `model` pin / `model_provider` pin / omni block `base_url=http://localhost:20128/v1` + `wire_api=responses` + `env_key=NINEROUTER_API_KEY` / `notify` path backslashes intact / exec exit 0 / run header / reply token. Clean up the script afterwards.

## Restore to gpt-5.6

```toml
model = "gpt-5.6-luna"
model_provider = "openai"
```
(backup taken: `config.toml.bak-app-ds-20260807-063954`).

## Related

- `config.pre-deepseek-20260731-1740.toml` on this machine: previous state where Codex ran entirely via `omni` (9router), `model = "gpt-5.6-luna"` — the file that proved `omni` was the historically-correct provider name for the 9router route.
