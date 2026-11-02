# Freeze Targets SQLite SSOT Migration & Exit Code 5 Elimination (2026-11-02)

## 1. Căn Nguyên Runner 2FA Văng Mã Thoát 5
- **Hiện tượng:** Báo cáo 2FA TikTok toàn farm trả về `Hoàn tất 0 | Bỏ qua 0 | Lỗi 0` kèm thông báo: `mã thoát 5 (kẹt Workbook lock hoặc OneDrive chưa hydrate)`.
- **Root cause kỹ thuật:** 
  - Tại tầng adapter/workbook (`core/workbook.py`), việc đọc/ghi tài khoản đã được cơ giới hóa qua `farm_db` SQLite (`farm_master.db`).
  - Tuy nhiên, tại file entrypoint batch `run_batch_live_2fa.py`, hàm `freeze_targets()` vẫn giữ logic legacy kiểm tra file lock `~$...xlsx` và gọi `openpyxl.load_workbook(workbook_path)`.
  - Khi file Excel bị đồng bộ ngầm bởi OneDrive hoặc bị process khác lock quá 5 lần retry:
    $\rightarrow$ `targets is None` $\rightarrow$ Runner ném `BLOCKED: WORKBOOK_HYDRATION_FAILED` và exit với mã 5 trước khi kịp dispatch bất kỳ máy nào.

## 2. Giải Pháp Chuẩn Hóa SSOT SQLite (`freeze_targets_from_sqlite`)
- **Nguyên tắc:** Toàn bộ việc nạp danh sách mục tiêu chạy 2FA (`BatchTarget`) chuyển hẳn sang query trực tiếp SQLite SSOT `D:/Taadaa/data/farm_master.db`:
  ```python
  def freeze_targets_from_sqlite(db_path: Path, journal_root: Path, limit: int) -> list[BatchTarget]:
      # SELECT a.rowid, a.machine_id, m.device_serial, a.username, a.twofa_secret, a.password
      # FROM tiktok_accounts a JOIN machines m ON ...
  ```
- **Ưu tiên mục tiêu (Sorting Hierarchy):**
  1. `blank_pass = True`: Tài khoản chưa có mật khẩu ưu tiên chạy trước.
  2. `password_only = False`: Tài khoản chưa có 2FA ưu tiên trước tài khoản chỉ cần đổi pass.
  3. `has_journal = True`: Ưu tiên resume các journal DPAPI đang dở dang.
  4. `source_row`: Giữ thứ tự ổn định.
- **Tốc độ:** Truy vấn SQLite hoàn tất trong $\approx 0.005s$, loại bỏ hoàn toàn rủi ro nghẽn I/O và lock contention trên Excel.

## 3. Phân Định Giữa "Dọn Dữ Liệu" vs "Sửa Code Farm"
- **Dọn dữ liệu server/DB thuần túy:** (dọn lock mồ côi `.codex/device-locks`, dọn `.dpapi` journal mồ côi, dọn log cũ trong `reports/`, optimize SQLite):
  - **TUYỆT ĐỐI KHÔNG CẦN CANARY MÁY THẬT.**
  - Không cần chờ ca nuôi feed kết thúc; nghiệm thu bằng read-back đối soát số liệu (`COUNT(*)`, bytes giải phóng).
- **Sửa code runner/automation farm:** (bất kỳ file `.py` nào trong các repo farm điều khiển Android):
  - Bắt buộc đi qua `unified_patch_pipeline.py`.
  - Bắt buộc kiểm chứng Canary máy thật (Gate 6) có screencap/OCR hợp lệ để chứng minh không làm văng app hay hỏng UI thiết bị.
  - Cần đảm bảo thiết bị canary đã nhả device-lock trước khi chạy kiểm chứng.
