---

name: hotmail-outlook-automation

description: Hotmail/Outlook account automation on the Android farm — mailbox-alive live checks, change-info pipeline (password change + logout devices), eligibility gates from gmail_clean_v2, and security/recovery entry points.

---



# Hotmail/Outlook Automation

- **BoxTaiKhoan API**: Endpoint mua tự động `POST /ajaxs/client/product.php` (id 60 - OAuth2 393đ). Format: `mail|pass|refresh_token|client_id`. Lưu ý: Khi mua số lượng lớn, gọi API mua lẻ từng acc (`amount=1`) qua vòng lặp giúp nhận trực tiếp mảng `data` đầy đủ, tránh phụ thuộc vào trang chi tiết đơn hàng `/product-order/` trên web.
- **Kiến trúc kho Gmail Clean V2 & 2 Cột Trạng Thái (User update 2026-08-25)**:
  - `gmail_clean_v2.xlsx` là **Single Source of Truth** chứa cả Gmail và Hotmail của farm.
  - Cột 11: `info_changed` (đánh dấu `1` khi đã đổi pass/thông tin bảo mật).
  - Cột 12: `app_logged_in` (đánh dấu `1` khi đã đăng nhập vào app Outlook trên điện thoại).
  - **Quarantine Mail Lỗi**: Tài khoản bị lỗi token, die, hoặc không đọc được mail/OTP phải xóa ngay khỏi `gmail_clean_v2.xlsx` và lưu vào `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` để không bị script chọn lại gây kẹt máy.
  - **Cấm mở App Outlook khi có Token**: Mailbox có token Graph API (Hotmail loại 2) bắt buộc đọc OTP/Magic link trên PC; chỉ mở app khi user yêu cầu rõ ràng và phải giữ device lock/canonical runner. Chi tiết provenance và báo cáo: `references/purchase-provenance-and-reporting.md`.
- **Kiến trúc kho Gmail Clean V2 & 2 Cột Trạng Thái (2026-08-25)**:
  - `gmail_clean_v2.xlsx` là **Single Source of Truth** chứa cả Gmail và Hotmail của farm.
  - Cột 11: `info_changed` (đánh dấu `1` khi đã đổi info/pass bảo mật Hotmail).
  - Cột 12: `app_logged_in` (đánh dấu `1` khi đã login vào Outlook app trên thiết bị).
  - Hotmail mới mua về nạp thẳng vào `gmail_clean_v2.xlsx` (để trống 2 cột này). Script reg TikTok (`_detect_clean.py`) tự quét các mail chưa có ID TikTok trong `taikhoan_dat_v2_updated .xlsx` để chạy.
  - **Quarantine Mail Lỗi**: Tài khoản bị lỗi token, die, hoặc không lấy được OTP bắt buộc XÓA khỏi `gmail_clean_v2.xlsx` và lưu vào `D:\Taadaa\Hotmail\hotmail_failed_quarantine.txt` để chống script chọn lại gây kẹt vòng lặp.
- **Chống xoay ngang màn hình (Rotation Lock)**: Phải chạy đầy đủ `settings put` + `content insert` vào `system:accelerometer_rotation=0` và `user_rotation=0` trước khi mở Outlook.
- **Batch Login ATX XML-First & Tự động khôi phục ATX**: Dùng `run_batch_login_xml.py` (port 7912) điều hướng từ onboarding, selector Outlook, form email/pass đến xác nhận drawer. Tích hợp `reset_atx_agent` từ `automation_core.persistent_ui` để tự động hard-reset ATX daemon + UiAutomator stub khi gặp lỗi kết nối/502 Bad Gateway. Chi tiết: `references/batch-hotmail-login-atx-autorecovery-20260822.md` và `references/boxtaikhoan-api-and-xml-batch-login-20260822.md`.
- **Hotmail Change-Info Selection & Quản lý Mail Tạm**: Quy tắc lọc Hotmail ngâm >= 7 ngày, bỏ qua tài khoản đã change pass/secured, thực trạng flow hiện tại (đổi pass + logout everywhere để revoke OAuth2 token + quét và gỡ mail khôi phục tạm của shop getnada/fviainboxes), và quy tắc cập nhật workbook/backup: `references/hotmail-change-info-pipeline-and-untrusted-removal-20260823.md`.
- **Device Lock Isolation & Anti-Collision**: CẤM đặt `allow_takeover=True` hoặc `takeover_authorized=True` trong batch login tự động tránh cướp lock của cron nuôi acc / feed session; bắt buộc force-stop Outlook sau khi nạp xong. Chi tiết: `references/batch-login-device-lock-safety.md`.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Repo `D:\Taadaa\Hotmail` (package `taadaa-hotmail`, editable install). Canonical provider login logic lives in `flows/hotmail_login.py`; cross-project Outlook field selectors live in `automation_core.outlook` (never fork/sync a copy). Consumer: `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` wires `_canonical_hotmail_check_alive` into OTP timeout + reject branches.

`docs/ui-compatibility.md` — UI contracts (ID/owner, UI signature, selectors, safety bounds, post-action verification, regression tests).



## Login method landscape (2026-08-13) — Gmail app fails, Outlook app wins



- **Gmail app CANNOT log Hotmail/Outlook accounts anymore**: it uses IMAP/SMTP basic auth (plain email+password); Microsoft disabled basic auth for consumer Outlook.com accounts in Sept 2022 → selecting "Outlook, Hotmail và Live" in Gmail setup shows "Không thể xác thực" (screenshot-verified machine 30, farm panel). A leaked OAuth token (`M.C515_BAY...` artifact) cannot be pasted as the password either — Gmail app only accepts password/app-password.

- **Microsoft Outlook app uses OAuth** (Microsoft-hosted login page inside the app) → logs in with plain email+password, **NO 2FA/app-password required for consumer accounts**. This is the correct path for the farm. The 2FA + app-password + manual IMAP (`outlook.office365.com:993` SSL / `smtp.office365.com:587` STARTTLS) workaround for Gmail app is not worth it at scale.

- **Chrome webmail is not scriptable reliably** (DOM churn, anti-bot, datacenter-IP captcha) — do not build farm automation on it. Outlook app + UI-tap script (same pattern as TikTok flows) is the scalable route.

- **Farm S7 (Android 8) needs Outlook ≤ 4.23xx** (mid-2023): newer 5.26xx require Android 10+ and won't install. Verified working build (2026-08-13/14, installed `Success` on máy 1, 2, 6, 38): **4.2325.1 arm-v7a nodpi minAPI26** from APKMirror's variant page. APK stored at `D:\OneDrive\apk-bank\com_microsoft_office_outlook\com.microsoft.office.outlook_4.2325.1-32325818_minAPI26(armeabi-v7a)(nodpi)_apkmirror.com.apk` (103MB).

- Install recipe: `adb push <Windows-path> /data/local/tmp/outlook.apk` (adb needs Windows `D:\...` paths, not MSYS `/d/...`) then `adb shell pm install -r -d /data/local/tmp/outlook.apk` → `Success`; clean up `/data/local/tmp/outlook.apk` after. Verify with `adb shell dumpsys package com.microsoft.office.outlook | grep versionName`.

- **Downloading the old build**: from the farm host (datacenter IP) APKMirror/APKPure are Cloudflare-blocked for scripted fetch and APKCombo keeps only the 3 newest versions (all Android 10+) — do not rabbit-hole through mirrors. Reliable path: user downloads on their own PC Chrome (home IP passes Cloudflare) and drops the APK into the bank folder. Sanity-check before install: `unzip -l <apk>` (APK is a zip container; a few-KB file = ad page, not the APK) + `md5sum`.



## Finding unregistered Hotmail accounts (source of truth, 2026-08-14)



- **Canonical email inventory** = `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`, sheet `Gmail Accounts` (columns: `số máy | tài khoản gmail | pass mail | 2fa | mail khôi phục | ngày tháng năm sinh | ngày tạo | mã phụ hồi`). Holds ALL farm emails (gmail + hotmail) — user points here for "mail chưa reg TikTok".

- **Unregistered = email in gmail_clean_v2 NOT present in `taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản` (GMAIL column)** — no TikTok row/ID yet.

- ⚠️ **Trap: `NGÀY TẠO` empty does NOT mean unregistered.** Many hotmail rows have empty `NGÀY TẠO` yet already carry a TikTok `ID` (username) — first pass wrongly flagged máy 6/30/37/56, user corrected ("máy 6 làm lol có hotmail chưa reg tiktok"). The real reg signal is the `ID` column: non-empty = registered. Cross-file diff is the reliable method.

- Result 2026-08-14: 44 unregistered emails, 5 hotmail → machines **38** (aug***, flo***), **54** (eul***), **57** (Der***), **66** (Dau***). Outlook installed on máy 38 (`ce06160685310f1c04`, Android 8.0.0, rảnh launcher).

- **Serial mapping**: `taikhoan_run_safe.xlsx` sheet `Accounts` (`May | Device ID | ID`) covers only machines 1-2; for all other machines the serial lives in `taikhoan_dat_v2_updated .xlsx` (`Máy` + `device ID` columns). Always resolve serial from the workbook, never `adb devices` order.

- Reusable: `scripts/find_unregistered_hotmail.py` (cross-references both workbooks, prints máy + masked email only, never credentials).



## Mailbox alive check (`check_mailbox_alive`)



`flows/hotmail_login.py::check_mailbox_alive(adb, device, email, password, artifact_dir) -> str` is a thin wrapper over `login(force_login=False)`:



| Result | Meaning |

|---|---|

| ALIVE | login `SUCCESS` / `ALREADY_SIGNED_IN` — inbox reached + target account confirmed |

| BLOCKED | `LoginBlocked` containing captcha/passkey/protection/wrong-password/account-could-not-be-confirmed |

| UNKNOWN | transport/other exception, or `LoginBlocked` not matching markers → **keep the mail** |

| DEAD | login did not verify inbox (⚠ see user stance) |



**User stance (2026-08-05):** "login không được mà báo die là không hợp lý" — a login that fails to reach the inbox must NOT be classified DEAD; the mail may still be alive (wrong password, unverifiable UI). DEAD should mean a distinct, proven signal (mailbox closed/deleted). Do not finalize DEAD semantics until that's designed; when in doubt classify UNKNOWN and keep the mail.



## Live-check workflow (verified 2026-08-05, machine 1 → ALIVE)



1. **Pick mail**: read `D:\OneDrive\codex_gmail_debug\register gmail\gmail_clean_v2.xlsx`, sheet `Gmail Accounts`. Filter `@hotmail`/`@outlook` domains. **User preference: choose the BOTTOM row per machine (the newest-added mail)**, not the older rows. `khoaleemagic@gmail.com` (and other `khoa*` recovery mails) exist ONLY as the recovery mailbox of ~40 Gmail rows — there is NO row/password for them in the workbook; if Microsoft sends OTP to a `khoa*` address, the code cannot be read. No Hotmail row has a `khoa*` recovery mail.

2. **Resolve serial** ONLY from `D:\OneDrive\codex_gmail_debug\tiktok-luot nuoi acc\data\taikhoan_run_safe.xlsx` sheet `Accounts` (`May` → `Device ID`) via `resolve_machine_serial_from_source` / `validate_target_serial`. Never from `adb devices`, hardcoded constants, or the proxy workbook. Missing/conflicting mapping → fail preflight `MACHINE_SERIAL_MISMATCH`.

3. **VPN preflight**: `python D:\Taadaa\gan-proxy\scripts\gan_proxy_fleet.py run --machines <n> --workers 1 --timeout 45` → verify `tun0 UP` AND Android VPN `CONNECTED` (dumpsys connectivity) before any Hotmail action. A generic START_VPN broadcast without `.AdbCaller` + proxy extra is not valid.

4. **Clean machine state** before running (farm machines often sit in TikTok SplashActivity / RecentsActivity).

5. **Run** with `PYTHONPATH=.` (needed for `tools.append_mail_account` imports). Result artifact `login_<ts>.json` written under the artifact dir; `LOGIN_SCREEN_RESULT` status confirms the flow reached the end.



## change-info pipeline (password change + logout devices)



Two entry points — use the RIGHT one:



- ✅ **`flows/hotmail_change_info.py`** — canonical. Args: `--email`, `--machine`, `--live` (required), `--artifacts`, `--force-login`, `--full-scope-takeover`, `--resume-logout-only`. New password via env `HOTMAIL_NEW_PASSWORD` (or getpass prompt). It auto-runs: VPN → device lock → login → change-password → logout-devices → remove-getnada. `--live` requires exactly one `--email` or `--all-eligible`.

- ❌ **`scripts/change_info_hotmail.py` / `scripts/change_hotmail_password.py` / `scripts/logout_hotmail_devices.py`** — all call `flows.hotmail_security.run_security_task`, which is **fail-closed** with `LEGACY_SECURITY_ENTRYPOINT_DISABLED_USE_HOTMAIL_CHANGE_INFO`. Never use them for live work.



**Eligibility gates** (any failure → `FINAL_BLOCKED`; run `load_hotmail_targets(evidence=collect_login_evidence())` to preview):

- Domain ∈ {hotmail.com, outlook.com, live.com, msn.com}; password present; machine present; no duplicate email

- `ngày tạo` (login date) parseable, not future, `age >= MIN_LOGIN_AGE_DAYS` (7)

- **Login evidence artifact** in `.ai-runs` matching email+machine+date via `collect_login_evidence()`. Without it → `LOGIN_DATE_UNVERIFIED` (24 of 31 farm mails hit this). Evidence files live under `.ai-runs/hotmail-machine-<m>-<date>/result_machine_<m>_account_<n>.json` with `verified` or `exact_mailbox`+`inbox_marker` fields.


### Live change-info preflight & the `HOTMAIL_NEW_PASSWORD` fail-closed gate (2026-08-21)

The new-password secret is a HARD PREREQUISITE — the flow gates it BEFORE any serial/VPN/lock action, so a live run is impossible without it and you must stop cleanly (leaving locks intact):

- Gate at `flows/hotmail_change_info.py:1085`: `if not new_password and not resume_logout_only: fail("FINAL_BLOCKED", "NEW_PASSWORD_MISSING")` — this runs BEFORE serial resolution (1122), VPN setup (1137), and lock acquisition (1173). Under `--live` with no env var, `cli()` line 1923 falls back to `getpass.getpass("Mật khẩu Hotmail mới: ")` — which HANGS in a non-interactive agent and cannot proceed.
- **Preflight (run this BEFORE launching any live change-info):** `if [ -n "$HOTMAIL_NEW_PASSWORD" ]; then echo PW_PRESENT; else echo PW_ABSENT; fi`. If absent → STOP. Report `FINAL_BLOCKED / NEW_PASSWORD_MISSING (SECRET_NOT_PROVISIONED)`. Do NOT run `--live`, do NOT touch device/lock state, do NOT hardcode or print the credential. The run is impossible without the secret; a `NEW_PASSWORD_MISSING` stop leaves every lock fully intact (correct).
- Supply the secret by exporting `HOTMAIL_NEW_PASSWORD` safely in the shell before invoking; never pass it as a CLI arg or print it into a report. The flow reads it ONLY from env (`_new_password_from_env_or_prompt` → `os.environ.get("HOTMAIL_NEW_PASSWORD")`); there is NO secret-loader file in the repo. "Use the env var if provided" means the var must already be exported in the agent's shell — it is not auto-injected.
- `new_password == target.current_password` also fails closed (`NEW_PASSWORD_UNCHANGED`, line 1089) — the supplied password must differ from the current one.


### Safe read-only verification before a live run (2026-08-21)

Verify target→machine→serial mapping and eligibility WITHOUT touching the device, VPN, or lock by running the flow with NO `--live` and NO password:

```
PYTHONPATH=. D:/Taadaa/python-envs/automation/Scripts/python.exe flows/hotmail_change_info.py --machine <N> --email <addr>
```

- Prints one JSON per target: `{"target":"machine-<N>-row-<R>","row":R,"machine":"<N>","email":"<addr>","login_date":"...","age_days":N,"eligible":true,"gate_failure":null,"status":"ELIGIBLE","state":"CLASSIFIED"}`.
- This is the correct FIRST STEP of a live retry: confirm the locked target is the intended machine/serial and eligible, keep the existing lock files untouched, then only proceed to `--live` once `HOTMAIL_NEW_PASSWORD` is present and the OTP mailbox env (`OTP_MAIL_USER`/`OTP_MAIL_APP_PASSWORD`) is set. (Read-only inventory returns `ELIGIBLE` even when no `HOTMAIL_NEW_PASSWORD` — eligibility ≠ runnability; the password gate is separate.)


### Device-lock preservation during retry (invariant)

- For a user-requested retry, the existing v2 lock files (`C:\Users\Kibe\.codex\device-locks\machine_<N>.lock.json` + `serial_<serial>.lock.json`, `status":"running"`, `owner_active":true`) MUST stay intact. Verify they exist and match machine+serial BEFORE each machine; do NOT release/unlock at end; do NOT touch other machines' locks. A preflight that stops at `NEW_PASSWORD_MISSING` leaves locks fully intact — that is correct.
- Run machines ONE AT A TIME (the OTP mailbox `thanhdatbui1995@gmail.com` is SHARED — see OTP rule). Never parallelize change-info retries.



## Verification



- Unit tests: **PHẢI dùng venv `automation`, KHÔNG dùng python global** (16/08: `PYTHONPATH=. python -m pytest` với Python 3.12 global FAIL collection ngay `ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'` — site-packages global cài automation_core CŨ thiếu symbol mới). Lệnh đúng:

  `PYTHONPATH=. D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` → **163 passed** (16/08). `-p no:cacheprovider` vì `.pytest_cache` permission denied trên D:; `PYTHONPATH=.` vẫn cần (`tools.append_mail_account` import cần nó).

- `python -m compileall -q flows/ tests/` and `git diff --check` before commit.

- Commit only the intended files (`flows/*.py` + tests + docs); repo may show unrelated modified files from other workstreams — leave them.



## Pitfalls



- **ATX-agent là PRIMARY đọc UI — CẤM gọi `uiautomator dump` trực tiếp (user rule 2026-08-16, user nổi giận vì bị vi phạm).** Trên máy S7 yếu (Android 8) `uiautomator dump` bị **Killed** (OOM) → `capture_ui_xml`/automation_core fail `non_xml_ui_dump`. Đọc UI qua ATX JSON-RPC: `POST /session/{pid}:com.github.uiautomator/jsonrpc/0` với `{"method":"dumpWindowHierarchy","params":[true]}` (pid = process `com.github.uiautomator`). Gõ text WebView = tập trung field bằng `click` rồi `adb shell input text`, tap submit bằng `click`. Chi tiết + bảng method đúng/sai: `references/atx-agent-jsonrpc-api.md`.

- **Shop hotmail "loại 2" (OAuth2, kèm `refresh_token|client_id`) đọc OTP được từ PC qua Graph API** — token sống, scope `Mail.Read` (không có User.Read/Mail.Send); đổi pass ngày 7 giết token. Đã build reader vào `Tiktok_Reg/hotmail_provider.py::read_tiktok_otp_from_graph_token` (commit `8752c7b`): đổi refresh_token → access_token → `/me/messages` → regex 6 số (ưu tiên Graph, fallback outlook-app; token từ file/env/arg, KHÔNG hardcode). Quyết định loại 1 vs loại 2 + script test `scripts/test_graph_token.py`: `references/graph-api-otp-token.md`.

- **Verification tests Hotmail phải chạy đúng venv automation + BỎ PYTHONPATH Hermes**: `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider` (16/08: 163 pass; 17/08 sau thêm ATX tests: 184 pass). Nếu quên `env -u PYTHONPATH`, `automation_core` import từ Hermes venv (bản CŨ thiếu `DeviceLockNeedsUserDecision`/`capture_atx_session_ui`) → collection fail. `PYTHONPATH=.` vẫn cần cho `tools.append_mail_account`; `git diff --check` sạch trước commit.

- **Refer to machines by PANEL NUMBER (1-80), never by serial suffix.** "Máy 337" (serial `...3337`) meant nothing to the user ("Đéo có máy nào là máy 337 cả") — serial `9885e6303951513337` = **máy 2**. Resolve serial→panel number via the workbook BEFORE reporting which machines were touched, and state the workbook source when quoting data findings (user: "mày đọc dữ liệu ở đâu v?").

- **Inbox URL is not mailbox identity**: `outlook.live.com/mail/...` or a URL-only `inbox_matches_account` result can be true while Chrome is showing a different signed-in account or a stale login surface. For OTP/magic-link work, require visible masked target-account evidence (or an exact trusted source-row identity) before selecting a message. If identity is missing/conflicting, classify `FINAL_BLOCKED` and do not read the first six-digit string.

- **Chrome 138 + farm accessibility OFF** (`enabled_accessibility_services=null`): WebView exposes ONLY `url_bar` in the hierarchy — form fields (`loginfmt`, `i0116`, `i0118`, `passwordEntry`) and page text are invisible to `ui_xml`/`uiautomator dump` (0 nodes). Symptom: login finds the email field then dies with "Could not identify Outlook password field" or "Could not select Keep me signed-in: Yes". The screen is actually fine — the tree is empty. **Coordinate fallback works**: pixel-scan the screenshot for the Microsoft blue button (b>140, 0<r<120, 60<g<140), tap the centroid. Verified: tap `(540,1593)` passed keep-signed-in → `outlook.live.com/mail/0/inbox` URL proof → login OK. Never change shared selectors for this; branch by UI signature with bounded coordinate fallbacks.



### Quy trình Takeover & Device Lock Persistence (2026-08-22)

- **4 Bước Takeover Toàn Diện:**
  1. `Change/Reset Password`: Đổi mật khẩu mạnh, lưu trữ Excel ngay kèm backup an toàn.
  2. `Sign Out Everywhere`: Truy cập `account.live.com/proofs/manage/additional` $\rightarrow$ Đăng xuất khỏi mọi nơi để revoke session token cũ.
  3. `Security Proofs Cleanup`: Gán Mail KP bảo vệ trong giai đoạn nuôi farm (30-60 ngày) $\rightarrow$ Gỡ Mail KP tức thì bằng OTP trong ngày xuất bán.
  4. `Inventory & App Sync`: Đồng bộ pass mới vào Outlook App và Inventory.
- **Quy tắc Device Lock Lease & Tự Động Unlock Sau Hoàn Tất (User Rule 2026-08-22):**
  - Trong quá trình thao tác/sửa lỗi: Bắt buộc giữ lease lock (`takeover_authorized=True`, `takeover_scope='FULL_SCOPE_TAKEOVER'`).
  - **Sau khi hoàn tất 100% quy trình:** BẮT BUỘC **TỰ ĐỘNG UNLOCK NGAY** (xóa file lock trong `C:\Users\Kibe\.codex\device-locks`), tuyệt đối không để máy bị khóa cứng làm cản trở lịch chạy farm.
- **Xử lý Hotmail còn dính Mail KP của shop phôi ban đầu (`kh*****@gmail.com`):**
  - Khi web đòi OTP của mail shop cũ mà ta không nắm quyền: KHÔNG cố đổi pass trên web (tránh phá vỡ session).
  - Giữ nguyên phiên đăng nhập trong App Outlook trên máy để tiếp tục nhận mã TikTok phục vụ nuôi farm / đăng ký.

### Change-Info trên Chrome vs Reset mật khẩu qua Gmail khôi phục (2026-08-21)

- **Cơ chế Change-Info:** App Outlook không hỗ trợ đổi mật khẩu/bảo mật native -> BẮT BUỘC thực hiện qua trình duyệt Chrome trên máy (chạy qua IP proxy của máy) tại `account.live.com/password/Change` hoặc `account.live.com/password/reset`.
- **Khác biệt cốt tử giữa 2 form nhập email khôi phục của Microsoft:**
  - **Form Reset Password (`account.live.com/password/reset`):** Bên ngoài ô nhập đã có sẵn đuôi `@gmail.com` cố định -> **CHỈ nhập prefix:** `thanhdatbui1995`.
  - **Form Security Proof khi đăng nhập Chrome (`login.live.com` - "Xác minh email của bạn"):** Ô nhập liệu có nhãn "Email" hoàn toàn trống -> **BẮT BUỘC nhập đầy đủ toàn bộ địa chỉ:** `thanhdatbui1995@gmail.com`. Nếu chỉ gõ prefix, Microsoft sẽ báo lỗi đỏ *"Email này không trùng với email thay thế liên kết với tài khoản của bạn..."*.
- **Bẫy bóc tách mã OTP: LinkId `521839` của Microsoft:**
  - Mọi email xác thực/reset của Microsoft luôn chứa URL điều khoản: `.../fwlink/?LinkId=521839`.
  - Regex bắt mã 6 số nếu tìm generic sẽ bắt nhầm `521839` thay vì OTP thật -> Phải ưu tiên pattern theo cụm từ (`(?:ma cua ban|code is|ma bao mat)[^\d]{0,20}(\d{6})`) và blacklist loại bỏ hoàn toàn số `521839`.
- **Xác minh danh tính trước khi đổi pass trên Chrome (`_verify_target_identity_before_logout`):**
  - Trên mobile Chrome, trigger mở menu danh tính là `mectrl_main_trigger` (avatar góc phải trên), đóng menu qua trigger hoặc phím Back (keyevent 4).
  - Khi form đổi pass đã hiển thị trực tiếp trên session target (`account.live.com/password/Change`), cho phép fallback xác nhận danh tính để không bị chặn oan bởi `menu_not_dismissed`.
- **Nút Lưu (`UpdatePasswordAction`) & Markers thành công tiếng Việt:**
  - Nút "Lưu" trên giao diện xoay ngang/mobile có resource-id `UpdatePasswordAction` (cần cuộn nhẹ màn hình nếu bị che).
  - Sau khi submit, Microsoft chuyển hướng sang trang quản lý tài khoản với các tiêu đề tiếng Việt -> `_PASSWORD_SUCCESS_MARKERS` cần bao gồm: `"thay đổi mật khẩu"`, `"tài khoản microsoft"`, `"thông tin của bạn"`, `"quản lý tài khoản"`.
- **Quy tắc Device Lock khi fix máy (User Invariant):**
  - Khi user yêu cầu "lock máy lại để fix", lease lock trong `C:\Users\Kibe\.codex\device-locks` phải được giữ nguyên (`release_on_terminal=False` hoặc duy trì file lock) cho đến khi hoàn tất và có lệnh từ user. Tuyệt đối không tự ý release lock giữa chừng.
  - Chạy tuần tự từng máy để tránh xung đột mã xác thực OTP Gmail khôi phục chung (`thanhdatbui1995@gmail.com`).
  - Chi tiết lọc tài khoản >7 ngày, bỏ qua tài khoản đã change và cập nhật Excel: `references/change-info-7day-filter-and-workbook-marking-20260823.md`.

### Opaque-dump coordinate fallbacks (implemented in `flows/hotmail_login.py` 2026-08-05)



Fixed pattern (with regression tests `OpaqueDumpFallbackTests` in `tests/test_hotmail_login.py`):

- `_ui_has_content(xml)` decides opaque vs real dump. **Must skip, in order:**

  1. `url_bar` resource-ids (`URL_BAR_IDS`);

  2. **Chrome's own chrome ids** (`CHROME_CHROME_IDS`: `toolbar`, `home_button`, `menu_button`, `tab_switcher_button`, `location_bar_status`, `toolbar_buttons`, `optional_toolbar_button`, `toolbar_hairline`, `toolbar_progress_bar_container`, `menu_button_wrapper`, ...) — ChromeToolbar nodes are package `com.android.chrome` so the package filter alone does NOT exclude them, and their `imagebutton`/`button` classes make the function wrongly return True;

  3. **any node whose `package` != `com.android.chrome`** — SystemUI status-bar nodes (`com.android.systemui:id/battery_percentage_view`, `clock`, `scrim_*`) are present on EVERY dump. ⚠ LIVE FINDING (2026-08-05): many SystemUI nodes have NO `package` attribute at all (only `resource-id` = `com.android.systemui:id/...` or bare `android:id/...`), so the package filter alone misses them and `battery`/`clock`/notification text makes `_ui_has_content` return True on a page that is genuinely opaque. **ALSO filter `resource-id` by `SYSTEMUI_IDS` prefixes** (`com.android.systemui:`, `android:id/`). The same resource-id filter must go into `visible_flat_text`, or notification-shade text (Gmail/Google Play/system "60 thư mới", VPN) pollutes every marker check;

  4. **WebView wrapper `content-desc`** = "Lượt xem trên web" / "web view" / "luot xem tren web" — compare with `.casefold()` on BOTH sides, the live desc is capitalized `'Lượt xem trên web'` and a case-sensitive `"lượt xem trên web" not in desc` returns True (bug found live);

  5. only then count `webview`/`edittext`/`button` classes, non-empty `text`, or non-generic `desc` as real content.

- `account_login_email_node`: opaque + `login.live.com` in active URL → `LOGIN_EMAIL_POINT (540,831)`.

- `login()` password step: opaque + `login.live.com` URL after email submit → `LOGIN_PASSWORD_POINT (540,1143)` (new constant).

- `tap_keep_signed_in_yes`: opaque → tap `(540,1593)` up to 2×, verify prompt gone. On REAL dumps it also needs a fallback: if `tap_text("Có","Yes")` fails or doesn't clear the prompt, tap `(540,1593)` anyway (bounded).

- `inbox_matches_account`: opaque + `has_outlook_inbox_url` → True (URL proof replaces the account-menu check only when the dump is otherwise empty; identity gates still apply upstream).

- **`login()` first-step predicate AND the inbox-first branch must also accept `has_outlook_inbox_url(xml)`** (2026-08-05). On an opaque dump with a live session `has_inbox_marker` is False (WebView text invisible), so without the URL proof the flow falls into the login branch and dies `Could not identify Outlook password field` even though the mailbox is already signed in. This fix is what finally moved the change-info pipeline from `LOGIN_NOT_VERIFIED` to `ALREADY_SIGNED_IN` (and past login into security reauth).

- **`visible_flat_text` MUST apply the same package filter as `_ui_has_content` (only `com.android.chrome` nodes)** — otherwise SystemUI notification-shade text (Gmail/Google Play/system "60 thư mới", VPN) pollutes EVERY marker check (`has_inbox_marker`, `has_saved_password_prompt`, CAPTCHA) and the phone sitting on the notification drawer looks like WebView content. Live symptom: pipeline fails "password field" while `mResumedActivity` is fine but the drawer is open; also `uiautomator dump` includes `search_box_text 'Tìm thẻ của bạn'` when a new-tab page is up.

- Bounded guard discipline: fallback coordinates ONLY when `_ui_has_content` is False AND the active Chrome URL matches the expected page; never on a dump with real interactive nodes (those keep semantic resolution).

- Enabling `settings put secure accessibility_enabled 1` + TalkBack on one machine DOES make the WebView expose fields (e.g. `passwordEntry`) — but TalkBack service is not installed farm-wide, so don't rely on it.



### `tap_text` substring-match trap (2026-08-05, hard-won)



`tap_text(adb, device, xml, "Có", "Yes")` used substring matching (`label in text`), so the **email node `susannemortimerabby9@hotmail.com` matched "co"** (inside `@hotmail.com`) and got tapped at `(540,528)` instead of the "Có" button at `(540,1629)` — keep-signed-in never dismissed, `LoginBlocked("Could not select Keep me signed in: Yes")` even though the button WAS in the dump. Fix: collect candidates, score `(exact_match, is_button)`, sort, tap best (exact Button > exact node > substring Button > substring). Vietnamese button text is `'Có'` (C + U+0301 combining acute) — `normalize_text` NFD-strips it to "co", so exact match compares normalized forms. Regression test: `test_tap_text_prefers_exact_button_over_email_substring`.



### Saved-password sheet ("Sử dụng mật khẩu đã lưu?" / "Use a saved password?")



Chrome remembers the old password for `login.live.com` and re-shows this sheet on EVERY fresh login (especially after the pipeline restarts VPN and reloads Chrome). It overlays the form even when no password field is exposed. Fixes in `flows/hotmail_login.py`:

- `ensure_target_login_form` now dismisses the sheet (Back key, verify gone, else `LOGIN_SAVED_PASSWORD_PROMPT_NOT_DISMISSED`) **before** the `if not password_node: return xml` early-return — previously the early return skipped the dismiss entirely.

- `has_saved_password_prompt` is text-based via `visible_flat_text`; on opaque dumps it cannot prove the sheet — acceptable, the sheet only blocks when it is exposed.

- Symptom when unhandled: pipeline ends `LOGIN_NOT_VERIFIED` (or `Could not identify Outlook password field`) while the machine sits on the saved-password sheet with the correct mail.



### Pipeline loop trap: VPN restart resurrects the saved-password sheet



`flows/hotmail_change_info.py` runs `gan_proxy_fleet` VPN setup on every invocation → Chrome reloads → saved-password sheet reappears → login fails again → pipeline writes `FINAL_BLOCKED` + leaves a `blocked` lock with a dead PID → next run's VPN step returns `SKIPPED_DEVICE_LOCKED`. The loop: clean stale lock → re-run → sheet again. Mitigations, in order of escalation:

- Deleted Chrome `Login Data` db would fix it but `/data/data/com.android.chrome` is not readable without root.

- Next options: run the pipeline with `--force-login` (explicitly logs out the existing Chrome session first), or clear Chrome app data (needs user approval — destructive).

- **`pm clear com.android.chrome` (user-approved 2026-08-05) DID break the loop** and got the pipeline past the sheet. Cost: Chrome first-run onboarding + no saved session + possible marketing-page redirect (see Fresh Chrome section below). This is the reliable breaker when saved-password keeps resurrecting.

- Lesson: when a Hotmail live pipeline fails repeatedly with the same UI signature, break the loop by removing the *state* that resurrects it (saved credential / session), not by re-running the same login.



### Fresh Chrome after `pm clear com.android.chrome` (2026-08-05, machine 30)



User approved clearing Chrome app data to kill the saved-password sheet / session loop. After `pm clear`:

- Chrome enters **FirstRunActivity** on next launch. Settings flags (`settings put global first_run_complete 1` etc.) do NOT skip it — it's stored in Chrome's own prefs. To pass it: the screen shows an animated "Xem thêm" (Learn more) `more_button` then a blue **"Tôi hiểu"** button (`[564,1728][1008,1872]`, tap ~`(786,1800)`). Pixel-scan for the blue button when opaque; both buttons ARE exposed in the dump on this screen.

- There is ALSO a second onboarding interstitial later: **"Quyền riêng tư nâng cao trong quảng cáo trên Chrome"** (Enhanced ad privacy) with buttons **"Xem thêm"** → **"Tôi hiểu"** (both exposed as `android.widget.Button`, last one ~`(786,1800)`). Dismissing it returns to the tab — it appeared right after first-run while the pipeline was mid-login.

- **`https://outlook.live.com/mail/0/inbox` WITHOUT `?nlp=1` redirects to the Microsoft 365 marketing page** (`microsoft.com/vi-vn/microsoft-365/outlook/...`, often 502 Bad Gateway under proxy). The flow's `OUTLOOK_URL` includes `?nlp=1` — that is what lands on the real `login.microsoftonline.com` form with `i0116` exposed. If you open the URL manually, use the `?nlp=1` variant.

- After `pm clear`, the first-run → marketing-page → login path is flaky; verify `active_chrome_url` after each step and re-open with `?nlp=1` when it lands on the marketing page.

- `pm clear` also drops the Chrome session, so the next pipeline run starts from a clean login form (no saved password, no SSO) — good for breaking the saved-password loop, but reauth/proof may be required again since the SSO session is gone.



### Security reauth proof screen (current blocker, 2026-08-05)



After login returns `ALREADY_SIGNED_IN`, change-password runs a **reauth** step. On a normal Hotmail the machine hits:



**"Xác minh danh tính của bạn"** on `login.live.com/login.srf?wa=wsignin1.0...` with:

- Target email shown, and **"Gửi email đến th\*\*\*\*\*@gmail.com"** — Microsoft sends the proof code to the account's **recovery email, which here is a Gmail** NOT the Hotmail being processed.

- Buttons: **"Tôi có một mã"** (I have a code) and **"Tôi không có bất kỳ thứ gì trong số này"** (I don't have any of these).

- Pipeline failure: `security_email_proof_screen_lost_before_submit`, `failure_signature: PASSWORD_CHANGE_FAILED`, state `FINAL_BLOCKED`. Evidence captures under `.ai-runs/.../security/reauth-proof-01-before.{xml,png}`.



The blocker is a **business decision, not a code bug**: to proceed you need either (a) access to that Gmail recovery mailbox to read the OTP (flow needs a step to fetch it), or (b) choose "Tôi không có bất kỳ thứ gì" and see where Microsoft routes (may hard-block). Recovery Gmail `th*****@gmail.com` — check whether it exists in the farm inventory before assuming access. DO NOT classify the mailbox DEAD over this; it's a protection gate, mail is alive.



**RESOLVED (2026-08-05, user confirmed):** the recovery Gmail `th*****@gmail.com` IS in inventory and its OTP is readable. The recovery Gmail is `thanhdatbui1995@gmail.com` — it is `DEFAULT_RECOVERY_EMAIL` in `flows/hotmail_recovery.py`, and the OTP reader is **`D:\Taadaa\add mail khoi phuc\read_otp_mail.py`** (IMAP poll, env `OTP_MAIL_USER` + `OTP_MAIL_APP_PASSWORD` — both already set in the shell; verify with `echo $OTP_MAIL_USER`). Test: `cd "/d/Taadaa/add mail khoi phuc" && OTP_LOOKBACK_SECONDS=604800 python read_otp_mail.py --once --verbose` → exit 1 = IMAP login OK but no new code in lookback window (not an auth error). Run the script (or `run_add_recovery.py`) with the OTP env AFTER Microsoft sends the code.



**OTP realtime flow (worked end-to-end 2026-08-05, machine 30):**

1. On the proof screen the email field is pre-filled with `thanhdatbui1995@gmail.com`; the blue **"Gửi mã"** button is at `(841,1316)` (pixel-scan: big blue band y≈1250-1370, x≈684-1007, centroid `(841,1316)`). Tap it.

2. Poll the recovery mailbox: `cd "/d/Taadaa/add mail khoi phuc" && OTP_SENDER_HINT="microsoft" OTP_LOOKBACK_SECONDS=1800 python read_otp_mail.py --once --verbose` → prints `CODE=<6digits> FROM=<...Microsoft...> SUBJECT=Mã bảo mật tài khoản Microsoft cá nhân`. Took ~25-40s for the mail to arrive in this run; retry a few times if exit 1.

3. Verify the phone has focus (IME `mInputShown=true`), type the code with `adb shell input text <code>`, then `input keyevent 66`.

4. Success → URL moves to `privacynotice.account.microsoft.com/notice` (privacy notice). Tap the blue "Tiếp tục" (~`(827,1733)`; blue band y≈1680-1780) → lands on **`account.live.com/password/change`**.

5. The privacy-notice screen may need 2 taps (first tap scrolls/re-renders, second submits); re-scan the blue band after each tap — `(827,1721)` was the working second tap.

- Quick mail check without OTP parse: read the last few IMAP subjects with a small inline script (From/Subject) to confirm Microsoft's code mail arrived.



**Technical root cause of `security_email_proof_screen_lost_before_submit`** (`flows/hotmail_security.py` ~1184-1216): the flow finds `proof-confirmation-email-input` (in `_EMAIL_PROOF_FIELD_IDS`), types `DEFAULT_RECOVERY_EMAIL`, calls `ime hide`, then re-dumps — and on opaque dumps the proof screen is GONE from the new dump (WebView re-rendered / focus lost), so line 1208 raises before the "Gửi mã" tap. On a real (non-opaque) dump this wouldn't happen; the fix path is to submit without requiring a fresh proof-screen dump after `ime hide` (tap "Gửi mã" from the pre-hide xml, or coordinate fallback on `login.live.com` + proof markers), then poll OTP via `read_otp_mail.py`.



**Opaque-farm identity verification on security pages** (`flows/hotmail_security.py`, 2026-08-05): `_verify_target_identity_before_logout` (used by change-password AND logout) requires an identity badge (`mectrl_currentaccount_secondary`/`identitybadge`/`bannertext`) or the account-menu tap (`O365_MainLink_Me`). On opaque dumps neither resolves → `password_change_target_identity_not_verified` then `password_change_target_identity_menu_not_dismissed`. Fix landed: `_proof_target_is_verified` has an opaque fallback — when `_ui_has_content(xml) is False` AND `_active_url(xml).endswith("/password/change")`, accept the URL proof (the page is only reachable through the verified target session; login already proved the inbox URL for this email). This mirrors the `inbox_matches_account` URL-proof pattern. ⚠ It still requires `_ui_has_content` to be genuinely False — a single stray Chrome/SystemUI text node flips it True and the fallback silently doesn't apply, which is why the SystemUI/`CHROME_CHROME_IDS` filters above matter.



### Outlook app login surfaces (live 2026-08-16, machines 38/54)



Adding a brand-new mailbox inside the Outlook app (4.2325.1 on farm S7) hits several surfaces the login flow must recognize — all discovered live:



- **First-run onboarding carousel** (fresh install / cleared data): slides vary ("Chào mừng bạn đến với Outlook", "Được kết nối và bảo vệ", calendar...). Identify by the CTA pair, NOT slide text: `btn_primary_button` "THÊM TÀI KHOẢN" + `btn_secondary_button` "TẠO TÀI KHOẢN MỚI" (`_outlook_app_onboarding_visible`). Tap primary → account-type selector.

- **Account-type selector** ("Chọn loại tài khoản", `ChooseAccountActivity`): normalize_text strips diacritics → match `"chon loai tai khoan"` (NOT `"chọn loại tài khoản"` — that string never matches). Tap the "Outlook" provider entry **by resource-id `btn_add_account_outlook`, NOT by text** (entry has NO accessible text — `tap_text("Outlook")` silently misses; use `_tap_outlook_app_add_account_entry`, center (540,576)). The same selector can appear mid-flow after tapping add-account; the email login form may then be **pre-filled with the previous email** → skip straight to password.

- **WebView password field** (Microsoft `AuthorizationActivity`): the password EditText has class **bare `EditText`**, NOT `android.widget.EditText` — `edit_nodes` must accept both (`node_class.endswith(".EditText") or node_class == "EditText"`), else `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`. Resource-id is `passwordEntry`. Field coordinate fallback when opaque: tap (540, ~980) for recovery/email inputs, type, dismiss keyboard with keyevent 4, then tap the blue "Tiếp theo" (~870, 1180).

- **Email-detail surface** (an opened message persisted across launches): no `messages_listview`/toolbar; detect via `conversations_recycler_view` + `message_view` (`_outlook_app_email_detail_visible`). Readers must `keyevent 4` back out to the folder surface BEFORE any inbox/identity gate, else `OUTLOOK_APP_INBOX_NOT_VERIFIED` fires on a fully signed-in app.

- **Drawer scrim trap**: `_close_outlook_app_drawer` tap (950,900) on weak S7 machines can land the app on **Archive** ("Không có gì trong Lưu trữ") instead of closing the drawer. Recover via the Archive empty-state CTA "ĐI ĐẾN HỘP THƯ ĐẾN" (`_outlook_app_open_inbox_from_archive`).



**`_outlook_app_account_present` MUST NOT assume single-mailbox** (bug fixed 2026-08-16): the old version returned `True` whenever the drawer was closed ("single-mailbox devices are the norm"), which made `login_outlook_app` report `ALREADY_SIGNED_IN` for a mailbox that was NOT in the app — the OTP reader then silently read the wrong inbox. User rule (2026-08-16): **login mail mới vào app khi đã có sẵn hotmail** — when the target mailbox is absent and a password is provided, `read_tiktok_otp_from_outlook_app` / `read_tiktok_magic_link_from_outlook_app` must call `login_outlook_app` to ADD the account (Outlook app only, never Chrome), then re-verify. The account-present check opens the drawer via `account_button`, verifies `drawer_header_summary` identity, closes the drawer (with Archive recovery), and returns the real result.



**How to CONFIRM the active mailbox (user-taught, 2026-08-16, machine 38):** open Outlook → tap the avatar/initial (chữ A) at the top-left → read the FIRST LINE at the TOP of the drawer — if it shows the target email, that mailbox is the ACTIVE one. Close the drawer → inbox shows. This is the human-verifiable proof; always state the visible top drawer line when reporting a login success (not just "drawer identity matches"). Encoded in script: `outlook_app_artifact_payload(..., drawer_top_line=...)` writes `_outlook_app_drawer_top_line(verified)` into the success artifact — the artifact JSON's `drawer_top_line` must equal the target email for a login to count as confirmed.



### ATX-agent primary UI dump/click trong login runner (2026-08-17, máy 31)



`flows/hotmail_login.py::ui_xml` giờ ATX-primary: JSON-RPC `dumpWindowHierarchy [true]` tới `/session/{pid}:com.github.uiautomator/jsonrpc/0` (pid từ `ps -A`) → fallback `capture_ui_xml` (persistent-first, guard xml rỗng) → exec-out uiautomator. atx fail KHÔNG raise — rơi xuống tầng sau. **`flows/login_outlook_one_machine.py` KHÔNG cần sửa**: ATX nằm trong `ui_xml`/helpers mà runner gọi. Chi tiết + test: `references/atx-primary-hotmail-login-20260817.md`.



- **`_atx_jsonrpc_call` chạy probe qua `AdbClient.shell` TRỰC TIẾP, KHÔNG qua `run_adb`** → test cũ mock `run_adb` (giả lập máy không-atx) vẫn pass KHÔNG cần monkeypatch None và vẫn validate đúng fallback shell. Mọi exception trong probe (kể cả adb thật fail vì serial ảo) → None. Đây là lệch với hướng dẫn cũ \"mọi test cần `_atx_capture_ui_xml = lambda: None`\" — chỉ bắt buộc khi atx-primary gọi automation_core THẬT qua cùng đường mock.

- **Màn \"Chọn loại tài khoản\": entry \"Outlook\" KHÔNG có text** — `tap_text(adb, device, xml, \"Outlook\")` KHÔNG land (root cause `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` máy 31). Fix: `_tap_outlook_app_add_account_entry` tap center node `btn_add_account_outlook` bounds [360,384][720,768] → (540,576) qua `_atx_input_tap`. Dùng cho CẢ 3 call-site account-type-selector trong `login_outlook_app` (onboarding, persisted surface, và nhánh thứ 3 sau drawer-add-account) — đừng để sót nhánh nào.

- Password field ẩn (S7 uiautomator OOM): `_atx_app_password_field_point` = password-typed EditText từ ATX dump, fallback (540,690) máy 31. **`_outlook_app_fill_password_and_finish`**: node visible → `type_text(sensitive=True)` (AdbKeyboard giữ cho máy uiautomator OK); node ẩn → ATX-tap field → `_atx_adb_text` (`input text`; ATX `setText` = UiObjectNotFound trên WebView) → keyevent 4 dismiss IME → tap \"Tiếp theo\" bằng text hoặc ATX (540,1011) máy 31 → xử lý mọi interstitial → verify drawer → ghi artifact. Trả False → caller raise `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` (giữ status cũ).

- Regression: `tests/test_atx_primary_ui.py` (module riêng: pid parse, JSON-RPC payload/errors, dump/tap helpers, password point, add-account entry, ui_xml ordering, fill-password ATX fallback, sensitive path).

- Pitfall edit: block ATX đặt TRƯỚC `class LoginBlocked` → NameError lúc import (forward reference); đặt sau class def — nhưng `LoginBlocked` ở giữa file (không phải đầu), đừng giả định vị trí.

- Pitfall edit khác: **thay block `if` lớn bằng patch multi-dòng dễ vỡ indentation** — khi `patch` báo lỗi 3 match hoặc indentation sai lệch, dedent bằng script (đọc file, sửa prefix 4-space theo line range, ghi lại) rồi verify `ast.parse` — KHÔNG vật lộn với nhiều patch nối tiếp.



### OTP-reader vs TikTok DOB screen race (reg path, machine 38, 2026-08-16)



When TikTok reg reads the OTP from the Outlook app and the code is valid, TikTok immediately advances to the DOB screen ("Ngày sinh của bạn là ngày nào?") — while the reader may still be typing the code, so the OTP digits get typed into the DOB date-picker field (`712503` visible inside the birthday field). Fix: after OTP entry + Enter, the flow must RE-CHECK the screen for the birthday screen BEFORE typing more digits; if the birthday screen is up, stop typing and call `fill_birthday` (it has fallback DOB 01/01/1999 when the workbook DOB is empty — machine 38's `augustus` row had no DOB and `fill_birthday(device_id, "", stt=...)` still succeeded). `fill_birthday` post-tap lands on the TikTok password screen — from there `fill_password_and_login` + `handle_post_auth_screens` + `wait_login_success` continue the reg. Use `--resume` (not restart) when the machine is mid-flow at the password screen: `social_reg_v1.py <stt> --resume --email <mail>`.



### "Hãy bảo vệ tài khoản của bạn" (account protection) in the Outlook APP path



Same protection gate as the Chrome reauth path, but hit while **adding a brand-new consumer mailbox inside the Outlook app** (machines 38/54, 2026-08-16): after correct email+password, Microsoft shows "Hãy bảo vệ tài khoản của bạn" asking for a recovery email. Current code raises `OUTLOOK_APP_ACCOUNT_PROTECTION_REQUIRED` and blocks — must instead:

1. Fill the recovery field (WebView underline input, tap ~(540,980), type) with `DEFAULT_RECOVERY_EMAIL` = **`thanhdatbui1995@gmail.com`** (user-confirmed 2026-08-16: "Điền mail kp là thanhdatbui1995@gmail.com"). Do NOT invent a sibling mailbox from the machine's source rows — the recovery mailbox must be the configured one, and it must be a DIFFERENT mailbox than the one being added.

2. Dismiss keyboard, tap blue "Tiếp theo" (~(870,1180)).

3. Microsoft sends a security code to `thanhdatbui1995@gmail.com` (Gmail) → poll with `D:\Taadaa\add mail khoi phuc\read_otp_mail.py` (`OTP_MAIL_USER`/`OTP_MAIL_APP_PASSWORD` env, `OTP_SENDER_HINT="microsoft"`), then enter the code.

- **IMAP hotmail basic auth is dead** (confirmed live 2026-08-16): `imaplib` login to `outlook.office365.com` / `imap-mail.outlook.com` with the plain hotmail password fails `AUTHENTICATE failed` / `Basic authentication is disabled.` — you CANNOT read the hotmail inbox OTP via IMAP with a normal password. The recovery OTP comes from the **Gmail** recovery mailbox via app password. When the user says "lấy otp từ script đọc imap", they mean `read_otp_mail.py` on the Gmail recovery mailbox, not IMAP on the hotmail itself.



### First-login interstitial screens (live 2026-08-16, machines 38/54/57/66) — all handled in `login_outlook_app` → `_outlook_app_finalize_new_account`



- **QuickNote modal** ("Ghi chú nhanh về tài khoản Microsoft của bạn", OneAuth WebView): OK button does NOT respond to a plain `input tap` — **swipe down first** (`input swipe 540 1200 540 400 400`) which reveals the real Microsoft-blue OK button (~(539,1703) portrait), THEN tap. Without the swipe the tap silently does nothing and the modal persists (user-confirmed: "Swipe xuống rồi bấm ok là qua"). Handlers: `_outlook_app_quick_note_visible` + `_handle_outlook_app_quick_note`.

- ⚠️ **QuickNote VARIANT WITHOUT the "Ghi chú nhanh" title (live machine 66, 2026-08-16, FIXED):** the same OneAuth privacy dialog can render with THREE sections ("Những nội dung quan trọng của bạn ở ngay đây" / "Quyền riêng tư của bạn là ưu tiên hàng đầu của chúng tôi" / "Bạn đang nắm quyền kiểm soát") + blue OK button but NO "ghi chu nhanh" title text. Without detection the OTP reader dies `OUTLOOK_APP_INBOX_NOT_REACHED_FROM_ARCHIVE` on an otherwise signed-in app. **FIX LANDED**: `_outlook_app_quick_note_visible` now returns True when ≥2 of the 3 normalized privacy-bullet markers are present — markers MUST keep the **`đ` letter**: `"nhung noi dung quan trong cua ban o ngay đay"`, `"quyen rieng tu cua ban la uu tien hang đau cua chung toi"`, `"ban đang nam quyen kiem soat"`. ⚠️ GOTCHA: `normalize_text` (NFD) strips diacritics but does NOT convert `đ`→`d` (đ has no combining char), so writing `"ngay day"` never matches the normalized `"ngay đay"` — always write the đ in markers. Dismissal is the same swipe-down + tap OK (`(539,1703)` fallback). This dialog also re-appears across relaunches until OK actually lands — force-stop + relaunch does NOT clear it (machine 66 needed the real OK tap at `(540,1705)`).
  - ⚠️⚠️ **REGRESSION WARNING (17/08 — Hotmail repo commit `5bd7d4a`): đổi 3 marker này `đ`→`d` là SAI.** Lý do lúc đó: thấy `normalize_text` strip dấu → tưởng `đ` cũng bị strip → marker có `đ` không match. SAI — NFD KHÔNG phân rã U+0111 (đ không có combining mark) → text normalize VẪN là `ngay đay`/`hang đau`/`dang nam` (chỉ các dấu khác bị strip). Marker viết `d` (thiếu `đ`) KHÔNG BAO GIỜ match → variant B (không có title) kẹt nút OK vô hạn. Gotcha máy 66 ghi sẵn đã cảnh báo đúng — đừng "sửa" marker đã verify live chỉ vì suy luận trên giấy. **ĐÃ REVERT 17/08 tối (commit `5fbf986`)** — marker quay lại `đ`; verify bằng `grep "ngay đay" flows/hotmail_login.py` trước khi chạy reg. Đừng lặp lại lần nữa.
  - **Màn "Inapp UnifiedConsent" (máy 75 18:06) = CHÍNH LÀ QuickNote variant, KHÔNG phải màn mới:** dump thật có title "Ghi chú nhanh về tài khoản Microsoft của bạn" + 3 bullets + nút OK center (540,1704) — `_outlook_app_quick_note_visible` match qua TITLE marker (không chứa `đ` nên không dính bug marker). Lý do kẹt THẬT: **`read_tiktok_magic_link_from_outlook_app` (nhánh READER) KHÔNG gọi `_outlook_app_finalize_new_account`** — hàm dismiss QuickNote chỉ chạy trong nhánh login/add-account (dòng ~2128-2170), reader mở app đụng modal → raise `OUTLOOK_APP_INBOX_NOT_VERIFIED`. KHÔNG cần detector riêng cho "UnifiedConsent" — nó là cùng modal. **FIX ĐÃ LANDED (17/08 tối):** (a) canonical reader CẢ OTP + magic-link: sau `open_outlook_app`, nếu `_outlook_app_quick_note_visible`/`_outlook_app_add_another_visible`/`_outlook_app_privacy_tour_visible` → gọi `_outlook_app_finalize_new_account` TRƯỚC vòng `wait_for(inbox/archive/folder/login)` (modal không match 4 state đó → wait timeout 60s → INBOX_NOT_VERIFIED; commit `aa3311c`); (b) helper Tiktok_Reg `_read_magic_link_with_inbox_recovery`: dismiss popup feedback → quick note → "Hộp thư đến" → mail TikTok mới nhất → ATX click nút Xác minh email (commits `fd378db` + `7fbe7f7`). ⚠️ **XML WebView có thể CHỈ expose label "Inapp UnifiedConsent" — title "Ghi chú nhanh" KHÔNG có trong text node** (dump 19:16 máy 75: TEXTS=['Inapp UnifiedConsent','60%','19:16']) → detection phải fallback marker `inapp unifiedconsent` (đã thêm vào `_outlook_app_quick_note_visible` canonical + recovery Tiktok_Reg) và nút OK tap theo TỌA ĐỘ ẢNH (540,1704) qua `_atx_click` — không dựa text "OK" nếu dump rỗng.

- **AddAnotherAccountActivity** ("Thêm một tài khoản khác?", buttons "CÓ LẼ ĐỂ SAU"/"THÊM"): after successful new-mailbox login the app asks whether to add another account. Tap "CÓ LẼ ĐỂ SAU" (bottom-left ~(300,1770)) to reach the inbox. Handlers: `_outlook_app_add_another_visible` + `_handle_outlook_app_add_another`.

- **PrivacyTourActivity** (multi-slide "Dữ liệu của bạn, theo cách của bạn" → "Cùng nhau cải thiện" → "Nâng tầm trải nghiệm của bạn"): decline diagnostics (TỪ CHỐI ~(540,1760)), tap TIẾP THEO / TIẾP TỤC VỚI OUTLOOK (~(825,1830)) until folder surface. Handlers: `_outlook_app_privacy_tour_visible` + `_handle_outlook_app_privacy_tour`.

- **WebView action-button coordinates (1080x1920 portrait)**: code-entry screen ("Nhập mã") button ≈ **(778,528)**; recovery-email screen ("Hãy bảo vệ") ≈ **(870,1180)**. `_tap_outlook_app_action_button` branches on screen text.

- **`input tap` often does NOT register on Microsoft WebView buttons — `keyevent 66` (Enter) DOES** after focusing the field (worked on machines 54/38 for both recovery-email submit and code submit). When a WebView button ignores taps, tap the field then press Enter.

- ⚠️ **`_atx_click`/ATX JSON-RPC trong social_reg_v1: adb FORWARD phải chạy trên adb HOST, KHÔNG qua `shell()`** (bug thật máy 75, 2026-08-17, fix commit `cf054c7`): `shell(device_id, "forward", ...)` = `adb -s <dev> exec-out forward` → CHẠY TRÊN THIẾT BỊ → `/system/bin/sh: forward: not found` → forward không tồn tại → HTTP tới `127.0.0.1:7912` → `WinError 10061 connection refused` → ATX click fail ÂM THẦM (log `[atx-click] failed`, `[adb warn] /system/bin/sh: forward: not found`, `capture-mode skip: ... quicknote_<serial>.png` không tạo được). Fix đúng: `subprocess.run([ADB_EXE, "-s", device_id, "forward", "tcp:7912", "tcp:7912"], capture_output=True, timeout=30)` (lệnh adb host). Triệu chứng dễ lừa: `_atx_click` trả False nhưng script vẫn chạy tiếp các bước khác → tưởng lỗi màn hình, thật ra là forward chết. Verify bằng 1 click thử rồi kiểm tra result True. (Lưu ý thêm: capture-mode `os.system(... 2>nul)` KHÔNG tạo file trong bash — dùng `2>/dev/null`; `os` đã import dòng 21.)

- **Password-field render race**: after tapping "Outlook" on the account-type selector, `outlook_app_password_visible` can return True while `choose_password_node(edit_nodes(xml))` still returns None (WebView field renders later than the dump). Fix: `_outlook_app_password_node_with_retry` re-dumps up to 5× (0.8s apart) before failing. Use it at EVERY password-node resolution site in the login flow.

- **Screenshot resolution trap**: the vision model reports WRONG pixel sizes (says 720x1280 when PNG is 1080x1920, or misses landscape). ALWAYS verify with `wm size` + PIL `im.size` before computing tap coordinates; landscape flips all coordinates.

- **`open_outlook_app` force-stops nothing — Chrome can keep foreground**: after adb dropouts, launching Outlook via monkey/MAIN may leave Chrome on top → `LOGIN_FORM_NOT_IDENTIFIED`. Force-stop `com.android.chrome` + `com.microsoft.office.outlook` first, then launch, then verify `mResumedActivity` is Outlook.

- **adb dropouts kill the device mid-run**: `wm user-rotation lock` and long shell batches can drop the serial; wait and re-query `adb devices` before continuing — do not assume the device vanished.



**NO-ROTATION GUARD (user rule 2026-08-16 — user is FURIOUS about auto-rotate):** never allow any component to enable auto-rotate / landscape. Before ANY app launch: `settings put system accelerometer_rotation 0` + `settings put system user_rotation 0` + `wm user-rotation lock 0`. `prepare_device(lock_rotation=True)` can flip `accelerometer_rotation` back to 1 on Samsung builds — the runner (`flows/login_outlook_one_machine.py`) re-asserts all three after the lock. Do NOT rely on a single settings write; re-assert before every run and verify with `settings get system accelerometer_rotation` (must be 0) + PIL image size (must be portrait).



### ⚠️ AdbKeyboard IME bắt buộc cho password input (batch fail 2026-08-17, máy 75-80)



- **Triệu chứng:** máy mới chạy login fail `BLOCKED AdbKeyboard IME is unavailable; refusing unsafe password input` — `type_text(sensitive=True)` (dòng 616-636 `flows/hotmail_login.py`) check `ime list -s` có `com.github.uiautomator/.AdbKeyboard` không; máy xiaowei mới CHƯA cài → từ chối nhập pass an toàn. (Máy cũ như 31 đã có sẵn.)

- **Fix:** pull APK từ máy đã có: `adb -s <co-may> pull "/data/app/com.github.uiautomator-*/base.apk" C:\\Users\\Kibe\\tmp\\adbkeyboard.apk` → push tới máy mới `/data/local/tmp/adbkeyboard.apk` → `pm install -r -d` → **`adb shell ime enable com.github.uiautomator/.AdbKeyboard`**.

- ⚠️ **Cài APK xong CHƯA ĐỦ — phải `ime enable`:** `ime list -s` chỉ liệt kê IME ĐÃ ENABLE; `ime list -a -s` liệt kê TẤT CẢ (kể cả chưa enable). Flow check `ime list -s`, nên IME chưa enable vẫn fail `refusing unsafe password input` dù package đã cài.

- Verify chuẩn: `ime list -s | grep AdbKeyboard` (case-sensitive "AdbKeyboard", KHÔNG lowercase "adbkeyboard" → 0 match đánh lừa).

- S7 `pm install -r -d` RẤT chậm (lệnh đầu timeout 300s) — đừng tin lệnh install trả nhanh; verify bằng `pm list packages | grep uiautomator`.



**⚠️ OTP is SHARED across machines — RUN ONE MACHINE AT A TIME (user rule 2026-08-16):** the recovery mailbox `thanhdatbui1995@gmail.com` receives OTPs for EVERY machine being added. `read_otp_mail.py` reads the LATEST code in the mailbox — running machine B while machine A's OTP is still unread returns A's code, and entering it on B fails (or worse, enters a valid code for the wrong account). Therefore: NEVER run the account-protection flow in parallel; start machine N's protection → wait for its OTP → enter it → verify inbox → only THEN start machine N+1. Any tap/OTP-enter done by hand during development must be immediately encoded into the script (user rule: mọi bước đều phải handle lại script, không làm tay).



### Test-mock detail for `run_adb`



`run_adb(adb, device, *args)` — a mocked call's `args` is `(adb, device, 'input', 'tap', x, y)`. Filter taps with `c.args[2] == "input"` and the slice `tuple(c.args[2:])` includes `'input'`. Also: `patch(..., side_effect="SUCCESS")` on a string iterates characters — wrap non-exception returns in a `def _fake(*a, **k): return value` when a function needs to raise or return a plain value.

- **Stale device lock blocks the VPN step**: `gan_proxy_fleet.py run` returns `SKIPPED_DEVICE_LOCKED` (and the change-info pipeline then fails `VPN_PROVIDER_RESULT_NOT_VERIFIED`) when a lock file exists even with a dead PID. Clean stale locks first (tasklist confirms PID dead → delete `machine_<n>.lock.json` + `serial_<serial>.lock.json`), then re-run.

- **RecentsActivity stuck over Chrome** (Samsung OneUI): `dumpsys activity top` shows `DecorView@...[RecentsActivity]` + `button_cancel`/`button_done` while `mResumedActivity` says Chrome; Back/HOME don't dismiss. Fix: `am force-stop com.sec.android.app.launcher` → HOME → re-open Chrome via `am start -a android.intent.action.VIEW -p com.android.chrome -d <url>`, then re-run.

- Farm machines frequently sit in TikTok `SplashActivity` / `SAASceneWrapperActivity`; the login flow opens Chrome over them fine, but check `mResumedActivity` before assuming a clean start.

- Pipeline may hit `LOGIN_BLOCKED` mid-login on a machine whose Chrome session holds a different account; `--force-login` is the explicit escape hatch (logs out existing Chrome session first).



### Magic-link reader pitfalls (live máy 75, 2026-08-17)



`read_tiktok_magic_link_from_outlook_app` (canonical `flows/hotmail_login.py`) used by TikTok reg khi TikTok tự đổi OTP→magic-link ("Kiểm tra hộp thư" — màn không có field nhập mã, chỉ nút "Gửi lại email"):



- **Reader RAISE `LoginBlocked` thay vì trả None** — `OUTLOOK_APP_INBOX_NOT_VERIFIED` khi app mở ở folder surface (sidebar) thay vì active Inbox; `OUTLOOK_APP_INBOX_LOST_DURING_MAGIC_LINK_READ` khi mở được mail nhưng không tap được link. Mọi caller có pattern `code = reader(...); if not code: recovery` sẽ KHÔNG BAO GIỜ chạy recovery — phải bọc try/except quanh lời gọi.

- **Reader CÓ THỂ TREO VÔ HẠN (blocking)** — máy 75 kẹt 1.5h: mở đúng mail TikTok (nút đỏ hiện) nhưng không tap, không return, không raise → mọi fallback sau lời gọi vô nghĩa. **Fix 2026-08-17 (commit `7ef6685` + `9bea46c`):** đảo thứ tự — helper `_read_magic_link_with_inbox_recovery` tap nút "Xác minh email" TRƯỚC bằng **`_atx_find_click` (JSON-RPC atx-agent click THẬT)**, reader canonical chỉ gọi cuối cùng khi không tap được nút. ⚠️ KHÔNG dùng `find_text_tap` cho nút này (nó gọi `tap()` = `shell input tap`, không ăn WebView — log "✓ tap nút 'Xác minh email' (ATX)" hồi đầu là nhãn SAI vì thực tế gửi input tap shell). Verify live: `✓ [atx-find-click] (539,1631) → atx-click=True` → foreground chuyển TikTok.\n- **Magic link trong mail = nút ĐỎ "[Xác minh email]"** (node `resource-id="link"` clickable, content-desc "Xác minh email", KHÔNG phải link text trong body). ⚠️⚠️ **TRAP MATCH SUBJECT (máy 75 fresh10, fix commit `a314d5b`):** `_atx_find_click("Xác minh email", "Xac minh email", "Verify email")` tìm theo TEXT substring → match nhầm node SUBJECT mail "Hoàn tất đăng ký bằng cách xác minh email của bạn" (clickable=False, center (912,299)) → ATX click trả result True (UiAutomator click "thành công") nhưng KHÔNG mở app — tap nhầm → fail-closed "Magic-link chưa được bấm". **Fix: helper `_atx_click_link_button(device_id)` parse XML tìm node `resource-id="link"` + `clickable="true"` + desc chứa 'xac minh' → ATX click center (portrait (539,1463))** — TUYỆT ĐỐI không dùng find-by-text cho nút này. Phân biệt thêm: node TEXT tiêu đề "Xác minh email của bạn" (clickable=False, bounds khác) — tap nhầm không ăn. ⚠️ **Khi WebView không expose XML node `link` (máy 75, commit `67443c8`):** Fallback bấm trực tiếp vào tọa độ trung tâm nút đỏ `(540, 1460)` qua ATX JSON-RPC.
- **Phương án Graph API Deeplink Intent (Verified 22:34):** Thay vì bấm nút trên WebView, lấy deeplink URL qua `read_tiktok_magic_link_from_graph_token` -> `am start -a VIEW -d "<url>"` -> Android hiện Resolver dialog "Mở bằng" -> Tap **"CHỈ MỘT LẦN"** tại `(570, 1818)` -> TikTok mở thẳng và loading xác thực token.
- ⚠️ **QUY TẮC SỐNG CÒN CỦA TIKTOK MAGIC LINK SESSION (Live finding 22:53 máy 75):**
  - **CẤM TUYỆT ĐỐI force-stop (`am force-stop`) hoặc đóng recent app TikTok khi đang chờ magic link**: TikTok lưu session ID / registration auth state trong bộ nhớ tiến trình (RAM). Nếu app bị force-stop trước khi mở magic link (qua Chrome hoặc deeplink intent), phiên xác thực bị đứt -> TikTok mở lên báo lỗi bảo mật thiết bị: *"Đã xảy ra lỗi. Hãy đảm bảo sử dụng cùng thiết bị bạn đã sử dụng để gửi email xác minh."* (`TransparentCodeVerificationActivity`).
  - **Quy trình đúng**: Giữ nguyên ứng dụng TikTok ở màn hình *"Kiểm tra hộp thư của bạn"* (chạy ngầm), mở Outlook bấm link hoặc gọi intent deeplink để TikTok đang giữ session nhận intent và chuyển tiếp sang màn hoàn tất đăng ký (DOB / Password / Profile).\n- **`adb input tap` tọa độ KHÔNG ăn trên nút WebView trong Reading Pane** (Outlook intercept). ⚠️ KHÔNG NHẦM `find_text_tap`/`tap()` với ATX click: `tap(device_id,x,y)` = `shell input tap` (adb shell), KHÔNG phải ATX JSON-RPC — máy 75 kẹt hàng giờ vì log \"✓ tap nút Xác minh email (ATX)\" là nhãn SAI (thực tế gửi input tap shell → không ăn → vòng lặp). **ATX click THẬT = JSON-RPC trực tiếp** (user nhắc 2026-08-17: \"dùng atx trc r mà\", CẤM đề xuất uiautomator click — chỉ fallback):\n```python\nimport requests\nBASE = f\"http://127.0.0.1:7912/session/{pid}:com.github.uiautomator/jsonrpc/0\"  # pid từ `adb shell ps -A | grep com.github.uiautomator`\nr = requests.post(BASE, json={\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"click\",\"params\":[x,y]}, timeout=30).json()\n# r[\"result\"] == True → tap THẬT qua UiAutomator, ăn được nút link WebView\n```\n  Verified máy 75 (16:04): ATX click (539,1631) → `result True` → foreground Outlook → TikTok `SignUpOrLoginActivity`. Node nút link: `resource-id=\"link\"` class=`android.view.View` `clickable=\"true\"` content-desc=\"Xác minh email\" bounds (97,1565)-(982,1697) center (539,1631). ⚠️ Phân biệt node TextView tiêu đề \"Xác minh email của bạn\" (~(539,1175), clickable=false) — tap nhầm không ăn.

- **Recovery sequence đã encode** (`_read_magic_link_with_inbox_recovery` trong social_reg): mở app → tap "Hộp thư đến" (drawer item, desc "Hộp thư đến,Đã chọn", rid `drawer_item_title`, badge "Hộp thư đến (1)") → reader lần 2 → fallback tap nút Xác minh email.
- **CHỈ DÙNG MAIL TIKTOK MỚI NHẤT (user hướng dẫn "1", commit `92a181c`):** KHÔNG tap nút "Xác minh email" bừa ngay khi vừa mở Outlook — app có thể restore MAIL CŨ (vd 12:28/13:22) với link ĐÃ HẾT HẠN (~20 phút) → tap nút link chết = fail vô nghĩa, kẹt vòng lặp. Thứ tự chuẩn helper hiện tại: mở app → dismiss popup feedback → "Hộp thư đến" → mở mail TikTok MỚI NHẤT (item đầu list — Outlook sort newest-first) → ATX click nút Xác minh email → chỉ gọi canonical reader cuối cùng. Muốn mail chắc chắn tươi: tap "Gửi lại email" trên màn TikTok magic link (caller [7c]/[8b] đã làm) rồi mới đọc. ⚠️ **Popup feedback Outlook "Chúng tôi muốn lắng nghe phản hồi của bạn" (nút "KHÔNG, CẢM ƠN") chặn ĐẦU list Hộp thư đến** — tap mail TikTok không ăn, reader treo (máy 75 15:30). PHẢI dismiss ("KHÔNG, CẢM ƠN"/"Khong, cam on"/"No thanks") TRƯỚC khi tìm mail TikTok (commit f1d64a3).\n- **Mở URL magic-link bằng `am start -a VIEW` → ResolverActivity "Mở bằng" (TikTok / Samsung Internet)** — phải tap entry TikTok + "CHỈ MỘT LẦN" mới mở được CommonFlowActivity; mở Chrome KHÔNG xác nhận đăng ký (false positive "đã rời màn" vì Chrome chiếm foreground; dump non-TikTok ≠ thành công). Sau khi mở trong app: nếu link hết hạn → màn "Nhập mã 6 chữ số" + "Cuộc hội thoại đã hết hạn"; nếu còn hạn → màn Tạo tài khoản email form (field pre-filled) → tiếp tục flow.\n- **Sau khi tap nút Xác minh email thành công, foreground chuyển TikTok NHƯNG có thể về màn "Tạo tài khoản" nhập email** (email pre-filled đầy đủ — verify bằng dump XML, OCR cắt chữ đầu) chứ KHÔNG phải màn verified — link mở app nhưng TikTok chưa tự đánh dấu mail verified; cần tiếp tục bước đăng ký (đặt password...) như flow bình thường.
- **GUEST-FEED TRAP (máy 75 18:20):** feed TikTok đầy đủ tab (Trang chủ/Cửa hàng/Hộp thư/Hồ sơ) + video chạy KHÔNG chứng minh đã đăng nhập — đó có thể là feed khách. Proof thật: tap tab Hồ sơ KHÔNG ra popup login. Triệu chứng lừa: `[8b] Đã vào màn chính` + `login-success success UI proof` xanh rồi `[02_profile]` fail vì tab Hồ sơ chạm ra login sheet ("Số điện thoại" + "Tiếp tục với email/tên người dùng" + "Tạo tài khoản" = `I18nSignUpActivity`). Khi đó reg CHƯA xong — phải tap "Tiếp tục với email/tên người dùng" → gõ email → gửi link MỚI → ATX click nút Xác minh email → verify thật (login popup biến mất) mới tính success.
- ⚠️ **WORKFLOW CHỐT (user 2026-08-17 19:2x, máy 75): CẤM TUYỆT ĐỐI tự mở TikTok khi foreground không phải TikTok.** "Khi vào outlook tìm đc đúng mail ms nhất của tiktok bấm vào xác minh email, nếu bấm chính xác đúng thì nó TỰ mở app tiktok — mày k đc tự mở mà chỉ khi bấm đúng link đó sẽ tự mở app". Lỗi cũ: `wait_login_success` có 2 chỗ `monkey -p com.ss.android.ugc.trill` auto-resume (đầu vòng + giữa vòng "TikTok chưa foreground, resume...") → nhảy thẳng sang TikTok KHÔNG qua verify → màn "Nhập mật khẩu"/login sheet thay vì vào acc. **FIX (commit `ed459d0`):** non-TikTok foreground → save_ui_xml + screenshot + raise RuntimeError FAIL-CLOSED ("Magic-link chưa được bấm — không tự mở TikTok"). Trình tự đúng: màn magic-link TikTok → (tap "Gửi lại email" cho mail tươi) → mở Outlook → dismiss popup feedback → dismiss quick note → "Hộp thư đến" → mở MAIL TIKTOK MỚI NHẤT → ATX click nút "Xác minh email" → link TỰ mở TikTok → mới được coi là verify.
- **UI_XML_TIMEOUT / `uiautomator_null_root_node` transient (máy 75 18:19, fresh7):** atx dump trả null root + fallback uiautomator cũng fail → `STOPPED: [adb-timeout] UI_XML_TIMEOUT` ngay bước Open app. atx-agent + uiautomator process VẪN SỐNG + port 7912 LISTEN — service kẹt tạm, KHÔNG cần restart gì (kill process bị `Operation not permitted` — đừng cố, cũng đừng restart adb = CẤM). Retry/resume chạy lại sau vài phút tự hồi phục (verify: `ps -A | grep com.github.uiautomator` + test dump lấy XML len > 0). Đừng đổ lỗi thiếu atx-agent khi process sống — đây là kẹt service nhất thời.

- Mail magic-link subject KHÔNG chứa "tiktok" ("Hoàn tất đăng ký bằng cách xác minh email của bạn") → marker lọc không dấu loại mail. Thêm marker CÓ DẤU ("hoàn tất đăng ký", "xác minh email của bạn", "kiểm tra hộp thư", "nhấp vào liên kết"). ⚠️ `normalize_text` strip dấu TIẾNG VIỆT (NFD) nhưng **KHÔNG đổi `đ`→`d`** (U+0111 không có combining mark) — mọi marker phải giữ nguyên `đ` (xem gotcha QuickNote máy 66; đừng lặp lại regression 5bd7d4a). URL chỉ có trong **href HTML** (`ucenter_web/deeplink/email_verification?...code=<uuid>`), `_strip_html` bỏ thẻ `<a>` → regex từ raw HTML.\n- ⚠️ **PITFALL PATCH LỆCH INDENT NUỐT MẤT `else:` (máy 75 resume37-38, fix commit `c52832a`):** khi thêm nhánh fallback \"nếu KHÔNG thấy X → back về folder list\" bằng patch multi-dòng, block bị đặt TRONG nhánh `if` (mất `else:`) → fallback KHÔNG BAO GIỜ chạy đúng lúc cần — log chỉ thấy `✗ Không thấy: Hộp thư đến` rồi nhảy thẳng canonical reader (không có dòng \"back về folder list\"). Triệu chứng nhận diện: log thiếu dòng log của nhánh else dù điều kiện else chắc chắn xảy ra. Cách sửa đáng tin: đọc file → chèn `else:` đúng indent (8-space, thẳng hàng `if`) bằng python line-index + `py_compile`/`ast.parse` verify — KHÔNG patch fuzzy nối tiếp (nhiều lần trượt). Verify cấu trúc bằng read_file quanh vùng sửa: `if` body → `else:` → body else đúng indent. 
- ⚠️ **OUTLOOK MỞ SẴN MAIL DETAIL (state cũ) khi [7c] bắt đầu → LẠC NHÁNH OTP GRAPH (máy 75 fresh9, 2026-08-17, fix commit `7130fe7`):** `handle_tiktok_email_otp` đọc `otp_flat` từ màn HIỆN TẠI — nếu Outlook restore mail cũ (subject \"Hoàn tất đăng ký bằng cách xác minh email của bạn\") thì text này KHÔNG match magic_markers cũ (`dang ky bang lien ket` ≠ `dang ky bang cach...`) và cũng không match numeric → `prefer_magic_link=False` → nhánh else \"Non-Gmail target -> read via Outlook app\" → thử OTP Graph 2 lần (~13 phút) → fail `[7c] Không lấy được OTP`. **Fix: magic_markers phải có thêm subject mail** `xac minh email` / `hoan tat dang ky` / `complete registration` / `verify your email` — mặt khác [7c] cũng bị fail vì mail-detail state không có \"Hộp thư đến\". **Back về folder list khi không thấy \"Hộp thư đến\"** (keyevent 4 từ mail detail; xem atx skill: BACK lần 1 từ mail-detail = về folder list, đừng nhầm với \"BACK thoát app\" ở surface khác) → tìm \"Hộp thư đến\" lại → mở mail TikTok MỚI NHẤT → ATX click nút Xác minh email.

- Link hết hạn ~20 phút (mail ghi "Liên kết có hiệu lực trong 20 phút") → khi hết: "Cuộc hội thoại đã hết hạn" + màn "Nhập mã 6 chữ số" → chạy lại reg từ đầu lấy mail mới.

- Mở URL magic-link bằng `am start -a VIEW` mở Resolver "Mở bằng" (TikTok/Samsung Internet) — chọn TikTok + "CHỈ MỘT LẦN" → CommonFlowActivity; mở Chrome KHÔNG xác nhận được (false positive "đã rời màn" vì Chrome chiếm foreground). Chi tiết: skill `tiktok-reg-hotmail-outlook-flow` §Magic-link flow + `references/magic-link-flow-20260817.md`.



## List runner + gmail_clean_v2 token column (2026-08-17)

- **PHÂN BIỆT MÀN MAGIC-LINK vs MÀN OTP (user yêu cầu encode 2026-08-17, commit `47a5c54`):** đối chiếu XML thật (dump 16:48 máy 75 màn magic + ảnh 15:04 màn OTP sau khi mở link):

  | | **MAGIC LINK** | **OTP** |
  |---|---|---|
  | Text có | `kiem tra hop thu` • `dang ky bang lien ket` • `lien ket duoc gui` • nút **`gui lai email`** | `nhap ma gom 6 chu so` • **`gui lai ma`** • `resend code` • 6 ô vuông + bàn phím số |
  | Không có | ô nhập mã, bàn phím số | `kiem tra hop thu`, `lien ket` |

  ⚠️ **`gui lai EMAIL` ≠ `gui lai MA`** — chữ "email" không match `gui lai ma` (marker chống nhầm #1). Encode: `_post_auth_ui_state` check magic markers TRƯỚC `otp_required` → state mới `magic_link`; call site `fallback_state in ("otp_required", "magic_link")` → `handle_tiktok_email_otp` (tự prefer magic-link). Trước fix: màn magic bị vào nhánh `[7c] Lấy OTP TikTok từ inbox` → Graph không có mã số → resend → fallback reader treo → `STOPPED: Không lấy được OTP`. (Lưu ý: màn magic-link KHÔNG có state riêng trong `_post_auth_ui_state` nên `[8b]` xử lý bằng marker `kiem tra hop thu` trực tiếp — xem phần magic-link reader pitfalls.)

- **Màn "Inapp UnifiedConsent" Microsoft (máy 75 18:06):** XEM BULLET Ở TRÊN — đây CHÍNH LÀ QuickNote variant (title "Ghi chú nhanh về tài khoản Microsoft của bạn" + 3 bullets + nút OK center (540,1704)), KHÔNG phải màn mới. Root cause kẹt = reader path không dismiss QuickNote + marker `đ→d` regression (commit 5bd7d4a, cần revert). KHÔNG cần detector riêng.

- **MÀN LOGIN POPUP vs TERMS_CONSENT (user hướng dẫn 2026-08-17, commit `baa4173`):** popup đăng nhập TikTok (bottom sheet: "Số điện thoại" + "Đăng nhập" + "Tiếp tục với email/tên người dùng" + "Tạo tài khoản", activity `I18nSignUpActivity`) có FOOTER chứa "Điều khoản Dịch vụ" + "Bằng việc tiếp tục..." → `_post_auth_ui_state` match `"dieu khoan dich vu"`+`"bang viec tiep tuc"` → trả `terms_consent` SAI → script PENDING (màn này script không tự tap theo rule) trong khi thực tế cần tap "Tiếp tục với email" để tiếp tục reg. **Fix: state `login_popup` check TRƯỚC `terms_consent`** — markers `so dien thoai` / `tiep tuc voi email` / `continue with email` / `dang nhap bang so dien thoai` / `tao tai khoan` (kèm `APP_PACKAGE`). Xử lý ở 2 call site: `[8b]` handle_post_auth_screens (tap "Tiếp tục với email" → continue loop) + login_fallback (tap xong → return `registration_entry`). Màn terms_consent THẬT (sau khi đăng ký xong, "Điều khoản dịch vụ" + "Đồng ý và tiếp tục") vẫn giữ nguyên — không match login markers nên không bị nhầm ngược.

- ⚠️ **MÀN "EMAIL HOẶC TIKTOK ID" (email login form) — marker `tao tai khoan` GÂY NHẦM LẪN (user phạt 2026-08-17):** màn nhập email đăng nhập ("Email hoặc TikTok ID" + nút "Đăng nhập" + nút "Tạo tài khoản" ở dưới) CŨNG có text "Tạo tài khoản" → nếu `login_popup` markers bao gồm `tao tai khoan` thì màn này bị classify thành `login_popup` → script tìm nút "Tiếp tục với email" (không có trên màn này) → dừng sai. **Fix: bỏ `tao tai khoan` khỏi `login_popup` markers + thêm state `email_login_form` check TRƯỚC** (markers `email hoac tiktok id` / `email or tiktok id` / `tiktok id`). Đồng thời: **script ĐÃ CÓ handler cho màn này** (`email_form_markers` ~dòng 2615-2638 trong social_reg — gõ email + tap Đăng nhập) — KHÔNG thêm handler trùng lặp ở `[8b]` (agent từng thêm rồi bị user bắt revert vì "script log in bth r mày lại bắt đầu chế phá" — chế nhánh mới khi script đã xử lý = vi phạm rule CẤM tự sửa giữa live run). Khi nghi ngờ script thiếu handler, grep marker cũ trước khi thêm mới.



- **`scripts/hotmail_list_runner.py`** — login NHIỀU hotmail từ file TXT nguồn `mail|pass|refresh_token|client_id` (mặc định đọc file cố định `D:\Taadaa\Hotmail\hotmail_input.txt`), tuần tự 1 acc/lần (OTP shared), mỗi acc map 1 máy qua `--machine-map "75:mailA,76:mailB,..."` (hoặc `--machine-override`, `--serial`). SUCCESS hoặc `ALREADY_SIGNED_IN` → append row vào `gmail_clean_v2.xlsx` (kèm token) + **xoá acc khỏi TXT nguồn** (`--keep-tokens` giữ lại); BLOCKED/ERROR → giữ trong TXT + report. `--dry-run` xem plan trước. Chạy: `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe scripts/hotmail_list_runner.py [--list hotmail_input.txt] --machine-map ...`.
- **Khóa thiết bị khi chạy batch theo lệnh user:** Khi user chỉ đạo lock máy tránh bị tiến trình khác can thiệp, sử dụng `automation_core.device_lock.acquire_device_lock(machine=m, serial=s, project='hotmail-login', user_authorized=True, bypass_proxy_readiness=True)` tạo lock trong `C:\Users\Kibe\.codex\device-locks` để bảo vệ phiên làm việc.
- **Xử lý khi Microsoft báo sai mật khẩu (Stop Gate & Chống báo nhầm, 2026-08-20/21):**
  - **Chống báo nhầm sai mật khẩu (False Attribution Trap 2026-08-21):** Trước commit `871e1b6`, script không có detector `has_wrong_password_prompt` mà chỉ có `wait_for` chờ Inbox/Privacy -> khi WebView bị delay, màn hình "Chọn loại tài khoản" xuất hiện hoặc timeout, script văng `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` / `INBOX_NOT_REACHED` dẫn đến kết luận nhầm là "sai mật khẩu" và đi báo shop.
  - **ĐIỀU KIỆN DUY NHẤT ĐỂ KẾT LUẬN SAI MẬT KHẨU (Báo Shop):** BẮT BUỘC màn hình Microsoft xuất hiện chuỗi cảnh báo đỏ thật sự: `! Mật khẩu đó không đúng với tài khoản Microsoft của bạn.` (hoặc `That password is incorrect` / `Your account or password is incorrect`).
  - **Đã encode vào `flows/hotmail_login.py`:** Hằng số `WRONG_PASSWORD_MARKERS` (đã hỗ trợ NFD `đ` và `d`) + hàm `has_wrong_password_prompt(xml)`. `wait_for` thoát sớm ngay khi thấy marker sai pass và raise `LoginBlocked("OUTLOOK_APP_WRONG_PASSWORD")`. Nếu màn hình chỉ bị trắng, loading, kẹt nút bấm hay timeout thì TUYỆT ĐỐI KHÔNG BÁO SAI PASS mà phải xử lý UI/proxy.
  - **Khi gặp lỗi sai pass thật:** Tuân thủ nghiêm ngặt STOP GATE: chụp ảnh màn hình lỗi thật, gửi bằng chứng `MEDIA:<path>` cho user, giữ nguyên hiện trường trên máy, tuyệt đối không tự ý thử lại hay đoán mật khẩu.

- **Quy tắc chọn máy nạp Hotmail (2026-08-18):**
  1. Chỉ chọn máy **Online (`adb devices`) + CÓ PROXY HỢP LỆ** trong `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (chú ý: máy 78 và 80 proxy rỗng/None → CẤM log).
  2. Sắp xếp ưu tiên các máy có ít account TikTok nhất (đối chiếu `taikhoan_dat_v2_updated .xlsx` sheet `Tài Khoản`), sau đó đến ít mail trong `gmail_clean_v2.xlsx`.
  3. Kiểm tra mạng VPN/tun0 trước khi chạy: nếu mạng proxy chết, Outlook sẽ hiện toast lỗi *"Hiện không thể thêm tài khoản này."* khi bấm Tiếp tục.
  4. **Phân biệt chính xác các trạng thái Login Hotmail trên Outlook App & Báo cáo Shop (20/08):**
     - **Lỗi sai mật khẩu thật (Báo Shop):** Sau khi submit password, màn hình Microsoft hiện cảnh báo đỏ: `! Mật khẩu đó không đúng với tài khoản Microsoft của bạn.` -> Chỉ những tài khoản này mới tính là lỗi sai pass để báo shop bảo hành.
     - **Định dạng báo shop bảo hành:** Khi gửi danh sách lỗi cho user gửi shop, CHỈ gửi dạng `email|password` cực gọn, KHÔNG kèm chuỗi Token hay Client ID dài dòng.
     - **Lỗi Toast *"Hiện không thể thêm tài khoản này."*:** Xuất hiện ngay ở bước nhập email (chưa vào đến màn password). Nguyên nhân thường do Proxy của máy bị timeout/chết upstream không kết nối được tới server Microsoft -> Phải kiểm tra lại live proxy/VPN trước, không quy kết sai mật khẩu.
     - **Màn hình Inbox Zero (*"Đã xong công việc hôm nay / Tận hưởng hộp thư đến trống"*):** Đây là tài khoản **ĐÃ ĐĂNG NHẬP THÀNH CÔNG VÀO INBOX** (mật khẩu đúng 100%), không có thư tồn đọng trong tab Ưu tiên.
     - **Tài khoản Shop Loại 2 (OAuth2 Token):** Trước khi báo lỗi, luôn test `refresh_token` qua Graph API (`https://login.microsoftonline.com/consumers/oauth2/v2.0/token` + `/me/messages`). Nếu token `200 OK` thì tài khoản hoàn toàn sống và đọc OTP trực tiếp từ Graph API.
     - **Đồng bộ kho TXT ↔ Excel:** Acc nào đăng nhập thành công vào app Outlook -> Ghi ngay vào `gmail_clean_v2.xlsx` (kèm cột 9 Token, cột 10 ClientID) và XÓA khỏi `hotmail_input.txt`. Acc nào chưa thành công / lỗi -> GIỮ NGUYÊN trong `hotmail_input.txt` và không lưu trong Excel.
  5. **Xử lý các bẫy giao diện khi đăng nhập hàng loạt (20/08):**
     - **Bẫy lặp chuỗi trong `auto_complete_input_email`:** Khi dùng `adb input text` gõ email vào trường có autocomplete, bàn phím có thể tự nối đuôi email cũ (ví dụ `...hotmail.comotmail.com`). Cách xử lý an toàn: `am force-stop com.microsoft.office.outlook` rồi mở lại hoặc dùng `type_text` có xóa trường trước khi gõ.
     - **Mở từ trạng thái đã có tài khoản sẵn:** Nếu máy đã có sẵn một tài khoản Outlook, app mở thẳng vào Inbox (`CentralActivity`). Khi đó phải mở sidebar qua nút avatar (góc trên trái), bấm nút thêm tài khoản (`+` / `btn_add_account_outlook`) để vào form đăng nhập, thay vì giả định app luôn ở `AddAccountActivity`.
     - **Xử lý trọn gói chuỗi Privacy Tour:** Sau khi đăng nhập thành công, Outlook hiện chuỗi màn hình quyền riêng tư: "Dữ liệu của bạn, theo cách của bạn" (bấm `TIẾP THEO` ở góc dưới phải) -> "Cùng nhau cải thiện" (bấm `TỪ CHỐI` ở góc dưới) -> "Nâng tầm trải nghiệm" (bấm `TIẾP TỤC VỚI OUTLOOK`) để đưa app vào thẳng Inbox.

### Source-of-truth identity mapping and recovery-proof handling (2026-08-22)

- **Bắt buộc khóa cứng hướng dọc (`wm user-rotation lock 0`):** Lệnh `settings put system accelerometer_rotation 0` và `settings put system user_rotation 0` trên các dòng máy Samsung là **CHƯA ĐỦ**. Khi mở app / WebView / bàn phím, cảm biến hệ thống vẫn có thể tự lật ngang (`mCurrentRotation = 1`). BẮT BUỘC phải thực thi lệnh khóa cứng: `wm user-rotation lock 0` và kiểm tra lại `dumpsys window | grep mCurrentRotation` trả về `0`.
- **Kích hoạt Module Check Live Gmail trên máy thật khi bị lỗi Sync:** Khi tài khoản Gmail trên máy báo lỗi đồng bộ `Sync failed`, kiểm tra thanh thông báo hệ thống để tìm thông báo *"Dịch vụ Google Play: Yêu cầu đăng nhập"*. Bấm trực tiếp vào thông báo đó để mở trang xác thực của Google: nếu Google chuyển sang màn hình **`Xác minh danh tính của bạn - Xác nhận bạn không phải là rô-bốt (Captcha Bot)`**, tài khoản được phân loại là **DIE / CHECKPOINT CAPTCHA** $\rightarrow$ kích hoạt quy trình cleanup xóa khỏi máy và xóa khỏi Excel theo đúng quy trình Farm.
- **Do not re-ask for a linkage already present in the authoritative workbook.** Before interacting with a live device, read the exact TikTok row from `taikhoan_dat_v2_updated .xlsx` and the corresponding recovery-mail row. If the account ID, Gmail, and masked on-device proof agree, treat the mapping as established and proceed; report the evidence source instead of asking the user to repeat it.
- **Distinguish duplicate-ID rows by the full tuple, not the username alone.** Same TikTok ID can appear on multiple rows with different TikTok passwords, recovery Gmail, mail password, and 2FA. Identify a row by `(machine, ID, TikTok password, recovery Gmail, mail password, 2FA)`. If one row is wrong, clear only that row's account fields after making a timestamped workbook backup; re-open the saved workbook and verify the wrong Gmail is absent while the correct row remains populated.
- **Password-change proof is fail-closed.** A visible email label does not prove that its selector/radio is selected. Require an enabled Continue button or an explicit selected-state proof. If the selector remains disabled after bounded semantic/ATX interaction, do not send a code, brute-force taps, or change credentials. Capture the UI state, release the lock through the lease API, and report the verification blocker for later handling.
- **WebView handling:** use ATX JSON-RPC as the primary capture/action layer. Coordinate fallback is bounded by confirmed resolution/orientation and the expected screen signature; repeated blind taps are not recovery.
- **Live-run sequencing:** finish any unrelated batch that owns the target device before direct inspection. After a batch exits, inspect lock payload ownership; retained `handoff` files are not proof of an active owner. Reclaim only through an authorized `DeviceLock` takeover and explicitly release the diagnostic lease afterward. Never delete lock files manually as the normal recovery method.

Session-specific evidence and the disabled-selector reproduction are in `references/identity-mapping-and-webview-proof-20260822.md`.

### ATX-agent dynamic forward port & UI fixes trong `flows/hotmail_login.py` (2026-08-18 / 2026-08-22)

- ⚠️ **ATX forward port động theo serial (`_ensure_atx_local_port`):** Không bao giờ hardcode `tcp:7912` trong `_atx_jsonrpc_call`. Phải check `forward --list` tìm port động tương ứng của serial hoặc mở `forward tcp:0 tcp:7912` để lấy dynamic port riêng, tránh dump/tap nhầm sang máy khác khi chạy batch.
- **`_atx_uiautomator_pid` tương thích shell:** lệnh `ps -A` có thể fail mã 127 trên một số Android/ADB build → fallback gọi `run_adb(adb, device, "ps")`.
- **`_tap_outlook_app_id` qua `_atx_input_tap`:** Các nút quan trọng như `btn_primary_button` ("TIẾP TỤC" ở màn nhập email) nếu gửi `run_adb input tap` có thể không ăn WebView/overlay trên S7 → đổi qua `_atx_input_tap` (ATX click tâm bounds).
- **Màn "Chọn loại tài khoản" xuất hiện sau khi nhập email trong `login_outlook_app` (2026-08-22):** Ở một số máy (như máy 4), sau khi nhập email và bấm TIẾP TỤC ở `AddAccountActivity`, app hiển thị màn hình "Chọn loại tài khoản" (`ChooseAccountActivity`) thay vì vào thẳng password -> `login_outlook_app` (cả nhánh onboarding lẫn form thông thường) bắt buộc kiểm tra `_outlook_app_account_type_selector_visible` sau bước submit email để bấm lại entry "Outlook" (`_tap_outlook_app_add_account_entry`) và chuyển tiếp sang màn nhập password.
- **Xử lý hộp thoại "Đang đồng bộ cài đặt quyền riêng tư...":** Xuất hiện sau khi submit password, không có nút bấm; sau vài giây sẽ tự chuyển sang chuỗi màn hình Privacy Tour ("Dữ liệu của bạn, theo cách của bạn") → xử lý qua `_outlook_app_finalize_new_account`.
- **`vi_changer_runner.py` DeviceLock tương thích automation-core v2 (2026-08-22):** Subclass `DeviceLock` trong `vi_changer_runner.py` bắt buộc nhận và truyền `user_authorized` và `release_on_terminal` xuống `CoreDeviceLock`, tránh lỗi `TypeError: got an unexpected keyword argument 'user_authorized'` khi gọi qua `gan_proxy_fleet.py`.
- **Nhận diện tài khoản đã đăng nhập trong Drawer đa tài khoản (`outlook_app_identity_matches`):** Khi app đã có sẵn 1 tài khoản và log thêm tài khoản thứ 2, drawer có thể hiển thị summary của tài khoản cũ trong khi avatar của tài khoản mới xuất hiện ở thanh điều hướng bên trái (`account_navigation_view`) hoặc drawer mở sẵn → `outlook_app_identity_matches` kiểm tra cả text/content-desc của avatar node để xác nhận tài khoản đã đăng nhập thành công.
- **Nhận diện Inbox rỗng (`empty_state_title`):** Màn hình inbox của tài khoản mới tinh không có `messages_listview` mà chỉ có `empty_state_title` ("Đã xong công việc hôm nay") → `_outlook_app_message_surface_visible` phải bao gồm `empty_state_title` để không bị fail-closed `OUTLOOK_APP_LOGIN_FORM_NOT_IDENTIFIED`.

- **`gmail_clean_v2.xlsx` có cột 9 `token` + cột 10 `client_id`** (thêm 2026-08-17) — lưu refresh_token + client_id của hotmail loại 2 khi login/đổi pass. Luôn backup `.bak-<date>` trước khi sửa workbook. Cả 2 cột được `resolve_graph_credentials` đọc (col 9 token, col 10 client_id).

- **Reg TikTok đọc token TỪ workbook này (user rule 2026-08-17: "script tiktok reg đọc token từ cột đó"):** `Tiktok_Reg/hotmail_provider.py::resolve_graph_credentials` có nhánh cuối đọc `HOTMAIL_WORKBOOK` (default `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`) sheet `Gmail Accounts` — match `tài khoản gmail` (col 2) → token (col 9) + client_id (col 10). Priority: kwargs → token file env → token dir → token list → **workbook** → None (fallback outlook-app). client_id shop loại 2 **chung cả kho** (`9e5f94bc-e8a4-4e73-b8be-63364c29d753`), không phải riêng acc — vẫn lưu vào cột 10.

- **Workflow vận hành user (chốt 2026-08-17):** nạp acc qua **TXT** (nguồn 1 chiều, token dài không hợp excel/sheet) → login lên máy (cần cho đổi pass an toàn) → reg TikTok (OTP đọc qua token/Graph) → 7 ngày đổi pass trên máy → xoá acc thành công khỏi TXT + ghi gmail_clean_v2. Excel = nơi GHI KẾT QUẢ, TXT = nguồn CẤP. (Đổi pass sau 7 ngày → token cũ chết → đúc token mới bằng device-code flow **trên máy farm** (IP riêng, tránh CAPTCHA PC datacenter) → ghi đè cột 9; client_id giữ nguyên. Quy trình 3 bước đều script hóa được như login máy 31.)



### Batch login thực tế 2026-08-17 (máy 75-79) — pitfall môi trường quyết định pass/fail



- ⚠️ **ATX forward local port KHÔNG được chia sẻ giữa máy — mỗi máy 1 port ĐỘNG riêng** (`automation_core/persistent_ui.py::_ensure_forward` fix `9044b91`): `adb forward` map 1 local port → 1 máy; batch chạy nhiều máy mà reuse entry `tcp:7912` có sẵn (không check serial) → máy B/C gọi `127.0.0.1:7912` vẫn trỏ máy A → dump nhầm màn hình → `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`/`LOGIN_FORM_NOT_IDENTIFIED` đồng loạt. Fix đúng: nếu entry trong `forward --list` thuộc máy KHÁC → `forward --remove` trước, rồi tạo mới bằng `tcp:0` (ADB tự chọn port, ví dụ 55564/55656/56632) + parse local port từ RELIST (vì `adb forward tcp:0` không in stdout) + reuse nếu entry đúng serial (dùng port thật, không hardcode 7912). Verify live: M75 port 55564 + M76 55656 đều VERIFIED_HEALTHY. Kèm theo: fix phải copy sang site-packages trước batch (xem bullet bên dưới) — nếu không batch vẫn gọi port 7912 cũ.

- **Máy bị KHÓA màn hình (lock screen) → batch fail `LOGIN_FORM_NOT_IDENTIFIED`** dù ATX + AdbKeyboard đủ: màn khóa không có login form → flow không nhận diện được. Triệu chứng: `dumpsys activity activities` trả RỖNG (không thấy mResumedActivity), screencap thấy lock screen Samsung ("Vuốt màn hình để mở khóa"). Fix trước batch: `adb shell input keyevent 82` + `input swipe 540 1600 540 400 300` → verify `mResumedActivity` = Outlook SplashActivity (máy 77/79 real case). Các máy SUCCESS (75/76/78) thì không khóa.

- **Patch `automation_core` ở repo src KHÔNG tự tới site-packages farm (COPY install, không editable)** — list-runner/batch gọi `D:/Taadaa/python-envs/automation/Scripts/python.exe` TRỰC TIẾP (không PYTHONPATH) nên import automation_core từ `D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core` = bản CŨ. Sau mỗi commit fix core (`persistent_ui.py`, `ui.py`, ...) phải `cp src/automation_core/<file>.py "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"` rồi mới chạy batch. Triệu chứng lừa: test qua PYTHONPATH xanh nhưng batch vẫn fail `URLERROR WinError 10061` / port 7912 (đã xảy ra: fix `9044b91` có trong src nhưng site-packages vẫn 0 `forward_local_port`). Verify sau cp: `grep -c forward_local_port site-packages/automation_core/persistent_ui.py` > 0.

- Acc shop "TRUSTED" (loại 1, 262đ, live vĩnh viễn, mailKP fviainboxes): không kèm token, rẻ — hợp workflow login-app + đổi pass. Loại "OAuth2" (loại 2, 393đ, live 12-36 tháng, `mail|pass|refresh_token|client_id`): token đọc OTP từ PC, hợp reg song song.

- **`INBOX_NOT_REACHED` nhưng acc THỰC SỰ đã login (race verify drawer)** — máy 77 2026-08-17: flow báo `OUTLOOK_APP_INBOX_NOT_REACHED` nhưng màn thật là inbox (empty state) + drawer `drawer_header_summary` = đúng email target. Verify thủ công bằng ảnh: tap account_button (36,96)→(96,156) → dòng đầu drawer hiện email → acc đã vào. Xử lý: ghi workbook thủ công + xóa khỏi TXT (xác nhận ảnh), KHÔNG chạy lại login (đã đúng, chạy lại chỉ tốn OTP/hoặc lock). Root cause race: drawer chưa render kịp lúc flow verify.

- **Acc máy 75-80 (0 acc TikTok) dùng làm máy login hotmail mới**: serial lấy từ `taikhoan_run_safe.xlsx` sheet `Accounts` (máy 75=`ce011711d4cd802905`, 76=`9885b64d56305a3731`, 77=`ce05160595e7953b04`, 78=`ce0916090a9d320a01`, 79=`ce0516059d279f3e03`, 80=`ce061606cd45950405`), đều có Outlook 4.2325.1.

- ⚠️ **Máy 75-80 MỚI TINH (chưa từng login TikTok) — reg TikTok fail `[02_profile]`**: máy chưa có acc TikTok → mở app ra I18nSignUpActivity + login sheet (KHÔNG có profile tab) — flow `social_reg_v1.py` (profile → add account) chỉ hợp máy CÓ acc cũ. **FINAL FIX (commit fc4db19): `_is_fresh_signup = not _is_profile_screen_xml(xml_b2)`** — MỌI màn không phải profile screen thật (login/signup/consent/onboarding/home-feed) đều bypass `go_to_profile`, nhảy thẳng `choose_email_login`. Đừng detect bằng marker cụ thể (bản đầu `i18nsignup`/`tao tai khoan`/`tiep tuc voi email` FAIL trên máy thật vì XML b2 có lúc chưa load đủ / tree màn signup vẫn expose tab `Hồ sơ`). Trình tự màn: I18nSignUp sheet → "Tiếp tục với email/tên người dùng" (540,1235) → "Email hoặc TikTok ID" → Đăng nhập (540,878) → SignUpOrLoginActivity "Nhập mã" OTP 6 ô (đọc qua `read_tiktok_otp_from_graph_token` — verify live '585970') → DOB (`fill_birthday`, fallback PHẢI random 18+ — user bác 01/01/1999 cứng) → **"Tạo mật khẩu"** → **KHÔNG bao giờ chọn "Bỏ qua"/Skip — PHẢI tạo pass để ghi excel** (user chốt: "phải tạo mật khẩu để ghi excel chứ, m bỏ qua r phải tốn công chạy script đổi mật khẩu lần nữa à") — `make_tiktok_password()` sinh random thuần (letter+digit+special, 10-16 ký tự, KHÔNG derive từ mail pass, KHÔNG pattern @Ks) → post-auth → **display name = prefix rút gọn chế tiếng Việt** (`make_tiktok_name`: Lilyan→Linh, Gaye→Gia, Debi→Diệp, Ruffus→Rô, Ancil→An — KHÔNG dùng username dài; commit 361ff76). Chi tiết: skill `tiktok-registration-ops` §fresh-machine-signup-v2.



## References



- `references/live-check-session-20260805.md` — full live-test session: candidate list, gates breakdown, exact commands, VPN evidence, pipeline failure transcript.

- `references/change-info-machine30-run-20260805.md` — machine-30 change-password/logout live-run transcript: stale-lock VPN block, keep-signed-in coordinate pass, password state facts, SystemUI dump pollution.

- `references/machine30-reauth-otp-20260805.md` — machine-30 reauth-OTP + identity-fallback session: `pm clear` → first-run/onboarding → `?nlp=1` login → manual OTP proof (Gửi mã → read_otp_mail → privacy notice) → `account.live.com/password/change`, plus uncommitted code changes and the open `menu_not_dismissed` issue.

- `references/outlook-farm-rollout-20260814.md` — Outlook 4.2325.1 rollout: build selection (APKMirror variant, why ≤4.23xx), verified install recipe (Windows paths, `pm install -r -d`), machines done (1/2/6/38), unregistered-hotmail discovery method (cross-file diff; NGÀY TẠO empty ≠ unreg), and the serial-suffix naming correction.

- `references/atx-agent-jsonrpc-api.md` — ATX-agent 0.10.1 JSON-RPC API đã reverse-engineer: endpoint đúng `/session/{pid}:com.github.uiautomator/jsonrpc/0`, method `dumpWindowHierarchy`/`click`/`setText`, gõ text WebView qua adb, trình tự login Outlook app máy 31 bằng ATX.

- `references/atx-primary-hotmail-login-20260817.md` — encode ATX-primary vào `flows/hotmail_login.py` + `login_outlook_one_machine`: `ui_xml` ATX-first (probe qua `AdbClient.shell` để không dính mock `run_adb`), `btn_add_account_outlook` không-text root cause, `_outlook_app_fill_password_and_finish` (ATX-tap field → adb input text → Tap tiếp theo 540,1011), 3 call-site selector, test `tests/test_atx_primary_ui.py`, test-count baseline 163→184, pitfall dedent block lớn bằng script.

- `references/graph-api-otp-token.md` — đọc OTP qua Graph API từ refresh_token (loại 2 shop): cơ chế, kết quả test thật (Mail.Read OK, /me & sendMail fail đúng scope), quyết định loại 1 vs loại 2, script test.
- `references/hotmail-batch-login-fixes-20260818.md` — chi tiết fix dynamic ATX forward port, tap nút Tiếp tục qua ATX, xử lý màn Chọn loại tài khoản sau khi nhập email, matcher avatar drawer, và cơ chế chọn máy có proxy.
- `references/profile-switcher-and-otp-lessons-20260818.md` — ghi nhận các bài học về nhận diện Profile vs Home feed, gõ OTP và xử lý stale lock proxy.
- `references/outlook-app-toast-add-account-block-20260820.md` — Lỗi Toast "Hiện không thể thêm tài khoản này" khi bấm TIẾP TỤC ở AddAccountActivity và chiến lược định tuyến Hotmail Loại 2 (Graph API OTP).
- `references/oauth2-token-vs-password-and-reissuance-20260820.md` — Bản chất Hotmail loại 2: Token OAuth2 vs Password, cơ chế đúc token mới sau đổi pass và quy tắc đồng bộ TXT nguồn / Excel.
- `references/drawer-verification-and-shop-reporting-20260820.md` — Quy tắc báo shop bảo hành (chỉ gửi user|pass), phân biệt lỗi sai pass vs proxy timeout, và fix drawer verification trong `verify_and_write`.
- `references/false-positive-wrong-password-diagnosis-20260821.md` — Chẩn đoán lỗi báo nhầm sai pass do WebView delay/màn hình Chọn loại tài khoản, kỹ thuật gõ pass an toàn và điều kiện bắt buộc để kết luận sai mật khẩu.
- `references/boxtaikhoan-catalog-and-warranty-rules-20260821.md` — Bảng giá chi tiết, phân loại Loại 1 (262đ) vs Loại 2 (393đ), và chính sách bảo hành 24h từ BoxTaiKhoan.com.
- `references/boxtaikhoan-api-and-portrait-lock.md` — Endpoint mua Hotmail tự động từ Boxtaikhoan qua API Key, chuẩn hóa khóa cứng xoay dọc (Force Portrait) trên Samsung S7, và quy trình thay email TikTok khi Gmail cũ bị Captcha/Die.
- `references/boxtaikhoan-api-and-batch-login-locked-20260822.md` — Quy trình gọi API mua Hotmail tự động từ BoxTaiKhoan.com, fix bẫy lệch ngày/serial trong taikhoan_run_safe.xlsx, DeviceLock tuần tự và Portrait Guard trên S7.
- `references/boxtaikhoan-api-purchase-and-batch-locking-20260822.md` — Tự động hóa mua Hotmail qua API Key BoxTaiKhoan (`buyProduct`), bọc DeviceLock cho từng máy chạy tuần tự, guard xoay dọc, và xử lý ngày tháng lẫn vào cột serial `taikhoan_run_safe.xlsx`.
- `references/chrome-change-info-live-fixes-20260821.md` — Toàn bộ kinh nghiệm và fix thực chiến khi chạy Change-Info trên Chrome: AdbKeyboard base64, nhận diện layout "Sắp hoàn thành", dismiss pop-up mật khẩu, bấm nút Lưu/Có và đọc OTP qua Gmail.
- `references/chrome-change-info-pitfalls-and-workbook-rules-20260821.md` — Kiến trúc Chrome vs Outlook cho Change-Info, xử lý bẫy gõ phím/IME trên Chrome WebView, và quy trình cập nhật pass/mail KP/token vào workbook.
- `references/change-info-7day-tracking-and-mutation-rules-20260821.md` — Quy tắc kiểm soát 7 ngày ngâm, cập nhật cột pass/mail KP/token sau khi đổi info, và danh sách 4 tài khoản ngâm trên 31 ngày sẵn sàng đổi.
- `references/password-recovery-via-gmail-and-otp-privacy-trap-20260821.md` — Quy trình khôi phục mật khẩu Hotmail sai pass qua Gmail khôi phục, fix bẫy bóc tách OTP dính LinkId 521839 của Microsoft, và quy tắc giữ Lock máy khi sửa.
- `references/password-reset-and-recovery-workflow-20260821.md` — Quy trình chi tiết chuẩn từng bước khôi phục & đổi mật khẩu Hotmail qua Reset link + Gmail OTP reader trên Chrome máy farm (phân biệt 2 form email khôi phục, bóc tách OTP, chống xoay ngang).
- `references/password-reset-recovery-workflow-20260821.md` — Quy trình chi tiết chuẩn từng bước khôi phục & đổi mật khẩu Hotmail qua Reset link + Gmail OTP reader trên Chrome máy farm.
- `references/password-reset-recovery-gmail-live-flow-20260821.md` — Chi tiết 6 bước live reset password thành công qua Recovery Gmail trên Chrome WebView, xử lý xoay dọc, dismiss pop-up Google autofill, và cập nhật workbook.
- `references/change-info-live-preflight-and-new-password-gate-20260821.md` — Preflight kiểm tra `HOTMAIL_NEW_PASSWORD` (fail-closed trước serial/VPN/lock), lệnh inventory read-only xác minh machine/serial/eligibility không chạm lock, và quy tắc giữ lock khi retry.
- `references/recovery-email-lifecycle-and-marketplace-standards.md` — Vòng đời Mail KP (Giai đoạn nuôi farm cần Mail KP để chống checkpoint/chống back vs Giai đoạn xuất bán gỡ Mail KP bảo mật quyền riêng tư), quy tắc gỡ Mail KP tức thì của Microsoft (không dính 30 ngày pending), và khảo sát định dạng bàn giao tài khoản trên thị trường MMO (BoxTaiKhoan/Shop bot).
- `references/signout-everywhere-and-takeover-rules-20260822.md` — Chi tiết quy trình 4 bước Takeover toàn diện, cơ chế Sign Out Everywhere (hủy token 24h), và quy tắc điều khiển DeviceLockLease (`takeover_authorized=True`, `.lock_id`).
- `references/recovery-email-tradeoffs-and-logout-sync-20260822.md` — Phân tích rủi ro bẫy 30 ngày / kẹt checkpoint khách khi add Gmail cá nhân làm Mail KP, quy trình chuẩn nuôi Farm qua App Outlook (không add mail KP), các bước thực hiện Đăng xuất khỏi mọi nơi (Sign out everywhere) và đồng bộ lại App Outlook sau khi đổi pass.
- `references/unlock-rule-and-shop-recovery-mail-trap-20260822.md` — Quy tắc tự động nhả Lock sau khi hoàn tất toàn bộ quy trình, và phân loại xử lý Hotmail còn dính Mail KP của shop phôi (kh*****@gmail.com) trên App Outlook.
- `references/boxtaikhoan-api-purchase-and-token-specs-20260822.md`
- `references/boxtaikhoan-api-and-batch-portrait-lock-20260822.md` — Quy trình gọi API mua tài khoản `buyProduct` từ BoxTaiKhoan, fix lỗi xoay màn hình tự động bằng lệnh khóa cứng `wm user-rotation lock 0`. — Quy trình & Endpoint mua tài khoản tự động qua API Key trên BoxTaiKhoan.com, chuẩn OAuth2 Refresh Token exchange & Outlook REST API (`outlook.office.com`).

- OTP reading lives in TWO places, both needed for the reauth proof path: the standalone script **`D:\Taadaa\add mail khoi phuc\read_otp_mail.py`** (IMAP, `OTP_MAIL_USER`/`OTP_MAIL_APP_PASSWORD` env) and `flows/hotmail_recovery.py` in THIS repo (`DEFAULT_RECOVERY_EMAIL`, `poll_latest_otp`). The add-mail-khoi-phuc repo is the one the user pointed to for fetching the recovery OTP.

