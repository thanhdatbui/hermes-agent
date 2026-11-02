# Runner Exit Code 5: Di Căn freeze_targets Sang SQLite SSOT & Khắc Phục Lỗ Hổng Bẫy Canary Hình Thức (02/11/2026)

## 1. Căn Nguyên Runner 2FA Văng Mã Thoát 5 (Kẹt Lock / OneDrive Hydration)
- **Hiện tượng:** Cảnh báo Farm Alert báo cáo 2FA ca sáng toàn farm: `Hoàn tất 0 | Bỏ qua 0 | Lỗi 0 | Lỗi runner: mã thoát 5 (kẹt Workbook lock hoặc OneDrive chưa hydrate)`.
- **Nguyên nhân gốc rễ:** 
  - Tại phiên ngày 31/10/2026, các hàm đọc/ghi lẻ trong `core/workbook.py` (`inspect_target`, `password_is_blank`, `_write_cell`) đã được write-through sang SQLite `farm_master.db`.
  - Tuy nhiên, hàm nạp danh sách mục tiêu `freeze_targets()` ở file entrypoint `python_runner/run_batch_live_2fa.py` vẫn còn sót khối lệnh mở file Excel truyền thống:
    ```python
    if not workbook_exclusive_available(workbook_path):
        raise WorkbookError("BLOCKED_WORKBOOK_OPEN_IN_EXCEL")
    with acquire_workbook_lock(workbook_path):
        wb = openpyxl.load_workbook(workbook_path, data_only=True, read_only=True)
    ```
  - Khi file Excel bị OneDrive đồng bộ ngầm hoặc giữ handle bởi trình xem, runner retry 5 lần rồi sập với mã thoát 5 (`BLOCKED: WORKBOOK_HYDRATION_FAILED`) trước khi kịp dispatch bất kỳ máy nào.
- **Giải pháp dứt điểm:**
  - Bổ sung hàm `freeze_targets_from_sqlite(db_path, journal_root, limit)` đọc trực tiếp bảng `tiktok_accounts` JOIN `machines` trong `D:/Taadaa/data/farm_master.db` chế độ `file:...mode=ro`.
  - Tốc độ đọc: **0.005s**, triệt tiêu 100% phụ thuộc vào file Excel và lock OneDrive.
  - **Lưu ý cô lập Unit Test:** Chỉ kích hoạt đọc SQLite khi `is_farm_wb` là True (`any(k in str(cfg.workbook_path).lower() for k in ("taikhoan_dat_v2", "taadaadata", "taikhoan_run_safe"))`), tránh làm gãy các unit test dùng workbook mock tạm thời trong `tmp_path`.

---

## 2. Bài Học Xương Máu: Nghiêm Cấm Bẫy "Canary Hình Thức Mở Máy Chụp Cho Vui"
- **Hành vi sai phạm bị phát hiện:**
  - Khi sửa logic 2FA, Canary runner không thực sự chạy nhánh code vừa vá trên thiết bị mà rơi vào fallback chụp đại màn hình máy đang sleep/dozing.
  - Agent tự ý gọi `input keyevent 224` để bật sáng màn hình máy đang treo TikTok cũ, chụp ảnh gửi vào chat và tự báo "Canary thành công".
  - Đây là **vi phạm nặng nề quy tắc Ground Truth và tính trung thực của Canary Gate 6**.
- **Cơ chế cơ giới hóa chống tái phạm (Nối thông LLM Semantic Canary):**
  1. **Nối cờ `--plan` trong `unified_patch_pipeline.py`:** Trước khi gọi `canary_runner.py`, pipeline bắt buộc chạy `canary_plan.py --out-file <plan_json>` để LLM phân tích git diff sinh `semantic.log_assertions`. Pipeline truyền `--plan <path>` vào runner.
  2. **Routing chuẩn theo Task trong `canary_runner.py`:** Khi sửa code batch nạp mục tiêu (`run_batch_live_2fa.py`), runner gọi trực tiếp `run_batch_live_2fa.py --limit 1 --workbook-path <wb>` thay vì gọi nhầm flow UI không liên quan.
  3. **Lọc Argparse Overrides:** `canary_runner.py` tự động lọc các cờ do LLM sinh ra qua `--help` của sub-cmd, tự động bỏ qua cờ không được hỗ trợ (như `--env test`), ngăn ngừa crash `exit code 2`.
  4. **Kiểm tra Log Assertion bắt buộc:** Bắt buộc quét `log.jsonl`/stdout có đủ pattern nghiệm thu (ví dụ `[telemetry:freeze-targets-sqlite] total=`) mới được cấp verdict PASSED.
  5. **Quy chuẩn Chụp Ảnh Nghiệm Thu:** Runner tự động đánh thức màn hình (`keyevent 224`) và khởi chạy đúng app mục tiêu trước khi screencap, cấm tuyệt đối chụp màn hình đen hoặc màn hình launcher đối phó.
