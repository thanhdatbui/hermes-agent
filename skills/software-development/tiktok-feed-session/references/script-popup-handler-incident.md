# Script popup-handler incident: account-security update prompt

## Trigger
A Telegram alert showed the TikTok popup `Tài khoản của bạn cần được cập nhật` with the secondary action `Để sau`. The user later clarified that “handle script” meant fixing the automation, not tapping the live device.

## Correct interpretation
A screenshot of a live machine is evidence for the UI shape, not authorization for a live action. When the latest request says “handle script”, “xử lý trong script”, “sửa code”, or reports a recurring runtime exception, stay offline: inspect the classifier → dispatcher → consumer handler path, add a regression fixture, patch, and run focused verification. Only perform a live tap if separately requested.

## Root-cause pattern
The popup screen constant was defined in `core/benign_popup.py`:

```python
ACCOUNT_UPDATE_PROMPT_SCREEN = "manual-needed:account-update-prompt"
```

The consumer function `flows/benign_popup.py::dismiss_account_update_prompt_popup()` compared against that constant but did not import it. The runtime therefore raised `NameError: ACCOUNT_UPDATE_PROMPT_SCREEN is not defined` even though the classifier and shared popup detector were already present.

## Verification recipe
1. Confirm the consumer import boundary explicitly; do not assume a symbol in a sibling module is in scope.
2. Build an XML fixture containing the exact title, security-link body, clickable `Để sau`, and the other CTA.
3. Confirm classification is `manual-needed:account-update-prompt`.
4. Confirm typed dispatcher action is `dismiss_later_button` and selector bounds point to `Để sau`, not the security-link CTA.
5. Exercise the consumer handler with a temporary XML artifact and a post-action feed XML artifact. Assert one tap only, no link/security action, and verified post-capture.
6. Run compile, focused regression, and `git diff --check`. Do not run live merely to validate an offline import fix.

## Regression shape
The focused consumer test should assert:

- `dismiss_account_update_prompt_popup()` accepts the classified screen;
- `result.dismissed is True` after a verified post-capture;
- `result.selector["popup_type"] == "account_update_prompt"`;
- `result.selector["action"] == "dismiss_later_button"`;
- the only ADB action is a tap at the center of the verified `Để sau` bounds.

## Pitfalls
- Do not “fix” this by adding a generic `Để sau` rule: that label is also used by save-login and other security-sensitive dialogs.
- Preserve detector precedence and exact title/body evidence in the shared detector.
- A successful live click or a disappearing Telegram alert is not proof that the script is fixed.
