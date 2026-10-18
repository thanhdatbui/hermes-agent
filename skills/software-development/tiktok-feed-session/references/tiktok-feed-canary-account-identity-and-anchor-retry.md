# TikTok feed canary: identity mismatch and profile-anchor retry

## Validated incident pattern

A bounded single-device `feed-session-smoke` run can complete the feed actions and profile navigation but return `manual-needed` when the expected account argument is wrong. In the validated run, the artifact summary recorded 3/3 swipes and successful profile navigation, while the final XML showed `@vophuc725`; the supplied expected account was a different value. Reclassify this as an input-contract mismatch, not a feed-flow regression.

## Evidence-first recovery

1. Keep the failed run directory and record exit code, summary, XML, screenshot, and artifact paths.
2. Read the final XML and run fresh WinRT OCR on the final screenshot to identify the displayed account and screen.
3. Separate flow evidence from identity evidence: successful swipes/profile navigation do not prove expected-account equality.
4. If the displayed identity is unambiguous, rerun once with that proven identity and the same bounded canary scope. Do not start a retry loop.
5. Accept PASS only when the corrected run returns success and the final screenshot is visually inspected as the intended Profile/TikTok screen without a blocking popup or black/partial render.

## Anchor retry rule

On profile/account-switch retry, prefer the original valid display-name switch anchor, then a freshly resolved valid display-name anchor, then a safe fallback. Do not let a username-only node (for example a `t3y` resource ID) replace a valid display-name anchor. Reject candidates without a center, without clickable=true, or with known username-only resource IDs; fail closed when no safe anchor remains.

## Evidence from the fix

- Focused test: 128 passed.
- Single-device canary with corrected identity: exit 0, 3/3 swipes, profile verification success.
- Final screenshot was inspected with vision; it showed the intended TikTok Profile screen without black screen or covering popup.
