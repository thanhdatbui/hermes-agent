# Cross-Farm Watchdog & 2FA Excel Elimination and SQLite SSOT Hardening (2026-11-03)

## 1. Bối cảnh & Hiện tượng lỗi
Trong phiên đối soát toàn farm ngày 2026-11-03, sau khi cơ sở dữ liệu SQLite trung tâm (`D:/Taadaa/data/farm_master.db`) được chọn làm Single Source of Truth (SSOT), một loạt script chạy cron/watchdog ban đêm và định kỳ bị lỗi hàng loạt:
- **Batch 2FA TikTok (`night_tiktok_2fa_watchdog.py` / `run_batch_live_2fa.py`):** Báo cáo 126 lỗi (43 `WorkbookError` trên cụm Kibe và 69 `POST_SUCCESS_VERIFICATION_FAILED` trên cụm Admin).
- **Nguyên nhân kép:**
  1. `freeze_targets_from_sqlite`: Lấy `a.rowid AS source_row` của SQLite truyền vào cho worker con `run_capture_phase_b.py`. Khi worker con đối chiếu với Excel cũ (`taikhoan_dat_v2_updated .xlsx`), thứ tự dòng bị lệch hoàn toàn so với SQLite $\rightarrow$ văng `WorkbookError("SOURCE_ROW_IDENTITY_MISMATCH")`.
  2. `_verification`: Nghiệm thu hậu kiểm ép điều kiện `password_saved = not password_is_blank(...)`. Trên cụm Admin, 141 tài khoản reg đời cũ chưa có mật khẩu (`blank_pass=True`). Dù 2FA đã bật thành công, kiểm tra pass trống khiến toàn bộ 69 máy bị đánh trượt oan.
  3. `_write_cell`: Worker con vẫn cố mở file Excel bằng `openpyxl` trước rồi mới update SQLite. Khi file Excel cũ không còn tồn tại trên đĩa, worker ném `FileNotFoundError` / `BadZipFile` làm sập mẻ chạy.

## 2. Giải pháp cơ giới hóa & Kiến trúc chuẩn hóa

### A. Triệt tiêu hoàn toàn sự phụ thuộc vào file Excel ở runtime
1. **Freeze Targets:**
   - Khi có `farm_master.db`, nạp trực tiếp danh sách mục tiêu từ database.
   - Nhận diện phân cụm Kibe vs Admin dựa trên `--workbook-path`:
     - Nếu đường dẫn chứa `admin`: chỉ nạp máy `>= 200`.
     - Nếu đường dẫn chứa `kibe`: chỉ nạp máy `<= 80`.
2. **Nghiệm thu hậu kiểm (`_verification`):**
   - Đọc trực tiếp từ SQLite SSOT theo `(username, machine_id)`.
   - Bổ sung điều kiện: `password_ok = password_saved or target.blank_pass`. Tài khoản chưa có pass khi bật 2FA thành công được công nhận hợp lệ.
3. **Write-Through song song không chặn (`_write_cell`):**
   - Cập nhật trực tiếp `farm_master.db` (bảng `tiktok_accounts`, cột `twofa_secret` và `password`) **ngay bước đầu tiên**.
   - Kiểm tra `if not path.exists(): return backup`. Nếu file Excel legacy không tồn tại hoặc lỗi zip, hàm lướt qua an toàn, bảo toàn trạng thái trong SQLite.

### B. Mở rộng cho các Watchdog & Repo khác trên Farm
1. **Gmail 2FA (`GPM auto/scripts/run_add_2fa_remaining.py`):**
   - Khi hàm `sync_secret_to_excels` hoàn tất bật 2FA cho profile GPM, bổ sung write-through:
     ```python
     from farm_db import update_mailbox_credentials
     update_mailbox_credentials(email, twofa_secret=clean_secret)
     ```
     vào bảng `mailboxes` của `farm_master.db`.
2. **Farm Idle Screen Healer (`tools/farm_idle_screen_and_app_healer.py`):**
   - Hàm `load_mapping()` ưu tiên nạp `device_serial -> machine_id` trực tiếp từ bảng `machines` trong `D:/Taadaa/data/farm_master.db` (160 mapping thiết bị). Chỉ fallback về Excel khi thiếu DB.
3. **Gmail 2FA Morning Watchdog (`tools/post_morning_gmail_2fa_watchdog.py`):**
   - Hàm `get_gpm_candidates()` đọc email, password, và twofa_secret trực tiếp từ bảng `mailboxes` thay vì cố nạp `master_gmail_manager.xlsx`.
4. **Feed Session Watchdog (`tiktok-luot nuoi acc/scripts/feed_session_watchdog.py`):**
   - Đọc đối soát primary từ bảng `tiktok_accounts` SQLite SSOT. Sửa điều kiện log telemetry reset follow count: chỉ thông báo reset về 0 khi `natural_cnt == 0`.

## 3. Checklist nghiệm thu và Kỷ luật thực thi
- [x] Cấm dùng `rowid` SQLite làm `source_row` khi còn đối chiếu Excel.
- [x] Phân tầng kiểm tra: Nếu `target.blank_pass` là True, cấm ép `password_saved`.
- [x] Tuyệt đối không để `openpyxl` chặn dòng thực thi chính khi SQLite SSOT đã nhận dữ liệu.
- [x] Chạy kiểm thử focused test với timeout an toàn trước khi đóng phiên (tránh test suites có sleep loop gây timeout 600s).
- [x] Mọi thay đổi mã nguồn bắt buộc tuân thủ Unified Patch Pipeline và đạt điểm Closeout Gate Approved (Score >= 80) trước khi push.
