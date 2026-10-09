# Pitfall: Báo Cáo Lệch Pha (Báo "0 Trống Slot" Khi Farm Còn Thiếu Nick)

### 1. Hiện tượng & Triệu chứng:
- Watchdog phiên (`feed_session_watchdog.py`) báo cáo:
  `• Tổng máy xử lý: 58 máy`
  `+ Trống slot/chưa có nick (0): Không có`
- Trong khi đó, alert hệ thống bên dưới (như Preflight Reg Bù `ensure_row_accounts.py`) lại cảnh báo:
  `Phát hiện 22 máy trống slot cần reg bù!`
- Người dùng phát hiện 2 alert mâu thuẫn, nghi ngờ watchdog "báo cáo láo / lấp liếm".

### 2. Nguyên nhân gốc rễ (Root Cause):
1. **Runner safe-skip trước khi tạo folder per-machine:**
   - Khi runner (`tiktok_runner.py`) gặp máy trống nick trong safe workbook (`account row X is empty (no username), skipping`), nó skip ngay từ khâu tiền kiểm và ghi nhận vào `run_manifest.json` (trong mảng `multi_machine_summary`), **hoàn toàn KHÔNG tạo thư mục `machines/machine_<N>`**.
2. **Watchdog chỉ quét thư mục con mà bỏ qua file manifest tổng:**
   - Hàm duyệt run `parse_run_all()` chỉ duyệt qua các folder `machines/machine_*` để nhặt kết quả. Các máy bị skip không có folder nên biến mất hoàn toàn khỏi tập `all_machines`.
3. **Coi tập máy có nick là 100% mục tiêu:**
   - Hàm `get_expected_machines_for_row(row)` đọc từ `hermes_cron_source_config.json` (vốn được sinh từ các dòng có nick trong safe workbook).
   - Nếu Row đó mới chỉ nạp 58 máy trên tổng 80 máy của Farm, `expected_machines` chỉ gồm 58 máy.
   - Watchdog tính `empty` bằng cách lọc trong `all_machines` (vốn chỉ gồm 58 máy có folder) $\rightarrow$ số máy trống trả về `0`, tổng máy xử lý hiển thị 58 máy thay vì 80 máy của Farm.

### 3. Quy chuẩn phòng tránh & Xử lý (Invariant Solution):
1. **Phải đọc `run_manifest.json` làm Source of Truth cho toàn bộ batch:**
   - Trong `parse_run_all()`, trước hoặc song song với việc quét thư mục con, BẮT BUỘC parse file `run_manifest.json` tại thư mục gốc của run.
   - Duyệt qua `multi_machine_summary` để trích xuất toàn bộ máy có trạng thái `config-error` hoặc `stop_reason` chứa `is empty (no username)` thành trạng thái `skipped-empty`.
2. **Quy mô Farm chuẩn (80 máy):**
   - Khi tổng kết các chỉ số của một Row, danh sách máy trống (`empty`) phải được đối soát trên toàn bộ 80 máy vật lý của Farm.
   - Bất kỳ máy nào không có nick ở Row tương ứng trong workbook BẮT BUỘC phải được liệt kê rõ ràng vào dòng `Trống slot/chưa có nick (N): ...`, tuyệt đối không được giấu nhẹm hay bỏ qua.
