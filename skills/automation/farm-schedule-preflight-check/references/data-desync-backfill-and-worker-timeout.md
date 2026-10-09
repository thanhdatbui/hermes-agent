# Data-desync backfill và worker timeout

## Tình huống
Preflight báo M28 đã đủ 8 nick nhưng workbook thiếu slot 5. Đối soát read-only xác nhận:

- `D:/Taadaa/data/tiktok_tracker.db`: `farm_account_info` có `@anggiathinh2905`, `may=28`, `tik=5`; `account_mapping` thiếu riêng nick này.
- `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx`: sheet `Tài Khoản`, Excel row 222 (`Máy=28`, `Folder Video=221`) bị trống.
- `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx`: Excel row 223 (`Máy=28`) bị trống ID.
- Backup đích danh `D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx.bak_20260924_082531.xlsx` và `*.bak_clean_duplicates_20260923_084324.xlsx` cùng xác nhận nguồn row 222:
  `ID=anggiathinh2905`, `PASS=X!vlNMIgUtGN3Vp`, `GMAIL=raknidoprao@hotmail.com`, `PASS MAIL=ChriDs6cnulty`, `NGÀY TẠO=2026-08-25`, `device ID=ce031603a3dc2d2804`; 2FA và ngày sinh rỗng.

## Quy trình chuẩn
1. Đóng băng target: không reg thêm, không logout, không `pm clear`, không sửa SQLite chỉ vì thấy lệch.
2. Chọn backup theo exact identity `Máy + Folder/slot + device ID`; xác nhận bằng backup thứ hai hoặc log đăng ký.
3. Soạn Patch Contract với exact files, sheet, row, columns, preserved fields, backup, atomic method và readback.
4. Worker chỉ sửa các file workbook được chỉ định. Không rebuild combined safe workbook để che việc source workbook còn sai; sync combined chỉ sau khi source đúng và qua entrypoint chính thức.
5. Thành công chỉ khi readback cho thấy đúng ID/email/pass/device, M28 đủ 8 nick và không duplicate. Mtime mới hoặc exit code không phải bằng chứng.
6. Worker timeout/không có summary là `UNPROVEN`; kiểm tra lại file đích trước khi retry. Lần retry phải dùng contract hẹp hơn, không gửi lại prompt cũ.
7. `account_mapping` là derived state: chỉ cập nhật nếu có entrypoint chính thức đã biết; nếu không, báo `UNAPPLIED_DB_DERIVED_STATE`, không tự viết SQLite.

## Pitfalls
- Dòng hiển thị qua text extraction có thể lệch một dòng so với Excel row; luôn xác nhận bằng `openpyxl` row index và header.
- `taikhoan_run_safe.xlsx` và `taikhoan_run_safe_combined.xlsx` là hai tầng khác nhau; sửa source Kibe trước, không coi combined là source of truth.
- Worker có thể timeout do workbook I/O chậm; timeout không đồng nghĩa đã ghi. Readback bắt buộc.
