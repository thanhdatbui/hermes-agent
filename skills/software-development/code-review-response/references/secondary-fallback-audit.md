# Secondary Fallback Audit Recipe

## Trigger

Use this when a patch adds a stricter classifier/reader or claims that an unsafe legacy fallback is no longer used. Typical examples include login-vs-registration seam classification and numeric OTP mailbox reads.

## Procedure

1. **Define the protected contract.** Write down the exact forbidden behavior, such as: “numeric Hotmail/Outlook OTP may only come from the verified newest-row reader; stale CDP/browser preview readers are forbidden.”
2. **Inventory symbols.** Search the repository for every call to the primary reader, every legacy reader, and every shared retry/resend helper. Include helpers called only after failure.
3. **Trace all branches.** Review separately:
   - initial success path;
   - primary reader returns `None`;
   - timeout/exception path;
   - code rejected by the target UI;
   - shared resend/recovery path;
   - post-refresh re-read path.
4. **Check control-flow claims against code.** A nearby comment such as “never fall back to CDP/browser” is not evidence. Any reachable call from a protected path is a finding, even if the normal path avoids it.
5. **Use negative call-site tests.** Monkeypatch forbidden readers to record calls or return a decoy old code. Assert they are not called when the strict reader fails, after resend, and after refresh. Also assert the decoy code is never entered.
6. **Run static closure.** Perform a final search for the forbidden symbols and inspect every occurrence in context. Do not approve solely because focused tests pass.

## Evidence and verdict

Report the exact locator for the remaining call, the triggering branch, and the passing tests separately. A test suite can prove the intended path while a static/control-flow finding proves the implementation is still unsafe. For a P0/P1 contract violation, the verdict remains `REJECT` despite green focused tests.

## Key lesson from the TikTok Reg/Login seam audit

The initial handler correctly selected `_try_get_otp_outlook_newest()`, and 86 focused tests passed. However, `_request_and_read_fresh_tiktok_email_otp()` still called `_try_get_otp_outlook_cdp()` and `_try_get_otp_browser()` after the newest reader failed, including again after a rejected-code refresh. The implementation therefore contradicted its own fail-closed comment and had to be rejected.
