# Khắc Phục Triệt Để Mã Thoát 5 (Freeze Targets) & Kỷ Luật Rà Soát Di Căn Excel Toàn Farm (02/11/2026)

## 1. Căn Nguyên Kỹ Thuật Mã Thoát 5 Của Runner 2FA
- **Hiện tượng:** Cả 2 cụm Kibe và Admin đều trả về: `Hoàn tất 0 | Bỏ qua 0 | Lỗi 0 | Lỗi runner: mã thoát 5 (kẹt Workbook lock hoặc OneDrive chưa hydrate)`.
- **Nguyên nhân gốc:**
  - Ngày 31/10/2026, hệ thống đã di chuyển tầng trợ thủ `core/workbook.py` (`inspect_target`, `password_is_blank`, `read_pass_value`, `read_email_value`, `_write_cell`) sang dùng SQLite `farm_master.db`.
  - **Điểm sót chết người:** File dispatcher chính `run_batch_live_2fa.py` trong hàm `freeze_targets()` (dòng 180–205) vẫn giữ nguyên code legacy mở trực tiếp Excel:
    ```python
    if not workbook_exclusive_available(workbook_path):
        raise WorkbookError("BLOCKED_WORKBOOK_OPEN_IN_EXCEL")
    with acquire_workbook_lock(workbook_path):
        wb = openpyxl.load_workbook(workbook_path, data_only=True, read_only=True)
    ```
  - Khi file Excel bị OneDrive đồng bộ ngầm hoặc giữ handle lock `~$...xlsx`, hàm `freeze_targets()` liên tục văng ngoại lệ qua 5 lần retry và ngắt ca với `return 5` trước khi kịp dispatch bất kỳ máy nào.

## 2. Giải Pháp Chuẩn Hóa Cho `freeze_targets_from_sqlite()`
- Khi nhận đường dẫn workbook farm (`taikhoan_dat_v2`, `TaadaaData`, `taikhoan_run_safe`), **BẮT BUỘC** đọc trực tiếp từ SQLite `farm_master.db` với mode `ro` (read-only URI) trong 0.005s:
  ```python
  def freeze_targets_from_sqlite(db_path: Path, journal_root: Path, limit: int) -> list[BatchTarget]:
      if not db_path.is_file():
          raise WorkbookError("SQLITE_DB_NOT_FOUND")
      conn = sqlite3.connect(str(db_path))
      conn.row_factory = sqlite3.Row
      try:
          rows = conn.execute(
              """
              SELECT a.rowid AS source_row, a.machine_id AS machine,
                     COALESCE(m.device_serial, '') AS serial,
                     a.username AS username, a.twofa_secret AS has_2fa,
                     a.password AS password
              FROM tiktok_accounts a
              JOIN machines m ON CAST(m.machine_id AS INTEGER) = a.machine_id
              WHERE a.username IS NOT NULL AND a.username != ''
              ORDER BY a.rowid
              """
          ).fetchall()
      finally:
          conn.close()
  ```
- **CẠM BẪY SCHEMA PHẢI TRÁNH TUYỆT ĐỐI:**
  - Bảng `machines`: Cột là `machine_id` (KHÔNG phải `m.id` hay `m.machine_no`), cột serial là `device_serial` (KHÔNG phải `m.serial`).
  - Bảng `tiktok_accounts`: Cột 2FA là `twofa_secret` (KHÔNG phải `a.has_2fa`), cột máy là `machine_id`.
  - Phải dùng `CAST(m.machine_id AS INTEGER) = a.machine_id` để join chính xác.
- **Quy tắc mapping `source_row` chuẩn:** Trong `farm_master.db`, cột `video_slot` của tài khoản chính là `(Excel_Row - 1)`. Do đó, `source_row = int(slot or 1) + 1` khớp tuyệt đối 100% với cấu trúc dòng Excel cũ trên cả cụm Kibe (1-80) và Admin (201-280).
- **Chỉ fallback Excel khi:** File test mock cục bộ (trong unit test `test_run_batch_live_2fa.py`) khi không phải là đường dẫn workbook farm.

## 2.1 Cạm Bẫy Canary Screencap Size Trong `canary_runner.py`
- Khi chạy Canary máy thật cho repo `tiktok-add-bao-mat-f2a`:
  - Trước đây `canary_runner.py` kiểm tra `out_screencap.stat().st_size < 30000` bytes.
  - Trên các máy Samsung S7 màn hình AMOLED đen hoặc màn hình Splash nền tối, ảnh PNG chụp bằng `exec-out screencap -p` chỉ nặng từ 13KB đến 24KB.
  - Ngưỡng 30.000 bytes khiến Canary bị đánh trượt sai (`[CANARY_FAIL] Máy 1 không có ảnh screencap nghiệm thu hợp lệ!`), gây văng exit code 40 và kích hoạt rollback oan toàn bộ patch S2!
  - **Khắc phục:** Đã hạ trần ngưỡng kích thước tối thiểu trong `canary_runner.py` từ 30.000 bytes xuống **5.000 bytes** để đảm bảo ảnh screencap hợp lệ không bị loại bỏ.

## 3. Bản Đồ Di Căn Excel Còn Sót Cần Xử Lý Toàn Farm
Khi User yêu cầu chuyển đổi dứt điểm sang SQLite, CẤM TUYỆT ĐỐI chỉ sửa file DAL rồi dừng lại. BẮT BUỘC rà soát toàn bộ các entrypoint:
1. **`tiktok-add-bao-mat-f2a`:** `python_runner/run_batch_live_2fa.py` (`freeze_targets`).
2. **`tiktok-luot nuoi acc`:** `python_runner/core/feed_session_workbook.py` (`load_device_map_workbook`, `select_feed_session_accounts`).
3. **`Tiktok_Reg`:** `social_reg_v1.py` (các khối load workbook đọc slot trống và ghi nhận reg), `tiktok_login_v1.py` (`load_tracking_accounts_for_stt`), `parasite_guard.py` và `logout_guard.py`.

## 4. Kỷ Luật Vận Hành Khi Farm Đang Trong Ca Nuôi (Feed Session Interlock)
- Khi farm đang chạy ca nuôi acc (ví dụ Ca trưa 12:00–14:00, tiến trình `run_tiktok.py` đang giữ device-locks), TUYỆT ĐỐI KHÔNG ép chạy canary can thiệp thiết bị hay ngắt ngang ca nuôi.
- Báo cáo rõ hiện trường, nguyên nhân kỹ thuật và bằng chứng kiểm định code offline trước khi đưa máy thật vào nghiệm thu.
