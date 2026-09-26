# Closeout remediation and Sol review (2026-09-26)

## Trigger
Use when the user says `chốt phiên`, `đóng phiên`, `kết thúc phiên`, or asks whether the deliverable is done.

## Non-terminal rejection rule
A closeout reviewer result of `REJECTED`, `MINOR_FIXES`, or score `<85` is **REMEDIATION_REQUIRED**, not a terminal `BLOCKED_AT_REVIEW`. Record the finding, evidence, next action, and attempt; dispatch the narrowest remediation worker; run focused offline verification; rerun the reviewer. Continue until `APPROVED >=85` or a true terminal `HARD_STOP`.

`HARD_STOP` is reserved for irreversible safety/business decisions, credential issues, explicit cancellation, true safety/integrity violations, unauthorized fallback, or exhausted bounded remediation with preserved evidence. Missing metadata, stale/malformed plans, missing anchors/tests, low score, verification failure, and quality-remediation exhaustion are recoverable (`REMEDIATION_REQUIRED` / `REVIEW_REMEDIATION_EXHAUSTED`) unless independent evidence proves otherwise.

## Evidence and gate selection
1. Isolate candidate files from unrelated dirty work before review.
2. If a modified monolithic test file causes the closeout gate to run the entire file and hit its hard timeout, treat this as gate-selection failure—not patch failure.
3. Run the exact impacted subset with `pytest -k ...` and preserve command, exit code, duration, and output.
4. `--skip-test` never substitutes for focused evidence; if used for a second review, attach the independently captured focused-test output.
5. Review the current diff plus fresh test evidence, not worker summaries.

## Sol review
- Send Sol the actual source/diff in a self-contained prompt. A response saying it cannot access local files is not an engineering verdict.
- After every material patch, rerun Sol with fresh source and fresh tests.
- `APPROVED` is valid only after integration is inspected, not merely helper tests.
- Required lifecycle: `review → REMEDIATION_REQUIRED → focused verify → review again → APPROVED/HARD_STOP`.

## Integration checks
Before requesting approval, verify:
- Production `main()` invokes the remediation state machine.
- `<85` persists blocker/evidence/next_action/attempt/max_attempts and re-enters remediation.
- Verification must be exactly `passed is True` before success; false/missing/None/0 blocks second review.
- Success persists verification evidence.
- Reviewer approval requires valid schema: `APPROVED`, score >=85, `ready_to_close=True`, non-empty evidence, and all rubric fields.
- Dispatch lifecycle distinguishes `REMEDIATION_REQUIRED`, `SOL_PLAN_REQUIRED`, `SOL_FALLBACK_PENDING`, `ALLOW`, and `HARD_STOP`.

## Known evidence pattern
A focused test result such as `34 passed in 3.95s`, plus `py_compile` and scoped `git diff --check`, is useful evidence but does not replace integration review.
