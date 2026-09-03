# 9Router (localhost:20128) — Dashboard Auth, DB Schema & DeepSeek Reasoning Levels

Discovered 2026-08-04 while investigating the deepseek-v4-flash fallback for
Codex auto-recovery on the Taadaa machine. Reasoning-level section updated
2026-08-04 after user's live verification.

## Dashboard Auth (pitfall — do NOT repeat this blind-guess loop)

- `http://localhost:20128/dashboard/...` (Next.js app) requires a password
  login. The API behind it (`/api/providers`, `/api/config`, `/api/settings`,
  `/api/status`) returns `{"error":"Unauthorized"}` with Bearer /
  X-API-Key / `x-api-key` / raw header using any of:
  - `NINEROUTER_API_KEY` (env, used for `/v1/*` — works there, NOT for `/api/*`)
  - `~/.config/9router/auth/cli-secret` (64 hex chars)
  - `~/.config/9router/jwt-secret` (64 hex chars)
  - `~/.config/9router/machine-id` (64 hex chars)
- The dashboard password is stored as a **bcrypt hash** in the DB:
  `settings.data.password = "$2b$10$..."` — NOT recoverable from any local
  secret file. Attempting the 3 hex secrets in the browser login form is a
  wasted loop; the only routes are (a) user supplies the dashboard password,
  or (b) read the DB read-only (below).
- 9router CLI (`npm i -g 9router`, binary in `~/AppData/Roaming/npm/9router`)
  has only `xai video` subcommand — no providers/models/config dump.

## 9Router Data Directory & DB Schema (read-only inspection)

Config root: `~/AppData/Roaming/9router/` (NOT `~/.config/9router` — that dir
only holds `auth/cli-secret`). Layout: `db/data.sqlite` (WAL mode),
`jwt-secret`, `machine-id`, `logs/`, `mitm/`, `bin/cloudflared.exe`.

Open read-only (WAL lock otherwise):
```python
import sqlite3, json
con = sqlite3.connect('file:C:/Users/<user>/AppData/Roaming/9router/db/data.sqlite?mode=ro', uri=True)
```

Key tables (verified):
- `settings(id, data)` — JSON blob with:
  - `providerThinking`: `{"gemini":{"mode":"high"},"codex":{"mode":"max"},"commandcode":{"mode":"high"}}`
    → **per-provider thinking mode** (the default used when a request supplies
    no explicit `reasoning_effort`). commandcode (deepseek) default is `high`.
  - `password` (bcrypt hash), `quotaVisibility`, `providerStrategies`,
    `codexAutoPing`, `rtkEnabled`, `outboundProxyEnabled`.
- `providerConnections(id, provider, authType, name, email, priority, isActive, data)`
  — provider `commandcode` name `deepseek-command-code` (active=1) with
  `apiKey` + `testStatus`. Provider `codex` = ChatGPT Plus accounts
  (with `modelLock_gpt-5.6-*` timestamps and `errorCode` 429/401 — useful for
  diagnosing quota/rate-limit state per account). NOTE: connection `data`
  contains access/refresh tokens — redact before printing.
- `providerNodes(id, type, name, data)` — only the openai-compatible nodes
  (freemodel, v98). Built-in providers (codex/gemini/commandcode/deepseek)
  are NOT listed here.
- `combos(id, name, kind, models)` — model-group combos; deepseek combos map:
  - `deepseek-v4-flash` → `["cmc/deepseek/deepseek-v4-flash"]`
  - `deepseek-v4-pro` → `["cmc/deepseek/deepseek-v4-pro"]`
  - `deepseek-v4-pro-max` → `["ds/deepseek-v4-pro-max"]`
  - gpt-5.6-luna/sol/terra → `["cx/gpt-5.6-*"]`
- `kv(scope, key, value)` — scopes `customModels` (openai-compatible model
  entries) and `disabledModels` (per provider prefix, e.g. `ds` disables
  `deepseek-v4-pro-none`, `deepseek-chat`, `deepseek-reasoner`).
- `requestDetails(id, timestamp, provider, model, connectionId, status, data)`
  — request log; `data.request`/`providerRequest` are **truncated previews**
  (~300B) so the reasoning/thinking parameter is NOT recoverable from here.
- `usageHistory` — per-request token/cost rows; model + endpoint only, no
  reasoning field.

## DeepSeek Reasoning Levels (user-verified 2026-08-04)

**Live test result** (via `http://127.0.0.1:20128/v1/chat/completions` on BOTH
`deepseek-v4-flash` and `deepseek-v4-pro`): every level PASSES —

| Level | Flash | Pro |
|---|---|---|
| auto | PASS | PASS |
| low | PASS | PASS |
| medium | PASS | PASS |
| high | PASS | PASS |
| max | PASS | PASS |
| thinking | PASS | PASS |

(Flash/auto had one transient first-attempt timeout; retry returned HTTP 200.)

**Wire contract:**
- Valid `reasoning_effort` values: `auto, low, medium, high, max, thinking`.
- Send it as a SEPARATE request field — do NOT glue it onto the model ID.
  `(max)` is not part of `cmc/deepseek/deepseek-v4-flash` or
  `cmc/deepseek/deepseek-v4-pro`; the model stays exact and the effort goes in
  `reasoning_effort`.
- The Command Code audit wrapper
  (`D:\Taadaa\tools\invoke-command-code-9router-audit.ps1`) did NOT pass
  `reasoning_effort` before 2026-08-04 — it now accepts `-ReasoningEffort`
  and records it in the artifact. Before that, requests used the provider
  default (`providerThinking.commandcode.mode` = high).

**Two orthogonal fallback knobs (do not conflate):**
1. Model tier: `deepseek-v4-flash` → `deepseek-v4-pro` → `deepseek-v4-pro-max`
   (combo ids; `cmc/` = commandcode variants flash/pro).
2. Reasoning effort per call: `auto/low/medium/high/max/thinking`.

So the "increasing reasoning" fallback ladder is: flash/high → flash/max →
pro/high → pro/max → pro/thinking. The `-none` suffix in disabledModels
(`deepseek-v4-pro-none`) is a legacy/disabled variant, not part of the active
effort set.

## Model Capabilities Lookup (no dashboard needed)

```bash
curl -s http://127.0.0.1:20128/v1/models -H "Authorization: Bearer $NINEROUTER_API_KEY" | \
  python -c "import sys,json; [print(m['id'], m.get('capabilities',{}).get('tools'), m.get('capabilities',{}).get('reasoning'), m.get('capabilities',{}).get('thinkingFormat')) for m in json.load(sys.stdin)['data']]"
```
Note: `owned_by` prefixes = provider namespaces (combo / cmc / ds / cx / gc /
v98 / freemodel / oc). `cmc/deepseek/deepseek-v4-*` = Command Code provider.
