# Row-slot picker design (2026-08-17) — supersedes lanes/blocks/jitter scheduling

Verified by probe + rewritten `test_hermes_cron_fleet.py` (46 tests: **45 passed, 1 xfailed**).

## What the picker now emits (`picker.py::_entries`)

- **1 entry per feed-due account**, slot anchored to the account's PHYSICAL row:
  `row_slots = {1: "06:00", 2: "08:00", 3: "10:00", 4: "12:30", 5: "15:00", 6: "17:30"}`
  → `datetime.combine(logical, time(h, m), TZ)`, 60' slot_end. User rule 17/08:
  "row trống thì bỏ qua máy đó" — a machine missing a row simply has no entry.
- `blocks` is ALWAYS `[]` in produced payloads; entries carry **no**
  `block_id` / `session_index`.
- **Lanes are gone**: every calendar day schedules the same 6 rows (even AND odd).
  `blocks.lane_for_day / lane_rows / machine_day_seed` still exist (tests import
  them) but the picker never uses them.
- Rows >6 → skipped `UNSCHEDULABLE_CAPACITY` (was `CAPACITY_EXCEEDED` under lanes).
- Skip reasons now: `INVALID_FEED_STATE` / `EXECUTION_IN_FLIGHT` / (intended)
  `NOT_DUE` — see production bug below.
- Entry id = BASE form of `entry_id_for(manifest_id, account, machine, serial,
  account_row, slot_time, action_type, seed)` — no block/session args.
  Test helper `_rehash_entry(payload, entry)` recomputes entry_id + idempotency_key.

## Manifest validation for empty-block payloads (`manifest.py` ~316)

- ≤6 starts per machine AND ≥90' between adjacent starts, else
  `UNSCHEDULABLE_CAPACITY` (adjacent row slots are ≥120' apart, so canonical payloads pass).
- `_validate_entry` requires exactly the non-block key set; `blocks: []` is a
  REQUIRED payload key (`del p["blocks"]` → SOURCE_CONFIG_INVALID).

## Runner / CLI consequences

- `Runner.clear_cache_due()` is **always False** for row-slot manifests (needs a
  `block_index == 3` block, which never exists). CLI `--clear-cache` therefore
  prints the declaration JSON but never appends `CLEAR_CACHE_REQUESTED`. Tests
  assert exactly that (no request ever queued, rc 0, no subprocess).
- `select_due_entries` / `run_entry` unchanged: dry-run preview works at 01:30 for
  the last row-slot entry (acct-6 17:30, slot_end 18:30); 02:00 cut-off unchanged.

## ⚠️ PRODUCTION BUG (found 2026-08-17, NOT fixed — production edits out of scope)

`picker.py:263` references `ReasonCode.NOT_DUE`, which **does not exist** in
`models.ReasonCode` nor `manifest._SKIPPED_REASONS`. A just-fed account
(`last_feed_success_at` 0-1 days ago, `_feed_decision` → NOT_DUE) crashes the pick
with `AttributeError: type object 'ReasonCode' has no attribute 'NOT_DUE'` at
`skipped.append({"reason_code": ReasonCode.NOT_DUE.value})` instead of being skipped.
Guarded by `test_pick_skips_not_due_accounts` marked `xfail(strict=False, reason=...)`
with the full explanation. Fix belongs in production: add `NOT_DUE` to the enum +
`_SKIPPED_REASONS` (then the xfail flips to pass — remove the marker).

## Test-file structure (reference for future fleet edits)

- `ROW_SLOTS` module constant mirrors picker dict; `fleet_source()/seven_source()/
  _large_source_raw()` fixtures unchanged from the lane era.
- `_fleet_pick_two_machine` → 12-entry row-slot manifest (machine 2 = acct-7..12,
  rows 1-6, SERIAL_B), re-hashes assignment + all entry ids via
  `_rehash_assignment_id` / `_rehash_entry`.
- Entry-level tamper matrix: metadata splice → `MAPPING_CONFLICT`; entry_id /
  cloned-entry / payload-seed / duplicate-account tamper → `MANIFEST_IDENTITY_MISMATCH`;
  off-grid or other-day slot → `RESERVED_BLOCK_CONFLICT`; 7th machine start (60' gap)
  → `UNSCHEDULABLE_CAPACITY`.
- **CLI tests must pin the live permit**: stray `runtime/hermes-cron/permits/
  tiktok_runner.permit` (left from the live pilot) makes `hermes_cron_runner.main`
  raise `SystemExit("--execute live requires --repo and --feed-workbook")` because
  `--execute or --repo or --feed-workbook` triggers the permit guard. Hermetic fix
  (no repo mutation):
  `monkeypatch.setattr(python_runner.scripts.hermes_cron_runner, "_runner_live_permit", lambda: None)`.

## Pitfall hit while iterating

- **Cross-source pick on one state root fails**: a second `_pick()` with a DIFFERENT
  SourceConfig against the SAME root fails `SOURCE_CONFIG_INVALID` from
  `load_snapshot_bundle` (`_validate_generation`) — the bundle cache is source-bound.
  Each pick test needs a fresh state root (pytest `state_root` fixture does this;
  ad-hoc scripts must use a fresh TemporaryDirectory per check, not one shared root).
- **`patch` tool fuzzy matcher mangled indentation twice** on multi-line replaces in
  the test file (replacement lines landed in the wrong indent level → IndentationError,
  lint misleadingly labelled it "pre-existing"). Use full-function old_string context
  or rewrite the file with write_file; always py_compile after multi-line patches.