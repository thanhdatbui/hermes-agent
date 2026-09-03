# Antigravity 429 on large-context requests (gemini 3.6 flash) — verified 2026-08-15

## Symptom

`hermes chat -m ag/gemini-3.6-flash-{low,medium,high} --provider custom:9router` fails with HTTP 429 `RESOURCE_EXHAUSTED`, but the SAME model succeeds when tested in the 9Router dashboard or via direct API call. User sees "model works fine in the app" → confusing.

## Root cause (proven via `server.log`)

The difference is **request size**, not key/model/provider.

- Direct curl, 1 message, small context:
  `POST gemini-3.6-flash-high → antigravity/gemini-3.6-flash-high · FMT: openai→antigravity · STREAM · 1 MSG · THINK:high · ACC:thanhdatbui19951@gmail.com` → **succeeded**
- Hermes chat carries full session (system prompt + toolset + `29 TOOL` messages):
  `… · STREAM · 2 MSG · 29 TOOL · THINK:high · ACC:thanhdatbui19951@gmail.com` → `ERROR 429 · 15214ms`

Antigravity upstream enforces a per-request token/quota ceiling; large-context requests get 429 even when the account is healthy.

## modelLock escalation

After a 429, 9router applies `modelLock_<model>` to the account with **exponentially increasing reset** (2s → 4s → 6s → 13s …). Any retry inside the lock window fails INSTANTLY with the same 429 without hitting upstream. Repeated retries lengthen the lock. Wait out the lock before retrying.

## Workaround: direct curl for short completions

```bash
curl -sS -X POST "http://127.0.0.1:20128/v1/chat/completions" \
  -H "Authorization: Bearer $NINEROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini-3.6-flash-high","messages":[{"role":"user","content":"..."}],"max_tokens":2000,"stream":false}'
```

- `$NINEROUTER_API_KEY` lives in **OS env** (`printenv` shows it), NOT in `~/AppData/Local/hermes/.env`. The .env has `OMNIROUTE_API_KEY` which is a DIFFERENT key → `Invalid API key` if used against 9router.
- Model id accepts both `ag/gemini-3.6-flash-high` and bare `gemini-3.6-flash-high`.
- Use `stream:false` + python to decode, or grep `"content"` chunks when streaming.

## Confirm route/lock state

`tail C:\Users\Kibe\AppData\Roaming\9router\logs\server.log` and grep the model name:

- Healthy call: `🔵 ▶ POST gemini-3.6-flash-high → antigravity/gemini-3.6-flash-high · … · N MSG · THINK:high · ACC:<account>` then `COMBO Model ag/gemini-3.6-flash-high succeeded`
- Locked: `⚠️ [AUTH] <account> locked modelLock_gemini-3.6-flash-high for Ns [429]` then `all 1 accounts locked …`

If hermes chat must be used with gemini: keep session context small (fresh `-q`, minimal history) — but hermes always injects its toolset, so for short text rewrites the reliable path is direct curl.
