# LANES lặp row — shape change lần 2 (2026-08-20, fix cron RESERVED_BLOCK_CONFLICT)

## Bối cảnh

Cron `phase9-staging-picker` (06:00 ngày 2026-08-20) fail `ValueError: RESERVED_BLOCK_CONFLICT` tại `manifest.py:558`; cron `phase9-watcher-tiktok-feed` (06:07) fail cùng nguồn. Manifest ngày không được tạo → toàn bộ lịch nuôi acc hôm đó không chạy. State hỏng: `manifests/<day>/ACTIVE.lock` = "000" (0 byte), `snapshot_bundles/<day>/ACTIVE` = 0 byte (chưa publish).

## Root cause (verify bằng chạy thật)

1. **Commit 7053491** (19/08 23:09) đổi `JITTER_MINUTES` từ `(-20,-15,15,20)` → `tuple(range(-25,26))` (liên tục từng phút). NHƯNG `models.py:is_schedulable_interval` yêu cầu `minute % SLOT_GRID_MINUTES(5) == 0` → jitter 1 phút lệch grid → `RESERVED_BLOCK_CONFLICT`. Verify: 312/534 entries BAD (minute%5 != 0) trước fix, 0 BAD sau fix.
2. **Block 1 anchor = window start 06:00 + jitter âm (-25..-5)** → s1 05:35..05:55 TRƯỚC window → cùng lỗi. Verify: mọi j ∈ {-25,-20,-15,-10,-5} đẩy s1 < 06:00.
3. **Commit 1f7225a** (19/08 23:30) đổi LANES `(2,4,6)/(1,3,5)` → `(2,4,2)/(1,3,1)` (Row 1/2 chạy 2 lần/ngày). NHƯNG validator có 2 chỗ cấm account ở 2 block khác nhau → tự từ chối chính output của picker.

## Fix 3 lớp (commit 3735dd6)

### Lớp 1 — blocks.py
```python
# PHẢI là bội số của SLOT_GRID_MINUTES (5)
JITTER_MINUTES = tuple(range(-25, 26, 5))   # (-25,-20,...,25) 11 mốc
```

### Lớp 2 — picker.py (`_entries`)
```python
if block_index == 1:
    jitter = max(jitter, 0)   # anchor 06:00 = window start, jitter âm trước window
# block 2/3 KHÔNG clamp: s3_end max = 19:00+25'+180'+2*60' = 00:25 hôm sau < 02:00
```
- Đã verify 0/66 tổ hợp jitter×gap vượt window (loop `for j in range(-25,26,5) for gap in range(35,61,5)`).
- CẢNH BÁO: clamp block 3 ban đầu tính sai đơn vị (viết `(1560-1390)//60 = 2` thay vì giây) — nếu clamp chạy sẽ ép jitter 5/10/...25 về 2 → `2 % 5 != 0` → TÁI TẠO bug grid. Dead-code clamp = nguồn bug tiềm ẩn; verify bằng số rồi BỎ hẳn.

### Lớp 3 — manifest.py (CẢ HAI chỗ)
- **Entry-level** (`validate_manifest`): account xuất hiện lần 2 → cho phép nếu block pair = {1,3} (prev_index, cur_index từ payload["blocks"]), cấm nếu khác.
- **Block-level** (`_validate_block_structure.account_blocks_idx`): `len(_bids) in (1,2)`; nếu 2 → `{block_index} == {1,3}` + CÙNG machine (`len({e["machine"] for e in entries if e["account"]==_key}) == 1`); cấm >2.

### Lớp 4 (phát hiện khi chạy suite) — picker.py dedupe skipped
Block 1+3 cùng account bị skip (INVALID_FEED_STATE/NOT_DUE) → `skipped` chứa account 2 lần → validator `skip["account_id"] in accounts` sau `accounts.add` → `SOURCE_CONFIG_INVALID`. Fix: `if not any(s["account_id"] == account.account_id for s in skipped):` trước mỗi append (3 nhánh: exception, decision.reason_code, not feed_due).

## Test hardcode phải quét (đều đã hit)

| Pattern cũ | Sửa thành |
|---|---|
| `{e["account"]} == {"acct-2","acct-4","acct-6"}` | `{"acct-2","acct-4"}` (row 6 ngoài lane A) |
| odd day `{"acct-1","acct-3","acct-5"}` | `{"acct-1","acct-3"}` |
| anchors `["06:00","12:45","19:15"]` | recompute RNG: seed 7/day 10/8/machine 1 → block1 jitter 15 → `["06:15","12:30","19:00"]`; odd day → `["06:00","12:50","18:35"]` (block1 -25 clamp 0, block2 +20, block3 -25) |
| `JITTER_MINUTES == (-20,-15,15,20)` | `(-25,-20,-15,-10,-5,0,5,10,15,20,25)` + `all(j%5==0)` |
| golden entry hash `entry-v1-1f885...` | `entry-v1-08fe3de6588f554b8d5c2b572f1dd072` (slot_time 06:15) |
| wrapper "default-off" tests | repo live có permit thật `runtime/hermes-cron/permits/*.permit` (tạo 17/08) → wrapper ĐÃ ACTIVE → set `env["HERMES_CRON_PERMIT_FILE"] = "C:/nonexistent-permit-hermes-cron"` để ép nhánh inactive |
| forge manifest `new_block_ids[block["account"]]` | account 2 block → KEY COLLISION → key theo `block["block_id"]` cũ: `new_block_ids[entry["block_id"]]` |
| `_fleet_pick_two_machine` rows (4,5,6) | máy 2 dùng acct-1/3/5 rows (1,3,5) |

## RNG probe để recompute anchors (không đoán)
```python
from python_runner.hermes_cron.blocks import machine_day_seed, JITTER_MINUTES
import random
rng = random.Random(machine_day_seed(date(2026,8,10), 1, 7) ^ (0x9E3779B9 * block_index))
jitter = rng.choice(JITTER_MINUTES)
if block_index == 1: jitter = max(jitter, 0)
gap = rng.choice(tuple(range(35,61,5)))
```

## Verify cuối (offline trước khi dọn state)
1. Chạy entrypoint picker thật với state cũ → tạo manifest OK (534 entries / 178 blocks / 141 skipped cho 2026-08-20).
2. Verify manifest: account row 2 xuất hiện block [1,3], row 4 block [2] — đúng LANES.
3. Dọn ACTIVE.lock 0-byte hỏng cũ (cả manifests/ + snapshot_bundles/).
4. Full hermes_cron suite: 363 passed, 1 skipped.
5. Commit + push; watcher load_active OK.
