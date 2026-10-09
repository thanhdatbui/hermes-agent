# Tight-Budget Review Remediation

Use this when a delegated code-review fix provides exact production/test files and a small tool-call budget (especially <=10 calls).

## Execution shape

1. Batch-read the named source and test anchors in the first call; confirm the exact function boundaries and test import conventions.
2. Apply the minimal production and regression-test edits immediately in the next write call. Do not spend the budget on repeated micro-searches, broad history searches, or optional discovery once the prompt has supplied exact anchors.
3. Run the required focused pytest command and `git diff --check` after the final edit. Earlier test output is baseline evidence only and becomes stale after any edit.
4. If a pre-edit test run reveals an unrelated/stale fixture failure, record its exact node and output, but do not opportunistically repair it unless the requested change causes it or it blocks collection. Report it separately from the requested-fix result.

## Failure mode to avoid

A pass can spend all iterations inspecting small regions and running a baseline suite before any write occurs. That leaves the exact requested fix unapplied and makes the final status incomplete. Prefer fewer, larger bounded reads followed by the patch and final evidence.
