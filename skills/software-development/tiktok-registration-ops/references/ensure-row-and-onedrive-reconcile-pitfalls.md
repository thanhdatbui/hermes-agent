# Pitfalls & Workflow: On-Demand Account Provisioning & OneDrive Reconciliation

## 1. Cú pháp gọi canonical `ensure_row_accounts.py`
- Đối số `row` (1..8) là **positional argument**, không phải flag `--row`:
  ```bash
  # ĐÚNG:
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3 --dry-run
  python D:/Taadaa/tools/ensure_row_accounts.py 8 --machines 3 --apply-only

  # SAI (gây argparse crash exit code 2):
  python D:/Taadaa/tools/ensure_row_accounts.py --row 8 --machines 3
  ```
- Cờ `--apply-only` dùng khi đợt batch reg đã ra `tracking_result_*.json` thành công nhưng bị lỗi ở tầng merge workbook; cờ này áp dụng lại merge mà không chạy lại ADB/UI.

---

## 2. Quy tắc xóa slot nick DIE để trigger Reg bù
- `_detect_clean.py` và `ensure_row_accounts.py` kiểm tra slot trống theo điều kiện:
  `if not val or not str(val).strip() or str(val).strip().lower() == "none":`
- **PITFALL:** Nếu gắn hậu tố `_DIE` (ví dụ `annhubvqttr_DIE`) vào cột TikTok ID, detector vẫn coi ô đó là có tài khoản và báo `Toan bo may da day du tai khoan! Khong can reg`.
- **BẮT BUỘC:** Khi huỷ nick DIE:
  1. Ghi vết tài khoản và lý do DIE vào `gmail_die_tong.txt`.
  2. Xóa triệt để dòng mail khỏi `gmail_clean_v2.xlsx`.
  3. Xóa trắng hoàn toàn (`""`) cột TikTok ID trong **CẢ HAI** file:
     - `taikhoan_run_safe.xlsx` (để script nhận diện slot trống).
     - `taikhoan_dat_v2_updated .xlsx` (để cron `taikhoan-run-safe-sync` không sync đè ngược lại giá trị cũ).

---

## 3. Khắc phục PermissionError [WinError 5] khi Atomic Save trên OneDrive
- Thư mục OneDrive sync (`D:\OneDrive\TaadaaData\...`) thường xuyên giữ file lock trên file Excel đích, khiến thao tác `Path.replace()` hoặc `os.replace()` ném:
  `PermissionError: [WinError 5] Access is denied: '...tmp.xlsx' -> '...xlsx'`
- **Mẫu xử lý fallback chuẩn:**
  ```python
  import shutil

  tmp_path = target_workbook.with_suffix(".tmp.xlsx")
  wb.save(tmp_path)
  try:
      tmp_path.replace(target_workbook)
  except PermissionError as exc:
      try:
          shutil.copy2(tmp_path, target_workbook)
          tmp_path.unlink(missing_ok=True)
      except OSError as fallback_exc:
          raise PermissionError(f"Workbook replace/copy failed: {exc}; fallback: {fallback_exc}") from fallback_exc
  ```

---

## 4. Kỷ luật điều phối: Không tạo Watchdog thụ động khi User yêu cầu xử lý ngay
- Khi máy bị lock bởi phiên nuôi feed (`machine_<stt>.lock.json`), nếu user yêu cầu làm ngay / không chấp nhận trì hoãn:
  - **CẤM** tạo cronjob / watchdog thụ động dạng cron nhiều phút nếu chưa được user đồng ý.
  - Canh trực tiếp trạng thái file lock hoặc phiên feed. Ngay khi lock biến mất, kích hoạt trực tiếp lệnh reg chính thức qua background runner có `notify_on_complete=True`.
