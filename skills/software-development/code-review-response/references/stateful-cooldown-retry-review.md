# Stateful Cooldown/Retry Review Pattern

Use this checklist when reviewing a batch supervisor that automatically retries failed logins or external stages.

## Production invariants

- Cooldown eligibility uses only an authoritative failure record: matching stage, supported terminal failure status, and a parseable timestamp.
- Generic `updated_at` is not a failure-time fallback. Missing or malformed timestamps fail closed and preserve the current blocked/error state.
- Boundary comparison is explicit: just below the threshold remains blocked; just above it becomes pending.
- A persisted retry counter is incremented exactly when an automatic unblock is authorized. At the maximum, transition to terminal `QUARANTINE` before selection; do not unblock again.
- Failure and unblock telemetry is emitted by production paths and includes identity, machine, email, proxy port, retry count, and actionable detail.
- The unblocked state reaches the real executor/script call. Executor failure feeds back into the same failure state and telemetry contract.

## Minimum regression matrix

1. Threshold minus one hour: remains blocked and is not selected.
2. Threshold plus one hour: becomes `PENDING`, is selected, and increments retry count.
3. Missing timestamp and malformed timestamp: neither is unblocked, even when `updated_at` is old or valid.
4. Every supported failure status (`FAILED`, `ERROR`, `BLOCKED`) obeys the same cooldown.
5. Retry count at the maximum: becomes `QUARANTINE`, records the max-retry detail, and remains unselected on subsequent passes.
6. Integration: a selected pending profile invokes the configured login script; a false/failed result produces the structured failure result.

## Evidence rules

- Run the existing focused suite before adding tests to establish the baseline.
- Tests should call the production selector/executor and patch only external seams such as time, subprocess, profile API, and telemetry.
- Assert state mutation, selection result, retry count, telemetry payload, and executor arguments separately.
- Label targeted/ad-hoc evidence separately from the canonical pytest result; rerun the canonical command after the final edit.
