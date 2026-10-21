# Dual-Cluster Workbook Resilience

## Context

Use this reference when Kibe is the central coordinator and Admin is a separate thin-worker cluster with disjoint machine ranges. Identical hardware and shared source code do not imply identical failure behavior: storage roots, OneDrive participation, environment capture, ADB routing, runtime state, and process ownership can differ.

## Recommended topology

- Keep Kibe and Admin workbooks physically separate.
- Keep per-cluster state, artifacts, locks, and runtime roots separate.
- Treat Excel as an operator-managed ledger, not a concurrent database.
- For Admin's OneDrive-backed safe workbook, maintain:
  - primary: `D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx`
  - local cache: `D:/Taadaa/runtime/admin/taikhoan_run_safe.xlsx`
- The sync job writes both outputs from the same source snapshot.
- The runner prefers the configured primary and falls back to the local cache only when the primary is absent or unusable, according to the explicit contract.

## Root-cause checklist

When only Admin fails, compare these surfaces before blaming the device fleet:

1. workbook paths and trailing-space filenames;
2. OneDrive sync/locking and whether both PCs participate;
3. local versus remote process ownership and environment variables;
4. separate state markers and stale early-return conditions;
5. runner workbook resolution and fallback behavior;
6. report aggregation behavior when a cluster has zero runs;
7. ADB host/socket routing and machine-range filtering.

## Minimum implementation contract

1. Missing output must invalidate the "source unchanged" fast path and trigger a rebuild.
2. Both configured outputs must be written and independently verified as readable workbooks.
3. The runner must have deterministic primary/fallback precedence.
4. A corrupt or unreadable workbook must fail closed; existence alone is not validity.
5. Emit telemetry identifying selected source (`primary` or `local_cache`) and failure reason when fallback occurs.
6. Follow/farm reports must preserve an explicit `SKIPPED`/`NO_RUN` cluster block instead of dropping it because the Follow section is absent.

## Verification matrix

Focused tests should cover:

- source signatures unchanged + primary output missing => sync runs;
- both Admin outputs are configured;
- sync writes both outputs using a mocked writer or isolated temporary workbook;
- primary exists and is valid => primary selected;
- primary missing, valid local cache exists => local cache selected;
- both missing => return the primary path and let the existing missing-file error remain authoritative, or fail closed if the contract requires it;
- primary/local cache corrupt or unreadable => fail closed, never silently select bad data;
- no-run cluster block remains in the cross-farm report;
- telemetry records primary/fallback selection and fallback reason.

Run the focused tests after the final edit, then run the real sync/validator against an isolated or explicitly authorized runtime path. Do not describe a path-selection unit test as proof that production sync wrote both files.

## Reporting discipline

Report separately:

- code/test evidence;
- real sync output and workbook readability/row-count evidence;
- validator result;
- closeout verdict and score;
- commit/push state.

A worker exit code of zero or a passing focused test does not prove the local cache was populated, the fallback workbook is valid, or the closeout gate approved the change.
