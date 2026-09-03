# Tiktok_Reg — mail-die guard, farm uiautomator recovery, OTP extraction (2026-08-06)

## Mail-die guard — CẤM xóa mail sống (bug đã xóa 3 mail nhầm)

Triệu chứng: run recovery xóa `eulaliaphilomenaclementina7@hotmail.com` (54),
`DerekMudryk198575@hotmail.com` (57), `vonhuong2509200436@gmail.com` (36) khỏi
`gmail_clean_v2.xlsx` dù mail còn sống.

Root cause: nhánh mail-die trong `_enter_tiktok_email_otp_with_one_fresh_retry`
và nhánh `[7c]` dùng `if not _outlook_inbox_visible(current_xml)` làm điều kiện
xóa — nhưng UI dump không hiện inbox (Chrome đã navigate đi sau resend) KHÔNG
chứng minh mail die. `check_mailbox_alive` trả `ALIVE` mà vẫn bị xóa.

Fix (cả 2 nhánh): chỉ xóa khi `inbox_status not in {"ALIVE","UNKNOWN"}` VÀ inbox
không visible; ALIVE/UNKNOWN → log "giữ mail, không cleanup". Regression:
`tests/test_hotmail_mail_die_alive_guard.py` — mock `enter_otp_code→False`,
`_request_and_read_fresh_tiktok_email_otp→None`, `_canonical_hotmail_check_alive→status`,
`_outlook_inbox_visible→bool`; test gọi CALLER `_enter_tiktok_email_otp_with_one_fresh_retry`
chứ không phải hàm con (nhánh mail-die nằm ở caller, không nằm trong
`_request_and_read_fresh...` — hàm đó trả None sớm ở nhánh "refusing reuse").

Rule chốt (user): mail không có trên máy (AccountManager) ≠ mail die. Chỉ
CAPTCHA-confirmed (Google reCAPTCHA/identity blocker rõ ràng có evidence) mới
xóa source + Audit Pending. Mail bị xóa nhầm → restore từ backup
`workbook-backups/gmail_clean_v2_before_captcha_delete_<mail>_<ts>.xlsx` vào
đúng vị trí (trước row máy kế tiếp, machine > N) + xóa Audit Pending sai.
Pattern script: `scripts/restore_sttXX_source.py` + `scripts/remove_audit_sttXX.py`
(backup trước khi sửa, insert_rows đúng vị trí, reopen verify, SKIP nếu đã có).

## uiautomator dump `Killed` (EXIT=137) toàn farm — reboot + set_proxy

Triệu chứng: `uiautomator dump` trả `Killed`/`Bad file descriptor` (logcat:
`UiAutomation.connect → RuntimeException: Bad file descriptor`) trên NHIỀU máy
cùng lúc; `ADB_TRANSPORT_LOST_AFTER_VERIFIED_PERSISTENT_CAPTURE` từ core
(circuit breaker: persistent capture từng OK rồi fail = atx-agent/uiautomator
treo, KHÔNG phải ADB mất).

Fix: `adb reboot` từng máy → `uiautomator dump` hết `Killed` (E=0). Kill
atx-agent / `am force-stop com.github.uiautomator` KHÔNG đủ (atx tự restart,
service vẫn lỗi) — reboot mới reset UiAutomationService.

SAU REBOOT: VPN `tun0` KHÔNG tự lên (vichanger app không auto-connect; màn
"No LSPosed access"/LoginActivity API Key). Watcher `gan_proxy_fleet.py watch`
KHÔNG tự gán lại cho máy reboot (chỉ xử lý reconnect event). Fix: gọi
`set_proxy(ADB, serial, proxy, timeout)` từ
`D:\Taadaa\gan-proxy\scripts\vi_changer_runner.py` (mở app + broadcast
`vn.vichanger.app.START_VPN -e proxy <proxy>` → verify `vpn_connected`). Proxy
lấy từ `PROXYgandienthoai.xlsx` (cột device ID / proXy). Kiểm tra nhanh:
`ip addr show tun0 | grep inet` (có `inet` = OK).

## OTP extract nhầm số trong email (STT 34)

`extract_recent_tiktok_otp_from_gmail_conversation` regex toàn cục
`(?<!\d)\d{6}(?!\d)` bắt nhầm `111034` từ `truongthuy111034@gmail.com` trước
code thật `097038` (node header/other-thread xuất hiện trước). Fix: ưu tiên
code 6 số trong node có marker (`tiktok`/`ma tiktok`/`verification`/`xac minh`/
`confirm`/`verify`); fallback strip email
`[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}` trước regex. Regression:
`tests/test_gmail_otp_marker_node_fix.py`.

## Venv recovery cô lập + PYTHONPATH thứ tự

Runner `run_tiktok_recovery_new_handler.py` pin `REQUIRED_CORE_VERSION` (vd
0.4.31) — env automation chung có thể là version khác + đang bị scheduler khác
dùng. Tạo venv riêng:

```
python -m venv --system-site-packages D:\Taadaa\python-envs\tiktok-reg-recovery
env -i PATH=... "/d/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe" \
  -m pip install --no-index --no-deps --force-reinstall \
  D:\Taadaa\_core031_build\dist\automation_core-0.4.31-py3-none-any.whl
```

PITFALL pytest: `PYTHONPATH` phải đặt `...\tiktok-reg-recovery\Lib\site-packages`
LÊN ĐẦU, nếu không import `automation_core`/`PIL` từ hermes venv (PIL
`_imaging` ImportError, core sai version). Đủ:
`PYTHONPATH="D:\Taadaa\python-envs\tiktok-reg-recovery\Lib\site-packages;D:\Taadaa\Tiktok_Reg;D:\Taadaa\Hotmail"`
+ `env -i` + `-p no:cacheprovider`. Cũng cần `D:\Taadaa\Hotmail` trong
PYTHONPATH vì `flows.hotmail_login` không nằm trong site-packages venv mới
(nếu dùng venv riêng thay vì env automation đã cài taadaa-hotmail).

## Gmail phone verify / account không trên máy

- `GMAIL_RECOVERY_PHONE_VERIFY` = HEALTH_MANUAL → GIỮ mail (không xóa); chỉ
  CAPTCHA → HEALTH_CAPTCHA → cleanup device + source. Consumer
  `_gmail_account_live_probe` dùng core `run_google_live_check` (policy giống
  repo `add mail khoi phuc`).
- Account không trong AccountManager ≠ mail die (STT 36 `vonhuong...` không có
  account trên máy nhưng mail vẫn phải giữ trong source — đã restore).
- Gmail account CÓ trên máy nhưng flow báo `target_account_unverified` = thường
  uiautomator treo (dump rỗng), không phải mất account — xác nhận bằng
  `dumpsys activity top` uri `content://com.google.android.gm.sapi/<email>/label/`.

## Hotmail "Protect your account" (account.live.com)

`LoginBlocked` marker "protection" = Microsoft bắt thêm recovery email sau đăng
nhập thành công — KHÔNG phải pass/2FA sai, mail KHÔNG die. Flow chuẩn:
`D:\Taadaa\add mail khoi phuc\run_add_recovery.py` (RECOVERY_EMAIL =
`thanhdatbui1995@gmail.com`, đọc TOTP từ IMAP) hoặc
`Hotmail\flows\hotmail_recovery.py`. `tap_skip_now` trong hotmail_login.py cần
uiautomator hoạt động (nếu dump treo thì không tap được → tưởng LoginBlocked).
