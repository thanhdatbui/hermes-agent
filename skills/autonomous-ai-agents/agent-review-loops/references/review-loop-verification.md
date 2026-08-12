# Review-loop verification checklist

Use this after every material implementation change and before reporting approval.

## 1. Reconcile the reviewed artifact

- Identify the exact commit/ref the reviewer saw.
- Read the saved response artifact; take the first non-empty verdict line as authoritative.
- Check `git status`, `git show --stat <commit>`, changed-file allowlist, and `git diff --check`.
- Do not treat a worker summary, exit code, ad-hoc script, or test count alone as approval.

## 2. Validate findings against source

For each finding, record:

- file + symbol/line locator;
- concrete input/state transition;
- production consequence;
- whether the auditor's representation matches the implementation;
- executable regression test or artifact evidence.

Common false-positive trap: Android UI bounds may be normalized by the parser to `(x, y, width, height)` even though raw UiAutomator XML uses `[x1,y1][x2,y2]`. Read the parser before changing area/coordinate math. If the audit is correct, expose an explicit normalized size field rather than relying on ambiguous tuple semantics.

For any proposed return/status/outcome change, search every caller and test the escalation path. A new value that is not handled can cause silent skip or retry loops.

## 3. Lock and fail-closed invariant

- Acquire device before workbook.
- Release workbook in `finally`.
- Release device only after positive terminal success proof.
- For `MANUAL_REVIEW`, `CONFIG_ERROR`, `FOLLOW_BLOCKED`, unverified release, or release failure, preserve the device lease as auditable handoff; never force-unlock.
- Test workbook-acquire rollback, busy/foreign lock, release proof failure, retained handoff, and locks-disabled offline injection.

## 4. Canonical verification

Run the target repo's real commands, not a substitute probe:

```text
PYTHONPATH="D:/Taadaa/automation-core/src;." python -m pytest follow_runner/tests -q -p no:cacheprovider
python -m compileall -q follow_runner tools
 git diff --check
```

Then inspect the exact post-test diff/status. If a focused test fails, fix the production/test contract or fixture; do not weaken assertions merely to recover green.

## 5. Re-audit loop

After a usable `MINOR_FIXES` verdict:

1. patch only confirmed findings;
2. add or update regression tests;
3. rerun focused + full suite and static checks;
4. commit/push only the verified allowlist;
5. rerun the same audit route on the new commit;
6. stop only at `APPROVED`, or report a real blocker with the remaining artifact path.

If a later audit finding is speculative, prove/disprove it against source before changing code. Keep the audit report concise for the user: verdict, major/minor count, concrete action, commit/test evidence, and remaining gates.
