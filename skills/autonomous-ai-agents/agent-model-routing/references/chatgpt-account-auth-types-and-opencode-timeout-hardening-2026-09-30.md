# ChatGPT Web Account Auth Dual-Flow & OpenCode Bridge Timeout Hardening (2026-09-30)

## 1. ChatGPT Web Account Authentication Dual-Flow Invariant (User Correction)

### Problem
Automation recovery scripts (e.g. `cron_chatgpt_web_pool_watchdog.py`) historically assumed all ChatGPT Web accounts logged in via Google SSO (`Continue with Google`). When recovering newer accounts that were registered directly with Email + Password, the script hung or looped trying to click nonexistent Google SSO elements.

### The Invariant
ChatGPT Web accounts in the farm are split into two registration cohorts:
1. **Early Cohort (Google SSO)**:
   - Click `Continue with Google` / `Tiếp tục với Google`.
   - Pick Google identifier / account from account chooser.
   - Approve Google OAuth Consent.
2. **Later Cohort (Direct Email + Password)**:
   - Input Email into `#identifierId` or `input[name="identifier"]` -> Click `Next` / `Tiếp tục`.
   - Input Password into `input[name="Passwd"]` or `input[type="password"]` -> Click `Next` / `Tiếp tục`.
   - Submit TOTP if 2FA is active (`#totpPin`).

### Recovery Automation Requirements
- Detect current page state dynamically:
  - If direct email input is present -> Fill email + password.
  - If SSO / Google login is present -> Execute SSO flow.
  - If OpenAI Onboarding asks for Age (`input[name="age"]`) -> Fill `24` to avoid 60s session drop.
- **5-Worker Parallel Execution**:
  - Run with `ThreadPoolExecutor(max_workers=5)` at 05:00 AM daily.
  - Desktop GPM automation runs in memory (32-64GB host RAM) and is strictly decoupled from the physical Android phone farm.
- **Token Extraction**:
  - Extract `__Secure-next-auth.session-token` (re-assemble chunked cookies `.0`, `.1`, ...) rather than raw semicolon strings.
  - Directly update OmniRoute SQLite DB (`provider_connections.api_key`), reset `test_status = 'active'`, `is_active = 1`, and clear `last_error`.

---

## 2. OpenCode HTTP Bridge Timeout Hardening (`opencode_bridge.py` on :20130)

### Problem
When the primary provider socket dropped transiently, Hermes triggered its fallback chain to `custom:opencode` (`opencode/muse-spark-1.3-contributor-free`).
Hermes immediately logged:
```text
[Error: OpenCode opencode/muse-spark-1.3-contributor-free request timed out after 35s]
```

### Root Cause
In `D:/Taadaa/tools/opencode_bridge.py`:
```python
timeout = 45 if image_paths else 35
```
A hardcoded 35-second subprocess timeout prematurely killed the `oc_farm.py` subprocess. While small ping prompts take ~12s, full agent context windows (20K+ tokens of tools, rules, and history) require 40s–60s in OpenCode's cloud queue.

### Remedy
- Raised timeout:
  ```python
  timeout = 120 if image_paths else 90
  ```
- Restarted bridge process (PID 22708).
- Verified live Vietnamese response in 14.06s with 200 OK.
