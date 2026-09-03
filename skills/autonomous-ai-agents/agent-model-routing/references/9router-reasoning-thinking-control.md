# 9router reasoning/thinking control — how THINK:X in console log is decided

Discovered 2026-08-06 while debugging why 9router console log showed `THINK:auto`
for `cmc/deepseek/deepseek-v4-flash` even though Hermes config said `reasoning_effort: max`.

## Where the THINK label comes from (9router v0.5.45–0.5.50, bundled Next build)

Console log line `POST <model> → <provider>/<model> · FMT: ... · STREAM · N MSG · M TOOL · THINK:X · ACC:<conn>`
is built in `app/.next-cli-build/server/chunks/92500.js` (route) + `8499.js` (helpers).

1. `sS(body)` (export in `8499.js` chunk 52136, fn `j`) reads the **post-translate body** and returns a mode:
   - `output_config.effort` → `{mode:level|auto|none}`
   - `thinking.type` (`disabled`→none, `enabled`/`adaptive`→budget|auto)
   - `reasoning_effort` string, or `reasoning.effort` object → level|auto|none
   - `thinkingConfig`/`thinkingLevel`, `enable_thinking`/`thinking_budget` fallbacks
   - else `null`
2. `fmtThink(mode)` (chunk `1829.js`, fn `m`) formats: `none`→"off", `auto`→"auto",
   `budget`→"3k" style, `level`→the level string. **A mode that is not one of
   `none/auto/budget/level` renders as `auto`** — this is why `mode:"thinking"`
   (invalid) shows up as `THINK:auto`.
3. Provider-level thinking override (`providerThinking`) is applied in the route
   (`8895.js` / `92500.js`): `if (ae?.mode && "auto" !== ae.mode)`:
   - `"on"` → `thinking:{type:"enabled", budget_tokens:1e4}`
   - `"off"` → `thinking:{type:"disabled"}`
   - **any other value** → `a.reasoning_effort || (a={...a, reasoning_effort: b})`
     — i.e. it injects `reasoning_effort` ONLY if the client didn't already send one.

## The `providerThinking` settings table (9router)

Stored in `~/AppData/Roaming/9router/db/data.sqlite`, table `settings`, column `data`
(JSON, single row id=1). Example:

```json
"providerThinking": {
  "gemini": {"mode": "high"},
  "codex": {"mode": "max"},
  "commandcode": {"mode": "thinking"},   ← invalid mode → THINK:auto
  "gemini-cli": {"mode": "minimal"}
}
```

- Valid modes seen in code: `on` / `off` / `auto` / level strings (`low/medium/high/max`)
  / budget numbers.
- **`"thinking"` is NOT a valid mode** — the route treats it as a generic
  `reasoning_effort` value, commandcode doesn't recognize it, and the console log
  falls back to `THINK:auto`. Same for `"minimal"` (gemini-cli) — it becomes
  `reasoning_effort:"minimal"` upstream.
- Fix: `UPDATE settings SET data=json_set(data,'$.providerThinking.commandcode',json('{"mode":"high"}'))` — or edit via dashboard.
- Settings are read **per request, no cache** (`getSettings` → `SELECT data FROM settings WHERE id = 1` in chunk 4884.js module 42655) → **no 9router restart needed** after DB edit.

## What Hermes actually sends

- `agent.reasoning_effort` (config.yaml `agent:` section) → `resolve_reasoning_config()`
  (`hermes_constants.py:999`) → `{enabled: True, effort: <level>}`.
- DeepSeek V4 allowed efforts: `DEEPSEEK_V4_REASONING_EFFORTS = ("low","high","max")`
  (`hermes_constants.py:802`). `medium` is REJECTED for deepseek-v4 (falls back to provider default).
- `_supports_reasoning_extra_body()` (`run_agent.py:5411`) returns True for
  `custom:9router` + localhost:20128 + `cmc/deepseek/`, `ds/deepseek-`, `deepseek-v4-`.
- Transport `chat_completions.py` (legacy path, since 9router has no provider profile)
  emits `extra_body: {"reasoning": {"enabled": true, "effort": "<level>"}}`.
  OpenAI SDK merges `extra_body` into the JSON body.
- 9router's `sS()` reads `reasoning.effort` → console shows `THINK:<level>`.

## Model-name suffix `(high)` / `(max)` — DO NOT USE via HTTP

`POST /v1/chat/completions` with model `cmc/deepseek/deepseek-v4-flash(max)` →
**403** `Model/provider not recognized: anthropic:deepseek/deepseek-v4-flash(max)`
— 9router forwards the suffix verbatim to commandcode which rejects it.
The dashboard tiles show `(high)`/`(max)` as a display of the *configured thinking
level*, not a model string to send. Set effort via body param instead.

## Verification recipe

```bash
# confirm what Hermes resolves
python3 -c "import sys; sys.path.insert(0,'.'); from hermes_cli.config import load_config; from hermes_constants import resolve_reasoning_config; print(resolve_reasoning_config(load_config() or {}, 'cmc/deepseek/deepseek-v4-flash'))"

# confirm 9router accepts the payload Hermes builds
curl -s -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H "Authorization: Bearer $NINEROUTER_API_KEY" -H 'Content-Type: application/json' \
  -d '{"model":"cmc/deepseek/deepseek-v4-flash","messages":[{"role":"user","content":"2+2=?"}],"max_tokens":8,"stream":false,"reasoning":{"enabled":true,"effort":"high"}}'

# inspect settings table
python3 -c "import sqlite3,os,json; con=sqlite3.connect(os.path.expanduser('~/AppData/Roaming/9router/db/data.sqlite')); print(json.loads(con.execute('SELECT data FROM settings').fetchone()[0]).get('providerThinking'))"
```

## Session-lag note (why a session felt slow — unrelated to reasoning)

`compression.threshold: 0.5` (config.yaml `compression:` section) means context
compression fires at 50% of the model context window (~524K tokens for a 1M ctx
deepseek). A long-lived session (700+ messages, ~527K tokens) runs every API call
at ~300K input tokens → 11s+ latency, and compression itself blocks the session
~1-2 min. Lowering to `0.3` (~314K trigger) keeps calls ~200-250K and cuts latency.
Applies to NEW sessions only (reasoning/compression config resolves at session init).
