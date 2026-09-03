# Delegated Verification and Diff Audit

Use this checklist for multi-process orchestration changes such as cohort dispatchers, cron launchers, watchdogs, and worker leases.

## Before accepting a worker result

- Confirm the worker's exact repository and working directory.
- Run `pwd`, `git status --short`, and `git diff --name-only` in that repository.
- Reject reports whose command/toolchain belongs to another project.
- Re-read the claimed production and test files; treat the worker summary as a lead, not proof.

## Cohort contract

- The denominator is the exact block/session being dispatched.
- `expected_machine_ids`, `entries_by_machine`, launch targets, deadline, and cohort identity must describe the same frozen set.
- Never derive expected machines from account-row count, summary files, folder count, or publication count.
- Resolve canonical fields from the production manifest (`blocks[]` for block identity); reject duplicate or contradictory aliases.
- Freeze the artifact before launching and fail closed on missing, malformed, tampered, or digest-mismatched artifacts.

## Process-boundary contract

Verify the actual argv/config boundary, not only helper functions:

- assignment manifest identity reaches the launcher;
- cohort artifact and worker identity reach every child;
- child publication writes cohort, assignment, block/session, entry, machine, and run identity into the canonical run manifest;
- watchdog accepts only a publication matching all expected identity fields and `final_status`.

A summary/details object is not sufficient if the artifact writer drops arbitrary fields. Test the final manifest file.

## Lease contract

Represent every spawned child/row in the lease. A lease remains active while any valid child PID is alive; it is removed only after all children have exited or the lease is invalid/expired according to the explicit contract. Add a regression test where the first child is dead but a later child remains alive.

## Final verification

After the last edit:

1. Run focused boundary tests in a fresh interpreter.
2. Run the full relevant suite; do not reuse counts from before the last edit.
3. Run compile/import checks and a CLI argument smoke test with the actual pinned import path.
4. Run `git diff --check`.
5. Audit the final diff for missing parser returns, incorrect resolved paths, dropped identity fields, and unrelated dirty files.
6. Verify pre-existing stashes and dirty files were not reset or overwritten.

Classify a setup/import failure separately from a production failure: fix the invocation and rerun rather than weakening the code contract.
