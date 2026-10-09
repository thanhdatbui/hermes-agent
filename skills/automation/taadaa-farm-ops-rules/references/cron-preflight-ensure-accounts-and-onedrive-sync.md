# Cron Preflight Ensure Accounts & Multi-Repo / OneDrive Sync Parity

## 1. Cơ Chế Auto-Reg Bù Tài Khoản Preflight (`ensure_row_accounts.py`)
- **Bối cảnh & Cảnh giác sai lầm (Anti-Assumption):**
  - Trước đây, Feed Runner (`tiktok-luot nuoi acc`) chỉ ghi nhận `skipping` khi gặp hàng tài khoản rỗng (ví dụ: `account row 6 is empty (no username)`).
  - Operator đã nâng cấp cơ chế: Trước mỗi phiên feed (ở mọi session, không chỉ session 1), cron runner `tiktok_runner.py` gọi hàm `_preflight_ensure_accounts(row)` để kiểm tra và tự động reg bù ngay lập tức trước khi chạy feed.
  - **CẤM TUYỆT ĐỐI Coordinator phán bừa:** "Hệ thống không tự động reg inline vì sợ xung đột device_lock". Khi user thắc mắc "đã tự gọi reg chưa", phải kiểm tra ngay logic preflight `ensure_row_accounts.py` và lịch sử git mới nhất.

- **Luồng hoạt động của `ensure_row_accounts.py <row>`:**
  1. Đọc `taikhoan_run_safe.xlsx`, tìm tất cả máy thiếu account ở hàng `<row>`.
  2. Lọc bỏ các máy đã reg hôm nay (`get_machines_registered_today`).
  3. Kiểm tra kho `gmail_clean_v2.xlsx`: Nếu máy thiếu mail, tự động gọi `buy_hotmail.py` để mua Hotmail OAuth2 và nạp vào máy.
  4. Khởi động batch reg `_run_all_targets.py` (tự động acquire device-lock, chạy tối đa 20 targets/batch).
  5. Tự động merge tracking (`apply_deferred_tracking_results.py`) và đồng bộ an toàn sang `taikhoan_run_safe.xlsx` (`sync-safe-workbook.py`).
  6. Gửi báo cáo Telegram tổng kết đợt preflight reg bù.

- **Chốt chặn an toàn trong `tiktok_runner.py`:**
  - Nếu sau preflight mà Row đó vẫn có 0 account hợp lệ (`_count_valid_accounts_for_row(row) == 0`), runner sẽ từ chối spawn feed session (`return 0`) để tránh tạo các run vô nghĩa gây spam alert.
  - **Lưu ý nguyên nhân máy trống không được auto-reg bù:**
    - Khi máy trống nhưng KHÔNG được reg bù, KHÔNG ĐƯỢC vội kết luận là "cron bị xóa" hay "không có cơ chế".
    - Kiểm tra ngay `REG_DAILY_COOLDOWN_ACTIVE` trong `~/.codex/device-locks/reg_daily_cooldowns.json`. Nếu máy đó trong ngày hôm nay đã reg thành công 1 tài khoản (ví dụ ở ca khác), policy bảo vệ thiết bị sẽ chặn reg tiếp cho đến hết ngày (`cooldown_until: <ngày_hôm_sau>`) để chống bị TikTok gắn cờ theo IP/thiết bị.
    - Kiểm tra `ensure_row_accounts.py <row> --dry-run` để thấy rõ máy bị bỏ qua vì lý do gì.

---

## 2. Tam Giác Đồng Bộ Cron Script (Git Repo <-> Local Runtime <-> OneDrive Shared)
Hệ thống cron runner tồn tại ở 3 vị trí then chốt:
1. **Repo Master / Git Tracked:**
   `D:\Taadaa\Hermes\deploy\hermes-home\scripts\tiktok_runner.py` (và `feed_session_watchdog.py`)
2. **Local Runtime Hermes:**
   `C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py`
3. **OneDrive Shared (cho toàn farm & Admin):**
   `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\tiktok_runner.py`

- **Hiện tượng Lệch Bản (Stale Deploy Drift):**
  - Khi operator sửa code trên git repo (`Hermes/deploy/...`) hoặc trên OneDrive nhưng chưa deploy đè sang `AppData/Local/hermes/scripts/`, cron thực tế của Hermes sẽ chạy bản cũ.
  - Các triệu chứng điển hình:
    - Cron chạy bản cũ dùng `sys.executable` (venv của Hermes thiếu `openpyxl`) gây lỗi ngầm khi preflight.
    - Thiếu logic check mọi session hoặc thiếu đếm valid accounts.
- **Quy trình Kiểm tra & Đồng bộ Bắt buộc:**
  1. Khi user báo "đã fix lại... pull bản mới nhất về":
     - `cd D:/Taadaa/Hermes && git log -n 5 deploy/hermes-home/scripts/`
     - So sánh diff giữa repo và local: `diff -u "D:/Taadaa/Hermes/deploy/hermes-home/scripts/tiktok_runner.py" "C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_runner.py"`
  2. Khi đồng bộ deploy, BẮT BUỘC copy đồng thời vào CẢ HAI đích:
     - Local runtime: `C:/Users/Kibe/AppData/Local/hermes/scripts/`
     - Kho dùng chung: `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/`
  3. Đảm bảo cờ `-Python target_python()` trỏ đúng môi trường `D:/Taadaa/python-envs/automation/Scripts/python.exe`.

---

## 3. Cạm Bẫy Deferred Tracking Writer & Placeholder `mailto:...` trong Cột Pass
- **Hiện tượng:**
  - Sau khi reg thành công trên máy (ví dụ Máy 11, 18), file tracking result `tracking_result_stt11_*.json` sinh ra bị thiếu trường `tracking_row: ""` và `tik: ""`.
  - Khi chạy `apply_deferred_tracking_results.py`, hệ thống báo lỗi `BLOCKED_DATA_CONFLICT` với blocker `RESULT_MISSING_ROW_OR_TIK`.
  - Nếu điền tay `tracking_row` vào JSON và chạy lại, writer tiếp tục chặn với `TRACKING_ROW_HAS_ID_OR_PASS`.
- **Nguyên nhân cốt lõi:**
  - Trong `taikhoan_dat_v2_updated .xlsx`, một số dòng trống (chưa có ID, chưa có Email) lại bị dính chuỗi placeholder trong cột Password (ví dụ `mailto:Ps34834@934` hoặc `mailto:PhamChi&%5E%1998@Ks` - dấu vết sót lại từ các đợt assign mail cũ).
  - Hàm tìm slot `find_deferred_tracking_slot(stt, email)` trong `social_reg_v1.py` yêu cầu:
    ```python
    if row_stt == stt and empty_slot is None and all(
        value in (None, "") for value in (row_id, row_pass, row_gmail)
    ):
        empty_slot = (idx, row_tik or "")
    ```
    Do `row_pass` không rỗng, hàm coi dòng đó không trống và bỏ qua, dẫn đến không gán được `tracking_row` và `tik`.
  - Trong `deferred_tracking_writer.py`, chốt chặn an toàn `if not _cell_blank(row_id) or not _cell_blank(row_pass): return None, None, "TRACKING_ROW_HAS_ID_OR_PASS"` tiếp tục từ chối ghi đè vì thấy cột Password đã có dữ liệu.
- **Biện pháp xử lý:**
  - Trước khi áp dụng tracking deferred, phải rà soát và làm sạch các chuỗi rác/placeholder `mailto:...` trong cột Password của các slot chưa có ID.

---

## 4. Chốt Chặn Ghi Đè Safe Workbook (`TAADAA_ALLOW_OVERWRITE_TOKEN`)
- **Nguyên tắc an toàn:**
  - Workbook `taikhoan_run_safe.xlsx` được bảo vệ bằng cơ chế Guard Token chống ghi đè tuỳ tiện từ tiến trình lạ.
  - Khi gọi script đồng bộ `sync-safe-workbook.py`, BẮT BUỘC inject biến môi trường:
    `TAADAA_ALLOW_OVERWRITE_TOKEN="taadaa-writer-3c47f89f35e44795a79267e09fbcc72d"`
  - Nếu gặp `SYNC_ERROR: WORKBOOK_REPLACE_FAILED`, nguyên nhân do Windows file locking hoặc OneDrive đang sync nền file đích trong tích tắc. Chỉ cần retry sau 0.5s - 1s là ghi thành công.

---

## 5. Giới Hạn Cứng 8 Tài Khoản TikTok Trên Điện Thoại vs Bảng Tính
- **Triệu chứng (Case Máy 13, 19, 24):**
  - Bảng tính `taikhoan_dat_v2_updated .xlsx` hiển thị Máy còn trống ở Slot 7/8 (`ID = None`).
  - Runner chạy đến bước `[4] Tap Add account` thì crash với lỗi:
    `RuntimeError: [04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account', ...)`
- **Nguyên nhân cốt lõi (Trùng Hotmail cũ & Nick ký sinh):**
  - App TikTok Android có trần cứng tối đa **8 tài khoản/thiết bị**. Khi đạt đủ 8 nick, nút "Thêm tài khoản" biến mất hoàn toàn khỏi giao diện.
  - Lỗi nạp mail cũ khiến 1 mail Hotmail nạp vào 2 máy khác nhau -> máy thứ 2 khi login/reg bị đăng nhập vào chính tài khoản của máy thứ 1 (nick ký sinh, ví dụ nick M37 log ở M13, nick M51 log ở M24).
  - Máy ký sinh thực tế có đủ 8 nick trên app nhưng bảng tính Excel lại không có tên các nick này ở Slot 7/8, dẫn đến hệ thống tưởng thiếu và liên tục gọi reg bù gây crash `[04_add_account]`.
- **Kỷ luật điều phối & Quy trình xử lý:**
  - **KHÔNG canary lẻ tẻ hay reg đè mù quáng:** Khi user yêu cầu xử lý, phải **canh hết phiên/ca nuôi chính** (chờ 100% máy nhả device lock về HOME), không can thiệp giữa chừng làm nghẽn 4G/ADB của ca nuôi.
  - **Phải quét đối soát toàn farm (All máy):** Khi máy rảnh, quét snapshot UI switcher toàn farm để lập bản đồ nick thực tế, tìm ra mọi cặp nick bị log trùng giữa 2 máy.
  - **Logout nick ký sinh:** Thực hiện logout tài khoản trùng khỏi máy sai vị trí (giữ lại ở máy chính chủ) để app hạ xuống 7 nick, nút "Thêm tài khoản" xuất hiện trở lại rồi mới tiến hành reg bổ sung.
  - **Tối kỵ phản hồi chậm do lệnh quét/tìm kiếm đĩa diện rộng bị timeout:** Chỉ inspect O(1), không grep/find/glob sâu làm đơ coordinator.
