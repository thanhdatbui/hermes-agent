# Scheduler Migration: 3 Ca × 3 Phiên → 4 Ca × 2 Phiên (2026-09-09)

## Summary
User quyết định chuyển từ 3 ca × 3 phiên (6 acc/máy, Row 1-6) sang 4 ca × 2 phiên (8 acc/máy, Row 1-8).
Mục đích: trải đều 24h, tăng số acc/máy, giảm tải máy (mỗi ca ngắn hơn), tạo khoảng nghỉ đêm hợp lý.

## New Architecture
- **4 Ca rải đều 6 tiếng:** Anchors `("06:00", "12:00", "18:00", "00:00")`
- **2 Phiên/Ca:** Phiên 1 (~30-40 phút) + pair_gap (35-60 phút nghỉ) + Phiên 2 (~30-40 phút)
- **Phiên 2 = Phiên cuối ca:** Kích hoạt Upload Hook + Follow Hook + Clear Cache Hook
- **Lane:** Ngày Lẻ = Row 1,3,5,7 (Lane B) | Ngày Chẵn = Row 2,4,6,8 (Lane A)
- **Mỗi acc chỉ 1 block/ngày** (khác cũ: Row 1/2 chạy 2 block/ngày)

## Files Changed
### tiktok-luot nuoi acc (7 files)
1. `python_runner/hermes_cron/blocks.py` — BLOCK_ANCHORS, LANES, build_block_sessions (2 tuples), AccountBlock.session_slots
2. `python_runner/hermes_cron/picker.py` — _feed_decision (successes_today cap=2), _entries (block_index 1-4)
3. `python_runner/hermes_cron/manifest.py` — CONSTRAINTS (feed_row_max=8, blocks_per_machine_day=4, sessions_per_block=2), _validate_block_structure (2 sessions, block_index 1-4, account 1 block/day)
4. `python_runner/flows/multi_machine_feed_session.py` — _effective_block_index (accept 1-4), _effective_session_index (accept 1-2), _is_final_block4_session (renamed from block3), upload gate (session_index==2), clear_cache gate (block_index==4, session_index==2)
5. `python_runner/tests/test_hermes_cron_contract.py` — Golden vector hash update
6. `python_runner/tests/test_upload_hook_alerts.py` — _session_index fixture = 2
7. `python_runner/tests/test_clear_cache_hook.py` — Function rename, block_index=4, session_index=2, new test data
8. `scripts/hermes_cron/feed_session_watchdog.py` — SESSION_WINDOWS 4 ca × 2 phiên

### tiktok-follow (18 files)
1. `follow_runner/config.example.yaml` — budget_per_session_min=15, max=18, default=18
2. `config/machine*.yaml` (17 files) — Same budget update

## Pitfalls Encountered

### 1. Golden Vector Hash Drift
**Problem:** Changing `CONSTRAINTS` in manifest.py changes the `reference_assignment` and `reference_entry` hashes in test_hermes_cron_contract.py.
**Fix:** Recalculate using Python script (not manual guessing):
```python
from python_runner.hermes_cron.manifest import CONSTRAINTS
from python_runner.tests.test_hermes_cron_contract import stdlib_reference_bytes
# Recompute hash and update assertion
```

### 2. _effective_block_index Only Accepts (1,2,3)
**Problem:** Source had `return raw if raw in (1, 2, 3) else None`. Block 4 → None → _is_final_block4_session always False → clear_cache_hook never runs.
**Fix:** Change to `(1, 2, 3, 4)`.

### 3. _effective_session_index Must Be Limited to (1,2)
**Problem:** If kept at (1,2,3), session_index=3 is still accepted → potential race condition with old 3-session mode.
**Fix:** Change to `(1, 2)`. Also update cohort fallback: `plan_session in (1, 2)`.

### 4. Function Rename Not Applied to All Call Sites
**Problem:** `_is_final_block3_session` renamed to `_is_final_block4_session` in function def but 4 call sites still used old name.
**Fix:** Use `sed -i 's/_is_final_block3_session/_is_final_block4_session/g'` or grep -rn to find all occurrences.

### 5. String Reason Mismatch
**Problem:** Source returned `"not-block3-final-session"` but test expected `"not-block4-final-session"`.
**Fix:** Update source string to match.

### 6. sed Mangles Python Dict Quotes
**Problem:** `sed 's/"_block_index": 3/"_block_index": 4/g'` strips the opening `"` when the pattern includes it.
**Fix:** Use Python `str.replace()` or `patch` tool instead of sed on Python dict strings.

### 7. Test Fixture Default Values
**Problem:** `_make_dummy_context(block_index=3, session_index=3)` defaults need updating to `(4, 2)`.
**Fix:** Change defaults AND verify all call sites that don't pass explicit args.

### 8. Watchdog File Sync
**Problem:** `C:\Users\Kibe\AppData\Local\hermes\scripts\feed_session_watchdog.py` (runtime) differs from `scripts/hermes_cron/feed_session_watchdog.py` (repo).
**Fix:** Copy runtime → repo after editing runtime file. Use Python shutil to handle Windows paths.

## Follow Budget Change
- Old: 3 sessions/day × 9-12 follow/session = ~35/day
- New: 2 sessions/day × 15-18 follow/session = ~35/day
- Config: `budget_per_session_min: 15`, `budget_per_session_max: 18`, `budget_per_session: 18`
- Applied to: `config.example.yaml` + all 17 `config/machine*.yaml`
