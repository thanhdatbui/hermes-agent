# 4 Ca x 2 Phiên Invariants & Manifest Structure (Hermes Cron)

## 1. Context
Chuyển đổi lịch nuôi acc TikTok từ chế độ cũ (3 ca x 3 phiên / ngày, 6 hàng, 3 block) sang chế độ 4 ca x 2 phiên / ngày (8 hàng, 4 block, 2 phiên mỗi block).

## 2. Invariants trong `manifest.py`

### 2.1. `CONSTRAINTS` Dictionary
- `feed_row_max`: `8` (trước: `6`)
- `max_accounts_per_machine_day`: `4` (trước: `3`)
- `blocks_per_machine_day`: `4` (trước: `3`)
- `sessions_per_block`: `2` (trước: `3`)
- `lanes`:
  - Lane A: `[2, 4, 6, 8]`
  - Lane B: `[1, 3, 5, 7]`
- `block_anchors`: `["06:00", "12:00", "18:00", "00:00"]` (trước: `["06:00", "12:30", "19:00"]`)

### 2.2. Fail-Closed Validation trong `_validate_block_structure`
1. **Block entry IDs length**:
   `len(block["entry_ids"]) != 2` (mỗi block chứa đúng 2 sessions).
2. **Block index range**:
   `block["block_index"] not in (1, 2, 3, 4)`.
3. **Session index per entry**:
   `entry.get("session_index") not in (1, 2)`.
4. **Machine block capacity**:
   `len(_bids) > 4` (tối đa 4 blocks/máy/ngày).
5. **Account block quota**:
   Mỗi account chỉ được gán tối đa 1 block/ngày (`if len(_bids) > 1: raise ValueError(ReasonCode.MANIFEST_IDENTITY_MISMATCH.value)`). Bỏ quy tắc 2 block sáng + tối cũ.
6. **Block entries binding**:
   - `len(block_entries) != 2 or [e["session_index"] for e in block_entries] != [1, 2]`
   - Unpack đúng `s1, s2 = block_entries[0], block_entries[1]`
   - Xóa bỏ mọi liên kết và kiểm tra của `s3`.

## 3. Verification Commands
Sau khi chỉnh sửa `manifest.py`, luôn chạy:
```bash
python -m py_compile "D:/Taadaa/tiktok-luot nuoi acc/python_runner/hermes_cron/manifest.py"
git -C "D:/Taadaa/tiktok-luot nuoi acc" diff python_runner/hermes_cron/manifest.py
```
