# Account Logged Out Popup Triage & Farm Alert Policy

## 1. Context & Detection
- **UI Screen:** TikTok modal popup with title "Trạng thái tài khoản" (Account status) and body "Tài khoản của bạn đã bị đăng xuất. Hãy thử đăng nhập lại." (Your account has been logged out. Please try logging in again.) with an "OK" button.
- **Detector:** `core.benign_popup.detect_account_logged_out_popup(root)` checks for both title markers (`"trạng thái tài khoản"` / `"account status"`) and body markers (`"đã bị đăng xuất"` / `"logged out"`).
- **Classification:** `core.classifier` maps this directly to `manual-needed:login` (confidence 0.99, `manual_needed=True`).

## 2. Policy & Behavior
1. **Fail-Closed Gate:**
   - This popup is strictly an account/login safety state, **never** treated as a benign dismissible popup.
   - The automation must **not** tap "OK", press BACK, or attempt automated re-login blind actions.
2. **Farm Alert Dispatch:**
   - When encountering `manual-needed:login`, `send_farm_machine_alert` captures a device screenshot, overlays a red top banner (`[MAY {N}] - HH:MM:SS DD/MM`), and posts an alert to Telegram Farm Alerts group (`-5373649734`).
3. **Lock & Scene Preservation:**
   - The device lock transitions to `blocked` (with standard TTL 90m).
   - The device remains on the current screen (holding scene) so operators or dedicated recovery tools can triage the account credentials or status safely.
