# ChatGPT Account Lifecycle Engine, Dual-Channel OTP & Safe Purge Protocol

## 1. Overview & Problem Context
When maintaining a large pool of ChatGPT accounts (consumer web sessions) running over GPM browser profiles and multiplexed behind OmniRoute (`:20129`) / 9Router (`:20128`), accounts intermittently expire sessions or suffer permanent deactivations (`account_deactivated`).

Running a blind GPM browser launch for every account in a 70+ account pool causes immense resource waste (RAM/CPU) and slow cron execution. Furthermore, accounts purchased across different batches have heterogeneous credential structures:
- **Batch A (OAuth2 Graph)**: Contains Microsoft Graph OAuth `refresh_token` + `client_id`.
- **Batch B (Password-Only / Expired OAuth)**: Lacks valid refresh token; Graph API returns `400 Bad Request / invalid_grant`.

## 2. Dual-Channel OTP Retrieval Architecture

When OpenAI's login flow (`auth.openai.com`) triggers email verification requiring a 6-digit OTP:

```text
               [OpenAI Email Verification OTP]
                              │
               (Check if account has refresh_token)
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
       [Has Graph Token]            [No Token / Password Only]
               │                             │
    Call Microsoft Graph API                 │
               │                             │
       ┌───────┴───────┐                     │
    (Success)       (Failed)                 │
       │               │                     │
       ▼               └─────────────┬───────┘
   [Got OTP]                         │
                                     ▼
                    [Fallback: Outlook Webmail on GPM]
                    - Open tab: outlook.live.com/mail/0/
                    - Use canonical login selectors:
                      * Email: input[name="loginfmt"]
                      * Switch: #idA_PWD_SwitchToPassword
                      * Pass: input[name="passwd"]
                      * Submit: #idSIButton9
                      * KMSI: #declineButton / #idSIButton9
                    - Scan inbox text for \b(\d{6})\b
                    - Close tab and return OTP to ChatGPT form
```

### Critical Implementation Rules:
- **Always use canonical pre-existing login code**: Never reinvent Microsoft login selectors; use the tested selectors from `batch_gpm_hotmail_password_login.py` and `read_otp_gpm.py`.
- **Close the mail tab immediately**: After extracting OTP, close the tab (`/json/close/{tab_id}`) to free memory before continuing the ChatGPT CDP interaction.

## 3. Account Lifecycle Management & O(1) Skip Engine

All audit and healer runs must consult a durable lifecycle state file (`D:/Taadaa/runtime/chatgpt_account_lifecycle.json`):

### Lifecycle States:
- `DEAD_DEACTIVATED`: Account detected with OpenAI error `"Bạn không có tài khoản vì tài khoản đó đã bị xóa hoặc vô hiệu hóa"` (`error_code: account_deactivated`).
- `LIVE`: Account successfully authenticated, reached New Chat interface (`chatgpt.com`).
- `UNKNOWN`: Transient timeout, network glitch, or captcha challenge requiring operator intervention.

### O(1) Skip Invariant:
Before initiating GPM profile launch (`/api/v3/profiles/start/{id}`), check `state.get(email, {}).get("status") == "DEAD_DEACTIVATED"`.
If dead:
1. Log `[SKIP] Account {email} already marked DEAD_DEACTIVATED`.
2. Append audit event `SKIPPED_DEAD`.
3. Return `("SKIPPED_DEAD", proof_path)` in < 0.5s without touching GPM API or starting Chrome.

## 4. Safe Purge Protocol (SQLite & API Sync)

When `DEAD_DEACTIVATED` is confirmed:
1. **Proof Capture**: Capture full-window screenshot via CDP `Page.captureScreenshot`, save to `D:/Taadaa/runtime/artifacts/deactivated_{email}.png`.
2. **API Deletion**: Send `DELETE /api/providers/{p_id}` to both OmniRoute (`:20129`) and 9Router (`:20128`).
3. **SQLite Purge with Exact Matching**:
   - Query `provider_connections` in `~/.omniroute/storage.sqlite`.
   - Match account using exact match function (`is_account_match`):
     * `email.lower().strip() == target`
     * `name.lower().strip() == target` or delimited by space/parentheses (e.g. `email (GPM Web)`).
     * **NEVER use loose substring `target in email`**: A loose substring deletes unrelated accounts (e.g. deleting `user@domain.com` accidentally deletes `user@domain.com.vn`).
4. **Transaction Safety**:
   - Wrap SQLite operations in context manager `with conn:`.
   - Never leave unhandled exceptions without rollback.
   - Clean matching model IDs from `combos.data` JSON string (`chatgpt-web-pool`, `gpt-web-sol`, `review`).
   - Sync updated combo in-memory via `PUT /api/combos/{cid}`.

## 5. Live Session Re-OAuth & Token Extraction
When an account authenticates into ChatGPT successfully:
1. Call CDP `Network.getCookies` for `https://chatgpt.com`.
2. Extract cookie `__Secure-next-auth.session-token`.
3. Update `config.session_token` in `provider_connections` via SQLite and `PUT /api/providers/{id}`.
4. Record state `"status": "LIVE"`, `"has_token": true`.

## 6. Atomic Persistence Invariant
To prevent 0-byte corrupt state or report files when tasks are killed:
- Always write to temporary file first: `f"{path}.tmp"`.
- Call `os.replace(tmp_path, path)` for atomic rename.
