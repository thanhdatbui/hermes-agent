# Đối soát Nick Ký sinh & Cơ chế Deferred Tracking Auto-Sync (17/09/2026)

## 1. Bài học đối soát Nick Ký sinh (Parasite / Cross-Device Duplicates)
- **Sai lầm chết người**: Chỉ kiểm tra trùng lặp trên file Excel (`taikhoan_dat_v2_updated .xlsx`).
  - Trên Excel, mỗi dòng có thể có 1 nick khác nhau (không trùng tên nick giữa các dòng).
  - Nhưng trên **thiết bị thật (S7)**, nick ký sinh đã bị đăng nhập từ trước vào TikTok Account Switcher (do batch cũ chạy nhầm máy hoặc rớt mạng).
- **Phương pháp đối soát chuẩn**:
  1. Dump XML giao diện thật của Bottom Sheet Account Switcher trên từng máy (`get_ui_xml`).
  2. Bóc tách danh sách nick thực tế đang có trên thiết bị:
     - Match các node `android.widget.Button` có resource-id obfuscated: `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]`.
  3. So khớp ngược danh sách nick trên máy với danh sách nick chính chủ của máy đó trên Excel:
     - Nick nào có trên máy thật nhưng KHÔNG thuộc danh sách của máy đó trên Excel -> **Chắc chắn là nick ký sinh**.
  4. Nạp vào `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py` để canh máy rảnh và logout đơn lẻ đúng nick ký sinh, trả lại slot trống.

## 2. Cơ chế Auto-Sync Deferred Tracking vào Excel sau Batch Reg
- **Nguyên nhân bug cũ**:
  - `_run_all_targets.py` chạy các worker con với `--defer-tracking-write` để tránh xung đột ghi đè Excel.
  - Sau khi reg xong, runner kết thúc ở chế độ "proof-only launcher" và đánh dấu `NOT_ATTEMPTED_BY_LOCAL_LAUNCHER` mà không tự sync.
  - Hậu quả: Nick đã vào máy thật nhưng Excel bị trống ô ID -> Ca nuôi đọc Excel thấy trống lại tiếp tục gọi reg bù -> Gây kẹt trần 8 nick (`MACHINE_FULL_8_ACCOUNTS`).
- **Giải pháp chuẩn đã chuẩn hóa**:
  - Cuối batch `_run_all_targets.py`, tự động gom toàn bộ các file `result_json` thành công và gọi `write_deferred_results_sequential`.
  - Giữ exclusive write lock, tạo backup tự động trước khi ghi, và cập nhật ngay vào `taikhoan_dat_v2_updated .xlsx`.
  - Trong `scripts/deferred_tracking_writer.py`, hàm `_check_expected_row` tích hợp fallback dynamic `resolve_tracking_slot` khi `tracking_row`/`tik` bị trống hoặc bị trôi lệch vị trí.
