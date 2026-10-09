# Canonical login routing and subprocess proof

## Evidence contract

For a fresh machine-scoped run, prove invocation from the machine's own `log.jsonl`, not from source inspection or a batch summary. A real invocation should leave a start event (`start_fast_login`, `start_reconcile`, or an equivalent command event), followed by a finish event containing `returncode`, timeout/exception, and preferably redacted stdout/stderr. If the complete fresh log has none of these, classify the worker as **NOT INVOKED**, not failed.

Bind the conclusion to:

- run ID and machine artifact root;
- exact `log.jsonl` path and line numbers;
- missing event family;
- terminal event that ended the flow.

## Routing-trace recipe

1. Read the fresh machine log around the blocker and capture the terminal classification verbatim.
2. Open the matching `ui.xml` and screenshot. Confirm the auth surface from actual nodes/text; do not use the presence of a `manual-needed` summary alone.
3. Search the direct consumer flow for the canonical runner command and the recovery helper.
4. Find every early return between classifier output and recovery helper. Pay special attention to identity/manual-row adapters that return immediately on `manual-needed:login`.
5. Compare the source branch order with the fresh log: if the log has a login classification but no subprocess start event and source has an earlier manual-row return, the routing defect is proven offline and the live worker was not run.

## Patch contract template

- **Predicate:** route only the canonical login/auth classification (`manual-needed:login` or the consumer's exact equivalent).
- **Before return:** call the existing canonical recovery helper with the exact expected account and machine context.
- **Success:** retry verification exactly once with recovery disabled/bounded to prevent recursion.
- **Failure:** preserve `manual-needed:login` and the exact artifact/reason; do not collapse into generic manual-needed.
- **Exclusions:** do not invoke login for popup, verification, captcha, capture-invalid, or unrelated account-missing states unless the product contract explicitly maps them.
- **Regression:** mock the identity guard to return the login manual row; assert the recovery helper is called once, the retry is bounded, and non-login manual rows do not call it.

## Reporting language

Use explicit classifications:

- `INVOKED — failed`: start and finish/returncode evidence exists.
- `INVOKED — success/unverified`: process evidence exists, but postcondition is separately gated.
- `NOT INVOKED — routing bypass`: blocker artifact exists, but no subprocess-start event and an earlier return bypasses the recovery branch.
- `UNPROVEN`: the log is incomplete, mismatched, or the attempt identity cannot be bound.

Never call a canonical login worker "failed" when the only evidence is the downstream manual-needed result.
