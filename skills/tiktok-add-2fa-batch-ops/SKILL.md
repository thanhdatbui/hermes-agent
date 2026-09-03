---
name: tiktok-add-2fa-batch-ops
description: "Chạy batch bật 2FA TikTok bằng repo D:\\Taadaa\\tiktok-add-bao-mat-f2a — preflight chọn máy, lệnh chạy từng máy, quy tắc rotate pass, audit/backfill pass workbook↔artifact, verify sau chạy, pitfalls đã vá (2026-08-25)."
---

# TikTok Add 2FA Batch Ops (repo tiktok-add-bao-mat-f2a)

References:
- `references/2fa-cron-device-lock-conflict-prevention.md` — cơ chế device lock vật lý (`user_authorized=True`), nguyên nhân `user_authorized=False` không tạo file lock khiến cron nuôi acc chiếm máy, và quy tắc chống xung đột (2026-08-25).
- `references/pass-workbook-audit-20260825.md` — kết quả audit 77 nick pass artifact ↔ workbook và quy trình backfill.
- `references/m26-otp-webview-blocker-20260825.md` — hồ sơ debug đầy đủ màn OTP không nhận input tự động (m26, TikTok 46.6.3): mọi cách đã thử đều fail, blocker thật của máy, bàn giao user nhập tay.

## Entrypoint — chạy TỪNG máy (worker đơn)
```bash
cd /d/Taadaa/tiktok-add-bao-mat-f2a && /d/Taadaa/python-envs/automation/Scripts/python.exe python_runner/run_capture_phase_b.py \
  --machine <M> --serial <SERIAL> --expected-username <ID> --source-row <EXCEL_ROW> \
  --workbook-path "D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx" \
  --workbook-sheet "Tài Khoản" --live
```
- Workbook CHUẨN có dấu cách trước `.xlsx`; sheet `Tài Khoản` có dấu.
- Cột: A=Máy, C=ID, D=PASS, E=2FA. Target = slot theo row trong REG (row 1 = dòng đầu của máy, row 2 = dòng 2…) có ID nhưng cột 2FA trống.
- Serial tra từ `PROXYgandienthoai.xlsx` (Máy ↔ device ID).
- `run_batch_live_2fa.py` đã hỗ trợ máy 1–80 + header "device id" nhưng worker đơn dễ kiểm soát hơn.

## Preflight bắt buộc trước batch
1. Lịch cron nuôi: `load_active` từ `D:\Taadaa\runtime\kibe\cron-state` (xem skill farm-schedule-preflight-check) — loại máy đang chạy hoặc sắp chạy trong 60'. Khi user đặt điều kiện kiểu "cron hôm nay chạy row X thì làm" — PHẢI đọc manifest kiểm chứng lịch thật (row xen kẽ theo ngày: vd 22/08=row2+4, 23/08=row1+3), sai điều kiện thì báo số liệu hỏi lại, đừng tự chạy.
2. ADB online: `adb devices` thấy serial (path `C:\Program Files (x86)\xiaowei\tools\adb.exe`).
3. Lock sạch: `C:\Users\Kibe\.codex\device-locks` không có machine_N/serial_X của target.
4. VPN: `automation_core.require_android_vpn(client, required=True)` → connected + tun_up.
5. ATX: `capture_atx_session_ui` trả XML `<hierarchy`.
6. User ra lệnh "lock lại khi chạy" = giữ lock suốt run; chỉ nhả khi SUCCESS hoặc user lệnh (kể cả "khoan/tạm dừng" → dừng ngay + gỡ lock).

## PASS None = pass nằm trong tracking artifact, KHÔNG phải chưa có pass
- Nick reg bằng `social_reg_v1.py --defer-tracking-write` ghi pass vào `tracking_result_stt<N>_<mail>.json` (thư mục `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<ts>\batch_1\stt_<N>\`) và CÓ KHI không flush về workbook (tracking_row trống cột PASS).
- Màn "Xác minh danh tính" của TikTok bắt nhập pass THẬT. Khi test thủ công bằng `adb input text` PHẢI escape ký tự đặc biệt (`& ! @ # ...`) như `_input_password` trong runner — không escape thì pass đúng cũng báo "Mật khẩu sai" (đã từng kết luận nhầm là pass sai trên m76).
- Quy trình vá nick thiếu PASS: tìm artifact theo tiktok_id → assert ID khớp row workbook → copy2 backup → ghi cột D → reopen verify. m76 đã vá theo cách này (10:04 25/08).

## OTP Gmail khi TikTok ép "Xác minh danh tính" (chỉ có 1 method email)
- IMAP với pass web trong `gmail_clean_v2.xlsx` KHÔNG đăng nhập được (Google chỉ nhận app password) — đừng mất thời gian thử biến thể.
- Đường đúng: gọi `_try_get_otp_gmail_app(serial, email, not_before=dt)` từ `D:\Taadaa\Tiktok_Reg\social_reg_v1.py` (load bằng importlib, thêm `sys.path.insert(0, Tiktok_Reg)` trước exec để fix `from device_lock import`). Nó mở Gmail app TRÊN MÁY, switch đúng account, refresh, đọc mã mới nhất.
- Sau khi lấy mã: force-stop Gmail (`am force-stop com.google.android.gm`) rồi mới mở TikTok — nếu không TikTok không quay lại foreground.
- Màn nhập OTP của TikTok đôi khi là WebView KHÔNG expose EditText trong accessibility XML. Cách gõ: tap vùng ô nhập (~540,700) rồi gửi từng số bằng `input keyevent KEYCODE_NUM` (7='0'..'16'='9'), sau đó tap Tiếp.
- Nhập xong OTP xong TikTok nhảy thẳng vào màn "Thay đổi mật khẩu" (bắt đặt pass) — chuẩn bị sẵn luồng pass.
- **Luồng đổi pass KHÔNG hỏi pass cũ** (user hỏi 25/08): TikTok bắt "Xác minh danh tính" bằng OTP mail trước → sau đó chỉ ĐẶT mật khẩu mới. Cách kiểm tra pass cột D đúng/sai: nhập pass Excel vào ô "mật khẩu mới" — báo "phải khác mật khẩu cũ" = pass cũ trùng Excel (ĐÚNG); nhận im lặng = sheet vẫn khớp. Cả 2 kết luận đều an toàn, không sợ lệch sheet.
- **PITFALL màn OTP WebView không nhận keyevent (hit m26 25/08, ĐÃ DÒ KỸ — bàn giao user):** EditText `code-input` bounds `[0,0][0,0]`, focused=true nhưng: tap mọi tọa độ Y (300–850), `input keyevent KEYCODE_NUM` từng số, `input text`, AdbKeyboard broadcast, TAB chuyển focus, set cả SamsungKeypad lẫn AdbKeyboard — đều KHÔNG vào số, IME `mInputShown=false` dù WebView focused. Khác m35/m44 cùng loại màn mà keyevent ăn; nghi do version TikTok (m26=46.6.3 vs m44=46.4.3). Kill app_process + restart + REBOOT đều không fix được lỗi này (reboot chỉ fix dump chết). Probe tự động 5 tọa độ cũng thất bại → **đây là blocker thật của máy, không phải lỗi script**. Xử lý: bàn giao user nhập tay.
- **PITFALL màn "Chọn phương thức xác minh" nút Tiếp enabled=false (hit m26):** row email có icon tròn bên phải (~912,676) là nút chọn; tap row lẫn icon đều KHÔNG bật được Tiếp (XML không expose checked-state, icon chỉ là android.widget.Image non-clickable). Các lần chạy trước ăn được vì method được pre-select sẵn. Khi gặp: thử tap đúng icon phải trước, rồi row; nếu Tiếp vẫn xám → dừng, chụp screencap đưa user xác nhận vị trí ô tick trên màn hình thật.

## OTP Hotmail/Outlook (máy m27, 25/08)
- Kiểm tra mail có sẵn trên máy: `dumpsys account | grep -i hotmail` — thấy `Account {name=..., type=com.google.android.gm.legacyimap}` = đã đăng nhập sẵn trong Outlook app, KHÔNG cần login lại.
- Đọc OTP: `read_tiktok_otp_from_outlook_app(ADB, serial, email, artifact_dir, timeout=150)` từ `D:\Taadaa\Hotmail` (`sys.path.insert(0, Hotmail)` rồi `from flows.hotmail_login import ...`; KHÔNG dùng `from Hotmail.flows...`). Import bị lỗi thì test import standalone trước khi chạy live.
- Lỗi `OUTLOOK_APP_INBOX_NOT_VERIFIED` khi app đang treo Splash → phục hồi theo thang 3 bước ở mục Verify (kill app_process → restart app → reboot máy).
- Flow đổi email nhận mã 2FA sang Hotmail: Bảo mật → Xác minh 2 bước → BẬT → bỏ qua điện thoại/thiết bị tin cậy → tap row Email → Cập nhật → nhập mail Hotmail → Tiếp tục → TikTok gửi OTP vào hotmail → đọc qua Outlook app.


- **Thang phục hồi máy treo SplashActivity + dump chết (đã chuẩn hóa 25/08 chiều, dùng theo đúng thứ tự):**
  1. `ps -A | grep app_process` → kill TẤT CẢ pid (uiautomator/atx-agent cũ giữ `UiAutomationService already registered!`) + `am force-stop com.github.uiautomator`, chờ 10-15s rồi dump lại.
  2. Vẫn "Killed"/XML rỗng → `am force-stop com.ss.android.ugc.trill` + monkey khởi động lại, chờ 20-30s (Splash load lâu là bình thường).
  3. Vẫn chết → **REBOOT máy** (`adb reboot`, chờ ~75s `sys.boot_completed`). Reboot fix dứt điểm tình trạng này trên cả m26 và m27.
  4. Sau reboot TikTok có hiện dialog "No LSPosed access !!!" → tap OK để tắt, force-stop + mở lại TikTok thì hết.
- Trên các máy này `capture_atx_session_ui` trả XML rỗng — phải dùng `adb shell uiautomator dump` trực tiếp.
- Row menu settings có thể chỉ có **content-desc** (vd "Bảo mật & quyền"), không có text — regex tìm cả hai, nhớ xử lý `&amp;` escape.
- Sau bật Authenticator xong TikTok bắt "Thêm điện thoại" → Bỏ qua (góc trên phải ~954,150) → có thể hỏi "Thêm vào thiết bị tin cậy?" → Bỏ qua lần nữa.
- Xóa email khỏi 2FA: tap row Email → nút "Xóa" → dialog "Xóa email?" → "Xác nhận".
- **Điều hướng settings bằng adb thô (không qua runner):** tab Ho so (972,1883) → menu (980,155) → Cai dat (623,1248 khi row bounds [330,1218][916,1278]) → scroll tìm "Bảo mật & quyền" theo content-desc → tap center → "Xác minh 2 bước" (thường y~936). Trạng thái method đọc từ cặp text: label trái (y=730 Điện thoại / 970 Email / 1264 Trình xác thực / 1558 Mật khẩu) + Tắt/Bật phải (y lệch ~3px).
- **Đổi email nhận OTP 2FA:** tap row Email → dialog có "Cập nhật"/"Xóa"/"Hủy" (nếu muốn đổi: chọn "Cập nhật") → màn nhập email mới có gợi ý @gmail/@hotmail/@outlook → tap ô input, XÓA SẠCH bằng lặp `keyevent 67` (~22 lần, `input text` đè lên text cũ không được), gõ mail mới (`@` = `input text '%s'` không ăn — dùng `input text 'user%shotmail.com'` sẽ thành space; cách đúng: gõ user rồi `%s` thay @ vẫn sai → phải dùng AdbKeyboard broadcast hoặc keyevent 61...; đã xác nhận `input text 'skitektfs@hotmail.com'` hoạt động sau khi clear xong) → "Tiếp tục". Lỗi "Nhập địa chỉ email hợp lệ" = còn dấu space thừa cuối.
- Workbook cột: F=GMAIL (mail nick), G=PASS MAIL. Khi đọc OTP cho nick, dùng mail ở cột F (không đoán từ ID).
- Workbook reopen: cột 2FA=True (secret 32 ký tự), PASS=True nếu trước trống.
- Journal: `D:\CodexRuntime\codex_gmail_debug-tiktok-add-bao-mat-f2a\journals` còn 0 file `.dpapi`.
- Locks đã nhả.
- UI thật trên màn 2-step: Email=Tắt, Điện thoại=Tắt, Trình xác thực=Bật, Mật khẩu=Bật (runner tự tắt email/phone sau khi authenticator confirm).

## Pitfalls đã vá (đừng revert; fix nằm ở commit automation-core `1bc6d88` + f2a repo tới `e65b1bd` + 27/08)
- TikTok build mới: anchor profile header là resource-id đuôi `pcq` và `pmi` (đã thêm vào `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`); `_CanonicalAdapter` bắt buộc có `prepare_switcher_anchor` (`swipe 540 1248 540 806 150`) để đưa sticky header lên trước khi mở switcher; two-step page dùng `two_step_status*` thay vì legacy `two_step_activity`.
- **Màn hình "Thiết lập một mã mới" khi nick đã có Authenticator cũ**: Khi vào màn Authenticator mà TikTok báo "Mã đã được gửi đến ứng dụng xác thực của bạn" kèm nút "Thiết lập một mã mới" (`id/l71`), `_wait_for_secret` tự động tap "Thiết lập một mã mới" để bung màn chứa khóa bí mật 32 ký tự.
## Pitfalls đã vá (đừng revert; fix nằm ở commit automation-core `1bc6d88` + f2a repo tới `e65b1bd` + 27/08)
- TikTok build mới: anchor profile header là resource-id đuôi `pcq` và `pmi` (đã thêm vào `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`); `_CanonicalAdapter` bắt buộc có `prepare_switcher_anchor` (`swipe 540 1248 540 806 150`) để đưa sticky header lên trước khi mở switcher; two-step page dùng `two_step_status*` thay vì legacy `two_step_activity`.
- **Màn hình "Thiết lập một mã mới" khi nick đã có Authenticator cũ**: Khi vào màn Authenticator mà TikTok báo "Mã đã được gửi đến ứng dụng xác thực của bạn" kèm nút "Thiết lập một mã mới" (`id/l71` hoặc `id/kyu`), `_wait_for_secret` tự động tap "Thiết lập một mã mới" để bung màn chứa khóa bí mật 32 ký tự.
- **Bỏ qua màn "Thêm điện thoại" & "Thiết bị tin cậy" sau OTP**: Sau khi submit mã OTP TOTP, TikTok hiển thị màn "Thêm điện thoại" (nút "Bỏ qua" ở góc trên trái `[24,72][232,228]`) và màn "Thiết bị tin cậy" trước khi về danh sách methods. `disable_email_and_confirm_stable` phải tap "Bỏ qua" để hạ các màn này trước khi tìm dòng Email.
- **Phân biệt trạng thái 2-Step Verification**: Khi tài khoản bật 2-Step qua Email+Password (nhưng Trình xác thực đang Tắt), header hiển thị "Xác minh 2 bước đang bật". `tiktok_2fa_enabled` phải kiểm tra trạng thái riêng của `_method_checked(xml, "Trình xác thực")` để tránh bị block nhầm `BLOCKED_ENABLED_2FA_WITHOUT_RECOVERABLE_JOURNAL`.
- Một số máy render setting TIẾNG ANH (`Settings and privacy`) dù farm tiếng Việt — `_tap_value` có bilingual fallback.
- Trang Bảo mật & quyền có row THẬT tên "Lưu thông tin đăng nhập": detector save_login nhận nhầm popup → loop `PREFLIGHT_POPUP_LIMIT_EXCEEDED:save_login`. Fix: preflight_popup bỏ generic matching khi classify ra màn F2A đã biết.
- Run fail giữa chừng vẫn để lại journal DPAPI (state CAPTURED/OTP_SUBMITTED) — rerun cùng lệnh sẽ RESUME từ journal, không enroll lại key.
- Test suite chuẩn: `pytest python_runner/tests` (174 passed sau các vá).

## Quy tắc đặt/đổi mật khẩu trong batch (user chốt 2026-08-25)
- Bước `ensure_password_saved` CHỈ chạy khi pass trong workbook thuộc dạng cần rotate: **trống**, hoặc **legacy farm** (`xxx@Ks` hoặc `Ten+số+@` như `Anhhoang3009@` — dạng chiếm đa số). Pass khác (random mạnh) giữ nguyên, KHÔNG đụng. Implement: `password_needs_rotation()` trong `core/passwords.py` + `read_pass_value()` trong `core/workbook.py` (commit `78f5cee`).
- Mục đích bước pass: nhân tiện đang sâu trong Settings bảo mật, hoàn thiện bộ ID + PASS + secret 2FA đầy đủ cho nick.

## PITFALL: màn "Xác minh danh tính" chặn trước màn đổi pass (hit 2026-08-25)
- TikTok hiện gate "Xác minh danh tính" trước khi vào đổi/tạo mật khẩu. 3 biến thể:
  1. Chọn phương thức CÓ "Mật khẩu": tap "Mật khẩu" → "Tiếp".
  2. Nhập mật khẩu trực tiếp: type mật khẩu HIỆN TẠI của nick → "Tiếp" (fix biến thể này ở commit `e65b1bd`).
  3. **OTP-ONLY — KHÔNG có lựa chọn Mật khẩu** (hit 6 máy 22/26/27/35/41/44): TikTok chỉ offer ĐÚNG 1 phương thức gửi mã qua Gmail (row masked `l***0@gmail.com` pre-selected, XML chỉ có ListView 1 row + Tiếp + Yêu cầu hỗ trợ; swipe/Back không lộ thêm method). Runner fail `PASSWORD_VERIFY_METHOD_NOT_FOUND`. Xảy ra với nick reg Gmail chưa từng set pass trong phiên. Bấm Tiếp → sang màn "Nhập mã gồm 6 chữ số" — cần luồng đọc OTP từ mailbox (kiểu XOAUTH2 đổi mail) mới đi tiếp được; CHƯA implement. Khi gặp máy này: bỏ qua, gom lại xử lý theo lô bằng flow OTP.
- TikTok xác thực pass THẬT ở biến thể 1-2 — nhập pass gen mới → báo "Mật khẩu sai", KHÔNG phải flow tạo pass mới.
- Giới hạn ~5 lần nhập sai. Thử tối đa 1-2 pass từ artifact rồi DỪNG, BACK về màn chọn phương thức — đoán mù có thể khóa account.
- Nguồn pass cũ để thử: `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<ts>\batch_1\stt_<N>\tracking_result_stt<N>_<mail>.json` (field `password`).
- ⚠️ KẾT LUẬN SAI ĐÃ ĐƯỢC SUA (25/08 chiều): pass artifact của m76 KHÔNG hề sai — lần test đầu gõ `adb input text` KHÔNG escape nên ký tự đặc biệt bị shell ăn mất → pass đúng báo sai. Test lại với escape chuẩn (như `_input_password`: `\` trước `&<>|;()$\`\"'!?#@*[]{}`, space=`%s`) → pass artifact 21/08 ĐÚNG và qua gate thành công. Trước khi kết luận "pass sai", luôn test lại với escape chuẩn.
- Workbook PASS=None + pass artifact (test đúng escape) vẫn sai = BLOCKER thật, báo user quyết (reset qua email / user tự tìm pass / bỏ qua máy).

## Audit toàn farm pass-workbook (user ra lệnh 2026-08-25)
- Khi phát hiện 1 nick thiếu pass do lỗi defer-flush, PHẢI quét ALL nick: so khớp `tracking_result_*.json` mới nhất mỗi tiktok_id ↔ cột D workbook.
- Kết quả audit 25/08: 77 nick trong artifacts; **9 nick có pass trong artifact mà thiếu trong workbook** (7 row trống cột D: dauntscyw62/donieovhdvc/juwancortese60/kylarpwp2ht/lanawakt0mv/lyndiaschles21/yaelmssp62p; 2 không có row: lieuhoan03/tanglam024); 3 row lệch pass (workbook giữ bản hợp lệ — reg retry); còn lại khớp tuyệt đối.
- Kết luận độ tin cậy: reg flow nhập pass bằng **AdbKeyboard base64** (không qua shell) nên pass ĐÃ GHI trong workbook KHÔNG bị lỗi ăn ký tự — chỉ test thủ công bằng `input text` mới dính. Không nghi ngờ hàng loạt pass trong workbook khi chưa đối chiếu.
- Quy trình vá 1 lô nick thiếu PASS: với từng nick — tìm artifact mới nhất theo tiktok_id → assert `tiktok_id` khớp cột C của row → `shutil.copy2` backup workbook → ghi cột D → reopen verify. Mẫu đã chạy: m76 row 602 (10:04 25/08).

## Lock thật + recovery sau crash (2026-08-25)
- `run_capture_phase_b.py` đã đổi sang `user_authorized=True` (commit `51dc610`): tạo lock THẬT mỗi live run theo lệnh operator; chỉ nhả khi SUCCESS, fail giữ lock `handoff`.
- **PITFALL proxy readiness timeout khi acquire device lock (hit m27 25/08):** Khi máy đã có VPN `tun0` UP nhưng hàm `wait_for_proxy_ready` bị timeout do port/readiness check, việc gọi `acquire_device_lock(..., user_authorized=True)` thông thường sẽ văng `TimeoutError: proxy readiness timed out`. Khi chạy script can thiệp/lấy OTP đơn lẻ, truyền thêm `bypass_proxy_readiness=True` vào `acquire_device_lock(...)` để lấy lock thành công mà không bị chặn bởi proxy gate.
- **PITFALL user_authorized=False không tạo lock trên đĩa (hit 25/08 chiều):** Trong `automation-core`, `acquire_device_lock(user_authorized=False)` chỉ trả về `_UnlockedDeviceLockLease` mà KHÔNG tạo file `.lock.json` trong `.codex/device-locks`. Nếu `run_batch_live_2fa.py` truyền `user_authorized=False`, cron nuôi acc (`tiktok_runner.py`) quét không thấy file lock sẽ nhảy vào chiếm máy làm đá app/mất focus. BẮT BUỘC dùng `user_authorized=True` khi muốn giữ độc quyền máy chống cron tranh chấp (đã fix ở commit `6927897`).
- **PITFALL script con tự release lock khi chưa xong (hit 25/08 chiều trên M26 & M27):** Script 2FA dùng `finally: lock.release()` khiến khi script gặp lỗi dừng lại (ở màn Outlook hoặc popup), lock bị xóa mất ➔ Cron nuôi acc 15:45 nhảy vào làm `TikTok focus lost`. Phải dùng `lease.finish(succeeded=is_success)` để giữ lock `handoff` khi chưa xong.
- Lock handoff từ run chết chặn rerun (`DEVICE_LOCK_UNAVAILABLE`) kể cả user_authorized=True. Clear bằng probe takeover rồi release: `acquire_device_lock(..., allow_takeover=True, takeover_scope='SAME_PROJECT_RECOVERY', takeover_authorized=True, takeover_reason=...)` → `lease.finish(succeeded=True)` rồi chạy lại runner bình thường.

## Batch orchestrator row N (2026-08-25)
- Gate check JSON: `C:\\Users\\Kibe\\AppData\\Local\\hermes\\scripts\\f2a_row1_gate_check.py` — phân loại ready/busy ca/near <60'/offline/locked.
- Runner tuần tự: `C:\\Users\\Kibe\\AppData\\Local\\hermes\\scripts\\f2a_row1_batch.py` — loop đọc workbook lại mỗi vòng (target thay đổi liên tục), clock-gate từng vòng từ manifest cron (hôm nay+mai), chạy 1 máy/lượt qua run_capture_phase_b, poll 5p khi idle, cutoff 17:00. Log: `f2a_row1_batch.log` cùng thư mục. Lưu ý: script hard-code row 1 (slot[0]); muốn chạy slot khác phải sửa `lst[0]`.
- **PITFALL treo loop (hit 11:49 25/08):** máy bị lock `handoff` không clear → runner retry CÙNG máy vô hạn (`start/result DEVICE_LOCK_UNAVAILABLE` lặp nghìn dòng cùng timestamp, batch đứng toàn bộ). PHẢI tail log batch định kỳ; thấy ≥3 lần result giống nhau liên tiếp = kill process, clear lock bằng probe takeover (mục Lock thật), mới chạy tiếp.
- **PITFALL bắt buộc khi user yêu cầu “lock lại chạy” (26/08):** trước khi chạy batch phải đặt giới hạn retry theo máy. Nếu result đầu tiên là `BLOCKED_ENABLED_2FA_WITHOUT_RECOVERABLE_JOURNAL`, `DEVICE_LOCK_UNAVAILABLE`, hoặc lỗi preflight tương đương thì **không retry mù**; ghi máy/row/ID, dừng batch để audit. Nếu lock là `handoff` và `owner_active=false`, coi là stale handoff cần recovery có kiểm soát; không tự xóa lock hay takeover nếu chưa xác minh đúng project/owner. Acceptance để chạy tiếp: không còn process Phase B cũ, lock owner đã được xác minh, rồi mới resume đúng target.
- **Audit sau dừng/restart:** kiểm tra không còn `run_capture_phase_b.py`; đọc journal DPAPI bằng chính Windows identity, chỉ lấy machine/row/username/state (không in secret); đối chiếu `state ∈ {written,email_disabled}` với cột 2FA Excel có secret 32 ký tự. `OTP_SUBMITTED`/`AUTHENTICATOR_CONFIRMED` mà Excel thiếu 2FA là trạng thái cần recovery ngay — không báo “an toàn” chỉ từ log batch.
- `references/interrupted-run-and-gateway-restart-audit-20260826.md`.
- `references/row1-stop-and-worker-cap-20260827.md` — phân biệt wrapper tuần tự với runner chuẩn tối đa 40 worker, quy trình dừng khẩn cấp và xử lý lock sau khi worker chết.

## Worker cap và báo cáo entrypoint (cập nhật 2026-08-27)

- Entrypoint repo `python_runner/run_batch_live_2fa.py` hiện có `MAX_BATCH_SIZE=40`, `--max-workers` mặc định **40**, và giới hạn hợp lệ 1–40; `ThreadPoolExecutor` dùng `min(cfg.max_workers, len(reserved_targets))`. Đã verify bằng `py_compile`, import/parse config và `python_runner/tests/test_run_batch_live_2fa.py` (`10 passed`).
- Wrapper triển khai tại `C:\Users\Kibe\AppData\Local\hermes\scripts\f2a_row1_batch.py` vẫn là orchestrator row 1 **tuần tự 1 máy/lượt**, không dùng `ThreadPoolExecutor`; không được báo “40 worker đang chạy” nếu thực tế đang dùng wrapper này.
- Khi user hỏi “max worker”, luôn trả hai giá trị: (1) cap/default của entrypoint repo, (2) concurrency thực tế của wrapper/lệnh đang chạy. Chỉ thay đổi cap khi user yêu cầu rõ; không tự chạy batch sau khi chỉnh.

## Session identification for cron reports

- Khi user hỏi “phiên tiếp theo cron gọi là phiên nào”, phải trả **phiên trong manifest**, không chỉ `next_run_at` của Hermes. Đọc full assignment manifest của logical day, bỏ qua `ACTIVE.json`/`ACTIVE.lock` không phải manifest JSON, lọc `slot_time >= now` theo HCM, lấy slot sớm nhất và nhóm các entry cùng `slot_time`.
- Báo tối thiểu: `Phiên N`, `account_row`, khung `slot_time–slot_end`, số/list máy. Sau đó mới báo tick scheduler có khả năng dispatch; slot start và runner tick có thể khác nhau (ví dụ phiên 2 bắt đầu 08:05 nhưng tick runner là 08:15).
- Nếu log có `already running — skipping`, kết luận phải là “phiên đã đến/được lập kế hoạch nhưng chưa xác minh đã được gọi/chạy”, không gọi là chạy thành công chỉ vì job `enabled=true` hoặc có `next_run_at`.
- Không dump toàn bộ manifest; trả lời ngắn, trực tiếp bằng tiếng Việt.

## Stop and stale-lock verification

- Khi user ra lệnh dừng, dừng batch cha trước, sau đó enumerate worker Phase B theo đúng process tree; không kill Gateway, cron watcher hoặc project khác.
- Kiểm tra process bằng process table thật, loại kết quả tự bắt chính lệnh kiểm tra (grep/wmic command-line dễ tạo false positive). Nếu worker PID đã chết nhưng lock vẫn `running/owner_active=true`, chỉ takeover/release bằng `SAME_PROJECT_RECOVERY` sau khi xác minh project/machine/serial; không xóa JSON thủ công. Giữ lock `handoff/owner_active=false` của máy fail để audit trừ khi user yêu cầu mở.


## Batch stop và giới hạn worker — bắt buộc
- Trước khi chạy phải xác định **đúng entrypoint**. `C:\\Users\\Kibe\\AppData\\Local\\hermes\\scripts\\f2a_row1_batch.py` là wrapper row 1 chạy **tuần tự 1 máy/lượt**; không suy ra max worker từ wrapper này. Entrypoint repo `python_runner/run_batch_live_2fa.py` hiện có `MAX_BATCH_SIZE=40`, `--max-workers` mặc định **40**, và `ThreadPoolExecutor(max_workers=min(...))`; phải re-check source nếu cấu hình thay đổi.
- Khi user yêu cầu dừng: dừng process batch cha trước, sau đó enumerate và dừng toàn bộ `run_capture_phase_b.py` worker con thuộc đúng process tree; không kill Gateway, cron watcher, hoặc worker của project khác.
- Sau khi kill worker, kiểm tra lại PID bằng process table thật, không dùng kết quả grep/wmic còn bắt chính câu lệnh kiểm tra. Nếu lock vẫn `running/owner_active=true` nhưng owner PID đã chết, chỉ recovery takeover cùng project với scope `SAME_PROJECT_RECOVERY`, xác minh project/machine/serial trước; không xóa JSON thủ công. Lock `handoff/owner_active=false` của máy fail giữ lại cho audit trừ khi user yêu cầu mở và đủ bằng chứng recovery.
- Sau stop phải verify: không còn batch/Phase-B process thật; lock active chỉ còn nếu có owner sống; Gateway vẫn running; cron vẫn enabled và không bị pause.
- Không báo batch “đã xong” khi chỉ process đã dừng. Phải phân biệt `success` đã verify workbook+journal+lock release với máy `failed/blocked` và máy đang dở dang do stop.
- Khi wrapper poll thấy máy lỗi lặp từ 3 lần trở lên (đặc biệt `DEVICE_LOCK_UNAVAILABLE`), dừng batch để audit thay vì chờ cutoff. Máy lỗi/preflight/UI blocker là terminal trong lượt đó, không retry mù.
- Wrapper hiện dùng clock-gate theo manifest; cutoff phải đọc từ code đang chạy, không tin docstring cũ. Nếu patched wrapper dùng cutoff động đến 23:59 thì phải báo đúng cutoff thực tế.

## Ca thành công mẫu
- 2026-08-23 — Máy 12 (th.thy081, row 90) & máy 13 (m.my7409, row 98): chuỗi fail ACCOUNT_SWITCH_ANCHOR_AMBIGUOUS → PROFILE_MENU_NOT_REACHED → OTP_ADVANCE_BUTTON_NOT_REACHED → save_login false positive → TWO_STEP_NOT_REACHED, từng bước vá như trên rồi rerun (có resume journal) đến khi cả 2 `status=success`, email tắt xác nhận qua UI XML.
- 2026-08-25 — Máy 76 (cleorbgtwyr): 2FA bật OK + secret ghi workbook; gate xác minh danh tính vượt được sau khi backfill pass từ artifact (row 602) + test lại với escape chuẩn. Bài học: "pass sai" phải loại trừ lỗi escape trước khi kết luận.
- 2026-08-25 chiều — m26 (trn.m.m620): bật Authenticator + xóa Email khỏi 2FA (ĐT Tắt/Email Tắt/Auth Bật/Pass Bật), secret mới ghi row 202; m41 (thu.trangg584): bật 2FA Email+Authenticator+Mật khẩu (giữ Email vì chưa có SĐT, xóa email chỉ còn 2 method), secret mới ghi row 322. Cả 2 vượt gate OTP bằng Gmail app trên máy; sau khi nhập TOTP TikTok bắt "Thêm điện thoại" → Bỏ qua 2 lần.
- 2026-08-25 chiều — m22 (ngomai.ly): user xử lý tay xong từ trưa; verify UI: ĐT Tắt/Email Tắt/Auth Bật/Pass Bật — chuẩn, secret cột E hợp lệ, không phải làm gì thêm.
- 2026-08-25 tối — m26 OTP gate: mail Gmail LIVE (đọc OTP mới OK qua app Gmail), nhưng màn nhập OTP không nhận input tự động + nút Tiếp không tick được method (xem 2 PITFALL trên) → lock giữ lại (`release_on_terminal=False`, TTL 2h) bàn giao user xử lý tay. Bài học quy trình: khi blocker là lỗi máy/UI thật, chốt sớm bằng screencap + bảng tóm tắt từng máy cho user, giữ lock, đừng loop thử vô hạn.

## Check mail live nhanh khi user hỏi "mail đó live k?"
- Gmail: gọi `_try_get_otp_gmail_app(serial, mail, not_before=now-30p)` — đọc được mã TikTok trong inbox = LIVE (không cần gửi mail test).
- Hotmail: `dumpsys account | grep -i hotmail` thấy account = đã login sẵn Outlook; đọc thử bằng `read_tiktok_otp_from_outlook_app`.
- Phân biệt rõ: mail chết ≠ máy hỏng. m26 mail live nhưng màn nhập OTP của TIKTOK trên máy lỗi → blocker nằm ở UI máy, không phải mailbox.