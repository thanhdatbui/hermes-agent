# Block-mode picker 2026-08-18 — verified output + test-alignment fix map

Design committed as `df9051d` ("feat(cron): hoàn thiện picker 3-ca/3-phiên parity lane chẵn/lẻ
(audit APPROVED)"). This file records VERIFIED picker output (ran the real code, not inferred) and
the exact per-test fixes that took the 5 cron suites from 73 fail → 250/250 pass.

## Verified picker output (real run, seed 7, day 2026-08-10, 6-account fleet source rows 1-6)

Even day → lane A rows (2,4,6) → 3 blocks × 3 sessions = 9 entries:

| block | idx | acc | row | s1 slot | s2 slot | s3 slot | gap | jitter |
|---|---|---|---|---|---|---|---|---|
| block-v1-dfb4b0a5… | 1 | acct-2 | 2 | 06:00 | 08:00 | 10:00 | 60 | 0 (clamped) |
| block-v1-c2de1219… | 2 | acct-4 | 4 | 12:45 | 14:35 | 16:25 | 50 | +15 |
| block-v1-c856dc89… | 3 | acct-6 | 6 | 19:15 | 20:55 | 22:35 | 40 | +15 |

- skipped = acct-1, acct-3, acct-5 all `CAPACITY_EXCEEDED` (outside even-day lane A).
- block 1 jitter: negative clamped to 0 (anchor 06:00 = window start).
- blocks 2/3 jitter +15 → s1 anchors 12:45 / 19:15 (NOT 12:30 / 19:00).
- 3-account source (rows 1-3) + even day → ONLY acct-b row 2 scheduled (block 1); ca 2/3 dropped
  (no acc at rows 4/6). Odd day 2026-08-11 → lane B (1,3,5): acct-a block 1 @ 06:15 (jitter +15;
  positive jitter allowed on block 1, only negative is clamped).

## Golden-vector facts (recomputed by RUNNING the code, never hand-inferred)

- `reference_source_revision` unchanged: `4ee077c1c2bbef1bdb2dcdb3194e5e11b06b5beca6bbcd1827765c01188c5d4e`
- `reference_assignment` (CONSTRAINTS now carries lanes A(2,4,6)/B(1,3,5)):
  `assignment-v1-15ff0af2529ef8b12fcd433f5c14daad` (was `50a67e2e…` under old lanes)
- `reference_block_id` = `block-v1-` + sha256(`2026-08-10|1|1|acct-2`)[:32] =
  `block-v1-dfb4b0a5be7a00601dc1c15834d68a74`
- `reference_entry` (manifest_id-bound, with block_id + session_index):
  `entry-v1-1f885a365ed967c65283e1136b3f9605` (was `8ee9becb…` under old manifest_id)
- Lesson: assignment_id and entry_id move TOGETHER — a sibling updating only the assignment
  constant leaves the entry constant stale and the test fails mid-file. Recompute both from code.

## Per-test fix map (tests only; production untouched by this session's edits)

`test_hermes_cron_p1_r2.py`:
- TARGET/TARGET1: both become row 2 (`{"machine":1,"serial":"SERIAL_A","account_row":2}`) — entries[0]
  is now acct-b row 2 (lane A even day), and journal validates target against the entry.
- `test_r6_custom_reader_snapshot_is_validated_before_freeze`: skipped set =
  `{INVALID_FEED_STATE, CAPACITY_EXCEEDED}` (acct-b in-lane invalid; acct-a/acct-c out-of-lane).
- `test_r10_watcher_cli_requires_source_config_for_self_consistent_machine_999_manifest`: forge must
  rehash `assignment_id` with `account_ids = entries ∪ skipped` AND re-derive block seeds via
  `machine_day_seed(day, 999, seed)` — otherwise `validate_manifest(forged, None)` fails before the
  watcher CLI gate.
- `test_r11_red_requested_day_binds_snapshot_and_preserves_midnight_mapping`: rows 1-3 + even day =
  single block acct-b; `select_due_entries(next-day 00:00) == []`.

`test_hermes_cron_regressions.py`:
- `test_valid_feed_then_post_preflight_stops_before_lock_or_feed`: pick day 2026-08-11 (odd, lane B
  rows 1,3,5) so acct-a row 1 is scheduled as block 1; clock `2026-08-12T23:00:00+07:00`,
  as_of `2026-08-12T00:30:00+07:00`; run_entry at 06:45 → `NO_HANDLER_IMPLEMENTED`.

`test_hermes_cron_contract.py`:
- `test_golden_vector_and_real_assignment_loader`: golden constants above; first entry assertions
  acct-2 / row 2 / session_index 1 / block_id present.

`test_hermes_cron_fleet.py` (edited by sibling subagent, verified by me):
- Lane account sets: even day `{acct-2,acct-4,acct-6}`, odd day `{acct-1,acct-3,acct-5}`;
  3 blocks × 9 sessions; skipped CAPACITY_EXCEEDED for out-of-lane; 2-machine fixture rebinds
  machine-2 blocks to the odd-lane accounts (acct-1,3,5) with `_rehash_block_identity`;
  duplicate-account-across-machines tests pick `m1_block` dynamically.

## Environment / commands

- Canonical run (from repo root, `PYTHONPATH=""`):
  `PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' PYTHONPATH=""
  /d/Taadaa/python-envs/automation/Scripts/python.exe -B -m pytest
  python_runner/tests/test_hermes_cron_contract.py python_runner/tests/test_hermes_cron_blocks.py
  python_runner/tests/test_hermes_cron_fleet.py python_runner/tests/test_hermes_cron_p1_r2.py
  python_runner/tests/test_hermes_cron_regressions.py -q` → 250 passed (~64s).
- Ad-hoc verify script pattern (banner-triggered): `tempfile`-based `hermes-verify-*.py` under
  `C:\Users\Kibe\AppData\Local\Temp` with explicit `sys.path.insert(0, str(_REPO))` (script lives
  outside repo; `PYTHONPATH=""` won't help it), run from repo cwd, delete after. First-failure
  `ModuleNotFoundError: python_runner` = harness setup, not product.
- Block-1 anchor assertion trap: do NOT assert absolute `06:00` for odd-day block 1 — positive
  jitter (+15/+20) is allowed on block 1 (only negative is clamped). Assert `06:00 <= slot < 06:30`
  and `jitter_minutes >= 0` instead.

## Concurrency note

A sibling subagent (`20260816_213915_15ea28ed`) was editing the same test files mid-session and
committed `df9051d`; the 4 remaining red tests + the stale contract golden entry were fixed on top
of its work. Re-read files before every patch (patch tool flags "modified since last read"); verify
full suite after the sibling commits.
