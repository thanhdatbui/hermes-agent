# ChatGPT Web Pool Feeder & Proxy Assignment Standards

## 1. Domain Separation: Mail Soaking vs AI Account Usability
- **Hotmail / Gmail Soaking**: Newly registered mail accounts undergo a cooling/soaking period (e.g. 7 days `WAIT_7D`) before security modifications (changing recovery mail, password) to prevent Microsoft/Google automated account locks.
- **ChatGPT Account Usability**: Once ChatGPT registration completes successfully, the AI account is immediately usable. Do **not** delay feeding ChatGPT accounts into OmniRoute under the assumption that the AI session requires soaking.

## 2. Multi-Account Proxy Density Invariant (≥ 2 Accs / IP)
When distributing accounts across proxy fleets (e.g. 72 active proxies covering MobiProxy 4G and MikroTik ports):
- **Density Target**: Every active proxy must be backed by at least 2 active ChatGPT Web connections to maintain redundancy and load-balancing headroom during tool-heavy sessions.
- **Relational Integrity in OmniRoute (`storage.sqlite`)**:
  - `provider_connections`:
    - `provider = 'chatgpt-web'`
    - `is_active = 1`
    - `proxy_enabled = 1`
    - `apiKey = <session_token>`
  - `proxy_assignments`:
    - `scope = 'account'`
    - `scope_id = <provider_connections.id>`
    - `proxy_id = <proxy_registry.id>`
  - `combos` (`chatgpt-web-pool`, `gpt-web-sol`):
    - Append `{ "id": ..., "kind": "model", "model": "chatgpt-web/auto", "providerId": "chatgpt-web", "connectionId": cid }` to `cb_data["models"]`.

## 3. The SSO vs Direct Login Trap in ChatGPT Web Feeders
- **Symptom**: Auto-feeder hangs or times out after 60-90s at `accounts.google.com/v3/signin/identifier` with zero session tokens extracted.
- **Root Cause**: Scripts written for Gmail profiles hardcode clicking `"Continue with Google"` (`js_click_google`). When processing Hotmail or custom domain profiles, this redirects to Google OAuth, which cannot authenticate non-Google addresses.
- **Remediation**:
  1. Inspect email domain before acting.
  2. For `@hotmail.com` / direct accounts:
     - Check if Playwright browser context already possesses an active `__Secure-next-auth.session-token` cookie. If yes, extract immediately without navigating the login form.
     - If session has expired or login page is visible, bypass Google SSO buttons. Fill email into `input[name="email"]` or `input[type="email"]`, click Continue, then fill `chatgpt_password` from supervisor state (`batch_gpm_5profiles_supervisor_state.json`) into `input[type="password"]`.
