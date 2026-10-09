# Delegated bounded-remediation closeout

Use this reference when a worker receives an explicit tool/iteration budget, exact target-file allowlist, and mandatory final commands.

## Acceptance rule

Treat the budget as an acceptance constraint. Reserve the final calls for every named post-edit check, especially the exact focused pytest command and `git diff --check`. Do not spend those calls on optional broad discovery after the patch. Syntax/lint success or a plausible diff is not evidence that tests pass.

## Worker handoff rule

A worker completion message is not evidence. The parent/coordinator must reconcile the live target files and final diff independently. If tests are added or edited after production code, all earlier test output is stale; rerun the exact user command against the final bytes.

## Honest closeout

If the budget expires before verification, report the implementation as partial/unverified and enumerate the missing commands. Preserve explicit no-commit/no-push boundaries. Never infer a passing suite from compile/lint output or from an unexecuted command.
