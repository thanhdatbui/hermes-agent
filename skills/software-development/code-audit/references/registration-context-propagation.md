# Registration Context Propagation Re-audit

## Contract

For context-aware TikTok email routing:

- Login email-submit callers pass `entry_surface="login"`.
- Signup/registration email-submit callers pass `entry_surface="signup"`.
- Every registration OTP/mail handler call passes `signup_mode` explicitly.
- If the registration caller cannot classify numeric vs magic-link mode, it passes the literal `signup_mode="unknown"`; the handler must fail closed before mailbox reads, resend, or live actions.
- A handler's default argument is not propagation evidence. The call site must be inspected.

## Read-only probe

1. Capture `git status --short`, `git diff --stat`, and the exact dirty diff before reviewing.
2. Parse all production Python files with `ast` and enumerate calls to both the classifier and OTP handler. Exclude tests, `.git`, `.runtime`, and generated caches from the production inventory.
3. For each `detect_after_continue` call, record the `entry_surface` keyword and compare it to the caller's proven surface.
4. For each `handle_tiktok_email_otp` call, record whether `signup_mode` is present. In registration wrappers, a missing keyword is P0 even if the handler accepts `None` by default.
5. Read the surrounding control flow to distinguish login OTP handling from registration OTP handling; filename alone is insufficient.
6. Run only offline focused tests and syntax checks. Do not use ADB, workbook, credentials, mailbox, or live artifacts.

## Failure pattern

A common incomplete fix updates the shared handler and the obvious registration branch, but leaves a resume/fallback branch or a live registration wrapper calling the handler without `signup_mode`. This can preserve the old heuristic path and bypass the new `unknown` fail-closed guard. A green classifier-focused test suite does not cover this call-site contract.

## Reporting

Use exact `file:line` locators. Classify an omitted registration mode as P0 when it can select numeric/magic-link/resend behavior or bypass fail-closed handling. Include the production call-site inventory and focused test result, then state whether the requested live-run gate is safe.
