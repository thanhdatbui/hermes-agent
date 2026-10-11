# Reviewer combo and two-pool salvage runbook

## Canonical reviewer routing

Use the OmniRoute `review` combo for closeout/reviewer work. The intended priority order is:

1. `chatgpt-web-pool` / ChatGPT-Web Sol primary.
2. `codex-terra` combo-ref as the immediate Terra Codex fallback.
3. Existing lower-priority fallbacks only after both primary and Terra are unavailable.

Verify before use:

- `GET http://127.0.0.1:20129/api/combos` and inspect the `review` combo.
- Confirm tier 0 is the ChatGPT-Web pool and tier 1 is a `combo-ref` to `codex-terra`, not merely one Terra model connection.
- Confirm `strategy: priority`, `failoverBeforeRetry: true`, and a bounded target timeout.
- Smoke-test `POST /v1/chat/completions` with `model: review`; a `200` response proves the combo is routable, not that every underlying account is healthy.
- Closeout must invoke `closeout_gate.py --model review` so the configured combo, rather than a manually selected single provider, performs the review.
- Never freeze or abort execution when the primary reviewer (ChatGPT-Web Sol) hits transient errors or rate limits. The combo automatically delegates to Codex Terra. When running manual tests, always fall back to the secondary models configured in the combo rather than stopping with an error.

## Two-pool cleanup and rescue

Target only the two relevant providers:

- `chatgpt-web` for the Sol Web pool.
- `codex` for the Terra Codex pool.

Read the current connection list from `GET /api/providers`. Do not infer health from combo membership or a pooled `200`: a pool can fail over to another account. For per-account verification, use `POST /api/providers/{id}/test` or an equivalent connection-pinned probe.

Classify conservatively:

- `active` / successful probe: retain.
- `429`, `usage_limit_reached`, quota exhausted, or cooldown: retain; the account is alive and temporarily limited.
- `expired`, `401`, `invalidated oauth`, or `Token invalid or revoked`: do not delete first. Attempt OAuth refresh/re-auth through the account's assigned proxy. Update the connection only after receiving and validating a replacement token.
- `banned`, `account_deactivated`, permanent upstream deactivation, or confirmed irreversible 403: remove from the OmniRoute pool only. Preserve the original GPM profile, Hotmail/farm record, and any external asset. User reminder: an OmniRoute/upstream `banned` status represents genuine deactivation/blocking, not an erroneous label from OmniRoute. Do not misclassify true deactivations as minor probe glitches.
  * Verified via live GPM login & Graph API OTP: when entering the 6-digit OTP from `noreply@tm.openai.com`, OpenAI directly responds with `error_code: account_deactivated` and an email from `trustandsafety@tm.openai.com` confirming access is disabled. Banned is real server-side account termination.
- `Cloudflare blocked / Sentinel / Turnstile required`: accounts whose web session tokens or Turnstile clearance have died and cannot complete upstream validation. Remove from active combos (`chatgpt-web-pool`, `gpt-web-sol`) immediately to stop dragging down pool latency.
- transient timeout, 5xx, SSL, or proxy failure: retry/probe through the same account's assigned egress before classifying; never call it dead from one transient result.
- `error` with insufficient evidence: quarantine/deactivate routing temporarily only if operationally necessary, record the evidence, and leave the farm asset untouched.

## Dangling combo model synchronization (Critical Pitfall)

Deleting rows from `provider_connections` in `~/.omniroute/storage.sqlite` does NOT automatically clean the `models` list stored inside `combos.data`!
Note schema: `combos` table has columns `(id, name, data)`, NOT `(id, name, models)`. The model list is nested inside JSON `data['models']`.
If dead connection IDs remain inside `combos.data`:
- OmniRoute retains in-memory references to deleted connection IDs.
- Live traffic and test probes will attempt routing to non-existent connections, causing artificial timeouts and delay spikes before failover.
- **Mandatory 2-step sync**:
  1. Update `combos.data` JSON in SQLite: filter `models = [m for m in models if m.connectionId not in deleted_ids and m.connectionId in valid_db_ids]`.
  2. Hot-reload in-memory routes via REST: for each modified combo, execute `PUT http://127.0.0.1:20129/api/combos/{id}` with the filtered body.
  3. Canonical script: `python D:/Taadaa/tools/clean_omniroute_pools.py` handles the full audit, DB deletion, combo JSON filtering, REST PUT hot-reload, and live smoke test.

## Automated GPM Login Verification & Re-Auth Pitfalls

When automating GPM browser logins to verify OpenAI accounts or recover pools (`login_audit_and_purge_deactivated.py`):

1. **Button selector mismatch on `chatgpt.com/auth/login`**:
   - `b.innerText.includes('Tiếp tục')` or `includes('Continue')` will match the first button containing that text: **"Tiếp tục với Google"**!
   - This causes unwanted redirection to `accounts.google.com/signin`, where OTP is mistakenly typed into Google's email field.
   - **Mandatory filter**:
     ```javascript
     const contBtn = buttons.find(b => {
         const t = (b.innerText || '').trim();
         return (t === 'Tiếp tục' || t === 'Continue' || b.type === 'submit') &&
                !t.includes('Google') && !t.includes('Apple') && !t.includes('thoại');
     });
     ```
   - Always verify URL changed to `auth.openai.com/email-verification` before attempting to fill OTP.

2. **GPM profile name substring matching**:
   - Profile names in GPM often include indexing and proxy port suffixes (e.g. `06 - KamilahRannels635404@hotmail.com - 5106`).
   - Exact equality matching (`email == profile_name`) yields 0 matches. Always use substring matching (`email.lower() in (p.get("name") or "").lower()`) and paginate through GPM API (`page=1..N`).

3. **Distinction between LIVE verification vs RE-OAUTH**:
   - Detecting that an account is LIVE on GPM browser (retaining active session, entering chat interface) is NOT the same as re-authenticating the router.
   - Simply confirming "LIVE" does not inject new credentials into OmniRoute/9Router.
   - To make live accounts usable in OmniRoute/9Router:
     * For **ChatGPT-Web**: Extract session cookie `__Secure-next-auth.session-token` or access token from `/api/auth/session` via CDP, then create/update connection in `:20129`.
     * For **Codex**: Must perform OAuth PKCE via `127.0.0.1:20128/api/oauth/codex/authorize` + callback on port 1455 + select personal workspace card to obtain fresh `refresh_token`.

4. **Visual evidence invariant**:
   - Never report `account_deactivated` or `LIVE` without verifying through native OCR or vision inspection first. Claiming an error screen while sending an image stuck at Google sign-in is a critical failure.

5. **Dual-Channel OTP Retrieval (Graph API vs Webmail Fallback)**:
   - **Rule (Invariant)**: Microsoft Graph API (`https://graph.microsoft.com/v1.0/me/messages`) ONLY applies to Hotmail accounts that have an active OAuth `refresh_token` and `client_id`.
   - Accounts without tokens or whose refresh tokens expired will return `HTTP 400 Bad Request` / `invalid_grant`.
   - **Mandatory Webmail Fallback**: When Graph API fails or token is missing, the automation MUST open the mailbox directly via GPM browser (`https://outlook.live.com/mail/0/`).
   - **Reuse Canonical Login Code**: CẤM tự chế selector hay script login Hotmail tạm bợ. BẮT BUỘC tái sử dụng các hàm và selector chuẩn từ `D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py` và `read_otp_gpm.py`:
     * Selector input: `input[name="loginfmt"]`, `input[name="passwd"]`.
     * Selector submit: `#idSIButton9`, `input[type="submit"]`.
     * Selector switch password: `#idA_PWD_SwitchToPassword`, `a:has-text('Use your password instead')`.
     * Selector KMSI bypass: `#declineButton`, `#idSIButton9`.
     * Mail row reading: `[role="row"]`, `[role="option"]`, bóc regex 6 số OTP.

6. **Account Lifecycle State Machine & Re-OAuth Watchdog**:
   - **Persistent State (`chatgpt_account_lifecycle.json`)**: Save account statuses (`DEAD_DEACTIVATED`, `LIVE`, `UNKNOWN`) atomically to disk.
   - **$O(1)$ Skip on Dead Accounts**: Any account marked `DEAD_DEACTIVATED` must be skipped immediately in all future cron runs and manual sweeps — do not spin up GPM profiles or attempt OTP for confirmed dead accounts.
   - **Periodic Re-OAuth on Dropped Sessions**:
     * Cron/watchdog probes connection health on `:20129` and `:20128`.
     * When session drop (401 / unauth / expired) is detected, attempt re-login on GPM using Dual-Channel OTP.
     * If OpenAI displays `account_deactivated` ("Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"): capture screenshot proof to `D:/Taadaa/runtime/artifacts/deactivated_<email>.png`, update state to `DEAD_DEACTIVATED`, purge connection from OmniRoute & 9Router, clean combo models, and skip permanently.
     * If login succeeds (active chat / session established): extract `__Secure-next-auth.session-token` via CDP `Network.getCookies`, update connection credentials in SQLite & REST API, restore to combo routing, and record `LIVE`.
   - **Report Output**: Always emit structured audit JSON to `D:/Taadaa/reports/chatgpt_lifecycle_report.json` with counts (total audited, live, dead purged, skipped) and detail breakdowns.

## Safety and evidence

- Never print access tokens, refresh tokens, passwords, OTPs, or full account identifiers in reports.
- Never test a pooled endpoint without a connection pin when making an account-level death decision; a pooled `200` can be a false positive from failover.
- Keep 429 accounts in the pool and let routing/cooldown handle them.
- Before deleting any provider connection, capture the connection ID, provider, sanitized status, last error class, and deletion result in an audit record.
- Refresh/re-auth must use the correct per-account proxy; direct-host requests can contaminate or revoke a pool.
- A background sweep must be event-driven and notify on completion; do not silently poll a long-running sweep.
