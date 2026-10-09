# Gmail-live gate and XML detector regressions

## Durable lesson

An optional/shared Gmail-live checker is a safety gate, not a convenience fallback. At the login call site, accept only an explicit `True`. Missing imports, missing/non-callable symbols, checker exceptions, and `None`/other unknown results must fail closed before app launch or any UI action. Keep explicit `False`/DIE handling intact.

## Offline regression recipe

1. Mock the checker with `True`, `False`, an exception, `None`, and a missing/non-callable value.
2. Assert the checker receives the normalized Gmail address.
3. Assert blocked outcomes return the project’s existing failure result and that `open_app`/entry-screen/navigation helpers are not called.
4. Assert non-Gmail addresses bypass the Gmail-specific gate.
5. Use package-scoped synthetic XML fixtures for confirmed detector states. Cover the M243 login-option sheet and M257 verification/OTP surface, then preserve existing new-account detection and unknown fail-closed behavior.
6. Run only the focused mocked test file and `py_compile`; no live ADB, browser, or network is needed for these semantics.

## Test-harness pitfall

A patch can define/import `check_gmail_is_live` without wiring it into `login_one_account`. A test that patches the symbol and only checks the final success result may miss this. Require an invocation assertion and a negative side-effect assertion so the regression test proves both dependency use and fail-closed ordering.
