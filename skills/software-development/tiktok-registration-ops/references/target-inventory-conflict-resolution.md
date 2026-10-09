# Xử lý lỗi TARGET_INVENTORY_CONFLICT khi chạy _detect_clean.py

## Triệu chứng
Khi chạy `python _detect_clean.py` tại repo `D:\Taadaa\Tiktok_Reg`, script dừng với mã lỗi exit 2:
```
DETECTION_BLOCKED: TARGET_INVENTORY_CONFLICT: machine <ID>
```

## Nguyên nhân
- Script `target_inventory.py` nạp cấu hình mapping máy từ các workbook:
  - `TRACKING_WORKBOOK` (`taikhoan_dat_v2_updated .xlsx`, cột 10 / J)
  - `TARGET_INVENTORY_WORKBOOK` (`taikhoan_run_safe.xlsx`, cột 2 / B)
- Quy tắc bất biến: Mỗi Machine ID chỉ được phép liên kết với đúng 1 Device Serial duy nhất. Nếu trong danh sách các dòng của cùng một máy có dòng chứa serial khác (ví dụ máy 30 gồm 8 dòng từ 234 đến 241, các dòng 234-240 mang serial `ce0217126cd4bc640c` nhưng dòng 241 lại mang serial khác như `ce061606900f682502`), hệ thống sẽ kích hoạt conflict gate và block toàn bộ quá trình detect.

## Quy trình khắc phục chuẩn
1. **Kiểm tra thông tin xung đột:**
   Sử dụng Python + `openpyxl` với đường dẫn chuẩn từ `project_paths.py`:
   ```python
   import openpyxl
   from project_paths import TARGET_INVENTORY_WORKBOOK, TRACKING_WORKBOOK

   wb = openpyxl.load_workbook(TRACKING_WORKBOOK, data_only=True)
   ws = wb.active
   for r in range(1, ws.max_row + 1):
       if ws.cell(row=r, column=1).value == <MACHINE_ID>:
           print(f"Row {r}: col 10={ws.cell(row=r, column=10).value}")
   wb.close()
   ```

2. **Cập nhật serial chuẩn:**
   Đồng bộ serial của dòng bị lệch về serial chính xác của máy trên cả hai workbook:
   ```python
   import openpyxl
   from project_paths import TARGET_INVENTORY_WORKBOOK, TRACKING_WORKBOOK

   # Cập nhật TRACKING_WORKBOOK (cột 10)
   wb1 = openpyxl.load_workbook(TRACKING_WORKBOOK)
   wb1.active.cell(row=<ROW>, column=10).value = "<CORRECT_SERIAL>"
   wb1.save(TRACKING_WORKBOOK)
   wb1.close()

   # Cập nhật TARGET_INVENTORY_WORKBOOK (cột 2)
   wb2 = openpyxl.load_workbook(TARGET_INVENTORY_WORKBOOK)
   wb2.active.cell(row=<ROW>, column=2).value = "<CORRECT_SERIAL>"
   wb2.save(TARGET_INVENTORY_WORKBOOK)
   wb2.close()
   ```

3. **Verify:**
   Chạy lại `python _detect_clean.py` để đảm bảo lỗi conflict đã được giải phóng và targets được detect bình thường.
