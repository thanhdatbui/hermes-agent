# Single-Account Live Verification (OmniRoute Antigravity pool)

Proves whether ONE pool member credential works, isolating connection vs model/combo failure.

## When
- Pool returns 200 but suspect member never appears in `call_logs` with success.
- Suspect shows `test_status=active` yet requests fail when routed to it.
- Need evidence before re-OAuth / proxy change / project rebind.

## Recipe

### Method A: Fast Direct Probe via Header (No Combo Mutation)
OmniRoute supports routing directly to a specific connection by passing the `x-omniroute-connection-id` header on standard chat completion calls:
```bash
curl -s http://127.0.0.1:20129/v1/chat/completions \
  -H "Authorization: Bearer $OMNIROUTE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-omniroute-connection-id: <connId>" \
  -d '{
    "model": "antigravity/gemini-3.7-flash-high",
    "messages": [{"role": "user", "content": "ping"}],
    "max_tokens": 5
  }'
```
This tests the exact connection directly without creating and deleting temporary combos in SQLite.

### Method B: Temporary Single-Target Combo (Fallback)
1. Copy the pool's exact step for that connection (`model` string, step `id` shape, `label`). Mismatched model id fails early with `ALL_TARGETS_SKIPPED` (capability pre-filter) and masks the real upstream verdict.
2. Create temp combo (priority, no retries):
   - `POST /api/combos` with one model target: `{model: <pool-identical>, providerId: antigravity, connectionId: <suspect>, strategy: priority, config: {maxRetries: 0, failoverBeforeRetry: true, maxSetRetries: 0}}`
3. Dispatch one minimal chat: `POST /v1/chat/completions` `{model: combo/<temp>, messages: [{role: user, content: 'Say OK'}]}`.
4. Control: repeat steps 2-3 with SAME model id on a known-good `connectionId`.
5. Cleanup: `DELETE /api/combos/<temp-id>` for every temp combo.

## Verdict rule
- Control 200 + suspect 403 `quota_exhausted` / `insufficient_quota` across 2+ model families (e.g. `gemini-3.7-flash-high` + `claude-sonnet-4-6` + `gemini-3-flash`) = connection-scoped credential failure, not model/combo.
- Pool-level 200 during this time proves nothing about the suspect (traffic served by siblings).

## Pre-checks that change the verdict
- **Proxy:** join `proxy_assignments` → `proxy_registry`, `socket.connect_ex` host:port. Dead proxy gives timeout, not 403. Reassign via `PUT /api/settings/proxies/assignments` and re-probe before declaring credential dead.
- **Quota source:** `key_value` / `providerLimitsCache:<connId>`. `fetchAvailableModels used:0` is a fallback mask; `retrieveUserQuota` with nonzero used is real. Direct `streamGenerateContent` envelope returning `401 UNAUTHENTICATED` = token rejected upstream → re-OAuth.
- **Provider /test is not proof:** writes a `connection-test` row, can return `active` + `probe 400 inconclusive`. Only real chat dispatch counts.
- **Host quirk & Auth URL binding:** Always use `http://192.168.110.123:20129/v1` (or the configured `OMNIROUTE_BASE_URL`) with `Bearer $OMNIROUTE_API_KEY` (`sk-068...237c`). Probing `localhost:20129/v1` without the auth header or with wrong loopback interface will hang or return 401/404.
- **Probe Timeout & Cascade Protection:** Inactive/expired accounts or bad upstream proxies often hang the connection instead of returning an immediate error. Always pass a strict timeout (`timeout=8.0` on SDK client or `--max-time 10` on curl) and NEVER probe suspects sequentially in an unbounded loop inside an interactive turn; otherwise the socket wait triggers the 180s gateway fallback ("The model provider failed after retries"). Probe 1-2 representative accounts first or use fast-fail concurrency.

## Evidence to record
- Suspect `connectionId` (short prefix ok), model ids tested, status codes, `call_logs` rows (`status, model, account, error_summary, combo_name, timestamp`), proxy name/host:port + OPEN/CLOSED, quota source per connection.
- Never paste tokens, secrets, or request bodies.
