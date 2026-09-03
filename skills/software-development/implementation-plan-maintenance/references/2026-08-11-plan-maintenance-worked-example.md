# Worked example — residual audit vòng 2 on the fleet-account-block-scheduler plan (2026-08-11)

Plan: `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md`, repo `D:\Taadaa\tiktok-luot nuoi acc` (python_runner/hermes_cron).
Task: apply 2 residual findings, plan-only ("KHÔNG sửa code repo"), report by locator. Result: 956 → 1151 lines, 0 standalone `...`.

Codebase-specific verified facts (journal/manifest/picker internals) live under `tiktok-farm-hermes-cron-migration/references/2026-08-11-fleet-plan-audit-v2-residuals.md` — read that before touching this plan.

## Finding archetypes (recur in audit rounds)
- **NIT A — validation gap in plan code**: `_validate_block_structure` needed value-level checks beyond topology:
  - `block["pair_gap_minutes"]` must equal the slot-derived gap `(parse(s2.slot_time) - parse(s1.slot_end)) / 60` (already present — keep).
  - `block["entry_ids"]` must equal per-entry recomputed `entry_id_for(manifest_id, ...)` (NEW — reject MANIFEST_IDENTITY_MISMATCH).
  - Adversarial test that proves the LAYER: deepcopy an entry but RE-HASH `entry_id`/`idempotency_key` with the real formula so `_validate_entry` passes and only block-level (account duplicate → account_blocks len 2) fires; assert `excinfo.value.args[0] == "MANIFEST_IDENTITY_MISMATCH"`. Pair it with the junk-id test (`"entry-v1-" + "f"*32`) which proves entry-level rejection — two tests, two layers.
- **NIT B — placeholder skeletons**: 8 test bodies with lone `...` in Phase 6/7 → fill each with concrete arrange/act/assert using the plan's own fixture family: `_fleet_pick(state_root, day)`, `_fleet_source_raw()` (raw dict for CLI tests writing `fleet-source.json`), `fleet_source()` (6 accounts rows 1–6, machine 1, SERIAL_A), `JsonFeedStateReader(fleet_feed())`, `FixedClock(...)`, keyword-only `Picker(...).pick(day=..., seed=..., owner_id=..., worker_id=..., clock=..., as_of=..., state_paths=...)`. Assert exact ReasonCode strings, exact counts (3 blocks/6 entries), exact anchors (`["07:00","14:00","21:00"]`).

## Report style delivered (user preference — "theo locator")
Change list grouped by locator, one bullet per edit:
- `Phase 4 Step 4.3 (dòng ~613–649)` — entry_ids value-level check + concrete `block_id_for(...)` args
- `Phase 4 Step 4.1 (test mới ~580–600)` — seventh-entry re-hash test
- `Phase 1 Step 1.3 (~152)` — grid_slots hour=1→hour=2 note
- `Phase 6 Step 6.1 (~838–930)` — 3 tests fleshed (due/offline/journal-canonical)
- `Phase 7 Step 7.1 (~961–1080)` — 6 skeletons filled
End with: file path, line delta, scan evidence (0 standalone `...`, N legit matches listed by line), and explicit "KHÔNG sửa code repo" statement.

## Bugs the review itself shipped (check before implementing — could not be fixed in this pass)
1. **`e["seed"]` in `_validate_block_structure` expected_ids** — entries do NOT carry a `seed` key (KeyError). Use payload-level `payload["seed"]` (manifest seed), same value `build_manifest_payload`/`_validate_entry` use.
2. **`"timestamp" in req` assertion in `test_journal_clear_cache_event_canonical`** — `JournalStore.append()` auto-adds only schema_version/terminal/manifest_id/manifest_sha256/manifest_path. Drop the assertion (or add an explicit timestamp field to the event spec).
Lesson: verifying function signatures is not enough — verify the actual dict keys the plan code indexes.

## Search snippet (search_files fails on Vietnamese paths)
```bash
cd "/d/Taadaa/tiktok-luot nuoi acc" && python - <<'PY'
from pathlib import Path
p = Path('target.md')
for i, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
    if '...' in line:
        print(f'{i}|{line}')
PY
```
Classify hits: standalone `...` in code fences = must fill; `entry_id_for(...)` / `sha256(...)` / `tuple[int, ...]` / `{None, ...}` = legit signature notation, enumerate in report.
