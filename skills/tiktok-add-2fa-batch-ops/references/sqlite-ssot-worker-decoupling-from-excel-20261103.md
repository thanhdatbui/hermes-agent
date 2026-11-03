# Triage: Kiến trúc "Gốc SQLite - Ngọn Excel" gây đổ vỡ hàng loạt trong 2FA Batch Runner (03/11/2026)

## 1. Bối cảnh sự cố
Đêm 03/11/2026, báo cáo tổng hợp 2FA ban đêm trả về 126 lỗi (43 lỗi `WorkbookError`, 69 lỗi `POST_SUCCESS_VERIFICATION_FAILED`). Nguyên nhân sâu xa là sự không đồng bộ giữa chính sách chuẩn hoá dữ liệu sang SQLite SSOT (`farm_master.db`) và mã nguồn thực thi thực tế.

## 2. Nguyên nhân cốt lõi ("Gốc SQLite - Ngọn Excel")
1. **Runner mẹ (`run_batch_live_2fa.py`):**
   - Đã chuyển sang hàm `freeze_targets_from_sqlite()` đọc trực tiếp từ `farm_master.db`.
   - Tuy nhiên, khi spawn worker con `run_capture_phase_b.py`, script vẫn truyền đầy đủ các cờ kế thừa: `--workbook-path`, `--workbook-sheet`, `--source-row` (lấy từ `a.rowid` SQLite).
2. **Worker con (`run_capture_phase_b.py`):**
   - Vẫn import `openpyxl` và phụ thuộc vào `core/workbook.py`.
   - Khi preflight, worker gọi `inspect_target()`. Mặc dù có đoạn try/except gọi `farm_db.get_account()`, nhưng nếu gặp bất kỳ lỗi mismatch nào (hoặc lookup không thấy do username lệch/mask), code lập tức fallback xuống `openpyxl.load_workbook(workbook_path)`.
3. **Thực trạng tài nguyên trên đĩa:**
   - File Excel `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated .xlsx` thực tế **không còn tồn tại** trên đĩa sau các đợt dọn dẹp chuyển dịch sang SQLite.
   - Hậu quả: Khi fallback nhảy vào `openpyxl`, worker văng ngay `FileNotFoundError` hoặc `WorkbookError: SOURCE_ROW_IDENTITY_MISMATCH` do `rowid` SQLite không tương thích với cấu trúc dòng bảng tính.

## 3. Bài học & Quy tắc giải pháp triệt để
- **Cắt bỏ hoàn toàn fallback Excel:** Khi repo đã được chỉ định chạy theo SQLite SSOT, mọi I/O liên quan đến Excel (openpyxl, workbook lock, workbook backup) phải bị loại bỏ ở tầng worker hoặc vô hiệu hóa triệt để, cấm nuốt lỗi để fallback ngầm sang Excel.
- **SSOT Write-Through:** Khi 2FA secret được tạo thành công, tiến trình ghi nhận trực tiếp vào bảng `tiktok_accounts` (`twofa_secret = ? WHERE username = ?`) và bảng `tiktok_workflow_state`, không ghi ngược vào file `.xlsx`.
