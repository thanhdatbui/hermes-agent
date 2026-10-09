# HƯỚNG DẪN TÍCH HỢP & VẬN HÀNH PREFLIGHT VALIDATOR TRONG CRON SYNC

## 1. Bối cảnh & Mục tiêu
- `hermes_taikhoan_sync_cron.py` chạy mỗi 5 phút để đồng bộ dữ liệu giữa `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx` và `hermes_cron_source_config.json`.
- Trước đây, nếu ai đó gõ nhầm dữ liệu, lệch dòng hoặc trùng nick trong Excel thì script sync vẫn vô tư đồng bộ dữ liệu rác sang runtime, khiến bot chạy ca nuôi lướt feed và upload bị văng lỗi hàng loạt.
- Nhằm thực thi thỏa thuận **Architecture Consensus (Sol Planner & Claude CLI, 17/09/2026)**, script `excel_preflight_validator.py` đã được tích hợp làm lớp bảo vệ Preflight Gate chặn đứng ở Bước 3.

## 2. Vị trí chốt chặn trong luồng chạy của `hermes_taikhoan_sync_cron.py`
1. Bước 1: Đồng bộ 1-chiều từ Master DAT sang Tik1..Tik6 (`sync-tik-workbooks.py`).
2. Bước 1b: Đồng bộ Keyword/Hashtag từ state.db sang Tik1..Tik8 (`sync-all-tik-keywords.py`).
3. Bước 2: Build lại `taikhoan_run_safe.xlsx` (`sync-safe-workbook.py`).
4. **BƯỚC 2.5 — PREFLIGHT VALIDATOR GATE**:
   - Gọi trực tiếp: `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir "D:/OneDrive/TaadaaData/kibe"`
   - Quét 5 nhóm Invariant Rules:
     - `Rule 1`: Số slot $\le 8$ trên mỗi máy.
     - `Rule 2`: Không có nick nào trùng lặp trên 2 slot khác nhau.
     - `Rule 3`: `Folder Video` khớp công thức $(m-1) \times 8 + \text{slot}$ và độc bản.
     - `Rule 4`: `Video Gốc` khớp công thức $(\text{slot}-1) \times 80 + m$ và độc bản trên cùng 1 file Tik.
     - `Rule 5`: Tính toàn vẹn của `taikhoan_run_safe.xlsx` (đủ serial, không trùng lặp).
   - **Xử lý vi phạm (Fail-Closed)**:
     - Nếu validator trả về `rc != 0` (FAILED):
       + In cảnh báo: `[PREFLIGHT_VALIDATOR_FAIL] Phát hiện vi phạm Invariant Rules trong Excel! Hủy đồng bộ sang runtime để bảo vệ Farm!`
       + Đánh dấu `failed = True` và log chi tiết các dòng vi phạm.
       + **NGĂNG CHẶN HOÀN TOÀN** việc gọi `generate_config_from_safe_workbook()` sang `hermes_cron_source_config.json`.
5. Bước 3: Chỉ khi Validator trả về `PASS 100%`, runtime config mới được phép cập nhật để bot bốc chạy.

## 3. Lệnh kiểm tra thủ công & gỡ lỗi
- Chạy kiểm tra nhanh toàn bộ kho Excel:
  ```bash
  python "D:/Taadaa/tools/excel_preflight_validator.py" --excel-dir "D:/OneDrive/TaadaaData/kibe"
  ```
- Chạy bộ unit test tự động 5/5 cases:
  ```bash
  python "D:/Taadaa/tools/test_excel_preflight_validator.py"
  ```
- Xem điểm thẩm định độc lập từ Sol Auditor:
  `D:/Taadaa/reports/sol_review_validator_scorecard.json` (Điểm 91/100, APPROVED).
