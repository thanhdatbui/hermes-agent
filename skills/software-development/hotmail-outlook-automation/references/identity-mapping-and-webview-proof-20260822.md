# Identity mapping and WebView proof handling — 2026-08-22

## Durable lessons

- Resolve the exact source row before interacting with a live device. A duplicated TikTok ID is not enough: compare machine, ID, TikTok password, recovery Gmail, mail password, and 2FA.
- If the authoritative workbook Gmail matches the masked proof shown on-device, do not ask the user to supply or reconfirm the Gmail. State the workbook evidence and proceed.
- Make a backup before mutating the workbook. After clearing a wrong row, re-open the saved workbook and verify both that the wrong Gmail is absent and that the intended correct row remains populated.
- On a recovery/password-change screen, an email label being visible does not mean it is selected. Require selector/radio proof or an enabled Continue button. If Continue remains disabled after bounded ATX/semantic interaction, stop without sending a code or changing the password.
- Microsoft/TikTok WebViews may expose labels while hiding the interactive radio in the accessibility hierarchy. ATX remains the primary action path; coordinate fallback must be bounded by a known screen signature and verified after the action. Repeated blind taps are not a recovery strategy.
- Handle device locks through the lease API. A completed batch can leave retained `handoff` artifacts; inspect payload ownership and use authorized takeover only when needed. Release the diagnostic lease explicitly after the action; do not manually delete lock files as the normal path.

## Session evidence pattern

The on-device proof was a masked Gmail address. The exact corresponding Gmail was found in the authoritative TikTok workbook row, so the mapping was established without user clarification. The recovery WebView showed the Gmail row and a disabled `Tiếp` button; bounded coordinate attempts did not enable it. Correct outcome: no OTP sent, no password changed, and the device lease was released.

## Reporting format

Report briefly:

1. Source row used and matched masked proof.
2. Whether the selector was actually enabled.
3. Whether any code or password mutation occurred.
4. Lock state after the attempt.

Do not include passwords, refresh tokens, client IDs, or full recovery credentials in the report.
