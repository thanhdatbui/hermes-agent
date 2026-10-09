# Chẩn Đoán Lỗi Upload Báo Missing ID / Read Workbook Error

## Bối cảnh & Hiện tượng (2026-09-17)
Khi bot báo cáo Phiên/Ca nuôi acc gửi về Farm Alert có danh sách dài các máy báo:
- `Lỗi script/xác minh (N): [READ_WORKBOOK_ERROR] Missing required fields: ID TikTok`
- hoặc `Bỏ qua: Khác (missing_account_id)`

Coordinator rất dễ mắc bẫy nhìn vào text summary rồi kết luận vội vàng rằng file `TikN.xlsx` bị trống nick/mất dữ liệu.

## Nguyên nhân gốc rễ
1. **Race Condition / Concurrent File Lock**:
   - Lúc feed session kết thúc và kích hoạt đồng loạt các subprocess upload hook, file `TikN.xlsx` có thể đang bị tiến trình sync/lock đè (đồng bộ OneDrive, script `sync_all_tik_keywords`, hoặc nhiều runner cùng truy cập).
   - Khi hàm `_read_row_from_xlsx()` hoặc `validate_row()` gặp exception sau 5 lần retry, code `account_source.py` sẽ ném: `[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok`.
2. **Merge kết quả giữa các đợt chạy trong cùng một Ca**:
   - Trong 1 ca (ví dụ Ca tối có thể có đợt chạy 1 lúc 18:00 và đợt chạy 2 lúc 20:00), máy đã upload thành công ở đợt 1 thì sang đợt 2 sẽ trả về `already_uploaded_in_shift`.
   - Nếu watchdog chỉ đọc run mới nhất hoặc merge đè trạng thái, các máy đã thành công ở đợt 1 có thể bị báo nhầm thành `Success (0)`.

## Checklist Đối Soát O(1) Bắt Buộc
1. **Kiểm tra trực tiếp file `TikN.xlsx` (không suy đoán)**:
   ```python
   import openpyxl
   wb = openpyxl.load_workbook(r"D:\OneDrive\TaadaaData\kibe\Tik5.xlsx", read_only=True, data_only=True)
   rows = list(wb.active.iter_rows(values_only=True))
   has_id = sum(1 for r in rows[1:] if r[2] and str(r[2]).strip())
   print(f"Total rows: {len(rows)-1}, has ID: {has_id}")
   ```
2. **Tra cứu ledger chính thức của đợt upload**:
   File ledger lưu tại: `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`.
   Lọc theo `logical_day` và `row` để kiểm tra máy nào đã có `status: success`.
3. **Chạy test preflight độc lập cho máy nghi vấn**:
   ```bash
   /d/Taadaa/python-envs/automation/Scripts/python.exe -m scripts.tiktok_workflow \
     --config D:/Taadaa/Tiktok-video/config.example.yaml \
     --workflow-workbook "D:/OneDrive/TaadaaData/kibe/Tik5.xlsx" \
     --single-device <SERIAL> \
     --preflight
   ```
   Nếu preflight trả về `OK workbook row` và `PREFLIGHT PASSED`, chứng tỏ mapping và dữ liệu ID trong workbook hoàn toàn hợp lệ.
