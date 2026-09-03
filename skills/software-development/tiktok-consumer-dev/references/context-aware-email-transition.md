# Context-aware email transition verification

## Durable pattern

Shared TikTok email-submit screens reuse OTP and email-verification copy. The
post-submit classifier cannot safely infer whether the flow is login or signup
from those markers alone. Preserve the caller's proven pre-submit surface:

- existing login identifier form → `entry_surface="login"`
- signup email form → `entry_surface="signup"`

Check the actual call path, not just source strings. The focused assertion should
capture the kwargs received by `detect_after_continue` and require the exact
surface.

## Registration mode contract

After a signup submit, recapture the fresh TikTok XML and run the classifier at
the boundary. Only these values are valid:

- `numeric`: route to numeric OTP handling
- `magic-link`: route to evidence-backed magic-link handling
- `unknown`: capture evidence and raise the signup-mode error before calling the
  mailbox handler

Use one helper for the classifier → handler transition, then route all direct
registration, resume, fallback, and live-registration callers through it. This
prevents a later caller from reintroducing `signup_mode="unknown"` and silently
losing the classifier result.

## Focused offline probe

For live/device-prohibited tasks, monkeypatch the module boundaries and run a
small probe through the real functions:

1. Invoke the canonical login identifier caller; assert `entry_surface="login"`.
2. Invoke live login and live registration email callers; assert `login` and
   `signup`, respectively.
3. Feed numeric and magic-link XML fixtures into the shared registration helper;
   assert the mailbox handler receives the corresponding mode.
4. Feed an ambiguous/unknown XML fixture; assert the helper raises the
   fail-closed error and the mailbox handler is never invoked.
5. Restore every monkeypatch, delete the Temp probe, and label output
   **ad-hoc verification**, not suite green.

A Temp probe must add the repository root to `sys.path`; otherwise Python imports
from the Temp directory and reports a misleading `ModuleNotFoundError`. Generate
its path with `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py",
dir=tempfile.gettempdir())` and clean it after the run.

## Evidence from the originating session

The actual path was verified with an offline probe after one corrected launch:
`AD_HOC_VERIFICATION_PASS` and `TEMP_CLEANUP_PASS`. The first attempt lacked the
repo path in `sys.path`; that was a probe-launch defect, not a product failure.
Targeted tests also passed under the available clean Python 3.11 interpreter,
but the durable claim for this pattern remains the focused behavior assertions,
not a full-suite claim.
