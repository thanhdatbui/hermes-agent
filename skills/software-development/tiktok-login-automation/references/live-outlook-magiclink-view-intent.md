# Live Outlook magic-link recovery via Android VIEW intent

Use for a user-directed, no-code-change recovery when TikTok is already on a confirmed magic-link screen such as `Kiểm tra hộp thư của bạn` + `liên kết` + `Gửi lại email`.

## Safety gates

- Do not press `Gửi lại email` when a fresh matching mail is already present.
- Do not search for or enter a six-digit code while TikTok is in magic-link mode.
- Do not click a mail anchor until the newest message is proven by subject and visible timestamp.
- Do not use `find_text_tap("TikTok")`: Outlook can group messages/leave many stale tabs, and the first row may be an old OTP mail.
- Do not use CDP JavaScript `.click()` for the verification link; it can navigate Chrome to TikTok web instead of invoking the Android app.
- Preserve TikTok state: bring Chrome with `monkey -p com.android.chrome 1` only; never `pm clear`, force-stop TikTok, or restart the registration flow.

## Proven bounded sequence

1. Capture before-state artifacts under `C:\Users\Kibe\AppData\Local\Tiktok_Reg\`:
   - `*_before_focus.txt`, `*_before_activity.txt`, `*_before.png`
   - bounded XML attempt and `*_before_xml.log`
2. Bring Chrome without destroying app state and capture `*_mail.png`, focus, and activity.
3. If Chrome remote debugging is available:
   ```bash
   adb -s <serial> forward tcp:9222 localabstract:chrome_devtools_remote
   curl http://127.0.0.1:9222/json/list
   ```
   Select the live Outlook page, then read-only-evaluate `document.title`, `location.href`, `document.body.innerText`, and anchors whose href contains `tiktok.com/ucenter_web/deeplink/email_verification`.
4. Require all of:
   - Outlook domain / live mailbox evidence;
   - subject equivalent to `Hoàn tất đăng ký bằng cách xác minh email của bạn`;
   - newest visible message timestamp (example: `T3 11/08/2026 11:22 CH`);
   - exactly one matching verification anchor for the selected message.
   Save the complete selected href locally (it contains a one-use token; do not paste it into normal chat output).
5. Open the exact href through Android intent, not a tap:
   ```bash
   adb -s <serial> shell am start -a android.intent.action.VIEW -d '<exact-href>'
   ```
   Save the intent output, then wait a bounded interval and recapture focus/activity/screenshot.
6. Final classification:
   - `CommonFlowActivity` + `Nhập mã gồm 6 chữ số` / `Gửi lại mã`: link transition succeeded, but the next OTP step is required. If OTP is forbidden, stop without input and report `LINK_VERIFY_SUCCESS_NEXT_STEP_OTP` (or the project's equivalent), not `VERIFIED_SUCCESS`.
   - account/feed/password-required: `VERIFIED_SUCCESS` with focus and screenshot/XML proof.
   - link does not transition or is expired: `FINAL_BLOCKED`; preserve the exact error UI and artifacts. Do not resend unless the user explicitly allows it.

## Recovering UI evidence when shell dump is killed

A Samsung `uiautomator dump` can return exit 137 even though the app UI is visible. Keep the failure log; do not fabricate selectors. If atx-agent/uiautomator service is already available, use the read-only HTTP hierarchy endpoint:

```bash
adb -s <serial> forward tcp:17912 tcp:7912
curl -fsS http://127.0.0.1:17912/dump/hierarchy > live_recovery_<target>_atx_dump_response.json
```

The response is JSON-RPC; extract its `result` string into the final XML artifact, then classify exact `text`/`content-desc` nodes. A bounded atx service restart may be used only to restore evidence collection; it must not restart TikTok or touch app data.

## Evidence/report contract

Keep the user-facing report short: status, current focus/activity, exact markers, prohibited actions not taken, and the LocalAppData evidence directory. Include subject/timestamp and the verification-anchor pattern, but redact the full tokenized href from chat. State explicitly that the repo, code, workbook, and lock were untouched when requested.
