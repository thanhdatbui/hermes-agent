# Chuyên Đề: Khử Hoàn Toàn Excel Khi Chuyển Sang SQLite SSOT (2FA TikTok & Mailboxes)

## Bối cảnh & Hiện tượng (2026-11-03)
Khi toàn farm chuyển đổi sang lưu trữ dữ liệu tập trung tại SQLite SSOT (`D:/Taadaa/data/farm_master.db`), một số script runner (`tiktok-add-bao-mat-f2a`, `GPM auto`) rơi vào tình trạng "nửa nạc nửa mỡ":
1. Tầng ngoài nạp danh sách mục tiêu từ SQLite (`freeze_targets_from_sqlite`).
2. Tầng trong hoặc hàm xác thực (`_verification`, `_write_cell`) vẫn cố tình mở file Excel bằng openpyxl.
3. Khi file Excel cũ không tồn tại hoặc sai lệch chỉ số dòng giữa SQLite `rowid` và Excel row, toàn bộ mẻ chạy bị văng lỗi hàng loạt (`WorkbookError`, `BadZipFile`, `POST_SUCCESS_VERIFICATION_FAILED`).

## Các bẫy cốt tử & Giải pháp cơ giới hóa

### 1. Bẫy lệch chỉ số dòng (`rowid` vs Excel `source_row`)
- **Triệu chứng**: Cụm Kibe chết 43 máy với lỗi `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH")`.
- **Nguyên nhân**: Code lấy `a.rowid AS source_row` từ SQLite gán vào `target.source_row`. Nhưng `rowid` trong SQLite bắt đầu từ 1 và không trùng với dòng Excel `taikhoan_dat_v2_updated .xlsx` (có header, các dòng bị xóa/bỏ qua). Khi worker đối chiếu `source_row` trên Excel thì sai lệch định danh.
- **Giải pháp**:
  - Không truyền `source_row` của SQLite để ép kiểm tra dòng Excel.
  - Hàm `_verification()` phải đọc và đối soát trực tiếp từ `farm_master.db` theo cặp `(username, machine_id)`.

### 2. Bẫy ép kiểm tra mật khẩu trên tài khoản mới (`blank_pass=True`)
- **Triệu chứng**: 69 máy cụm Admin bật 2FA thành công nhưng toàn bộ bị đánh trượt thành `POST_SUCCESS_VERIFICATION_FAILED`.
- **Nguyên nhân**: Dữ liệu lịch sử cụm Admin có hơn 200 nick tạo bằng Hotmail/SSO chưa từng đặt mật khẩu tĩnh (`password = NULL`). Khi bật 2FA TOTP thành công, hàm `_verification` lại ép `password_saved = not password_is_blank(...)` bắt buộc phải có password thì mới tính là verified.
- **Giải pháp**:
  ```python
  password_ok = password_saved or target.blank_pass
  verified = has_2fa and password_ok and journal_purged and released
  ```

### 3. Bẫy ghi đè Excel bắt buộc (`_write_cell` BadZipFile/FileNotFoundError)
- **Triệu chứng**: Worker con ném lỗi khi cố ghi 2FA Secret vào file Excel đã bị xóa/di dời.
- **Nguyên nhân**: `_write_cell` ép chạy `single_writer_workbook_update` mở file Excel trước rồi mới cập nhật SQLite sau.
- **Giải pháp**:
  - Đảo ngược thứ tự: SQLite `farm_master.db` là Single Source of Truth (SSOT), bắt buộc cập nhật vào database trước qua `update_tiktok_credentials` hoặc `update_mailbox_credentials`.
  - Kiểm tra `if not path.exists(): return backup` để nếu không có file Excel hoặc mở file lỗi thì vẫn hoàn tất thành công 100% dựa trên SQLite.

### 4. Bẫy lọc cụm máy (Kibe vs Admin) khi freeze targets từ SQLite
- **Triệu chứng**: Lệnh chạy cho Kibe (Máy 1-80) lại freeze nhầm danh sách máy của Admin (Máy 201-280) và ngược lại.
- **Nguyên nhân**: `freeze_targets_from_sqlite` chỉ kiểm tra chung `machine <= 80 or machine >= 200` mà không nhận diện cờ cluster đang chạy.
- **Giải pháp**:
  - Nhận diện `is_admin = 'admin' in str(cfg.workbook_path).casefold()`.
  - Phân luồng dứt điểm: nếu `is_admin` thì chỉ lấy `machine >= 200`; nếu không thì chỉ lấy `machine <= 80`.
