# 3-CA PARITY picker — implementation + pitfalls (2026-08-18)

## Thiết kế chốt (user xác nhận qua 3 lượt hỏi — đừng tự diễn giải lại)

1. **3 ca/máy/ngày**: block_index 1/2/3, anchors `BLOCK_ANCHORS = ("06:00","12:30","19:00")`.
2. **Lane PARITY**: `blocks.py LANES = (("A",(2,4,6)),("B",(1,3,5)))` — ngày CHẴN (day.day%2==0) → lane A rows CHẴN (2,4,6); ngày LẺ → lane B rows LẺ (1,3,5). Ca 1/2/3 = lane rows[0/1/2].
3. **Nick giờ CỐ ĐỊNH theo row** — KHÔNG random thứ tự ca (user chốt: "1 nick chỉ chơi buổi sáng 2 ngày 1 lần" như người thật có thói quen; random ca = giờ lung tung như bot dễ detect). Jitter ±20' + stagger 2-8s = đủ chống fingerprint.
4. **Mỗi acc 3 phiên 60'**: session_index 1/2/3; s2 = s1_end + pair_gap; s3 = s2_end + pair_gap; pair_gap 35-60' grid 5 (`PAIR_GAP_MINUTES=(35,60)`, `_PAIR_GAP_GRID_MINUTES=5`).
5. **Máy thiếu acc row của ca → BỎ CA** (0-3 block/máy đều hợp lệ).
6. **Acc ngoài lane hôm đó → skipped `CAPACITY_EXCEEDED`** (bắt buộc — manifest validate `accounts != expected_ids` → MAPPING_CONFLICT nếu account không xuất hiện trong entries+skipped).

## Code đã implement

`picker.py _entries`: với mỗi máy, `accounts_by_row = {a.account_row: a for a in by_machine[machine]}`; trước loop block, append skipped CAPACITY_EXCEEDED cho account có `account_row not in rows` (lane hôm đó); sau đó loop block_index 1-3:
```python
row = rows[block_index - 1]
if row not in accounts_by_row: continue  # bỏ ca
account = accounts_by_row[row]
# feed decision (feed_due check) — không due → skipped NOT_DUE
jitter_rng = random.Random(machine_day_seed(logical, machine, seed) ^ (0x9E3779B9 * block_index))
jitter = jitter_rng.choice(JITTER_MINUTES)
if block_index == 1 and jitter < 0: jitter = 0   # CLAMP — 06:00 là window start
pair_gap = pick_pair_gap(logical, machine, seed, jitter_rng)
block = AccountBlock(day=logical, block_index=block_index, machine=machine,
    serial=account.serial, lane=lane, account_id=account.account_id,
    account_row=account.account_row, pair_gap_minutes=pair_gap,
    seed=machine_day_seed(logical, machine, seed), jitter_minutes=jitter)
# 3 entries với block_id + session_index 1/2/3 từ block.session_slots
```

`manifest.py _validate_block_structure`: `if len(_bids) > 3` (không `!= 3`) — máy 0-3 block hợp lệ.

`blocks.py`: `LANES = (("A",(2,4,6)),("B",(1,3,5)))` — `lane_for_day` giữ nguyên ("A" if day.day % 2 == 0).

## Pitfalls (mỗi cái từng fail thật 18/08)

### 1. Jitter -20' block 1 → RESERVED_BLOCK_CONFLICT
`build_block_sessions(block_index=1, jitter=-20)` → s1 = **05:40** (trước window 06:00) → `is_schedulable_interval` False → `_validate_entry` raise `RESERVED_BLOCK_CONFLICT`. Fix: `if block_index == 1 and jitter < 0: jitter = 0`. Chẩn đoán: probe `is_schedulable_interval` cho từng block×jitter×session — chỉ block1-jit-20 fail.

### 2. MAPPING_CONFLICT khi acc ngoài lane không vào skipped
Manifest validate line ~350: `accounts != expected_ids` — mọi account phải xuất hiện entries+skipped. Row-slot cũ không có khái niệm lane nên acc ngoài lane được skip tự nhiên (không có entry) — nhưng block-mode validate yêu cầu coverage. Fix: skip CAPACITY_EXCEEDED cho mọi account `row not in lane_rows(lane)`.

### 3. `_validate_entry` yêu cầu entry có block_id trong by_id + session_index 1..3
Entry không block (row-slot legacy) hoặc session_index thiếu → SOURCE_CONFIG_INVALID. Entry phải sinh qua `_entry(..., block_id=block.block_id, session_index=si)`.

### 4. Machine 22 example (verification chuẩn)
Ngày 18/08 (chẵn) lane A rows (2,4,6): máy 22 rows 1,2,4 → ca1=tooanh2604 (row2) 3 phiên 06:00/07:40/09:20; ca2=tangchi10 (row4) 3 phiên 12:10/14:10/16:10; acc row1 ngomai.ly → CAPACITY_EXCEEDED; row6 không acc → không ca3. Manifest thật: 107 blocks / 321 entries / 140 skipped, VALIDATE OK. Machine 1 (4 acc rows 1-4): ca1 row2, ca2 row4, ca3 row6 không acc → 2 blocks.

### 5. Test suite cũ (row-slot 17/08) fail hàng loạt — cần rewrite
73 test fail vì viết cho row-slot (6 entries/acc/day, all rows every day, entry-level tamper không block). Rewrite: `test_pick_creates_3_blocks_9_sessions` (lane parity), golden vector entries[0]=acct-2 row2 (ngày chẵn 10/08), tamper test sync block metadata + rehash block_id/session_index, `test_unschedulable_capacity_for_row_7` giữ (require_row 1..6). Worker luna cập nhật test — verify bằng full suite, không tự kê.

## Cron wiring state (18/08)

- Runner cron **PAUSED** trong lúc test rewrite — resume chỉ sau full suite xanh + audit.
- Wrapper deployed (repo_root probe fix + path forward slash).
- Cron no_agent chạy script với `cwd=HERMES_HOME/scripts` (KHÔNG workdir) → repo_root() phải probe path cố định. Xem `references/2026-08-18-cron-cwd-silent-nop-and-path-escape.md`.
