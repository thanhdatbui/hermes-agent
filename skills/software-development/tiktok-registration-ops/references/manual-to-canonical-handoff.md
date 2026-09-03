# Manual-to-canonical handoff

## Trigger

Use this whenever an operator intervention is needed to get a TikTok registration run past a popup, keyboard, disabled button, Outlook screen, or post-signup screen.

## Required sequence

1. **Do not treat the manual action as the fix.** Capture the exact UI state before and after: foreground activity, relevant text, node bounds, enabled/clickable/focused attributes, and the action that caused the transition. Redact email, password, OTP, tokens, and other credentials.
2. **Map the action to the canonical seam.** Find the existing helper/entrypoint that should own the behavior (`social_reg_v1.py`, not an ad-hoc reader or sidecar runner). Patch that helper rather than adding a one-off coordinate script.
3. **Encode the smallest robust behavior.** Prefer semantic UI resolution and fresh XML bounds. If coordinates are unavoidable, derive them from the current node bounds; do not reuse coordinates from a different keyboard/layout state. Preserve existing flow and tracking semantics.
4. **Exercise the edited code before the next live target.** Run `py_compile`, focused tests, and a diff review. If a test expectation encodes the old behavior, update the test to express the new contract and add a regression test for the old failure mode.
5. **Use the canonical entrypoint on the next attempt.** For a device already part-way through signup, use `social_reg_v1.py <stt> --resume` rather than restarting registration or continuing manual clicks. Let the script perform the final profile/tracking write.
6. **Verify by evidence, not exit code alone.** Require flow markers, a fresh TikTok profile/username proof when registration is claimed, and the canonical tracking result/workbook write. `PENDING`, `SKIP`, or an empty/init-only log is not success.

## Incident pattern retained from machine 57

- Password containing shell-significant characters was entered through the non-sensitive path; `$`/special characters were lost. The canonical fix was `sensitive=True` for both password fields so AdbKeyboard/base64 input is used.
- TikTok's Continue button was disabled or moved while the keyboard was open. The canonical fix hid the keyboard with Back, then resolved/tapped fresh bounds instead of relying on an old fixed coordinate.
- The post-signup name screen used `Tiếp tục`, while an older rename path used `Lưu`. The canonical helper now tries the appropriate semantic action/fallback.
- Outlook app handling must be wired into the existing mailbox orchestrator. Resolve the installed activity with `cmd package resolve-activity`; do not guess a component name. Popup dismissal and mail reading belong in the canonical Outlook handler.

## Anti-patterns

- Manually finish a device and then ask whether the script should be updated.
- Report success because a wrapper exited 0 while the worker logged `PENDING` or only a lock skip.
- Manually write tracking data after a run; resume the canonical script so its idempotent tracking path records the account.
- Run a fresh registration over a device paused mid-flow when a resume path exists.
