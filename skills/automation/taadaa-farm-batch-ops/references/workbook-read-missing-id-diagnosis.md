# Chẩn Đoán Lỗi Upload Video & Workbook Read Tránh Kết Luận Sai

## 1. Hiện tượng
- Watchdog hoặc báo cáo farm thông báo:
  `Lỗi script/xác minh (N máy)` hoặc `[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok`.
- Dễ dẫn đến kết luận vội vàng: *"Workbook TikX đang trống nick / chưa nạp ID"*.

## 2. Nguyên nhân gốc rễ
- `AccountSource.read_row()` chạy `validate_row()` và ném lỗi `Missing required fields: ID TikTok` khi mở file trúng thời điểm workbook đang bị ghi/sync:
  1. File workbook đang bị ghi/sync bởi cron đồng bộ (`sync_all_tik_keywords.py`, OneDrive sync, sync safe workbook) trúng lúc runner đọc file.
  2. Bị lock tạm thời hoặc file byte stream chưa hoàn tất, dẫn đến cell ID đọc ra `None`.
  3. Báo cáo watchdog tổng hợp (`feed_session_watchdog.py`) gom nhiều run folder trong cùng một Ca: nếu đợt 1 đã đăng thành công (ghi vào `shift_upload_history.json`) nhưng đợt 2 chạy lại và skip, báo cáo có thể hiển thị `Success (0)` nếu không kiểm tra kỹ lịch sử ca.

## 3. Thủ tục kiểm tra O(1) bắt buộc trước khi kết luận
1. **Kiểm tra số lượng nick thực tế trong workbook:**
   ```bash
   python -c "import openpyxl; wb=openpyxl.load_workbook('D:/OneDrive/TaadaaData/kibe/Tik5.xlsx', data_only=True, read_only=True); rows=list(wb.active.iter_rows(values_only=True)); print('Total rows has ID:', sum(1 for r in rows[1:] if r[2] and str(r[2]).strip()))"
   ```
   Nếu kết quả ra 79/80 hoặc đủ nick -> Dữ liệu hoàn toàn đầy đủ, không thiếu nick.

2. **Kiểm tra lịch sử đăng thực tế trong Ca:**
   Tra cứu `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json` xem máy nào đã có `status: "success"` với row của ca đó trong ngày.

3. **Chạy test Preflight xác nhận:**
   ```bash
   python -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config.example.yaml --workflow-workbook "D:/OneDrive/TaadaaData/kibe/Tik5.xlsx" --single-device <SERIAL> --preflight
   ```
   Nếu output `OK workbook row: machine=X` và `PREFLIGHT PASSED` -> Hệ thống sẵn sàng, lỗi trước đó chỉ là transient sync lock.
