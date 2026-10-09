# Distinguishing Code Defects from Runtime / Environment Alerts (Account Switcher Case Study)

Date: 26/09/2026
Context: Investigation of batch failures across farm machines with alert signatures:
- `M7 ACCOUNT_SWITCHER_FAILED open_profile_root failed ATX_SESSION_UNAVAILABLE`
- `M11, M66 select account failed ACCOUNT_MISSING`
- `M40 login/account screen detected`

---

## 1. Core Rule: Root Cause Classification

Before modifying any canonical switcher code or writing speculative patches, strictly verify whether the failure signature is an internal code bug or an external environment/state failure:

### A. Environment & Daemon Failures (Non-Code Defect)
- **Signature**: `ATX_SESSION_UNAVAILABLE`, `HTTPConnectionPool(port=7912)`, `ConnectionRefusedError`, `EXIT=137 (Killed)`.
- **Reality**: Device is sleeping (`mScreenState=OFF`, `mAwake=false`), Dozing, or the background `atx-agent` / `uiautomator` service crashed/was terminated by Android low-memory killer.
- **Action**: Do NOT patch switcher code. The switcher logic is unreachable because the transport/RPC layer is down. The required action is a preflight wake-up probe + daemon restart on the device, or reporting the machine as an environment failure.

### B. Account / Application State Discrepancies (Non-Code Defect)
- **Signature**: `select account failed ACCOUNT_MISSING`.
- **Reality**: The switcher successfully opened the profile dropdown/bottom sheet and inspected the DOM/XML, but the designated target username does not exist in the logged-in session list (session expired, account logged out, or wrong device assignment).
- **Action**: Do NOT alter the matching logic or broaden fuzzy matching recklessly. Route the account to the login/reconcile pipeline (`tiktok-login-reconcile`) instead of declaring a switcher bug.

### C. Login Screen Interception (Non-Code Defect)
- **Signature**: `login/account screen detected`.
- **Reality**: App session is completely logged out or in a fresh-install/cold state showing the login wall/choice screen (`com.zhiliaoapp.musically:id/...` login options).
- **Action**: Account switcher requires an active profile session root. If the app is at the login screen, it cannot switch profiles. Trigger the login flow, not a switcher patch.

---

## 2. Abort & Anchor Contract Discipline

If within the first exploration turns evidence confirms the failure is due to device state (offline, sleeping, missing account, login wall) rather than a broken code invariant:
1. **ABORT** immediately. Do NOT touch production files (`AGENTS.md`, `PROJECT_RULES.md`, core runners).
2. Report the verdict as **UNPROVEN (Environment / App State issue)**.
3. Provide an **Anchor Contract** detailing the necessary preflight (wake/daemon health) or pipeline reroute (login reconcile) instead of fabricating a code fix.
