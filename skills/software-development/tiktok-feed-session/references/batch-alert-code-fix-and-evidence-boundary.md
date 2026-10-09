# Batch alert: code fix and evidence boundaries

## Trigger
Use when a user sends a multi-machine TikTok feed alert and asks to investigate/fix the failures.

## Correct workflow
1. Keep the batch locked; do not treat canary as a substitute for investigation.
2. Run `python D:/Taadaa/tools/inspect_machine.py <N>` once for every explicitly named target. This is current-state evidence only.
3. Read the newest target-scoped log/artifact before assigning a root cause. Separate:
   - **Code-level proof:** source path, exact exception path, diff, focused mocked test.
   - **Live-incident proof:** matching XML/screenshot/log captured at failure time.
   - **Current device state:** result of present-time inspection; it cannot prove what happened earlier.
4. Dispatch a worker for the code investigation/fix. Preserve unrelated dirty files and keep the patch contract narrow.
5. Before accepting a wrapper/retry patch, inspect the canonical call chain. Verify whether the original exception is propagated, translated (for example to `NO_HANDLER_IMPLEMENTED` or `PROFILE_ROOT_NOT_CONFIRMED`), or swallowed. Never accept a retry that catches only a code that the callee no longer emits.
6. Require `git diff --numstat`, `git diff --check`, and one offline/mock focused test under 30 seconds. A failure in an unrelated existing test is evidence of that test failure, not proof of patch success.
7. Run the official live canary only after the code patch is verified; do not reopen the fleet before canary evidence passes.

## Classification pitfalls
- `ATX_SESSION_UNAVAILABLE`, `ACCOUNT_MISSING`, and login-screen detection are failure signatures, not proven root causes by themselves.
- A current `LauncherActivity`/sleeping screen does not prove that the earlier failure was ATX outage, logout, or missing account.
- If live XML/screenshot/log evidence is missing, report the live cause as `UNPROVEN` while still fixing a separately proven code-level hazard.
- Do not use ad-hoc ADB taps, logout, `pm clear`, or ATX restarts as the definition of “fixed.”

## Session-derived evidence
The account-switcher consumer wrapper was initially proposed as a retry seam, but canonical navigation could translate or swallow `ATX_SESSION_UNAVAILABLE`; this was the reason to verify the exception path before accepting the wrapper. A focused test also exposed an unrelated existing anchor expectation failure (`expected (540,616), got (50,50)`), which must be reported separately rather than silently changed.
