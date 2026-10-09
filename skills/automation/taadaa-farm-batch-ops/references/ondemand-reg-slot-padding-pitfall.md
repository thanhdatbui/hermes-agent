# Pitfall: On-Demand Reg Bù vs Thiếu Hàng Vật Lý Trên Master Tracking Sheet

## Bối cảnh
Khi cơ chế tự động reg bù (`ensure_row_accounts.py <row>`) chạy trước ca nuôi sâu (ví dụ: Ca 4 Phiên 1 chạy **Row 7** hoặc Ca 4 Phiên 2 chạy **Row 8**):
- Hệ thống phát hiện máy thiếu account ở Row đó trong `taikhoan_run_safe.xlsx`.
- Script kích hoạt `_run_all_targets.py` reg bù TikTok thành công và lưu kết quả vào `tracking_result_stt<M>_<email>.json`.

## Triệu chứng / Pitfall
- Tiến trình reg thành công (có file tracking json, có proof screenshot profile).
- Nhưng sau khi `apply_results(row=7)` chạy, tài khoản mới **KHÔNG xuất hiện trong `taikhoan_dat_v2_updated .xlsx` lẫn `taikhoan_run_safe.xlsx`**.

## Nguyên nhân cốt lõi
1. Master workbook `taikhoan_dat_v2_updated .xlsx` có một số máy (ví dụ M76..M79) chỉ mới được khởi tạo **6 hàng vật lý (Row 1..6)** thay vì đủ 8 hàng.
2. Logic tra cứu slot `machine_slots[stt]` đọc từ master workbook:
   ```python
   if stt in machine_slots and len(machine_slots[stt]) >= row:
       target_excel_row, target_tik = machine_slots[stt][row - 1]
       data["tracking_row"] = target_excel_row
   ```
3. Khi `row = 7` hoặc `row = 8`, điều kiện `len(machine_slots[stt]) >= row` bị **FAIL** vì máy chỉ có 6 slots.
4. Do đó `data["tracking_row"]` vẫn là rỗng `""` và script apply không thể xác định dòng cần ghi đè, dẫn đến kết quả reg bị bỏ rơi trong folder run mà không merge được vào sheet nuôi.

## Cách xử lý chuẩn
- Trước khi chạy hoặc khi xử lý reg bù cho Row 7/Row 8, kiểm tra số hàng vật lý của các máy trong `taikhoan_dat_v2_updated .xlsx`.
- Nếu máy chưa đủ 8 hàng (`len(slots) < 8`), phải chèn thêm các hàng trống đủ 8 slot cho máy đó trên master tracking sheet trước khi chạy apply deferred tracking.
