# Final-Boundary Remediation Pattern

Use this recipe when a closeout reviewer rejects a change for missing integration evidence, over-broad intent classification, or weak observability.

## Minimal implementation shape

1. Keep the existing low-level helper contract stable when possible.
2. Add a small production seam that models the actual final-response boundary (for example, `_maybe_append_*_for_final_response`).
3. Route the live boundary through that seam; a test-only wrapper is not integration evidence.
4. Keep the dependency mocked/offline and preserve existing routing/tool schemas.

## Regression contract

The focused test should call the production seam with a fake handler and assert:

- the complete primary answer is preserved;
- the expected integration label is appended on success;
- the exact handler positional/keyword arguments, including stable request IDs, are sent;
- the handler is called at most once;
- handler failure is fail-open and returns the primary answer with an unavailable marker.

For classifiers, explicitly cover ordinary questions and imperative strings ending in `?` as false, then cover every required advice marker as true. Punctuation alone is not intent.

## Conversation-level observability

Log at the real boundary, not only inside the transport adapter. Use a stable event/message such as `advisor_triggered` with `decision_class`, normalized `status` (`ok`/`unavailable`), and `request_id`; optionally log cheap `advisor_skipped` events for non-advice turns. Never log full user text, secrets, or raw provider payloads. Map exceptions and malformed outcomes to `unavailable` while preserving the primary response.

## Verification and budget discipline

Treat the user-named final commands as acceptance criteria. Reserve enough calls after the last edit for the focused test, compile check, diff hygiene check, and final scoped `numstat`. If a tool-call budget is consumed before those commands run, report the candidate as partially verified rather than implying all final checks passed. Preserve unrelated dirty paths and compare scoped `numstat` to detect accidental whole-file churn.
