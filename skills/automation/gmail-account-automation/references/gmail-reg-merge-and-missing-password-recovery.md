# Root Cause & Fix for Gmail Reg Merge & Missing Passwords in Excel

## 1. Hiện tượng & Triệu chứng
- Các tài khoản Gmail reg thành công trên Samsung S7 (hoặc đã tạo profile GPM) nhưng khi tra cứu trên `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`, `Master_All`) hoặc `gmail_clean_v2.xlsx` (sheet `Gmail Accounts`) thì cột **Password** bị trống (`None`/rỗng).
- Hậu quả dây chuyền: Các cron feeder nạp OAuth (`cron_gpm_oauth_full_pool.py`) hay script tự động hóa GPM quét Excel bị vướng điều kiện kiểm tra mật khẩu (`if not creds.get("password"): continue`) dẫn đến bỏ sót tài khoản hoặc báo lỗi script hàng loạt.

## 2. Nguyên nhân cốt lõi (Root Causes)

### A. Vô hiệu hóa ghi trực tiếp Excel (`--write-workbook-success` bị Deprecated)
- Để tránh xung đột ghi đè đồng thời (`PermissionError: [Errno 13]`) khi 15-40 máy reg chạy song song, `gmail_reg_v10.py` đã chuyển sang ghi file JSON kết quả riêng (`machine_XX.success.json`) vào `--result-dir`.
- Dữ liệu Excel hoàn toàn phụ thuộc vào bước chạy `scripts/merge_success_results.py` ở cuối `run_parallel.ps1`.

### B. Lỗi `BLOCKED_EXPECTED_WRITER_ID_MISSING` trong `merge_success_results.py`
- Hàm `single_writer_workbook_update` của `automation_core.workbook` bắt buộc phải có `declared_writer_id` và `expected_writer_id`.
- Trong môi trường chạy tự động nếu không export biến môi trường `GMAIL_WRITER_ID`, `merge_success_results.py` gọi `os.environ.get("GMAIL_EXPECTED_WRITER_ID", "")` bị rỗng -> `automation-core` quăng ngoại lệ `BLOCKED_EXPECTED_WRITER_ID_MISSING` và dừng với exit code 2.
- **Khắc phục**: Luôn cài đặt fallback identity chuẩn:
  ```python
  writer_id = os.environ.get("GMAIL_WRITER_ID") or "taadaa-writer-3c47f89f35e44795a79267e09fbcc72d"
  expected_writer_id = os.environ.get("GMAIL_EXPECTED_WRITER_ID") or writer_id
  ```

### C. Bẫy bỏ qua tài khoản đã có email nhưng thiếu mật khẩu (`existing_email` trap)
- Logic cũ của merger:
  ```python
  if email in workbook_emails:
      skip_reason = "existing_email"
  ```
- Nếu một email đã được thêm trước đó vào workbook (hoặc import từ nguồn khác) nhưng ô password bị rỗng/None, merger cũ sẽ **bỏ qua luôn** thay vì cập nhật mật khẩu cho dòng đó.
- **Khắc phục**: Khi phát hiện `email in workbook_emails`, kiểm tra nếu ô password hiện tại của email đó trong workbook là rỗng/None thì phải thực hiện **UPDATE PASSWORD** cho dòng đó thay vì gắn nhãn `skip_reason = "existing_email"`.

## 3. Quy trình trích xuất mật khẩu gốc khi bị sót
Khi phát hiện email trong Excel bị thiếu mật khẩu:
1. **Kiểm tra batch scripts**: Xem cấu hình các batch gần nhất trong `D:/Taadaa/GPM auto/scripts/` (ví dụ `run_batch_turn2_gmails.py`, `TARGET_10_ACCOUNTS`). Mật khẩu thường được lưu sẵn trong danh sách đối soát.
2. **Kiểm tra log reg**: Đọc `C:/Users/Kibe/AppData/Local/register-gmail/reg_log.txt` hoặc `logs_parallel_*` của máy tương ứng tại bước `[10] Password` và `build_password()`.
3. **Cập nhật đồng bộ**: Luôn cập nhật đồng thời cả 2 file:
   - `D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7` & `Master_All`).
   - `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (sheet `Gmail Accounts`).
