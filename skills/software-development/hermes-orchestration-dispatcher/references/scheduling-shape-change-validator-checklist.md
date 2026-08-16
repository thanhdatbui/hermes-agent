# Scheduling shape-change → validator crash checklist

Context: khi một "shape change" của scheduler (sessions_per_block 2→3, anchors đổi, jitter thêm,
pair_gap grid đổi, slot_grid 15→5) được implement xong nhưng suite đỏ hàng loạt, **kiểm tra validator
trước khi đụng tests** — picker thường CRASH trên chính output của nó, nghĩa là "CHỈ SỬA TESTS" là
bất khả. Session thật: 2026-08-16 phase9-authority-910a8add, 44 fail → 0 fail.

## Triệu chứng

- `validate_manifest` ném `RESERVED_BLOCK_CONFLICT` ngay trong `_pick_locked` (picker tự crash).
- Hàng loạt test fail cùng 1 traceback ở `manifest.py` `_validate_entry`/`_validate_block_structure`.

## 5 gap validator thường gặp (check theo thứ tự)

1. **`required_keys` thiếu field mới** — picker thêm field vào block dict (vd `jitter_minutes`),
   validator `set(block) != required_keys` → reject MỌI block. Mỗi field mới = phải vào required_keys.
2. **`len(block["entry_ids"]) != 2` còn sót** — đổi sessions_per_block phải đổi cả check này (2→3).
3. **`session_slots` canonical check bỏ qua tham số mới** — `build_block_sessions(day, block_index,
   pair_gap)` không truyền `jitter_minutes` → jittered slots không khớp canonical → reject.
4. **Inter-block gap so trên slot THỰC (jittered)** — jitter làm gap thực 65-85' dù nominal ≥90'.
   Fix: so **nominal (unjittered)** slots qua `build_block_sessions(..., jitter_minutes=0)`. Design
   note: "anchor cố định quyết định, KHÔNG enforce runtime" — INTER_BLOCK_GAP_MINUTES chỉ là
   contractual non-jittered feasibility, không phải runtime gate.
5. **Anchor block 1 = window start + jitter âm** — anchor 06:00 (window bắt đầu 06:00) + jitter -15/-20
   → s1 05:45/05:40 < window_start → `is_schedulable_interval` false → RESERVED_BLOCK_CONFLICT.
   Fix ở picker: `if block_index == 1 and jitter < 0: jitter = 0` (block 2/3 giữ ±20 — anchor sâu
   trong window). Đừng clamp trong `build_block_sessions` (blocks.py test muốn jitter -15/-20 chạy
   được qua builder trực tiếp).

## Probe khi picker self-validation crash

```python
import python_runner.hermes_cron.manifest as manifest_mod
def _noop(*a, **k): pass
manifest_mod.validate_manifest = _noop   # KHÔNG patch picker_mod!
```
Picker import `validate_manifest` BÊN TRONG `_pick_locked` (`from .manifest import validate_manifest`),
nên patch `picker_mod.validate_manifest` vô dụng — phải patch module `manifest`.

## Probe RNG để biết trước picker sẽ sinh gì

Tái hiện RNG của picker (không cần chạy Picker) để xem jitter/gap/slots từng seed:
```python
rng = random.Random(machine_day_seed(logical, machine, seed))
order = rng.sample(due, len(due))
for bi, acct in enumerate(order, 1):
    gap = pick_pair_gap(logical, machine, seed, rng)
    jit = random.Random(mseed ^ (0x9E3779B9 * bi)).choice(JITTER_MINUTES)
    if bi == 1 and jit < 0: jit = 0
    sess = build_block_sessions(logical, block_index=bi, pair_gap_minutes=gap, jitter_minutes=jit)
```
Chạy 20 seed → xác định min gap thực, jitter từng block — dùng làm golden tham chiếu cho test.

## Pattern sửa test hardcode (không yếu test)

- **Anchors**: session-1 anchors GIỜ LÀ jittered — đừng assert `["06:00","12:30","19:00"]` cứng;
  assert giá trị thật deterministic (vd `["06:00","12:45","19:15"]`) + assert jitter từng block
  (block 1 == 0 vì clamp, block 2/3 ∈ JITTER_MINUTES).
- **clear_cache_due / block-3 end**: block 3 end thay đổi theo jitter — tính từ snapshot
  (`max(parse_hcm_timestamp(e["slot_end"]) for e in entries của block 3)`) thay vì hardcode 00:30.
- **Runner as_of**: jittered s1 (vd 12:45) dịch cả execution window (slot + 90') — as_of hardcode
  cũ (14:30) giờ MISSED; chọn as_of trong window thật.
- **Midnight mapping**: block-3 s3 giờ kết thúc 23:45 (không còn qua nửa đêm với anchor 19:00 + jitter
  +15) → select_due_entries lúc 00:00 chỉ bắt entry s3 còn trong grace 90' (22:45→00:15).

## Golden vector recompute

- source_revision/block_id KHÔNG đổi khi đổi shape (chúng hash config/source/block identity).
- assignment/entry ĐỔI khi CONSTRAINTS đổi (sessions_per_block, block_anchors, pair_gap, slot_grid).
- Recompute bằng stdlib hash ĐÚNG công thức test hiện có (`stdlib_reference_bytes` +
  `hashlib.sha256(...).hexdigest()[:32]`), không hardcode từ output picker — picker có resource_mapping
  làm manifest_id khác reference (reference dùng account_ids đơn giản).
