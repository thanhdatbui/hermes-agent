# Night 2FA SQLite SSOT Verification & Cluster Isolation (2026-11-03)

## 1. Căn Nguyên 2 Lỗi Khiến Toàn Farm Thất Bại 2FA (126 Máy)

### Lỗi 1: `POST_SUCCESS_VERIFICATION_FAILED` (69 máy trên cụm Admin)
- **Triệu chứng:** Runner báo hoàn tất nhưng 69 máy fail tại khâu hậu kiểm `_verification()`.
- **Bản chất code:**
  - Các tài khoản đã có 2FA trong sheet nhưng chưa có mật khẩu (`blank_pass=True`, `has_2fa=True`).
  - Runner dispatch cờ `--password-only` tới worker `run_capture_phase_b.py`.
  - Worker không mở profile/settings nhưng in giả `status: success`.
  - Parent runner `run_batch_live_2fa.py` hậu kiểm bằng lệnh:
    `verified = has_2fa and password_saved and journal_purged and released`
  - Vì mật khẩu trên workbook vẫn rỗng (`password_saved = False`), runner chuyển thành `status="failed", reason="POST_SUCCESS_VERIFICATION_FAILED"`.
- **Khắc phục:** Hậu kiểm trên SQLite SSOT `farm_master.db`, đồng thời công nhận `password_ok = password_saved or target.blank_pass` khi tài khoản chỉ yêu cầu thêm 2FA hoặc mật khẩu đang để trống hợp lệ.

### Lỗi 2: `WorkbookError` (43 máy trên cụm Kibe)
- **Triệu chứng:** Kibe văng `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH_USERNAME")`.
- **Bản chất code:**
  - `freeze_targets_from_sqlite()` dùng `a.rowid AS source_row`.
  - `rowid` trong SQLite là số tự tăng nội bộ (1, 2, 3...), không trùng khớp với số dòng thực tế trong file Excel (dòng 1 là Header, các dòng sau map theo slot `video_slot + 1`).
  - Không lọc dải máy theo cluster: Runner Kibe (máy 1-80) lại nạp cả mục tiêu của Admin (máy >200 rowid 888, 910...). File Excel của Kibe chỉ có ~640 dòng nên khi trỏ tới dòng 888 lập tức văng ngoại lệ.
- **Khắc phục:** Thêm cờ lọc cluster `is_admin = "admin" in str(cfg.workbook_path).casefold()` để cô lập máy Kibe (`<= 80`) và máy Admin (`>= 201`).

---

## 2. Kiến Trúc Lưu Trữ SQLite Master Giữa Kibe & Admin
- **Hiện tượng:** `farm_master.db` hiện lưu cục bộ tại `D:/Taadaa/data/farm_master.db` trên Kibe. Trên máy Admin chưa có file này, khiến runner trên Admin phải fallback về Excel cũ.
- **Rủi ro OneDrive:** Không đưa `farm_master.db` vào thư mục sync của OneDrive vì cơ chế WAL/journal (`.db-wal`, `.db-shm`) sẽ bị OneDrive lock handle ngầm gây `database is locked` hoặc hỏng index.
- **Quy chuẩn kiến trúc Hội đồng Cố vấn (Advisor Council):**
  - **Tức thì (Chuyển tiếp):** Đồng bộ 1 chiều file `farm_master.db` sang `admin-farm:D:\Taadaa\data\` qua mạng LAN.
  - **Dài hạn (Chuẩn hóa):** Dựng API endpoint trên Dashboard Kibe `:1905` (Single-Writer) để máy Admin query và push cập nhật 2FA/Password tập trung về Kibe, triệt tiêu nguy cơ Split-Brain.
