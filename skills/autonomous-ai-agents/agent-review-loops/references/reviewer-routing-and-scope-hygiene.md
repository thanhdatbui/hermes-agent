# Reviewer routing and scope hygiene

Use this reference for closeout reviews with large diffs or repeated binding failures.

## Rules

1. **Explicit tool authorization:** Never invoke Claude CLI, OpenCode, or any external coding CLI unless the user explicitly requested that tool. “Check”, “inspect”, or “review” is read-only; use local evidence and the authorized reviewer path. An allowlist entry is not user authorization.
2. **Provider-specific payload policy:** `sol_payload_guard` and its 37KB truncation / `APPROVED_PARTIAL` behavior apply to Sol Web / ChatGPT-Web calls. For an explicitly selected large-context Terra/Codex model (`cx/...`, `terra`, `codex`), transmit the complete staged diff and verified test evidence without Sol truncation, while retaining normal request safety and audit binding.
3. **Exact scope binding:** Before `closeout_gate.py`, obtain the actual staged file list and pass exactly that list as `--files`. Do not guess a narrower or broader scope. If cron/sync changes the index, re-check and re-bind before review.
4. **No reflexive L3:** Rejection, timeout, and worker failure are remediation states. Classify transient vs structural, use the permitted retry/remediation path, and report BLOCKED only when the applicable budget/safety conditions are genuinely exhausted, with concrete evidence. `APPROVED_PARTIAL` is never DONE even when the numeric score is at least 85.
5. **Evidence ladder:** For large diffs, first normalize line endings and remove unrelated files from staging; then run focused tests for each changed production module; then use a large-context reviewer with the full diff. Do not manufacture E2E evidence from mocks—label offline, mocked, local-service, and real-farm evidence separately.

## Failure patterns captured from a real closeout

- Passing `--files` that omits staged files causes an immediate binding mismatch before review.
- A scheduled skills-sync job can mutate the index between staging and review; always inspect status immediately before Gate invocation.
- A score of 88 with `APPROVED_PARTIAL` still fails the gate because truncation invalidates closeout readiness.
- A Terra review can correctly reject a green offline suite when integration evidence is absent; add isolated SQLite/GPM/ADB/CDP integration fixtures only when they are real and reproducible, not as claims of farm-wide validation.
