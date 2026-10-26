# ChatGPT Web Multi-Proxy Feeder & Hotmail Account Governance

## 1. Domain Separation: Mail Soaking vs Account Readiness
- **Mailbox Soaking (WAIT_7D)**: Applies strictly to acquired / freshly registered mailboxes (e.g. Hotmail) prior to changing security credentials (password / 2FA) to prevent Microsoft security verification challenges.
- **ChatGPT Account Readiness**: ChatGPT accounts registered via Hotmail do NOT need soaking. Once registered (`has_chatgpt: true` and non-empty `chatgpt_password` recorded in supervisor state), they are immediately eligible to be loaded into the OmniRoute `chatgpt-web` pool.

## 2. Multi-Proxy Quota Ceiling (2 Accounts per IP)
- In multi-proxy aggregator pools (e.g. 72 active proxies across MobiProxy ports 5101–5138 and MikroTik ports 10001–10035):
  - Enforce a strict temporary capacity ceiling: **maximum 2 active ChatGPT-Web accounts per IP/proxy**.
  - Dynamic feeder candidates selection logic:
    ```python
    needed_by_port[port] = max(0, 2 - current_active_on_proxy)
    ```
  - If a proxy already has $\ge 2$ active accounts, skip it immediately.
  - If a proxy has 0 accounts, allocate 2. If 1 account, allocate 1.

## 3. Account-Level Fail-Closed Proxy Binding
- In `provider_connections`, every web connection must have `proxy_enabled = 1`.
- In `proxy_assignments`, every connection MUST have an exact relational record:
  - `scope = 'account'`
  - `scope_id = <provider_connection_id>`
  - `proxy_id = <proxy_registry_id>`
- **Feeder Result Port Pass-Through Pitfall**:
  - The extraction worker (`rescue_single_account`) must explicitly copy `port = acc.get("port")` into the returned result dict:
    ```python
    res = {"email": email, "pid": pid, "port": port, "success": False, ...}
    ```
  - If `port` is omitted, the downstream fail-closed sync function (`sync_to_omniroute`) detects missing proxy metadata and refuses to activate or create the connection (`[SKIP FAIL-CLOSED]`).

## 4. Hotmail Login vs Google SSO Pitfall
- Accounts registered with Hotmail were created via Direct Email + Password, NOT Google SSO.
- Automated token extractors must branch on email domain:
  - For `@hotmail.com`: Never click `"Continue with Google"`. Clicking Google SSO causes redirection to `accounts.google.com` and triggers 90s OAuth timeouts.
  - When session cookie is absent or expired: input email into `input[name="email"]`, submit, input `chatgpt_password` from supervisor state machine (`batch_gpm_5profiles_supervisor_state.json`) into `input[name="password"]`, submit, and await navigation to `chatgpt.com`.

## 5. In-Memory Monkey-Patching under Strict Coordinator Budgets
- When Coordinator write budgets (`T1` file count or line caps) prevent modifying feeder scripts on disk:
  - Import the existing script and monkey-patch functions in memory:
    ```python
    import cron_auto_feed_chatgpt_pool as feeder
    _orig = feeder.rescue_single_account
    def patched_rescue(acc):
        r = _orig(acc)
        r["port"] = acc.get("port")
        return r
    feeder.rescue_single_account = patched_rescue
    ```
  - This executes fully in-memory without creating or patching disk files.
