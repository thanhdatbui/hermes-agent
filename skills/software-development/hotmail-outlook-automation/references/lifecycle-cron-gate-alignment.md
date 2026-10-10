# Hotmail lifecycle-cron gate alignment

## Eligibility contract
For the Hotmail change-info supervisor, an account is eligible only when:

- TikTok registration succeeded: workbook `ID` and TikTok `PASS` are both non-empty.
- ChatGPT registration exists: workbook `PASS CHATGPT` is non-empty, or an equivalent trusted state marker such as `chatgpt_registered_at` is present.

Keep the independent gates for supported Microsoft domain, recovery-mail availability, 7-day soak, changed/cooldown state, device lock, and one egress IP/proxy per 24 hours.

## Important implementation detail
Remove the retired Dual-OAuth requirement from **both** locations:

1. The `WAIT_7D -> CHANGE_INFO` state-transition result.
2. The scheduler candidate filter that decides whether a `WAIT_7D` or `CHANGE_INFO` profile may run.

Removing it from only the change script does not activate the cron: the supervisor can still skip every candidate before launching the script.

## Cron preflight
Before “resuming” the job, inspect the scheduler state. The supervisor may already be enabled and running every five minutes; in that case change the gate logic rather than creating a duplicate cron job. Verify the job ID, enabled state, schedule, and next run after the change.

## Verification
Use a bounded offline check: inspect workbook headers and count eligible Hotmail rows, run `py_compile`, and run a focused supervisor eligibility/state-transition test. Do not use live GPM profiles or devices for this gate change.

## Lifecycle Reporting & Cooldown Pitfall (2026-10-10)
- **Lifecycle 6h Report Breakdown & Error Transparency**: `cron_hotmail_gpm_lifecycle_6h_report.py` must explicitly separate ChatGPT Reg progress from Change Hotmail progress. In the supervisor state machine, `DONE` is achieved exclusively after completing `CHANGE_INFO` (change password, 2FA TOTP, sign out everywhere, relogin, and writing new password to Excel/state tracker).
  - **CẤM gộp nick lỗi vào hàng đợi**: Tuyệt đối không tính các tài khoản có `status in {"BLOCKED", "FAILED", "ERROR", "QUARANTINE"}` vào số lượng `Hàng đợi đổi pass (CHANGE_INFO)`.
  - **Dòng báo lỗi bắt buộc**: Báo cáo bắt buộc phải có dòng `⚠️ Lỗi / Kẹt cần cứu (BLOCKED): <count>` riêng biệt để người điều hành và Farm Alert phát hiện ngay các sự cố phát sinh trong ca, không được che giấu lỗi trong số đếm hàng đợi.
- **Canonical 5-Step Security Flow**: Script `gpm_change_hotmail_security.py` khi chạy đổi thông tin bắt buộc thực hiện đủ 5 bước tuần tự:
  1. *B1: Bật 2FA TOTP Authenticator* offline (`pyotp`), lưu Secret vào Cột 4 `gmail_clean_v2.xlsx`. Thiếu 2FA dừng ngay, cấm đổi pass mù.
  2. *B2: Đổi mật khẩu mới*, cập nhật Cột G `taikhoan_dat_v2_updated .xlsx` và Cột 3 `gmail_clean_v2.xlsx`.
  3. *B3: Sign out everywhere* xác nhận dialog thu hồi token bên bán toàn cầu.
  4. *B4: Relogin Live* với pass mới + TOTP (điều hướng trực tiếp `login.live.com`, cấm dùng `/logout.srf` gây redirect race condition).
  5. *B5: Bấm [Có] KMSI* (duy trì đăng nhập), tự động đóng Cookie banner trước khi thao tác/chụp ảnh để lưu session vĩnh viễn trên GPM profile.
  - Xóa trắng Cột 9 (`token = None`) trong `gmail_clean_v2.xlsx`, ghi nhận vào `hotmail_changed_tracker.json` và gán cooldown 24h cho Egress IP.
- **Proxy Cooldown Pitfall in Supervisor**: When `gpm_change_hotmail_security.py` aborts due to `[COOLDOWN_BLOCKED]` (the 24h per-IP cooldown), returning exit code 1 causes the supervisor to mark the profile `status: BLOCKED`. Because candidate selection lacks auto-unblock logic for `CHANGE_INFO` (unlike `HOTMAIL_LOGIN` which unblocks after 48h), candidates blocked by proxy cooldown become starved. Cooldown returns must either exit cleanly as waiting/cooldown or have an auto-unblock path once the 24h IP window elapses.
