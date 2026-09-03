# Captcha close-X recovery regression

## Incident pattern
`classify_tiktok_screen()` can see Captcha/verification text and classify the screen as `manual-needed:manual_challenge` or `manual-needed:verification` before the existing typed popup dispatcher gets a chance to run. This creates a false stop when the exact Captcha overlay has a safe, UI-identified close `X`.

## Correct behavior
- Captcha puzzle with the verified puzzle close-X: classify as the existing recoverable popup path (`manual-needed:popup`) so `detect_tiktok_popup_action()` / `dismiss_verify_dialog()` can close it and re-capture the UI.
- Captcha/verification with no verified close-X: retain fail-closed `manual-needed:manual_challenge` / `manual-needed:verification`; do not tap blindly or remove safety globally.
- Do not broaden a generic verification detector: quick-security, verify-email prompts, OTP/input screens, and unrelated dialogs must keep their specific classifiers and safety behavior.
- The existing post-dismiss re-capture is the proof of recovery. A close action alone is not success.

## Focused regression recipe
1. Use an XML fixture containing Captcha text plus the real puzzle close-X and, if present, the injected `verify-bar-close` banner node.
2. Assert the classifier selects the recoverable popup route and never mistakes `verify-bar-close` for the puzzle X.
3. Keep a paired fixture with the Captcha text but no puzzle close-X; assert it remains blocked.
4. Run focused classifier/popup/safety tests, then the feed/session tests covering Captcha/verification and popup dismissal.
5. Run `compileall` and `git diff --check`.

## Scope and safety
This change is classifier/flow logic only. Do not run a live farm machine merely to validate the classification change unless the user explicitly requests a controlled run. When the worktree already contains user changes, preserve them and inspect the diff before editing; do not restore an entire file to HEAD as a shortcut.
