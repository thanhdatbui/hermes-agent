# GPM Pure Login Closeout Handoff Lessons (2026-10-21)

## What worked
- Use GPM Local API v3 to start the profile, obtain `remote_debugging_address`, and attach with Playwright `connect_over_cdp`; do not inject a second proxy into the CDP path.
- Treat persistence as a restart property: a `login_only_success` event is not sufficient. Stop the profile, start it again through GPM API/CDP, and verify authenticated URL/body/identity.
- Before closeout, add offline mocked tests for explicit profile ID, paginated unique email match, zero/duplicate match fail-closed, start/missing-CDP-address failure, and stop/cleanup failure.

## Closeout failure modes
- `NEED_CONTEXT:<path>` means the reviewer payload was truncated or lacked the requested file context. It is not approval, not a zero-quality verdict, and not a reason to report DONE. Compact duplicate tests with helpers/parametrization while preserving strict assertions, or use the mandated reviewer handoff.
- A focused test result and Canary gate are necessary but do not replace the strict closeout verdict. Report exact score/verdict/exit code and continue remediation when the active policy requires `>=85`.
- After the configured strike threshold, stop Sol/Coordinator guesswork and dispatch the reviewer handoff with a frozen production-file scope. The handoff is not completion; verify the resulting diff and focused tests independently.

## Communication correction
- When the operator is frustrated, use concise Vietnamese: state the mechanical result first, own the specific workflow mistake once, then execute the next allowed remediation. Do not answer with a long apology, a menu of options, or a promise without a tool action.
