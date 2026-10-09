# Chẩn đoán & Khắc phục Lỗi Sync Lock Đè Workbook & Auto-Advance Veto

## 1. Hiện tượng & Cạm bẫy chẩn đoán (Diagnostic Trap)
- **Triệu chứng 1**: Khi chạy ca upload video TikTok (nhất là các slot Tik5..Tik8 hoặc ca tối), watchdog / runner báo hàng loạt máy (15–25+ máy) đồng loạt thất bại với lỗi:
  ```text
  [READ_WORKBOOK_ERROR] Missing required fields: ID TikTok
  ```
  hoặc trong `upload_result.json`:
  ```json
  {"status": "failed", "reason": "[READ_WORKBOOK_ERROR] Missing required fields: ID TikTok"}
  ```
- **BẪY CHẨN ĐOÁN NGUY HIỂM**:
  - Vội vàng kết luận file `TikX.xlsx` bị trống nick, chưa điền ID hoặc thiếu tài khoản.
  - Vội vàng viết script sync đè lại tài khoản hoặc báo user tạo thêm nick.
- **NGUYÊN NHÂN GỐC RỄ THỰC TẾ**:
  - File `TikX.xlsx` hoàn toàn có đủ 79/80 ID.
  - Xung đột Sync Lock / Write Race Condition: Các tiến trình nền (ví dụ `sync_all_tik_keywords.py` chạy mỗi 15 phút, OneDrive sync, script đồng bộ hashtag) gọi `wb.save(path)` trực tiếp lên file Excel sống.
  - Quá trình `openpyxl.Workbook.save()` ghi đè file theo từng chunk zip. Khi 20+ upload workers cùng lúc gọi `AccountSource.read_row()`, các worker đọc trúng thời điểm file đang được ghi dở dang hoặc bị OS lock độc quyền. Kết quả là openpyxl đọc được header nhưng các dòng dữ liệu trả về `None`, kích hoạt `validate_row` ném `Missing required fields: ID TikTok`.

- **Triệu chứng 2 (Auto-Advance Veto False Negative)**:
  - Máy đăng video thành công 100% (trên TikTok video đã lên, `report.json` ghi `status: "SUCCESS"`, `post_verified: true`, `video_number: 2`).
  - Nhưng trong watchdog và `upload_result.json` lại báo:
    ```json
    {"status": "failed", "reason": "post_verification_failed"}
    ```
  - **Nguyên nhân cốt lõi**: Lệnh ban đầu truyền `--video-number 1`. Khi vào script, state machine phát hiện video 1 đã có nên auto-advance lên video 2 (`state_machine.py` log ra chuỗi: `[AUTO-ADVANCE] Skipped 1 verified video(s); new video_number=2 (was 1)` - chú ý có **khoảng trắng** `new video_number=`).
  - **Cạm bẫy Regex Parse**: Tại caller `_run_upload_hook` (`multi_machine_feed_session.py`), nếu dùng regex `new_video_number=(\d+)` (dấu gạch dưới), parser sẽ không khớp với log thật có khoảng trắng, khiến `auto_advance_matched = False`, logic kiểm tra `actual_video_num == int(next_video)` bị lệch (2 != 1) -> Hook fail-closed veto nhầm thành `post_verification_failed`.
  - **Quy tắc sửa chuẩn**: Regex bắt buộc phải dùng `r"\[AUTO-ADVANCE\]\s+Skipped\s+\d+\s+verified\s+video\(s\);\s+new[ _]?video_number=(\d+)\s+\(was\s+(\d+)\)"` để hỗ trợ cả 2 định dạng (khoảng trắng hoặc gạch dưới).
  - **Cạm bẫy khi viết Test cho Upload Hook**: `_run_upload_hook` tích hợp cơ chế kiểm tra ngày dưỡng sinh `_is_account_organic_rest_day(m, r)` theo công thức băm ngày `(hash(date:m:r) % 3) == 0`. Khi viết unit test / pytest cho upload hook, BẮT BUỘC phải gán `child_ctx.config["_is_organic_rest"] = False` trong fixture, nếu không test sẽ bị skip tự động bởi `organic-rest-day-no-upload` vào các ngày trúng chu kỳ dưỡng sinh.

---

## 2. Kỷ luật Bắt buộc khi Ghi Workbook (Write Discipline - Đã chuẩn hóa qua Sol :20129)
- **CẤM TUYỆT ĐỐI**: Dùng `wb.save(str(p))` trực tiếp lên bất kỳ file workbook sống nào (`Tik1.xlsx` .. `Tik8.xlsx`, `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2.xlsx`) trong các cron script hay background worker.
- **BẮT BUỘC**: Phải ghi qua cơ chế **Atomic Update** (`atomic_workbook_update` từ `automation_core.workbook`):
  ```python
  from pathlib import Path
  import sys

  try:
      core_path = Path("D:/Taadaa/automation-core/src")
      if core_path.exists() and str(core_path) not in sys.path:
          sys.path.insert(0, str(core_path))
      from automation_core.workbook import atomic_workbook_update
  except ImportError:
      atomic_workbook_update = None

  def _update_workbook(target_path: Path) -> int:
      wb = openpyxl.load_workbook(str(target_path))
      try:
          # Thao tác sửa dữ liệu
          ...
          if updates > 0:
              wb.save(str(target_path))
      finally:
          wb.close()
      return updates

  try:
      if atomic_workbook_update is not None:
          return atomic_workbook_update(p, _update_workbook, backup=True)
      return _update_workbook(p)
  except Exception as e:
      sys.stderr.write(f"Failed to update {filename}: {e}\n")
      return 0
  ```
- **Lợi ích**: Tạo transaction lock lease, lưu `.bak` trước khi đè, ghi vào temp file cùng volume và hoán đổi nguyên tử `os.replace`. Không bao giờ để file sống ở trạng thái ghi dở cho các reader.

---

## 3. Kỷ luật Đọc Workbook (Read Resilience trong AccountSource - Đã đạt Sol :20129 APPROVED)
1. **Nâng Lock Timeout**: Trong `AccountSource.read_row()`, tăng `_wait_for_lock(lock_file, timeout=15.0)` với `time.sleep(0.2)` (thay vì 10s).
2. **Fallback Backup .bak tự động khi đọc hỏng**:
   ```python
   bak_path = self.workbook_path.with_suffix(self.workbook_path.suffix + ".bak")
   try:
       self._wb = openpyxl.load_workbook(
           self.workbook_path,
           read_only=True,
           data_only=True,
       )
   except Exception as read_err:
       if bak_path.exists():
           logger.warning(
               f"[ACCOUNT_SOURCE_FALLBACK_BAK] Không thể đọc file chính {self.workbook_path} ({read_err}); "
               f"thử fallback đọc từ {bak_path.name}"
           )
           try:
               self._wb = openpyxl.load_workbook(
                   bak_path,
                   read_only=True,
                   data_only=True,
               )
           except Exception as bak_err:
               raise AccountSourceError(
                   f"Không thể đọc cả file chính ({read_err}) và file backup {bak_path} ({bak_err})"
               ) from read_err
       else:
           raise read_err
   ```

---

## 4. Quy trình Xác minh O(1) của Coordinator (Evidence First)
Trước khi kết luận bất kỳ ca mass-fail "thiếu ID" nào:
1. **Kiểm tra nhanh số lượng ID trong file thật**:
   ```bash
   python -c "
   import openpyxl, io
   with open(r'D:\OneDrive\TaadaaData\kibe\Tik5.xlsx', 'rb') as f:
       wb = openpyxl.load_workbook(io.BytesIO(f.read()), data_only=True)
       has_id = sum(1 for r in wb['TaiKhoan'].iter_rows(min_row=2, values_only=True) if r[2])
       print('Has ID count:', has_id)
   "
   ```
2. **Chạy Single Preflight**:
   ```bash
   python -m scripts.tiktok_workflow --config D:/Taadaa/Tiktok-video/config.example.yaml --workflow-workbook "D:/OneDrive/TaadaaData/kibe/Tik5.xlsx" --single-device <serial_may_bao_loi> --preflight
   ```
3. Nếu preflight báo `PREFLIGHT PASSED` và `Has ID count >= 70` -> **Khẳng định ngay là lỗi Sync Lock Race Condition**, không được kết luận file thiếu ID.
4. **Kiểm tra ca báo `post_verification_failed`**: Đọc `report.json` trong runs folder; nếu `status == "SUCCESS"` và `post_verified == true` -> Khẳng định video đã đăng thành công, lỗi do cơ chế so khớp auto-advance ở hook ngoài.
