# Registration Route Sentinel Propagation

Reusable audit recipe for registration/login classifiers whose producer returns route states such as `registered`, `registered_otp`, `registered_auto_login`, `registered_deferred`, `verify_email_pending`, and `unknown`.

## Boundary matrix

For every production boundary, record:

| Boundary | Producer output | Caller action | Safe contract |
|---|---|---|---|
| pre-submit classifier | `login` / `signup` / unknown | submit detector | preserve explicit entry context |
| post-submit detector | registered/password, registered/OTP, auto-login, registration | registration/login wrapper | registered outcomes must not enter registration |
| current-screen fallback | registered OTP, magic-link pending, unknown | current-screen handler | defer registered OTP; continue only signup magic-link/numeric; unknown fails closed |
| terminal runner | deferred sentinel | retry/recovery/lock manager | terminal blocked state; retain UI and lock; no generic recovery |

## Procedure

1. Enumerate every spelling returned by the producer and every spelling consumed by each caller. Include wrappers and standalone/live entrypoints, not just the shared core.
2. Inspect both the normal post-submit path and the already-on-screen fallback path. They often have separate branches and can disagree.
3. For each registered result, trace whether any caller performs OTP fetch, resend, password generation/submission, BACK/HOME, relaunch, cleanup, tracking, or generic recovery before the defer guard.
4. Verify the defer sentinel reaches the terminal runner and that the runner preserves the current UI and retained device lock rather than routing through transport recovery or retry.
5. Test the route matrix offline: password, OTP already visible, OTP after submit, trusted feed/profile auto-login, signup magic-link, signup numeric OTP, unknown screen, and explicit-email/no-cross-email fallback.
6. Add an AST/source probe for all production calls to the classifier and all comparisons against route sentinels. A focused unit suite can be green while an older wrapper still accepts `registered_otp` and continues login.
7. Report only P0/P1 findings when the user requests a findings-only audit, with exact `file:line` locators and a minimal producer → propagation edge → consumer repair plan.

## Common failure pattern

A core function may correctly convert `registered_otp` or `registered_auto_login` to `registered_deferred`, while a live wrapper still accepts the pre-conversion state (`registered_otp`) and proceeds into OTP/password handling. This is a real control-flow defect even when the core classifier tests and runner terminal-state tests pass. The fix must be made at the wrapper boundary or the wrapper must consume the canonical deferred result.

Never treat a passing focused classifier suite as proof of end-to-end propagation; prove the exact caller chain.
