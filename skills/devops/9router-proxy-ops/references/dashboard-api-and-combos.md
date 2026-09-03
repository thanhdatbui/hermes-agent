# Dashboard API + Combo mechanics (verified 2026-08-07; combo defs re-verified 2026-08-17)

## Combo resolution — the slash rule
`9router/app/.next-cli-build/server/chunks/3212.js` (module 38775, fn `j`):
```js
async function j(a){ if (a.includes("/")) return null;   // slash → NOT a combo
  let b = await getComboByName(a);                       // no slash → look up combos table
  return b && b.models.length > 0 ? b.models : null; }
```
- `cmc/deepseek/deepseek-v4-flash` (slash) → direct provider route, combo NEVER consulted.
- `deepseek-v4-flash` (no slash) → resolved to combo models, tried in order.
- So any client config (Hermes `model.default`, `custom_providers[].model`, Codex) must use the combo NAME to get combo fallback.

### 429 RESOURCE_EXHAUSTED = AG quota chết; slash-path / combo-1-model → KHÔNG fallback (verified 2026-08-17)
- Triệu chứng: Hermes báo `API call failed after 2 retries: HTTP 429: [antigravity/claude-sonnet-4-6] [429]: {"code":429,"message":"Resource has been exhausted (e.g. check quota).","status":"RESOURCE_EXHAUSTED"}` — phạm vi `[...]` trong lỗi = đúng model/provider đã nhận request.
- Check quota: Quota Tracker `http://localhost:20128/dashboard/quota` (nút `Turn off Empty` lọc ra account hết quota). 17/08: card `thanhdatbui19951@gmail.com` → Claude Sonnet 4.6 **1000/1000 · 0% · reset 2d9h**; card `jinrakal@gmail.com` → sonnet 60/1000 (~94%), gemini 10/1000 (99%).
- Vì sao không tự fallback: Hermes gửi slash-path (`antigravity/claude-sonnet-4-6`) hoặc combo 1-model (`claude-sonnet-4-6`) → 9router route thẳng / không còn model nào để thử → 429 trả raw về Hermes, nhìn như "lỗi 9router".
- Fix: `/model worker` (fallback tới `ag/gemini-3.7-flash-high` còn 99%) hoặc `/model deepseek-v4-flash`. ĐỪNG `/model claude-sonnet-4-6` — combo 1 model, vẫn 429. Route account theo connection chứ không chọn tay được account còn quota.
- Phân biệt: 429 gemini do request QUÁ TO (29 tool messages, size-based) → `references/ag-gemini-429-fix.md`; cái này là hết quota THẬT (1000/1000) — check dashboard trước khi kết luận.

## Dashboard API auth (curl)
- Endpoint: `POST /api/auth/login` (NOT `/login` — that returns 405). Body `{"password":"123456"}` (or `INITIAL_PASSWORD` env).
- Response 200 sets `set-cookie: auth_token=<jwt>; Path=/; HttpOnly; SameSite=lax`.
- Extract and reuse:
```bash
TOKEN=$(curl -s -D - -o /dev/null -X POST http://localhost:20128/api/auth/login \
  -H 'Content-Type: application/json' -d '{"password":"123456"}' \
  | grep -i '^set-cookie' | sed 's/.*auth_token=\([^;]*\).*/\1/')
curl -b "auth_token=$TOKEN" http://localhost:20128/api/combos
```

## Combo CRUD
- List: `GET /api/combos` → `{"combos":[{id,name,kind,models,createdAt,updatedAt}]}`
- Create: `POST /api/combos` `{"name":"x","models":["a/b","c/d"]}` — name must match `^[a-zA-Z0-9_.\-]+$`; duplicate name → 400.
- Update: `PUT /api/combos/{id}` `{"name":...,"models":[...]}`
- Delete: `DELETE /api/combos/{id}` → `{"success":true}`

## Combos — current definitions (re-verified 2026-08-17 via `GET /api/combos`; order CHANGED since 15/08)
- `worker` = `[cmc/deepseek/deepseek-v4-flash, oc/deepseek-v4-flash-free, oc/hy3-free, ag/gemini-3.7-flash-high, ag/claude-sonnet-4-6, gpt-5.6-luna]` — Hermes main+worker default; gemini 3.7 thay 3.6 và đứng TRƯỚC sonnet, luna dời về cuối (log console xác nhận model 2/6 = oc/ds-free).
- `deepseek-v4-flash` = 12 model — fallback rộng nhất: `cmc/deepseek/deepseek-v4-flash, oc/deepseek-v4-flash-free, oc/hy3-free, gpt-5.6-luna, openrouter/cohere/north-mini-code:free, openrouter/nvidia/nemotron-3-nano-30b-a3b:free, nemotron-3-nano-omni-30b-a3b-reasoning:free, nemotron-3-super-120b-a12b:free, nemotron-3-ultra-550b-a55b:free, openrouter/openrouter/free, openrouter/poolside/laguna-s-2.1:free, laguna-xs-2.1:free]`.
- `gemini-3.7-flash-high` = `[ag/gemini-3.7-flash-high, ag/gemini-3.6-flash-high]` — fallback giữa 2 model AG.
- `claude-sonnet-4-6` = `[ag/claude-sonnet-4-6]` — combo 1 model, KHÔNG fallback hữu ích.
- `opencode-free` = `[oc/deepseek-v4-flash-free, oc/mimo-v2.5-free, oc/big-pickle, oc/hy3-free, oc/nemotron-3-ultra-free, oc/north-mini-code-free]`; `opencode-audit` = `[oc/nemotron-3-ultra-free, oc/big-pickle, oc/longcat-2.0-free, oc/ling-3.0-tiny-free]`.
- `plan-review` = `[gpt-5.6-terra, ag/claude-opus-4-6-thinking, cmc/deepseek/deepseek-v4-pro]` — plan/audit thường; smoke: Terra (codex credential inactive) → fallback AG Opus 4.6 → 2.6s OK.
- `plan-review-hard` = `[gpt-5.6-sol]` — plan/audit khó (SOL ONLY, user chốt 15/08; KHÔNG nhét pro/opus vào combo để 9router không tự fallback ngầm). Sol fail qua 9router → gọi Claude CLI `claude -p --model claude-opus-5` ngoài combo. Hiện sol 404 (codex credential inactive — chờ user bật auth codex); CLI đã re-auth OK 2026-08-15 (`claude -p --model claude-opus-5` → CLI_OPUS5_OK).
- **ALWAYS send `"stream": false` in chat payload** — AG models (gemini/opus/sonnet) return SSE `text/event-stream` when omitted, breaking JSON parse; with `stream:false` they return clean `application/json`. (Hit 2026-08-15: model/AG checks failed until explicit stream:false.)

## Console log (live diagnostic when requestDetails is stale)
- `GET /api/translator/console-logs` → `{"success":true,"logs":["[12:22:10] ℹ️  [CHAT] Combo \"deepseek-v4-flash\" with 2 models (strategy: fallback, sticky: 1)", ...]}`
- Markers to grep: `[COMBO] Trying model 1/2`, `[COMBO] Model ... succeeded`, `[FALLBACK] ⇄`, `[AUTH] ... locked modelLock_...`, `[TOKEN_REFRESH]`, `ERROR 403/429`.
- `requestDetails` table stopped logging 2026-08-07 (last row 06-08 12:10) despite live traffic — console-log API is the reliable recent-history source.

## Fallback verification recipe (no UI needed)
1. Create throwaway combo: `{"name":"fb-test-verify","models":["cmc/deepseek/NONEXISTENT-MODEL","oc/deepseek-v4-flash-free"]}`
2. `curl -X POST http://127.0.0.1:20128/v1/chat/completions -H "Authorization: Bearer $NINEROUTER_API_KEY" -H 'Content-Type: application/json' -d '{"model":"fb-test-verify","messages":[{"role":"user","content":"hi"}],"max_tokens":8,"stream":false}'`
3. Success = response `"model":"deepseek-v4-flash-free"` + `"cost":"0"`. Console log shows: 403 on fake model → `[FALLBACK] ⇄ ACC:... UNAVAILABLE (403) → NEXT ACCOUNT` → oc model succeeded.
4. DELETE the combo afterwards — user dislikes leftover test combos.

## Hermes config edits (custom_providers is a LIST)
- `patch`/`write_file` REFUSE to touch `~/AppData/Local/hermes/config.yaml` (security guard) — use `hermes config set`.
- `custom_providers` is a list → index it: `hermes config set custom_providers.1.model "deepseek-v4-flash"` (index 1 = 9router after cockpit).
- `hermes config get` does not exist; verify with `hermes config show` or `sed` the file.
- After changing model config, Hermes needs `/new` (or `/model` switch) to reload.

## Gemini free-tier quota (why gemini 429s)
- Free tier: 20 req/day/project/model — `generate_content_free_tier_requests`, quotaId `GenerateRequestsPerDayPerProjectPerModel-FreeTier`.
- 429 → per-account lock 300s (`modelLock_gemini-3.6-flash`); both accounts locked → `[AUTH] gemini | all 2 accounts locked ... reset after 4m 59s`.
- Traffic sources to gemini via 9router: Hermes `auxiliary.vision.model` (image analysis — the usual quota burner), `fallback_providers`, standalone audit jobs.
- If quota is precious: set `auxiliary.vision.model` → `oc/mimo-v2.5-free` (vision-capable free model), or drop gemini from `fallback_providers`.