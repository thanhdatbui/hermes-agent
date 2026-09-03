# p1_r2 test alignment to row-slot picker (2026-08-17) — 46 fail → 116 pass

Task: update `python_runner/tests/test_hermes_cron_p1_r2.py` (2537 lines) after the
row-slot picker commit `597d7e7` changed the fixture output. ONLY the test file was
edited; no production code. Baseline 70 pass / 46 fail → **116 pass / 0 fail**
(full-file canonical pytest ~55s, `git diff --check` clean).

## Root cause (verified by running the picker)

Seed-7 fixture under block design claimed `entries[0] = acct-b row 2 @ 05:40`
(jitter). Row-slot design emits:

```
entries[0] = acct-a row 1 @ 2026-08-10T06:00:00+07:00
entries[1] = acct-b row 2 @ 2026-08-10T08:00:00+07:00
entries[2] = acct-c row 3 @ 2026-08-10T10:00:00+07:00
blocks == []   (no block_id / session_index on any entry)
```

`journal._entry_target(entry_id)` (journal.py:155) derives the expected target
`{machine, serial, account_row}` from the manifest entry and rejects any event whose
`target` differs → `IDENTITY_MISMATCH`; downstream gates then raise
`invalid journal transition` (HANDOFF path), `MANIFEST_IDENTITY_MISMATCH`
(LAUNCH_RESERVED / RecoveryReservationV2), and `INVALID_PATH`
(`NotificationKeyMaterialV1._notification_material` target_hash mismatch).
Notification tests failed even though they never touch the picker — the material
constructor hashes the target dict.

## Fix pattern

Module-level: keep `TARGET` (row 2) for row-2 probes; add
`TARGET1 = {"machine": 1, "serial": "SERIAL_A", "account_row": 1}` and a comment
documenting the row-slot entry order.

Per-test scoping: apply `TARGET1` ONLY inside tests whose entry is `entries[0]`
(row 1). `test_concurrent_watchers_*` also needs `cap_target` → TARGET1 and the
final HANDOFF probe → TARGET1 (it reuses the same row-1 entry).

### Groups changed

1. **Watcher `process_failure` (15 tests)** — pass `TARGET1` as the target arg:
   `test_watcher_classifies_without_auto_recovery`, `test_deferred_lock_*`,
   `test_concurrent_watchers_*` (incl. CAP branch), `test_sensitive_*`,
   `test_unknown_recovery_*`, `test_failure_signature_alias_*`,
   `test_missing_callable_*`, `test_r7_watcher_records_bridge_*`,
   `test_r7_callable_unregistered_*`, `test_r8_unregistered_handler_*`,
   `test_r9_unregistered_*` (both params), `test_r9b_registered_handler_*`
   (2 probes), `test_r9b_unregistered_handler_*`, `test_r11_red_phased_bridge_*`.
2. **Journal append/replay (23 tests)** — `target = TARGET` /
   `target=TARGET` kwargs → `TARGET1`: r6 x2, `test_journal_rejects_event_superset_*`,
   r7_values, r7_replay (incl. `poisoned` dict `"target"`), r8_matrix,
   r8_artifact, r9_matrix (first probe only — entry[0]), r9_time, r9_finalize,
   r10_final_blocked, r10_recovery_failed, r10_no_handler, r11_red_final_blocked,
   r11_red_artifact (incl. `RecoveryReservationV2.create`), r11_final_v2,
   r9b ×3 (cap-replay, artifact-ref, finalize, final-replay),
   r10_recovery_invocation.
3. **Launch reservation (2 tests)** — `ExecutionReservationV2.create(target=TARGET)`
   → TARGET1: r9_execution, r9b_execution_replay (both main + replay branches).
4. **Notification material (5 tests)** — `NotificationKeyMaterialV1(..., TARGET, ...)`
   → TARGET1: r10_notify, r11_red_notify, r11_notify_identity (also the
   `target_hash == sha256_json(TARGET1)` assert), r9b_polarity, r10_reconciler.
5. **`test_r10_watcher_cli_*` (forgery rewrite)** — deleted the `forged["blocks"]`
   loop (`block_id_for`, `entry["block_id"]`); now splices `machine`/`serial` = 999
   on entries directly, rebuilds `entry_id_for(manifest_id, account, machine,
   serial, account_row, slot_time, action_type, seed)` (no block/session args),
   keeps `validate_manifest(forged, None)` → the watcher CLI still exits
   SystemExit (source-config gate is the assertion).
6. **`test_r11_red_requested_day_*`** — `entries[8]` (block-3 session-3) → `[]`:
   all row-slot slots 06:00/08:00/10:00 are >90' past at `2026-08-11T00:00:00`,
   so `select_due_entries` returns nothing. Early-morning 02:30 ValueError probe
   unchanged (2-6h window assert).
7. **`test_slot_seconds_*` (skip semantics)** — `entries == []` → `len == 2`
   (acct-b/c remain schedulable under row-slot; only the bad account is skipped);
   `skipped == [{"account_id": "acct-a", "reason_code": "INVALID_FEED_STATE"}]`
   (lane-level `UNSCHEDULABLE_CAPACITY` for the healthy accounts is gone).

## Non-changes / notes

- `TARGET` (row 2) stays for any test that intentionally probes the row-2 entry
  or whose entry is entries[1]; don't blanket-replace.
- Two imports became unused after the CLI rewrite (`machine_day_seed`,
  `block_id_for`) — harmless, left in place to avoid churn (test file only).
- Journal/recovery semantics untouched — only targets realigned to manifest entries.
- Final state: +84/−92 lines, 116 passed, diff-check clean, no production edits.