# Cron Setup Verification & Canary Simulation Protocol

## 1. Bối cảnh & Vấn đề (The Problem)
Khi thiết lập hoặc sửa chữa các cron job vận hành chuỗi trên Farm (ví dụ: `post_noon_chain_watchdog`, feed watchdog, 2FA watchdog, avatar watchdog):
- **Bẫy Mock / Dry-run Giả Lập**: Chạy cờ `--dry-run` chỉ in ra text hardcode (`TOTAL=40 SUCCESS=40...`), hoàn toàn không gọi vào script runner thật, không khởi tạo process và không giải quyết được các lỗi ngầm.
- **Hậu quả**: Các lỗi ngầm như xung đột serial (bốc nhầm password mail vào serial trong file mapping), sai cú pháp CLI (`--all-online` thay vì `--live`), ô nhiễm `sys.path` do chạy thiếu `cwd` (Python load nhầm file cũ trong thư mục Home `C:\Users\Kibe`), hoặc kẹt dead-owner device lock chỉ phát tác vào ngày hôm sau khi cron thức dậy chạy thật.

## 2. Quy tắc Bắt Buộc (Invariant Rules)
1. **CẤM TUYỆT ĐỐI chỉ chạy `--dry-run` / mock rồi chốt**: Mọi thay đổi logic hoặc setup cron mới BẮT BUỘC phải kiểm chứng luồng thực thi thật.
2. **Canary Giả Lập Đến Giờ Chạy Thật**:
   - Khi setup cron cho một khung giờ tương lai (ví dụ cron ca trưa 14:30 - 17:30 thiết lập lúc tối): BẮT BUỘC chạy thử với cờ bypass điều kiện thời gian (`--force` hoặc tương đương) trên ít nhất 1-2 máy thật đang rảnh (unlocked).
   - Nếu toàn farm đang bận ca nuôi hoặc có lock, phải kiểm tra process runner thực tế của từng Phase (`run_all.ps1`, `run_batch_live_2fa.py`) để xác nhận:
     - Inventory nạp đủ số máy, không conflict serial.
     - Tham số CLI được parser nhận diện hợp lệ (exit code 0).
     - Subprocess được cấp đúng working directory `cwd=str(REPO_DIR)` để cô lập `sys.path`.
3. **Phân biệt Dead-Owner Lock vs Active Lock**:
   - Khi kiểm tra lock trước khi chạy, các lock có trạng thái `blocked` hoặc `running` nhưng PID đã chết (`owner_active is False` hoặc `pid not in psutil`) không được coi là blocker active. Cần dọn dẹp hoặc cho phép watchdog tự động bỏ qua.
4. **Bảo đảm Ghi Dữ liệu Kết quả (Data Persistence)**:
   - Các tác vụ tạo secret/credential (như Add 2FA TikTok, Reg Gmail) bắt buộc phải xác nhận cơ chế lưu file (`write_2fa`, `write_cell`) ghi trực tiếp vào Workbook chính (`taikhoan_dat_v2_updated .xlsx`) và có kiểm tra xác thực sau khi ghi (`reopen_verify`).
5. **Cron Luôn Gửi Báo Cáo (Delivery)**:
   - Báo cáo kết quả của chuỗi phải luôn được xuất ra `stdout` để cơ chế delivery của cronjob tự động gửi về Telegram/kênh giám sát chỉ định.
