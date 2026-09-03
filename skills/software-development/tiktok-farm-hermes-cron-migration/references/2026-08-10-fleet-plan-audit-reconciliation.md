# 2026-08-10 — Fleet account-block plan: audit reconciliation (3 MAJOR + 3 MINOR + 4 NIT)

Plan: `.hermes/plans/2026-08-10_fleet-account-block-scheduler.md` (866 → 956 dòng sau fix).
Ràng buộc task: CHỈ sửa plan markdown, KHÔNG sửa code repo; giữ nguyên cấu trúc 8 phase; trả danh sách thay đổi theo locator.

## MAJOR 1 — Công thức build_block_sessions (pair-gap)
- Sai cũ: bảng feasibility ghi cột S2 "09:00–09:30" (đọc nhầm thành phiên 30'); test block 3 assert end 00:00 cho gap 90.
- Chốt: `S2_start = S1_end + pair_gap`. B1: gap 60 → S2 09:00–10:00 (end 10:00), gap 90 → 09:30–10:30 (end 10:30).
  B3: gap 60 → 23:00–00:00(+1), gap 90 → 23:30–00:30(+1). End max B1/B2/B3 = 10:30/17:30/00:30.
- Sửa tại: bảng feasibility (header thiết kế) + Phase 2 Step 2.1 (tests: thêm assert gap 90, sửa block-3 assert) +
  Step 2.3 (comment công thức) + Phase 5 `test_runner_accepts_block3_session_after_0100` (selector).

## MAJOR 2 — Golden vector / mốc 02:30 thống nhất 1 lần
- Trước: lệnh "đổi 01:30 → 02:30" xuất hiện 2 nơi (Phase 1 Step 1.1 VÀ Phase 5 Step 5.1) → trùng lặp, dễ lệch nhau.
- Chốt: Phase 1 Step 1.1 là nơi DUY NHẤT; thêm bullet "Mốc window thống nhất" vào Quy ước chung (đầu plan);
  Phase 5 (Files + note cuối Step 5.1) chỉ tham chiếu, không sửa lại; golden vector cập nhật ĐÚNG 1 LẦN ở Phase 3
  (tính lại reference hash bằng stdlib như test tự tính `reference_*` — không hard-code).

## MAJOR 3 — Baseline thực tế = 121 passed (không phải 117 / 3 failed)
- Plan cũ ghi "117 passed, 3 failed (3 đỏ tồn tại từ trước)" và Phase 0 là RED→GREEN (sửa journal.py/watcher.py,
  commit "dong 3 regression").
- Audit xác minh baseline thực tế 121/121 GREEN → Phase 0 chuyển thành **verification-only**: xóa Step 0.3 (RED)
  và Step 0.4 (GREEN), bỏ git add journal.py/watcher.py, bỏ commit "dong 3 regression", 3 test từng đỏ chạy riêng → PASS.
- Bài học: con số baseline ghi trong plan có thể SAI — verify với test suite/repo thật trước khi thiết kế Phase 0
  theo hướng "fix 3 test đỏ" (nếu làm theo plan cũ sẽ sửa code vô ích).

## MINOR 4 — Test entry chen giữa S1–S2
- Phase 4 Step 4.1: thêm `test_validation_rejects_foreign_entry_inside_pair_gap` — entry block khác (cùng máy)
  đặt slot_time 08:30 (giữa S1_end 08:00 và S2_start) → `pytest.raises(ValueError)`.
- Phase 4 Step 4.3: thêm nhánh fail-closed trong `_validate_block_structure` — với mỗi block, mọi entry khác block
  cùng máy có `gap_start <= slot_time < gap_end` → `ReasonCode.SOURCE_CONFIG_INVALID`.

## MINOR 5 — Test bỏ reserved blocks
- Phase 1 Step 1.1, `test_duration_reserved_and_cross_midnight`: thêm assert slot 12:30–13:30 & 17:30–18:30 được
  chấp nhận (reserved 12–14/17–19 đã bỏ), slot 03:00 bị chặn (ngoài window), `is_in_logical_window(02:00) == False`.

## MINOR 6 — Body test CLI dry-run block 3
- Stub `...` → body đầy đủ (Phase 5 Step 5.1). Pattern đã verify với code thật:
  - Gọi `runner_main([...])` TRỰC TIẾP (import từ `python_runner.scripts.hermes_cron_runner`), không spawn subprocess.
  - Args bắt buộc: `--state-root --offline-root --day --as-of --reference-time --source-config`.
  - `--as-of 2026-08-11T00:15:00+07:00`: sau nửa đêm, trong window, block 3 S2 đang due
    (`select_due_entries` lọc `slot <= now <= slot+90`, S2 slot 23:00–23:30 → due tới 00:30–01:00).
  - `--source-config` cần FILE thật (`SourceConfig.from_json(paths.regular_file(...))`) → viết raw dict fixture ra file;
    tách helper `_fleet_source_raw()` dùng chung với `fleet_source()`.
  - monkeypatch `subprocess.run` → assert `calls == []` (offline, không spawn); stdout JSON toàn `DRY_RUN_PREVIEW`;
    entry block 3 S2 (`slot_end` bắt đầu 2026-08-11T00) nằm trong journal previews; logical day giữ 2026-08-10.

## NIT 7–10
- 7: `reserved_intervals` trả `[]` VĨNH VIỄN — bỏ câu "có thể xóa ở Phase 3" (gây nhầm lẫn).
- 8: assert `gap % 15 == 0` trực tiếp trong `test_build_block_sessions_pair_gap_on_grid`.
- 9: `test_account_block_dataclass_shape` bỏ assert điều kiện `if seed == 1234 else True` → `seed = machine_day_seed(...)`
  + assert vô điều kiện.
- 10: `test_no_session_outside_assigned_block` dùng cặp block 1/block 3 (gap lớn nhất) thay vì block 1/block 2.

## Pitfalls phát hiện khi verify plan với repo thật
- **Test selector trong plan có thể là latent bug**: Phase 5 test cũ lọc `slot_time.startswith("2026-08-11T00")` —
  KHÔNG entry nào khớp (block 3 S2 slot bắt đầu 23:00–23:30 ngày logical 08-10) → StopIteration khi chạy. Phải chọn
  entry theo `block_id` + `session_index`.
- **`run_entry(execute=False)` trả `DRY_RUN_PREVIEW` TRƯỚC mọi slot check** (đọc runner.py ~309-311) — as_of 01:30 hợp lệ
  cho run_entry dry-run, nhưng `select_due_entries` lọc `slot <= now <= slot + 90` → CLI test phải dùng as_of trong
  due window (00:15), không phải 01:30.
- **`_assert_requested_day` (runner.py ~266-272)**: chặn `1 <= hour < 6` (cũ) → Phase 5 đổi thành `2 <= hour < 6`;
  hour 0 (00:15) luôn pass; `logical_day_for` giữ mapping midnight → ngày logical trước.
- **Same-file patch: KHÔNG batch song song** — nhiều patch tool calls cùng 1 file trong 1 turn chạy concurrent
  (read-modify-write race). Serialize 1 patch/turn (fuzzy replace-mode từng hunk) — an toàn hơn V4A multi-hunk cho
  markdown dài nhiều tiếng Việt.
- **Verify sau khi sửa plan**: grep các giá trị cũ (117 / 3 failed / "01:30 làm mốc ngoài window" / "09:00–09:30" /
  "Step 0.5" / "dong 3 regression"), check 8 header phase còn nguyên (`grep -nE '^## Phase'`), `git status --short`
  chỉ còn file plan bị đụng (code repo giữ nguyên dirty tree sẵn có).
