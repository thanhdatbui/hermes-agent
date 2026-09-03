# Phase 3 implementation — block planner (2026-08-11) — state + traps

Plan: `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md` dòng 358–508.
Repo: `D:\Taadaa\tiktok-luot nuoi acc`, branch master, HEAD `f1744bf` (Phase 2) khi bắt đầu.

## Đã implement (files đổi: blocks.py, manifest.py, picker.py, models.py, test_hermes_cron_fleet.py mới, test_hermes_cron_contract.py, test_hermes_cron_p1_r2.py — CHƯA COMMIT)

- `blocks.py`: thêm `block_id_for(day, block_index, machine, account_id)` =
  `"block-v1-" + sha256(f"{day}|{block_index}|{machine}|{account_id}")[:32]`; `AccountBlock.__post_init__` dùng nó.
- `manifest.py`:
  - `entry_id_for(..., block_id=None, session_index=None)` — CẢ HAI được hash vào material (dict insertion order
    không quan trọng — canonical_json sort keys).
  - `_entry(..., block_id=None, session_index=None)` — chỉ ghi key khi not None.
  - `build_manifest_payload(..., blocks=None)` — top-level `"blocks"`; **sau vòng recompute entry ids, rebuild
    `block["entry_ids"]` từ entries của block (sort theo session_index)**. ĐÂY LÀ BUG ĐÃ GẶP: `_entries` tính
    entry_id với `assignment_id_for(...)` KHÔNG có `resource_mapping` → assignment khác payload thật
    (vd `assignment-v1-87135e63...` vs `a65d5597...`) → entry ids bị build đè, nhưng `blocks[*].entry_ids`
    giữ id cũ → `validate_manifest` reject MANIFEST_IDENTITY_MISMATCH. Fix = rebuild trong build.
  - `validate_manifest`: required set thêm `"blocks"`; per-machine heuristic cũ (≤3 start, gap ≥180) chỉ chạy
    khi `not payload["blocks"]`; account-uniqueness: block-mode cho phép cùng account lặp CHỈ khi cùng block_id;
    gọi `_validate_block_structure(payload, source)` cuối.
  - `_validate_block_structure` (Phase 3 MINIMUM — Phase 4 sẽ thay bằng phiên bản đầy đủ của plan):
    blocks phải là list; nếu rỗng → return (legacy); mỗi block đủ 12 key, block_id regex + khớp công thức,
    entry_ids đúng 2 string khớp tập entry_id của entries tham chiếu; entry phải có block_id ∈ by_id và
    session_index ∈ {1,2}.
  - `_validate_entry`: mode-aware required set — block-mode thêm `block_id`/`session_index`; expected_id dùng
    `entry.get("block_id")`/`entry.get("session_index")` (None → legacy formula).
- `picker.py` `_entries` (bỏ hẳn DFS): lane theo parity; account ngoài lane → CAPACITY_EXCEEDED; feed/post
  decision giữ nguyên (INVALID_FEED_STATE / EXECUTION_IN_FLIGHT / POST_STATE_UNAVAILABLE /
  POST_REQUIRES_FEED_DUE / NO_VIDEO_AVAILABLE); `due` đủ 3 → `mseed = machine_day_seed(logical, machine, seed)`,
  `rng = random.Random(mseed)`, `order = rng.sample(due, len(due))`, `pair_gap = rng.choice((60, 75, 90))`,
  mỗi acc 1 `AccountBlock`, 2 entry FEED_ONLY (session_index 1/2); `len(due) != 3` → skip CẢ lane
  UNSCHEDULABLE_CAPACITY (trừ account đã skip reason khác — tránh duplicate skip, validate reject duplicate).
  `_entries` giờ trả `(entries, skipped, blocks)`; `_pick_locked` truyền `blocks=blocks` vào build.
- `models.py`: `FEED_ROW_MAX` 6 → 9 (rows 7–9 = overflow account cho capacity fixtures, KHÔNG thuộc lane nào;
  journal.py/watcher.py/runner.py vẫn hard-code 1..6 nhưng không bị đụng ở Phase 3 — skipped account không vào journal).

## Golden vector (contract) — cập nhật ĐÚNG 1 LẦN

- `reference_assignment` KHÔNG đổi (CONSTRAINTS không đổi): `assignment-v1-1ad3b6efcbf20bf30117afce900648b8`.
- entry mới (fleet 3-acc fixture, seed 7): block 1 = acct-2 (07:00, session 1, row 2):
  `reference_block_id = "block-v1-" + sha256(b"2026-08-10|1|1|acct-2")[:32]` = `block-v1-dfb4b0a5be7a00601dc1c15834d68a74`
  `reference_entry = entry-v1-49ba7d72c803ed0cda45d8f6b283dc3e`
- Cấu trúc test: reference dùng manifest_id của reference_assignment (config-mẫu, KHÔNG resource_mapping) —
  KHÔNG BAO GIỜ bằng entry thật của snapshot; pipeline check riêng dùng `snap.manifest_id`. 2 lớp độc lập.
- Tính hash mới: script python stdlib (json.dumps sort_keys separators=(",",":")) trước khi sửa assert.

## Fixture migration cho legacy tests (p1_r2 / watcher / regressions) — bắt buộc, plan thiếu

Plan sample code (dòng 455–495) đòi ĐÚNG 3 due/lane → mọi fixture 1-account (example config acct-a)
không lập lịch được → `entries[0]` IndexError ~71 test. Plan vẫn chạy p1_r2 ở verify → migrate fixture:

1. SOURCE = `SourceConfig.from_dict({...})` 3 acc `acct-a/b/c` rows 1/2/3, machine 1, SERIAL_A,
   revision `fleet-fixture-v1`, state_revisions `feed-v1`/`post-v1`. (KHÔNG sửa file example config — CLI test
   dùng nó và vẫn pass với manifest rỗng hợp lệ.)
2. FEED/POST dicts 3 acc. **LƯU Ý lỗi đã mắc**: comprehension `{c: ... for c in "abc"}` sinh key `"a"` thay vì
   `"acct-a"` → INVALID_FEED_STATE toàn bộ — phải `{f"acct-{c}": _feed_state(f"acct-{c}") for c in "abc"}`.
3. GIỮ seed=7 (mọi re-pick trong test dùng seed=7 phải khớp make_snapshot). Permutation
   `random.Random(machine_day_seed(date(2026,8,10),1,7)).sample([a,b,c],3)` = `[b,a,c]` → entries[0] = acct-b
   (row 2, 07:00). → `TARGET = {"machine":1,"serial":"SERIAL_A","account_row":2}` + mọi inline target row 1 → 2
   (watcher có ~6 chỗ, regressions ~2). Đừng đoán permutation — chạy script nháp.
4. Custom state dicts (vd post DUE chỉ cho acct-a) phải đủ 3 acc — thiếu → lane không fill → empty.
5. Assert chính xác bị vỡ cần sửa: `skipped == [...]` (vd bad-feed → 3 skip: INVALID_FEED_STATE + 2×
   UNSCHEDULABLE_CAPACITY), `reader.calls == ["acct-a"]` → 3 calls, `feed.calls == post.calls == 1` → 3,
   `select_due_entries("...T00:30") == []` → block3 S2 (23:15/23:30) vẫn due trong cửa sổ slot+90.
6. `run_entry(execute=True)` với as_of "06:30" trên entry 07:00 → `FUTURE_NOOP` — dời as_of 07:30.
7. Manual legacy payload (`test_prior_day_*`) với source 3 acc phải khai skipped cho 2 acc còn lại
   (validate recompute assignment với account_ids = accounts được entries+skipped bao phủ).

## Test thêm (nếu làm lại)

- Fleet test dùng `next_day = day+1` cho as_of/clock (day lẻ → as_of ngày kế T00:30, không hard-code).
- `test_pick_different_seed_changes_account_order_not_structure`: seed 99 → order [c,a,b] — chỉ assert cấu trúc.

## Tình trạng tại cutoff (tool-limit) — việc còn lại

- [x] fleet 5/5, contract 22/22 (27 chung), blocks 12/12
- [x] p1_r2: fixtures + 5 test đã patch (slot_seconds, prior_day, reads_one_immutable, feed_then_post_dry_run,
      custom_reader) — CHƯA re-run
- [ ] p1_r2 còn: `test_r10_watcher_cli_..._machine_999_manifest` (forge loop phải phủ 6 entries — account
      coverage), 5× `test_r11_red_launch_spec_mismatch_never_executes` (as_of 06:30 → 07:30),
      `test_r11_red_requested_day_...` (00:30 giờ trả block3 S2)
- [ ] watcher + regressions: migrate fixture (pattern trên), inline targets row 2, custom states đủ 3 acc,
      4 call-site `execute=True` as_of 07:30 (watcher:190, regressions:138/155 — 155 cần xử lý premise
      feed_then_post đã chết: picker không còn sinh feed_then_post)
- [ ] full suite + `py_compile` + `git diff --check` + grep `max_accounts_per_machine_day` (risk 9 plan)
- [ ] commit đúng message plan: `feat(cron): picker sinh 3 account-block/may/ngay (6 session, lane chan/le,
      seed per-machine-per-day), manifest them blocks, entry co block_id/session_index, khong reshuffle giua chung`
      — git add: picker.py manifest.py blocks.py test_hermes_cron_fleet.py test_hermes_cron_contract.py
      (+ test_hermes_cron_p1_r2.py vì fixture migrate là bắt buộc — báo user điểm này)
