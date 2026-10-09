# Sol self-repair and audit-chain integrity (2026-10-09)

## Reusable pattern

When the user explicitly chooses Sol to self-remediate after a Closeout Gate rejection:

1. Keep the candidate scope fixed to the gate's target files and findings. Do not switch to Claude or dispatch another worker unless the user explicitly authorizes that route.
2. Use the repository's Sol repair path (`sol_repair.py` / `closeout_gate.py --auto-repair`) and verify the live proposal before applying it. Worker/model summaries are not evidence.
3. For direct `sol_repair.py` calls, construct `FindingItem` with its actual schema (`id`, `description`, `severity`); do not guess field names such as `category`.
4. Prefer the allowlisted Sol route that returns a complete bounded proposal. In this incident, model `review` produced a valid two-file proposal after the first route timed out; the proposal was then inspected for exact old/new snippets and syntax status.
5. Apply only the proposal's exact production/test delta, run the named focused tests, inspect `git diff --numstat`, and re-run the gate. Do not add speculative full-suite or load-test code merely because the reviewer asks for generic evidence.
6. Treat reviewer feedback about broad substring matching as a concrete correctness issue: use exact normalized error messages or an explicitly bounded set of accepted variants, plus a negative test proving unrelated messages do not retry. Assert production logger telemetry with `caplog`; synthetic test-only telemetry is insufficient.

## Audit-chain fail-closed rule

`closeout_gate.py` depends on an append-only audit chain whose latest non-empty line must be valid JSON containing `self_hash`. If a gate run reports `Corrupted or unreadable audit chain`, preserve the file and report the integrity failure with the exact line/path as evidence. Do not manually rewrite, filter, truncate, or regenerate the global audit log to make the next run pass; that would destroy auditability and can invalidate prior evidence. Use the documented audit recovery/repair mechanism or escalate as a genuine gate blocker.

## Closeout interpretation

A Sol proposal or focused pytest pass is not approval. Only the final gate result for the exact candidate—`Verdict: APPROVED`, score >=85, and exit code 0—authorizes commit/push. A reviewer score of 84 remains rejected even when `ready_to_close` is advisory. If three same-scope rejections trigger a reviewer handoff, respect the routing contract; do not keep guessing patches. If the user has authorized Sol but not Claude, explain that the next required route is not authorized and leave the candidate unpushed.

## Evidence labels

Report separately:
- Sol proposal validity and the exact files/anchors it addressed.
- Focused pytest output and warnings.
- Gate verdict, score, exit code, and any audit-chain integrity error.
- Git state and whether commit/push occurred.

Never collapse these into a single "done" claim.
