# Account Switcher Missing Expected & Reconcile Login Recovery (Case Study Máy 10, 2026-09-02)

## 1. Triệu chứng & Nguyên tắc cốt lõi
- **Triệu chứng**: Alert `🚨 [MÁY N] DỪNG PHIÊN` với lý do `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`. Trạng thái giữ hiện trường `handoff` lock `blocked`.
- **QUY TẮC CỐT LÕI (User Invariant 2026-09-02 — TUYỆT ĐỐI KHÔNG SUY DIỄN)**:
  1. **Khi máy THIẾU nick (< 6 nick)**:
     - BẮT BUỘC tự động kích hoạt flow `tiktok-log-in` (`reconcile_tiktok_accounts.py`) để đăng nhập nick thiếu vào máy.
     - **TUYỆT ĐỐI CẤM tự ý đôn slot hoặc chuyển nick thiếu sang máy khác**.
  2. **Chỉ swap/re-map Excel khi và chỉ khi MÁY ĐÃ FULL ĐỦ 6 NICK**:
     - Máy thực tế trên thiết bị đã đăng nhập đủ 6 nick mà trong đó có nick thừa ở slot phụ (7/8) và thiếu 1 nick ở slot chính (1..6). Lúc này mới đôn nick phụ lên slot chính và chuyển nick thiếu sang máy trống để tránh logout/login churn.
  3. **Auto-Recovery trong Feed Session (`feed_swipe_smoke.py`, Case 74)**:
     - Khi `verify_and_switch_profile` gặp lỗi `account-switcher-missing-expected`, script tự động gọi `_maybe_recover_missing_account_via_login()` để chạy subprocess `reconcile_tiktok_accounts.py` nạp nick vào máy, sau đó retry switch profile tiếp tục phiên nuôi mà không dừng phiên.

## 2. Xử lý sự cố Lệch cột DAT (Date pasted into Device ID)
- **Hiện tượng**: Dòng tài khoản mới reg bị paste ngày tạo (vd `2026-08-25` hoặc `21/08/2026`) vào Cột 10 (`device ID`), đẩy serial phần cứng thật sang Cột 11 (headerless).
- **Hậu quả**: `compare_tiktok_accounts.py --plan-only` báo lỗi `CONFIG_ERROR: machine X has conflicting serials in workbook`.
- **Khắc phục**:
  1. Backup master workbook `taikhoan_dat_v2_updated.bak-...xlsx`.
  2. Chuẩn hóa Cột 10 (`device ID`) về đúng serial phần cứng từ `PROXYgandienthoai.xlsx` / `Tik1.xlsx`.
  3. Xóa sạch dữ liệu Cột 11 (`cell.value = None`).
  4. Chạy chuỗi sync workbook:
     - `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-tik-workbooks.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"`
     - `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py" --source "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --output "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" --tik-dir "D:/OneDrive/TaadaaData/kibe"`
     - `python "D:/Taadaa/tiktok-log-in/scripts/compare_tiktok_accounts.py" --workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_dat_v2_updated .xlsx" --machines <M> --adb-path "..." --plan-only` (phải đạt `PLAN_OK`).
     - `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/hermes_taikhoan_sync_cron.py"`.

## 3. Quy trình chạy Login Reconcile thủ công khi cần
1. **Kill tiến trình cũ & Dọn Lock**:
   - Kiểm tra và kill các tiến trình reconcile/grep/runner cũ đang tranh chấp.
   - Xóa file lock cũ trong `C:\Users\Kibe\.codex\device-locks\` (`machine_<M>.lock.json`, `serial_<serial>.lock.json`).
2. **Force-stop TikTok trên máy**:
   - `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
3. **Chạy reconcile**:
   ```bash
   cd /d/Taadaa/tiktok-log-in && env -u PYTHONPATH "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" scripts/reconcile_tiktok_accounts.py \
     --workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx" \
     --machines <M> \
     --adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe" \
     --source-runner "D:\Taadaa\tiktok-luot nuoi acc" \
     --login-project "D:\Taadaa\Tiktok_Reg" \
     --login-workbook "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
     --proxy-mapping "D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx" \
     --allow-live-reconcile \
     --full-scope-takeover
   ```
4. **Kiểm tra kết quả**:
   - Đọc summary json trong `D:\CodexRuntime\codex_gmail_debug-tiktok-log-in\`.
   - Chụp screencap màn hình xác nhận.
