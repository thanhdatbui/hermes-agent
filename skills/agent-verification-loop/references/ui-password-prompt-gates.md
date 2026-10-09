# UI Password-Prompt Gates

Session-derived checklist for browser automation that must save a password only
through the browser's native prompt.

## Production contract

- Keep the helper in a shared browser/CDP module.
- UI-only: locate a visible Save/Lưu button, click it, and return `True`.
- Return `False` on no prompt, wrong origin, invisible/unexpected control, or UI
  exception.
- Do not inspect or mutate SQLite, DPAPI, Chrome `Login Data`, or profile
  preferences from the helper.
- Track `password_submitted` in each flow.
- Invoke the helper only after the flow's authenticated success gate.
- Do not invoke it for `ALREADY_LOGGED_IN` unless the current flow explicitly
  possesses and submitted the password.

## Mocked test matrix

1. **Prompt present:** helper is called after password submission and before
   success bookkeeping; click is recorded and the returned status exposes the
   boolean result.
2. **No prompt:** helper returns `False`, no click occurs, and the main success
   path remains successful.
3. **Already logged in:** helper is not called because the password is unknown.
4. **Unexpected UI/error:** helper returns `False` and does not fall back to
   storage APIs or direct profile/database manipulation.
5. **Origin mismatch:** helper returns `False` without touching the button.

## Verification/reporting

Run the exact user-specified focused test command after the final source/test
edit, within the requested timeout. Report exact changed files, exact numstat,
real test output/exit code, and the limitation that Chrome may suppress or omit
the native prompt. Never claim password persistence merely because ChatGPT login
succeeded.
