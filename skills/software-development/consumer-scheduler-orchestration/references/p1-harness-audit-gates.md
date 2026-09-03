# P1 Core-Harness Audit Gates

Use this reference when a new cron/scheduler harness wraps an existing consumer launcher that already has preview and live modes. These gates keep an offline P1 implementation deterministic and prevent a harmless preview or stale artifact from being treated as a real execution.

## 1. Keep preview and execution state separate

Many PowerShell/Python launchers exit `0` during preview without starting the consumer or producing verifier artifacts. Therefore:

- `--dry-run` / preview must never write `LAUNCH_RESERVED`, increment an attempt, create a terminal result, or consume an idempotency key.
- A preview journal entry is permitted only as a non-terminal `DRY_RUN_PREVIEW` record; it must be ignored by eligibility and recovery logic.
- Only an explicit execute/live flag may enter the durable reservation critical section.
- Required regression: run dry-run for a due entry, then run execute; assert exactly one real reservation and one launcher invocation.

## 2. Bind success proof to one invocation

An exit code is not proof of a consumer result. Before a real launch:

1. Generate an `invocation_id` and a dedicated artifact root derived from it.
2. Under the journal lock, atomically append and flush `LAUNCH_RESERVED` containing entry ID, idempotency key, invocation ID, timestamp, and intended target identity.
3. Launch exactly once, retain PID/process identity and captured output, then parse only evidence produced beneath the dedicated root after the reservation.
4. Accept success only if the required report/summary, run manifest, and log evidence exist and their target fields match the scheduled machine, serial, and account row. Define the exact success predicate in code, not prose.

If the process crashes or the reservation has no completed proof, record a handoff/unknown state and do not blindly launch again. Required regressions: stale artifact ignored; exit `0` without fresh proof rejected; mismatched machine/serial/row rejected; correct fresh target proof accepted.

## 3. Close the cadence decision table before coding

A deterministic picker cannot infer business rules from partial dates. The source-config/schema must define a versioned decision table for both feed and post due states:

| Source state | Required policy |
|---|---|
| success on logical day | not due |
| success yesterday / elapsed one day | explicit due/not-due rule |
| elapsed exactly two days | due rule |
| elapsed three or more days | due plus highest-priority rule |
| never succeeded | explicit bootstrap policy |
| missing, malformed, or future date | fail-closed typed skip or an explicitly approved repair path |

The table must also define how `due.feed`, `due.post`, and `feed_only` versus `feed_then_post` are derived. Do not use wall-clock time, unordered maps, UUIDs, or random state in values claimed to be byte-stable. Derive identifiers/timestamps from logical day, normalized source revision, and seed, and serialize canonical JSON with stable ordering.

## 4. Make state vocabulary and persistence testable

- Version and close the enums for entry status, journal events, and `skipped.reason_code`; tests should assert every emitted value belongs to the published set.
- Manifest replacement requires write-temp -> flush/fsync -> `os.replace`; test a failure before replace preserves the prior valid manifest.
- Existing malformed manifest or journal state is fail-closed and must not be silently overwritten or treated as a valid reroll.

## P1 boundary

These protections belong in the harness and its fake adapters/tests. They do **not** require changing a shared scheduler/core library, modifying the existing consumer launcher, opening a real workbook, enabling cron, or running a device.
