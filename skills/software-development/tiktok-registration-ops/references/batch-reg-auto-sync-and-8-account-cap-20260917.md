# Quy trình & Pitfalls Đồng Bộ Excel và Phát Hiện Trần 8 Nick TikTok (17/09/2026)

## 1. Lỗi [04_add_account] do chạm trần 8 tài khoản TikTok
- **Hiện tượng**: App TikTok trên Samsung S7 chỉ cho phép đăng nhập tối đa 8 tài khoản. Khi đã đạt 8 nick, nút "Thêm tài khoản" biến mất khỏi bottom sheet dropdown.
- **Nguyên nhân**: TikTok obfuscate các resource-id của danh sách tài khoản qua nhiều version:
  `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`
  Nếu hàm `tap_add_account` chỉ tìm các ID cũ (`n72`, `lkp`), bộ đếm sẽ ra 0 nick và code nhảy xuống raise lỗi `[04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)` thay vì nhận diện đúng `MACHINE_FULL_8_ACCOUNTS`.
- **Khắc phục**: Đã cập nhật `tap_add_account` duyệt qua toàn bộ danh sách ID trên. Khi `_acc_count >= 8`, lập tức thoát dropdown, bấm Home và raise `MACHINE_FULL_8_ACCOUNTS`.

## 2. Kỷ luật Auto-Sync Deferred Tracking sau Batch Reg
- **Nguyên nhân gốc rễ lệch pha Excel vs Máy thật**:
  - Khi chạy batch reg qua `_run_all_targets.py`, worker con chạy với cờ `--defer-tracking-write` để tránh tranh chấp lock file Excel.
  - Worker chỉ sinh file JSON bằng chứng `tracking_result_stt*.json`.
  - Nếu runner `_run_all_targets.py` không có bước auto-sync, toàn bộ nick tạo thành công sẽ nằm trên máy thật nhưng file Excel `taikhoan_dat_v2_updated .xlsx` bị bỏ trống ô ID.
  - Hậu quả: Ca nuôi đọc file Excel thấy ô trống -> tưởng thiếu slot -> gọi script reg bù -> đâm đầu vào máy đã có 8 nick.
- **Giải pháp chuẩn hóa**:
  - `_run_all_targets.py` tự động gom các file `result_json` thành công ở cuối batch và gọi `write_deferred_results_sequential` để ghi khóa tuần tự vào file Excel.
  - Tuyệt đối không để batch reg ở chế độ "proof-only" bỏ rơi file JSON.

## 3. Auto-resolve Fallback Tracking Slot
- Khi file JSON thiếu `tracking_row`/`tik` hoặc vị trí dòng trên Excel bị trôi lệch:
  `deferred_tracking_writer.py` sử dụng hàm `resolve_tracking_slot(ws, stt, email)` để tự động dò slot trống còn lại của máy trên Excel thay vì fail `RESULT_MISSING_ROW_OR_TIK`.
