# Pitfall: TARGET_INVENTORY_MISSING_SERIAL

## Hiện tượng
Khi chạy `_detect_clean.py` hoặc `_run_all_targets.py`, quá trình detect mục tiêu reg bị dừng kèm thông báo:
```
DETECTION_BLOCKED: TARGET_INVENTORY_MISSING_SERIAL: row X
```

## Nguyên nhân
Trong file authoritative workbook `taikhoan_dat_v2_updated .xlsx` (hoặc `taikhoan_run_safe.xlsx`), một dòng thuộc một máy cụ thể có số máy nhưng ô cột `device ID` (serial) lại bị `None` hoặc để trống (thường do paste/nhập thiếu), trong khi logic fail-closed của `TargetInventory` yêu cầu mọi dòng có số máy hợp lệ đều phải có serial đồng nhất.

## Cách xử lý an toàn
1. Mở workbook đọc dòng bị thiếu (dòng `X`).
2. Xác định số máy (STT) của dòng đó.
3. Lấy serial chuẩn của máy đó từ các dòng khác cùng STT.
4. Điền bổ sung serial chuẩn vào ô `device ID` bị thiếu trên cả 2 workbook:
   - `D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (sheet `Tài Khoản`, column J / col 10)
   - `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (sheet `Accounts`, column B / col 2)
5. Lưu workbook và chạy lại `python _detect_clean.py` để verify target detection.
