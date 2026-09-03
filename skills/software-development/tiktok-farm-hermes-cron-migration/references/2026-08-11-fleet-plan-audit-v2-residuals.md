# Fleet account-block plan — residual audit vòng 2 (2026-08-11) + codebase truth

Plan: `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md` (đã revise 956 → 1151 dòng; KHÔNG sửa code repo).
Findings áp: **NIT A** (Phase 4 Step 4.3 `_validate_block_structure` + test tầng block) và **NIT B** (điền đủ mọi test skeleton Phase 6/7).
Workflow class-level (locator report, zero-placeholder, layered tests): xem skill `implementation-plan-maintenance`.

## ⚠️ 2 lỗi trong plan v2 phải sửa TRƯỚC khi implement (phát hiện khi ground-truth, chưa kịp sửa plan)
1. **`_validate_block_structure` dùng `e["seed"]`** trong `expected_ids = [entry_id_for(..., e["seed"]) ...]` — entry dict KHÔNG có key `seed` (KeyError). Sửa thành `payload["seed"]` (seed assignment-level — chính là giá trị `build_manifest_payload`/`_validate_entry` dùng). `_entry()` chỉ ghi: account, account_row, action_type, attempt, due, entry_id, feed, idempotency_key, lock, machine, post, serial, slot_end, slot_time, status.
2. **`test_journal_clear_cache_event_canonical` assert `"timestamp" in req`** — `JournalStore.append()` chỉ auto-add `schema_version=2`, `terminal=False`, `manifest_id`, `manifest_sha256`, `manifest_path`; KHÔNG có timestamp. Bỏ assert đó (hoặc định nghĩa field timestamp tường minh trong spec event Phase 6).

## Repo truth đã verify (read_file 2026-08-11) — dùng làm ground truth khi viết test vào plan
- **manifest.py**: `entry_id_for(manifest_id, account_id, machine, serial, account_row, slot_time, action_type, seed)` — 8 tham số, slot_time là ISO string; `manifest_id = f"{assignment_id}:{day}"`. `_validate_entry`: `set(entry) == required` với ĐÚNG 15 key (CHƯA có block_id/session_index) + regex `entry-v1-[0-9a-f]{32}` + lock/post shape chính xác → Phase 3 PHẢI thêm block_id/session_index vào required set và _entry. `validate_manifest`: `set(payload) == required` (18 key, CHƯA có blocks/maintenance) + `payload["constraints"] == CONSTRAINTS` (strict) + giới hạn cũ ≤3 entry/máy & spacing 180' (xung đột với 6 session — Phase 4 block-validation thay thế).
- **journal.py**: `append(event, **fields)` đi qua `reduce_and_validate` (replay-safe); auto-add như mục 2. `exact_fields`/`extras_by_event` (~dòng 430) + `TRANSITION_MATRIX` là allowlist — event mới CLEAR_CACHE_REQUESTED/DONE (Phase 6) cần vào CẢ HAI + matrix["execution"].
- **models.py**: `parse_hcm_timestamp` nằm ở đây (import từ models). `grid_slots`/`is_schedulable_interval` HARDCODE next-day limit `hour=1` (01:00) — Phase 1 phải đổi hour=2 (02:00) ở CẢ HAI + `is_in_logical_window`, dùng WINDOW_END_HOUR. Trước Phase 1: `is_schedulable_interval` window_end = next day 01:00.
- **picker.py**: `pick(*, day, seed, owner_id, worker_id, clock, as_of, state_paths=None, force_regenerate=False)` — keyword-only. Với state_paths: lock manifest_dir/active_lock/journal_lock của ngày; `_pick_locked` REUSE manifest active khi owner_id/worker_id/seed/source_revision/state_snapshot_digest khớp (đảm bảo "persist trước khi chạy, không reshuffle"). Journal đọc trong pick — kiểm tương tác `has_non_preview` trước khi khẳng định hành vi re-pick trong test no-KPI-makeup.
- **blocks.py drift (flag)**: plan Phase 1 CONSTRAINTS ghi `pair_gap_minutes: [60,90]` và blocks.py `PAIR_GAP_MINUTES=(60,90)` trong khi picker `rng.choice((60,75,90))` và validation `not in (60,75,90)` — grid 15 → tập thật {60,75,90}; [60,90] chỉ là tài liệu (validate so CONSTRAINTS == CONSTRAINTS cùng object nên không fail) — thống nhất hằng số khi implement.

## Locators đã sửa trong plan (báo cáo theo locator)
- Phase 4 Step 4.3 (~613–649): entry_ids check value-level + `block_id_for(block["day"], block["block_index"], block["machine"], block["account"])` đầy đủ tham số; giữ gap-from-slots check.
- Phase 4 Step 4.1: `test_validation_rejects_seventh_entry_with_valid_formula_id` (sau test more_than_6_sessions ~580–600) — re-hash entry_id đúng công thức → đi qua `_validate_entry` → reject block-level MANIFEST_IDENTITY_MISMATCH.
- Phase 1 Step 1.3 (~152): ghi chú grid_slots hour=1→hour=2.
- Phase 6 Step 6.1 (~838–930): `test_runner_clear_cache_due_after_block3` (+03:00 offline assert), `test_runner_cli_clear_cache_is_offline_no_subprocess` (runner_main + journal + stdout JSON + idempotent lần 2), `test_journal_clear_cache_event_canonical` (append/replay/unknown-event/DONE-trước-REQUESTED) — NHỚ bỏ assert timestamp.
- Phase 7 Step 7.1 (~961–1080): 6 skeleton điền đủ — no_kpi_makeup (FAILED journal → re-pick D+1), seed_unstable (2 root tmp_path, canonical_manifest_bytes), capacity_overload (9 account, deepcopy `_fleet_source_raw`), boundary 0200 (grid_slots 01:15 ∉ / 01:00 ∈), 20-seed invariants, tamper block_id.
- Test `test_no_session_outside_assigned_block` giữ nguyên (đã đủ từ v1).

## Fixtures của plan (bắt buộc dùng trong test mới)
- `fleet_source()` — SourceConfig 6 acc rows 1–6, machine 1, SERIAL_A; ngày chẵn → lane A (acct-1..3), lẻ → lane B (acct-4..6).
- `_fleet_source_raw()` — raw dict (Phase 5/6 CLI test ghi `fleet-source.json` từ đây).
- `_fleet_pick(state_root, day)` — helper pick+persist; `seven_source()` — Phase 3 (7 acc).
- `state_root` fixture: GIẢ ĐỊNH per-test (tmp_path) — CHƯA verify trong plan; flag khi implement (test no_kpi_makeup phụ thuộc journal không nhiễm giữa test).