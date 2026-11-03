# SQLite SSOT Migration & Elimination of Excel Workbooks in 2FA Batch Ops (2026-11-03)

## 1. Bối Cảnh Lỗi Báo Cáo 2FA Ban Đêm (03/11/2026)
- **Triệu chứng:** Toàn farm báo cáo `Hoàn tất 0 | Bỏ qua 68 | Lỗi 126`.
- **Phân loại 2 nguyên nhân cốt lõi do phụ thuộc Excel:**
  1. **Lỗi `POST_SUCCESS_VERIFICATION_FAILED` (69 máy cụm Admin):**
     - Các tài khoản đã bật 2FA trên Admin sheet có `blank_pass = True`.
     - Parent runner gán `--password-only`. Khi worker hoàn thành, parent chạy `_verification()`.
     - `_verification()` kiểm tra `password_saved = not password_is_blank()`. Khi kiểm tra workbook Excel thấy ô PASS rỗng $\rightarrow$ đánh rớt toàn bộ máy thành công với lý do `POST_SUCCESS_VERIFICATION_FAILED`.
  2. **Lỗi `WorkbookError` (43 máy cụm Kibe):**
     - `freeze_targets_from_sqlite()` query `SELECT a.rowid AS source_row` mà không filter theo machine range của cluster.
     - Dẫn tới máy cụm Admin (rowid > 800) bị nạp vào Kibe runner.
     - File Excel Kibe chỉ có ~640 dòng $\rightarrow$ `_validate_identity()` kiểm tra lệch dòng và ném `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH")`.

---

## 2. Chuẩn Hóa Kiến Trúc Chuyển Đổi Sang SQLite SSOT (`farm_master.db`)

### A. Nguyên tắc phân định dải máy Cluster
Khi nạp mục tiêu chạy batch từ SQLite SSOT `farm_master.db`:
- Bắt buộc kiểm tra dải máy tương ứng của từng cụm:
  - Cụm Kibe: `1 <= machine <= 80`
  - Cụm Admin: `201 <= machine <= 280`
- Loại trừ ngay từ vòng lọc candidate, tránh nạp chéo mục tiêu giữa 2 cụm máy.

### B. Hậu kiểm `_verification()` độc lập với file Excel
- Truy vấn trực tiếp trạng thái `twofa_secret` và `password` từ bảng `tiktok_accounts` trong `D:/Taadaa/data/farm_master.db`.
- Đối với tài khoản `blank_pass = True`, chấp thuận `password_ok = password_saved or target.blank_pass` để không chặn oan các tài khoản chỉ cần bật 2FA mà mật khẩu chưa được sinh/cập nhật.

### C. Write-through trực tiếp vào SQLite
- Tại `core/workbook.py` và `run_capture_phase_b.py`, khi lưu 2FA secret hoặc Password mới:
  - Bắt buộc ghi trực tiếp vào `farm_master.db` (bảng `tiktok_accounts`).
  - Không bắt buộc ghi đè lên file Excel vật lý khi database SQLite master đã ghi nhận thành công, loại bỏ hoàn toàn các lỗi lock contention `~$...xlsx` và lỗi đồng bộ OneDrive ngầm.
