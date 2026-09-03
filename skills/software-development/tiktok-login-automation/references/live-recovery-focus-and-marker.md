# Live recovery: focus, screenshot evidence, and OTP/magic-link markers

Use this for a **bounded, user-directed recovery**, not a registration runner.

## Safe sequence

1. Record `dumpsys window windows`, `dumpsys activity activities`, VPN state, and a screenshot before acting.
2. If Chrome/Outlook is foreground, launch TikTok without destroying its state:
   ```bash
   adb -s "$SERIAL" shell 'monkey -p com.ss.android.ugc.trill 1'
   sleep 2-5
   ```
   Do not `pm clear`, do not force-stop TikTok, and do not send signup/OTP input during diagnosis.
3. Immediately recapture focus/activity and screenshot. Treat this as a new observation.
4. After OCR or any slow evidence processing, verify focus/activity again and save a final screenshot. A farm process may switch the device back to Chrome/Outlook between captures; an old TikTok focus line is not final proof.

## Classification gate

- Only click `Đăng ký` or the email continuation when the screenshot/XML explicitly shows signup or method selection.
- OTP mode markers include `Nhập mã ... 6 chữ số`, `mã xác nhận`, `verification code`, `resend code`, or `Gửi lại mã`. If OTP entry/resend is prohibited, stop and report `FINAL_BLOCKED`.
- Magic-link markers include `Kiểm tra hộp thư`, `liên kết`, `link`, `Xác minh email`, or `Bạn có thể đăng nhập bằng liên kết`. Never substitute a numeric code.
- An activity such as `CommonFlowActivity` is not enough to identify the mode; classify from visible markers.

## Evidence bundle

Save, under LocalAppData, at least:

- `before` and `final` screenshots;
- `focus` and `activity` text captures from ADB;
- OCR output when XML is unavailable;
- UI dump output and its failure log, if attempted;
- a short `final_decision.txt` stating status, focus, exact markers, and actions deliberately not taken.

If UiAutomator returns a killed/non-XML payload, do not invent selectors or claim the XML state. Screenshot/OCR can still prove a high-confidence marker; include the failed XML log so the limitation is auditable.

## Reporting

Keep the user-facing report short and in Vietnamese: `FINAL_BLOCKED`/result, current focus, exact mode marker, no OTP/resend/no blind signup action, and the evidence directory. State that the repo was left untouched when that was requested.
