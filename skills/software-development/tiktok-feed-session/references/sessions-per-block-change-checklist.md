# Đổi số phiên/ca (sessions_per_block) — checklist đồng bộ

Bài học 2026-08-16 (plan 3 phiên/ca + follow hook): đổi `sessions_per_block` 2→3 KHÔNG chỉ sửa blocks.py — **manifest.py hardcode validator reject → crash ngay** (picker gọi `validate_manifest`). Worker 1 phát hiện khi phân tích, allowlist ban đầu thiếu → phải mở rộng.

## Checklist đổi sessions_per_block (2→3, anchors mới, grid 5, jitter)

### 1. blocks.py
- `PAIR_GAP_MINUTES` (60,90)→(35,60); `INTER_BLOCK_GAP_MINUTES` (180,300)→(90,300); `BLOCK_ANCHORS` (07:00,14:00,21:00)→(06:00,12:30,19:00); thêm `JITTER_MINUTES = (-20,-15,15,20)`
- `_PAIR_GAP_GRID_MINUTES` 15→5 (`_VALID_PAIR_GAPS` tự tính range(35,61,5))
- `build_block_sessions(day, *, block_index, pair_gap_minutes, jitter_minutes=0)` → **3-tuple**: s1 = anchor+jitter; s2 = s1_END + gap; s3 = s2_END + gap
- `_anchor_for(block_index, day, *, jitter_minutes=0)`; `_validate_pair_gap` message "35..60 grid 5"
- `AccountBlock` thêm `jitter_minutes: int = 0` (default — backward-compat, test cũ gọi không arg) + session_slots type 3-tuple

### 2. models.py
- `SLOT_GRID_MINUTES` 15→5 (line ~21)

### 3. manifest.py (BẮT BUỘC — hay quên nhất)
- `CONSTRAINTS`: sessions_per_block 2→3, pair_gap_minutes [60,90]→[35,60], inter_block_gap_minutes [180,300]→[90,300], slot_grid_minutes 15→5, block_anchors ["07:00",...]→["06:00","12:30","19:00"]
- Validator pair_gap: `not in (60,75,90)` → `not in tuple(range(35,61,5))`
- Validator session_slots: khớp `build_block_sessions(...)` (3-tuple)
- Validator session_index: `not in (1,2)` → `not in (1,2,3)`
- Validator len(block_entries): `!= 2 or [1,2]` → `!= 3 or [1,2,3]` + unpack `s1, s2, s3`
- Identity checks (account/machine/serial/session_slots/entry_ids): mở rộng (s1,s2)→(s1,s2,s3)
- Inter-block gap: `< 180` → `< 90`

### 4. picker.py
- Unpack 3-tuple: `((1, slots[0]), (2, slots[1]), (3, slots[2]))` + session_slots serialise 3 phần tử
- Jitter: `jitter_rng = random.Random(mseed ^ (0x9E3779B9 * block_index))` → `jitter = jitter_rng.choice(JITTER_MINUTES)` → truyền GIÁ TRỊ vào AccountBlock/build_block_sessions (blocks KHÔNG tự tạo rng — tránh double-jitter + RNG drift làm manifest cũ đổi)
- `rng.choice((60,75,90))` hardcode → `pick_pair_gap(day, machine, seed, rng)` (dùng _VALID_PAIR_GAPS mới)
- Docstring "6 sessions" → "9 sessions, 1/2/3"
- Import: thêm JITTER_MINUTES, pick_pair_gap từ .blocks

### 5. Tests (hardcode cũ → đỏ hàng loạt)
- test_hermes_cron_blocks.py: anchors, gaps range(35,61,5) %5, len session_slots==3, jitter assert (s2 = s1_END+gap KHÔNG s1_start+60+gap — test sai viết 08:20 đúng 07:55; duration 300' KHÔNG 420')
- test_hermes_cron_fleet.py (~15): len(entries) 6→9, session_index (1,2)→(1,2,3), anchors, gap, inter-block 180→90
- test_hermes_cron_contract.py: golden vector (recompute hash từ output thật — KHÔNG tự đoán), slot_time 07:00→06:xx (jitter), len(grid_slots) 77→229 (grid 15→5)
- test_hermes_cron_p1_r2.py: entries[5]→[8], as_of 07:30→06:30
- test_hermes_cron_regressions.py + watcher.py: dùng Picker → jitter deterministic per day+machine+block_index

## Reactive phiên 2/3 (audit OpenCode MUST FIX)
- Runner GHI `last_feed_success_at` vào feed state SAU mỗi phiên success (hiện không ai ghi)
- CAP 3 phiên/ngày: `_feed_decision` đếm success_timestamps hôm nay; ≥3 → NOT_DUE
- Runner KHÔNG biết session_index khi chạy child (manifest entry có nhưng không truyền xuống MachineAccount) → bỏ switcher phiên 2/3 cần plumbing, defer (giữ switcher mọi phiên an toàn)

## Follow hook cuối phiên
- Subprocess: `python <follow-repo>/follow_runner/run_follow.py --machine N --config <follow-repo>/follow_runner/config.example.yaml --account-row-index R` (KHÔNG import chéo — 2 core/PYTHONPATH)
- Đọc `FOLLOW_RESULT <json>` stdout + exit code; gate sensitive (login/OTP/captcha/verify trong stop_reason → skip ghi "sensitive-skip"); FOLLOW_FAILED ghi follow_failed:true không dừng; ghi follow_result.json vào child artifact
