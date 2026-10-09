# Coordinator anti-stall and fix-until-done

## Trigger
Use for farm incident alerts where the user explicitly asks to investigate/fix/recover until completion.

## Lessons from the account-switcher incident

1. **Do not turn a guard into a blocker.** A consumer rule forbidding cross-repo edits is not applicable after the user explicitly authorizes a shared/canonical fix. Dispatch the canonical worker with an exact allowlist and preserve unrelated dirty hunks.
2. **Separate gates.** Code/test, live canary, and fleet reopen are independent gates. Missing live evidence blocks canary/reopen only; it does not block offline source inspection, patching, or focused mocked tests.
3. **Stale fixtures are fixable work.** If a focused test fails because a mock has too few captures or returns the wrong post-navigation screen, patch the fixture minimally and rerun the focused test. Do not label this “test-only” and stop.
4. **Preserve semantic failure reasons.** Do not replace `ACCOUNT_MISSING`, `manual-needed:login`, or another typed blocker with a generic manual-needed string. Reports and routing must retain the original reason.
5. **Retry discipline.** A worker timeout is transient: retry once with a narrower exact contract. A structural failure gets a second contract with smaller scope. Then either perform the authorized exact surgery or report `BLOCKED` with concrete command/output evidence.

## Required execution ladder

1. Run the machine-scoped inspection command for every named machine.
2. Read the newest run log and exact attempt artifacts before claiming a live root cause.
3. Dispatch code investigation/fix to a worker with explicit files, anchor, test, and no-broad-scan constraints.
4. Verify diff and focused offline test independently.
5. Fix stale mocks/fixtures when the failure is proven to be fixture setup.
6. Run the repository's target-scoped live canary on the named failed machines; capture fresh UI evidence before cleanup.
7. Reopen the fleet only after canary success; otherwise keep the batch locked.

## Status vocabulary

- `DONE`: code/test gate and live canary/fleet gate passed with artifacts.
- `PARTIAL`: code/test gate passed; live canary or fleet reopen remains.
- `BLOCKED`: a specific blocker remains after the retry/escalation ladder; include the exact command, exit/output, and next bounded action.

Never use “insufficient evidence” as a substitute for an offline action that can still be performed. Never claim live success from a worker summary, exit code, stale screenshot, or generic launcher state.
