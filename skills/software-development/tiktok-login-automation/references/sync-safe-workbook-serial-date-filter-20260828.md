# Lỗi `CONFIG_ERROR: machine N has conflicting serials in workbook` do Cột Serial dính Text Ngày (2026-08-28)

## 1. Hiện tượng & Triệu chứng
Khi chạy reconcile account bằng script `scripts/reconcile_tiktok_accounts.py`:
```
CONFIG_ERROR: machine 15 has conflicting serials in workbook
```
Exit code 2 và tiến trình dừng ngay lập tức ở bước load workbook.

## 2. Nguyên nhân gốc
- Trong workbook `taikhoan_dat_v2_updated .xlsx`, cột 10 (`device ID`) ở một số dòng mới tạo bị ghi nhầm thành chuỗi ngày tháng (ví dụ: `23/08/2026` hoặc `2026-08-25`).
- Khi chạy script `sync-safe-workbook.py` để tạo `taikhoan_run_safe.xlsx`, logic cũ lấy nguyên giá trị cột 10 làm `Device ID`.
- Dẫn đến một máy (ví dụ Máy 15) có một số dòng chứa serial thật (`ad07170215e8f37ae0`) và một số dòng chứa chuỗi ngày (`23/08/2026`).
- Hàm `load_workbook_machines` trong `account_inventory.py` gom tập hợp serials của máy 15 thấy có >1 giá trị (`{'ad07170215e8f37ae0', '23/08/2026'}`) nên quăng lỗi `conflicting serials`.

## 3. Khắc phục
1. Trong `scripts/sync-safe-workbook.py`, thêm bộ lọc chuỗi ngày tháng:
   ```python
   source_serial = "" if re.match(r"^\d{2,4}[/-]\d{2}[/-]\d{2,4}$", raw_serial) else raw_serial
   ```
2. Nếu dòng bị khuyết serial do dính chuỗi ngày, script tự động fallback lấy serial chuẩn từ các dòng hợp lệ khác cùng máy hoặc từ `series_serials` / `EXTRA_MACHINES`.
3. Sau khi đồng bộ lại `taikhoan_run_safe.xlsx`, toàn bộ 480 dòng đều giữ đúng 1 serial hex chuẩn duy nhất cho mỗi máy.
