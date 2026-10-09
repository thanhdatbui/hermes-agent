# Triage Hiện Trường: Watchdog Báo Cáo Thiếu Cụm Farm (Dual-Cluster Missing Farm)

## Hiện Tượng
Cronjob `tiktok-feed-session-watchdog` gửi báo cáo tổng kết phiên (ví dụ Ca 2 Phiên 1/2) chỉ xuất hiện khối `【FARM KIBE - MÁY 1-80】`, hoàn toàn không có khối `【FARM ADMIN - MÁY 201-280】`.

## Cơ Chế Kiến Trúc
1. **Watchdog (`feed_session_watchdog.py`):**
   - Quét danh sách `CLUSTERS` (`kibe` và `admin`).
   - Kiểm tra `c_live = cluster["live_root"]` -> `date_live = os.path.join(c_live, target_date)`.
   - Nếu thư mục ngày không tồn tại hoặc không tìm thấy lượt chạy nào (`not session_runs`), watchdog thực hiện `continue` (bỏ qua cụm đó và chỉ báo cáo các cụm có dữ liệu).

2. **Runner (`tiktok_runner.py`):**
   - Mỗi tick 15 phút, runner kiểm tra các cụm trong `CLUSTERS`.
   - Gọi `valid_count = _count_valid_accounts_for_row(row, workbook_path=cluster_wb)`.
   - Nếu `valid_count == 0` (Row đó chưa có nick trong `taikhoan_run_safe.xlsx`, hoặc file Excel chưa được OneDrive sync về máy):
     + Ghi log: `tiktok_runner [<cluster>]: Row <row> co 0 account hop le... skipping window <window_key>.`
     + Ghi nhận `_save_state(row, window_key, now, state_file=cluster_state)` vào `runtime/<cluster>/cron-state/runner_simple_state.json`.
     + Bỏ qua (không spawn `run-feed-session.ps1`).
   - Do không spawn nên không tạo thư mục `runtime/<cluster>/live/<date>/row-<row>-<time>/`.
   - Watchdog khi quét sẽ không tìm thấy thư mục của cụm đó và âm thầm bỏ qua.

## Quy Trình Kiểm Tra O(1) An Toàn (Cấm Quét Đĩa)
1. **Kiểm tra trạng thái runner của cụm:**
   Đọc `D:/Taadaa/runtime/<cluster>/cron-state/runner_simple_state.json`:
   - Xác nhận `last_row` và `last_window`.
2. **Kiểm tra số tài khoản hợp lệ của Row:**
   Đọc `D:/OneDrive/TaadaaData/<cluster>/taikhoan_run_safe.xlsx`:
   - Kiểm tra xem Row đó có account nào không. Nếu 0 account -> Đây là lý do runner skip.
3. **Kiểm tra hiện trường thiết bị:**
   Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` (ví dụ N=201 cho Admin) để xác nhận trạng thái máy (màn hình, launcher, pin, kết nối ADB).
