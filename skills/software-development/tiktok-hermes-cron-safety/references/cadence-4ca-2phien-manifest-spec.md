# Cấu hình Cadence 4 Ca x 2 Phiên & Quy tắc Đồng bộ Manifest (TikTok Hermes-Cron)

## 1. Mô hình Cadence 4 Ca x 2 Phiên
- **Khung giờ (Block Anchors)**: `["06:00", "12:00", "18:00", "00:00"]` (4 block/máy/ngày).
- **Số phiên mỗi ca**: 2 phiên (Session 1 & Session 2). Mỗi phiên 60 phút.
- **Phân bổ Lane theo Parity ngày**:
  - Lane A (Ngày chẵn): Rows `[2, 4, 6, 8]` (tương ứng Ca 1, 2, 3, 4).
  - Lane B (Ngày lẻ): Rows `[1, 3, 5, 7]` (tương ứng Ca 1, 2, 3, 4).
- **Quy tắc gán Account**: Mỗi account chỉ chạy đúng 1 block duy nhất trong ngày (4 ca cho 4 account khác nhau trên cùng máy). Không còn mô hình 2 ca/ngày (sáng + tối) như bản 3 ca cũ.

## 2. Ràng buộc trong `CONSTRAINTS` (`manifest.py`)
```python
CONSTRAINTS = {
    "feed_row_max": 8, "feed_row_min": 1, "grace_minutes": 90,
    "max_accounts_per_machine_day": 4, "min_start_gap_minutes": 180,
    "reserved_blocks": [],
    "slot_duration_minutes": 60, "slot_grid_minutes": 5,
    "window_start": "06:00", "window_end": "02:00",
    "blocks_per_machine_day": 4, "sessions_per_block": 2,
    "pair_gap_minutes": [35, 60], "inter_block_gap_minutes": [90, 300],
    "lanes": [{"lane": "A", "rows": [2, 4, 6, 8]}, {"lane": "B", "rows": [1, 3, 5, 7]}],
    "block_anchors": ["06:00", "12:00", "18:00", "00:00"],
}
```

## 3. Quy tắc Xác thực `_validate_block_structure`
Khi validate manifest cấu trúc 4 ca x 2 phiên:
1. `block["block_index"] not in (1, 2, 3, 4)`: Chấp nhận từ 1 đến 4.
2. `len(block["entry_ids"]) != 2`: Mỗi block chỉ có đúng 2 entry ID.
3. `entry.get("session_index") not in (1, 2)`: Mỗi entry thuộc session 1 hoặc 2.
4. `len(block_entries) != 2 or [e["session_index"] for e in block_entries] != [1, 2]`: Sắp xếp theo session_index phải đúng thứ tự [1, 2].
5. `s1, s2 = block_entries[0], block_entries[1]`: Bỏ hoàn toàn tham chiếu `s3`.
6. Kiểm tra giới hạn máy: `len(_bids) > 4` raise `UNSCHEDULABLE_CAPACITY`.
7. Kiểm tra phân bổ account:
   ```python
   for _key, _bids in account_blocks_idx.items():
       if len(_bids) > 1:
           raise ValueError(ReasonCode.MANIFEST_IDENTITY_MISMATCH.value)
   ```
   (Bỏ hoàn toàn logic cũ `indices != {1, 3}`).

## 4. Kỷ luật thực thi khi nhận lệnh giới hạn Tool Calls (3-5 calls)
Khi người dùng yêu cầu "Hoàn thành ngay trong 3-5 tool calls. Báo cáo git diff":
- **Call 1**: `read_file` đọc chính xác vùng cần sửa trong file mục tiêu (không gọi `git status` hay grep/search lang thang).
- **Call 2**: `patch` áp dụng thay đổi code.
- **Call 3**: `terminal` chạy lệnh compile (`python -m py_compile ...`) và `git diff` cùng lúc.
Tuyệt đối không lãng phí iteration kiểm tra các file ngoài phạm vi yêu cầu.
