# Placeholder Alias Resolution & Stale Post Receipt Triage in TikTok Upload Workflow

## 1. Triệu chứng & Bối cảnh
- **Alert**: `🚨 [MÁY N] DỪNG PHIÊN` với lý do `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
- **Hiện tượng kép**:
  1. Switcher trên thiết bị thật hiển thị nhãn placeholder mặc định của TikTok (ví dụ `user9274263485158`) thay vì username mục tiêu (`verasdhkn0r`).
  2. Khi kiểm tra inventory bằng `compare_tiktok_accounts.py`, file gặp `CONFIG_ERROR: machine N has conflicting serials in workbook` do Cột 10 (`device ID`) bị dán nhầm chuỗi ngày tạo (`21/08/2026`), đẩy serial thật sang Cột 11 không có header.
  3. Khi retry upload video #2, workflow dừng ngay tại `VERIFY_POST` với lỗi `[POST_SUBMISSION_UNKNOWN] post_submission_state=UNKNOWN: không có bằng chứng TikTok ACCEPTED submission; không được ghi workbook hay báo success (COMPAT-POST-VERIFY-004)` do tồn dư file receipt cũ (`machine_3_account_verasdhkn0r_video_2.json`) ở trạng thái `intent_pending`.

---

## 2. Bản chất kỹ thuật & Nguyên nhân cốt lõi

### A. Cơ chế Placeholder Mapping (`user_alias`)
- Khi tài khoản mới đăng nhập hoặc chưa đồng bộ tên người dùng đầy đủ trên cache UI TikTok, switcher sẽ hiển thị nhãn `user<digits>` (ví dụ `user9274263485158`).
- `compare_tiktok_accounts.py` có cơ chế tự động tap vào placeholder, đọc Profile username đã load và ghi vào sheet `user_alias`.
- Khi `account_switcher.py` thực hiện exact match trên `node.text` / `content-desc` mà không tìm thấy, nó sẽ raise `ACCOUNT_MISSING`.

### B. Lệch Cột Serial trong Master DAT (`taikhoan_dat_v2_updated .xlsx`)
- Do thao tác paste thủ công hoặc script reg bù trước đó chèn thêm cột ngày hoặc dán lệch cột:
  - Cột 10 (`device ID`): bị ghi giá trị ngày tháng (`21/08/2026`, `23/08/2026`, `2026-08-26`...).
  - Cột 11 (không header): chứa serial phần cứng thật `9885e6344655484754`.
- Parser của `account_inventory.py` và `sync-safe-workbook.py` khi đọc Cột 10 thấy giá trị không hợp lệ hoặc thấy 2 serial khác nhau giữa các dòng của cùng một máy sẽ ném `conflicting serials in workbook`.

### C. Stale Post Attempt Receipt & Fingerprint Lock
- Trình quản lý Idempotency lưu vết từng lượt đăng tại `D:/CodexRuntime/tiktok-video/idempotency/post-attempts/machine_<M>_account_<A>_video_<V>.json`.
- Nếu lần chạy trước bị crash hoặc dừng ở trạng thái `intent_pending` (`post_submission_state=UNKNOWN`):
  - Hàm `_route_existing_post_receipt_to_verification()` trong `state_machine.py` sẽ chặn không cho thực hiện `MEDIA_PUSH` và chuyển thẳng sang `VERIFY_POST`.
  - Tại `VERIFY_POST`, vì submission chưa từng được ghi nhận `ACCEPTED`, quy tắc `COMPAT-POST-VERIFY-004` lập tức fail-closed chuyển sang `MANUAL_REVIEW` để chống đăng trùng.

---

## 3. Quy trình chuẩn hóa & Phục hồi dứt điểm (Standard Recovery SOP)

### Bước 1: Chuẩn hóa Serial Master DAT & Đồng bộ toàn Farm
1. Backup master: copy `taikhoan_dat_v2_updated .xlsx` sang `.bak-...xlsx`.
2. Chạy script chuẩn hóa Cột 10 & 11:
   - Nếu Cột 10 chứa chuỗi ngày tháng (`/` hoặc `-`) và Cột 11 chứa serial (chuỗi hex 16-20 ký tự): chuyển Cột 11 sang Cột 10 và gán `Cột 11 = None`.
   - Nếu Cột 10 và Cột 11 trùng nhau: gán `Cột 11 = None`.
3. Kiểm tra tính toàn vẹn:
   ```bash
   python "D:/Taadaa/tiktok-log-in/scripts/compare_tiktok_accounts.py" \
     --workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" \
     --machines 1-80 \
     --adb-path "C:/Users/Kibe/.GemPhoneFarm/app/adb-tool/adb.exe" \
     --plan-only
   ```
   *Yêu cầu: Bắt buộc đạt `PLAN_OK: 80 machine(s) validated`.*
4. Đồng bộ Safe Workbook:
   ```bash
   python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" \
     --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" \
     --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" \
     --tik-dir "D:/OneDrive/TaadaaData/kibe"
   python "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_taikhoan_sync_cron.py"
   ```

### Bước 2: Dọn dẹp Stale Post Receipt & Khôi phục Thiết bị
1. Lưu trữ và dọn receipt dở dang:
   - Di chuyển receipt cũ sang file `.bak`:
     `D:/CodexRuntime/tiktok-video/idempotency/post-attempts/machine_<M>_account_<A>_video_<V>.json.bak-<timestamp>`
   - Dọn fingerprint reservation JSON tương ứng nếu chưa `verified_success`.
2. Dọn file tạm trên điện thoại:
   ```bash
   adb -s <serial> shell rm -f /sdcard/DCIM/Camera/codex_* /sdcard/_ss*.png
   ```

### Bước 3: Chuyển tài khoản & Canary Test
1. Kích hoạt `open_account_switcher` và `select_exact_account` từ adapter để đưa TikTok về đúng nick mục tiêu.
2. Chạy canary upload:
   ```bash
   python -m scripts.tiktok_workflow \
     --config "D:\Taadaa\Tiktok-video\config.example.yaml" \
     --workflow-workbook "D:\OneDrive\TaadaaData\kibe\TikN.xlsx" \
     --single-device <serial> \
     --video-number <V> \
     --no-dry-run
   ```
3. Nghiệm thu:
   - Kiểm tra `checkpoint.json`: `status=SUCCESS`, `post_verified=True`, `profile_grid_scan` tăng baseline + 1.
   - Cột `Video Đã Đăng` trong `TikN.xlsx` và `taikhoan_run_safe.xlsx` cập nhật đúng số mới.
   - Chụp ảnh màn hình Profile để nghiệm thu Gate 6 trước khi đưa máy về Launcher Home.
