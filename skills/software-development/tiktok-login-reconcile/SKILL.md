---

name: tiktok-login-reconcile

description: >

  Debug and fix TikTok login reconcile/inventory failures on Android devices.

  Covers VPN preflight integration, UI compatibility handling (popups, image

  navigation fallbacks), automation-core API migration patterns, and the

  required docs/ui-compatibility.md audit trail.

---



# TikTok Login Reconcile — Debug & Fix Patterns

- **Outlook App Multi-Mailbox Switching & Drawer-Open Recovery (2026-09-03)**: Xử lý trình đọc OTP Outlook app khi Drawer mở sẵn lúc mở app (`OUTLOOK_APP_INBOX_NOT_VERIFIED`) và tự động chuyển đổi mailbox mục tiêu trên thanh left rail khi máy đăng nhập nhiều Hotmail: `references/outlook-app-multi-mailbox-and-drawer-recovery-20260903.md`.
- **Auto-Login Recovery Signature & Screen Preservation Compatibility (2026-09-03)**: Xử lý lỗi `TypeError: login_one_account() got an unexpected keyword argument 'preserve_current_screen'` giữa `account_reconcile.py` và `Tiktok_Reg/tiktok_login_v1.py` khiến luồng tự động phục hồi nick thiếu bị chặn `FINAL_BLOCKED`: `references/auto-login-recovery-signature-and-screen-preservation-compatibility-20260903.md`.
- **Khởi tạo & Đặt lại Mật khẩu Cho Nick Reg Passwordless qua Web Chrome (2026-09-02)**: Xử lý tài khoản reg qua Hotmail OTP/Magic Link bị báo sai mật khẩu lúc đăng nhập — sử dụng Web Chrome độc lập (`tiktok.com/login/email/forget-password`) + OTP XOAUTH2 Hotmail để đặt mật khẩu chuẩn theo Excel, tránh hoàn toàn bẫy xác minh chéo danh tính trên app: `references/passwordless-account-password-creation-via-web-20260902.md`.
- **Passwordless Hotmail OTP Login & Multi-Account Reset Pitfall (2026-09-02)**: Xử lý tài khoản reg bằng Hotmail không có pass tĩnh, luồng đọc OTP qua XOAUTH2 IMAP và pitfall chặn xác minh chéo khi cố reset pass trên máy nhiều nick: `references/passwordless-hotmail-otp-login-and-reset-pitfall.md`.
- **Hotmail/OTP Reg Backfilled Password vs Email OTP Verification (2026-09-02)**: Xử lý tài khoản reg qua Hotmail OTP/Magic Link bị báo "Mật khẩu sai" khi nhập pass cột D do pass mới chỉ ghi trên Excel mà chưa set trên TikTok — chuyển sang đăng nhập bằng Email để nhận OTP/Magic Link: `references/otp-reg-backfilled-password-vs-email-verification.md`.
- **Zero-Logout Account Swap & Excel Reconciliation (2026-09-01)**: Xử lý `account-switcher-missing-expected` khi máy đã đầy 6 nick và có sẵn nick thừa từ đợt reg — đôn nick tại chỗ và điều chuyển mapping trên Excel thay vì logout/login vòng vo gây checkpoint: `references/zero-logout-account-swap-reconciliation-20260901.md`.
- **Account Switcher Missing Expected Account Diagnosis**: Chẩn đoán và hướng xử lý khi script feed/reconcile thiếu tài khoản mục tiêu trong switcher: `references/account-switcher-missing-expected-diagnosis.md`.
- **TikTok Session Drop & Switcher Invalidation Diagnosis (2026-09-02)**: Chẩn đoán nguyên nhân rớt phiên / mất nick trong Switcher (Hardware brownout, SQLite WAL rollback, Server-side silent token revocation, Profile Soak 10-15s) và tránh các phán đoán sai (ViChanger/RAM/Proxy): `references/tiktok-session-drop-and-switcher-invalidation-diagnosis.md`.
- **Account Switcher Transient Missing & Device Reboot Recovery (2026-09-02)**: Xử lý switcher tạm thời thiếu nick sau khi thiết bị khởi động lại (uptime check, ATX pkill-9, stale lock cleanup, escape login modal sang Home feed trước canary): `references/account-switcher-transient-missing-and-device-reboot-recovery.md`.


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

- User asks to run reconcile/inventory/login on TikTok devices

- Reconcile script fails with navigation/popup/VPN errors

- Need to add new UI compatibility handling



## Target identity and live-state gate

Before any device-scoped action, resolve the requested machine number through the canonical device/workbook mapping and record the resulting serial. Never assign machines by the order returned from `adb devices`, by stale incident notes, or by a guessed config filename. Require an explicit machine-to-serial table and re-check that each target serial is online before touching it.

For a multi-target request, capture evidence independently per target and keep the target set exact. A successful ADB command, foreground activity, or screenshot file is not proof that the reported error is still present. If fresh evidence shows a different state than the user-reported failure (for example Launcher, SplashActivity, login, or an unrelated popup), preserve the scene, save the exact screenshot/XML/log evidence, and stop at the live STOP GATE. Ask before force-stop, relaunch, reboot, tap, retry, or recovery; do not silently broaden the intervention because the device is reachable.

When UI XML capture fails, use bounded activity/window/power diagnostics only to classify the current state; do not treat a missing XML dump as proof of the original UI error. Preserve matching screenshot evidence and label the original incident `UNPROVEN` until the exact failed-attempt artifact is available. See `references/live-target-resolution-and-stop-gate.md` for the reusable checklist and evidence record.



## Project Layout

- Consumer worktree: `D:\CodexRuntime\consumer-worktrees\tiktok-login-vpn-preflight`

- Main repo: `D:\Taadaa\tiktok-log-in`

- Automation-core: installed via pip (0.2.40), source at `D:\Taadaa\automation-core`

- Source runner: `D:\Taadaa\tiktok-luot nuoi acc`

- Login provider: `D:\Taadaa\Tiktok_Reg\tiktok_login_v1.py`



## Mandatory: docs/ui-compatibility.md

**Every UI/popup/VPN/navigation fix MUST add an entry to `docs/ui-compatibility.md`.**

- File is at `docs/ui-compatibility.md` in the repo root

- If missing from worktree, copy from main repo: `D:\Taadaa\tiktok-log-in\docs\ui-compatibility.md`

- Entry format: ID/owner, UI signature, selector/fallback order, safety bounds, post-action verification, regression tests, affected versions

- Also update `reports/AUDIT_LOG.md` with chronological summary



## Debugging Reconcile Failures

When reconcile hangs or fails, debug step-by-step instead of blindly retrying:



1. **Read `docs/ui-compatibility.md` first.** It is the contract of record for recovery order, selector/fallback ownership, and branches that must be preserved. Do not invent a conflicting policy from the live symptom.

2. **Check VPN first**: `adb shell ip addr show tun0 | grep inet`.

3. **Verify watcher reality with four layers**: scheduler/tray state, process tree, a fresh target-specific artifact after the current boot, and live device VPN proof. A scheduled task marked Disabled does not prove a tray-launched watcher is absent; a live watcher process without a fresh machine/serial artifact does not prove reconnect recovery ran.

4. **Test `_start_tiktok_and_wait` in isolation** and identify the exact blocking activity before changing code.

5. **Test Profile navigation semantic/image-first.** Coordinate navigation is only a bounded, resolution-gated fallback with post-action verification; never replace image/core navigation merely because the agent cannot inspect a screenshot.

6. **Call the canonical automation-core account-switcher entrypoint.** It owns Profile-root positioning, required scrolling, sticky identity-header selection, and switcher verification. Do not emulate that sequence with a bare tap unless the documented fallback signature and verification both apply.

7. **Check popups via activity state**: `dumpsys activity activities | grep -E 'mResumedActivity'`.

8. **Read the JSON outcome, not only `DONE`.** Preserve bounded live runs until natural exit unless concrete evidence proves a hang; do not repeatedly kill/restart the same run.



### Recovery ownership correction



- Reconcile inventory/Profile/switcher recovery is an app-level bounded force-stop/relaunch retry. It must not ad-hoc reboot the device.

- Device reboot belongs to the dedicated guarded recovery flow. That flow retains the central lock, waits for boot/unlock, and then waits for fresh watcher/VPN proof before TikTok resumes.

- Never delete another live owner's lock or bypass watcher readiness because `tun0` was previously up.



## Common Failure Signatures & Fixes



### VPN/proxy readiness timeout

- `acquire_device_lock` may wait for a watcher readiness marker. Diagnose the evidence chain before bypassing it: live owner lock, current watcher process tree, fresh target artifact for the current boot, then `tun0` + Android VPN proof.

- `live_vpn_verifier` is appropriate only as a bounded supplement when live VPN proof already exists; it must not hide a missed reconnect event or authoritative `proxy_failed` marker.

- A scheduled task can be Disabled while a tray/supervisor-launched watcher is still running. Conversely, duplicate watcher parent processes can race. Never infer health from scheduler state or process existence alone.

- If reboot completed but no fresh target artifact appears, debug reconnect detection/worker scheduling. If a ready artifact exists without verified proof, debug ViChanger assignment/VPN verification.

- Keep the device lock through guarded reboot recovery; do not make TikTok reconcile own device reboot recovery.



### UiAutomator hang on Samsung

- `navigator.dump_ui()` can hang indefinitely on some Samsung devices

- Use `dumpsys activity activities` to check for popups/text instead

- Never call `dump_ui()` inside a loop without a try/except + timeout



### Image navigation fails on SM-G930W8

- `detect_feed_controls` and `detect_profile_screen` may return None even when feed is visible

- `bottom_navigation_point(screenshot, "profile")` still works → use as fallback for `has_navigation_surface`

- `tap_profile` → coordinate fallback (972, 1857) when image-nav fails

- `open_account_switcher` → coordinate fallback: tap (540, 552), then verify "Chuyển đổi tài khoản" in UI dump



### Post-install consent popup (UniversalPopupActivity)

- Appears after TikTok data clear: "Đồng ý và tiếp tục"

- Dismiss with swipe: `input swipe 540 1600 540 400 300`

- Detect via `dumpsys activity` (NOT uiautomator dump)



### Google Play ToS/PlayCore popups

- Appear after TikTok force-stop on devices with pending Play updates

- `TosActivity`: tap "Chấp nhận" at (863, 1419)

- `PlayCoreAcquisitionActivity`: tap "Tải xuống qua Play" at (783, 1824)

- Detect via `current_package == "com.android.vending"` in activity dump



### Workbook column compatibility

- `account_inventory.py` SERIAL_HEADERS must include `"device id"` and `"deviceid"` for workbooks using that column name

- Proxy mapping uses VICHANGER_SERIAL_HEADERS = `("phoneId", "deviceId", "serial")`



### FINAL_BLOCKED fleet diagnosis (recovery-new-handler runs)

When asked "why are N machines FINAL_BLOCKED", aggregate from the recovery runner's own summaries instead of reading individual logs blindly. **Core interpretation: FINAL_BLOCKED means the SCRIPT run failed (exit≠0) or preflight refused — it does NOT mean the machine/account was banned by TikTok.** Machines still open TikTok fine; the script just never completed the flow.



1. **Find the active runtime root first.** `Tiktok_Reg/project_paths.py` computes `RUNTIME_ROOT` from `TIKTOK_REG_RUNTIME_ROOT` (fallback `%LOCALAPPDATA%\Taadaa\Tiktok_Reg`). As of 2026-08-07 the ACTIVE root was the project-local `.runtime` (`D:\Taadaa\Tiktok_Reg\.runtime\Taadaa\Tiktok_Reg\artifacts`); the `%LOCALAPPDATA%` copy was stale (last runs 2026-08-04). `ls -dt` both roots before trusting one — the two can disagree badly.

2. **Aggregate `*/recovery_summary.json`** under `runs/recovery-new-handler/`: each file carries `status_counts` and `targets[stt].blocker`. Group blockers per machine, count normalized signatures (strip `; exit_code=...`). Snippet in `references/final-blocked-fleet-diagnosis.md`.

3. **Per-machine root cause is in `stt_XX/attempt_*/stdout.log`** — grep `STOPPED|SUCCESS|signature|OTP`. The summary blocker (e.g. `PROCESS_EXIT_1`) is generic; the stdout tail tells the real story.

4. **Retry-loop tell**: a machine with runs every 10–15 min all failing (`ls -dt 2026080*/stt_XX | head`) means the run keeps re-firing on the same stuck machine. Read the LATEST run's stdout and check live device state (`adb shell dumpsys activity activities | grep mResumedActivity`) — the device may be sitting on Gmail, not TikTok.

5. **Dominant 2026-08-07 root cause**: OTP fetched successfully but the TikTok OTP screen is gone on return (`[otp-enter] TikTok OTP screen unavailable after Recents recovery`; TikTok reset to `SignUpOrLoginActivity`). Affected gmail (Gmail app) AND hotmail (Outlook CDP) flows alike. A machine stuck in this loop cannot succeed while the screen-preservation bug exists — do not keep re-running it.



Full machine-by-machine breakdown: `references/final-blocked-fleet-diagnosis.md`.



### TARGET_EMAIL_ALREADY_REGISTERED — preflight refusal, NOT a script failure

- Fired in `scripts/run_tiktok_recovery_new_handler.py` `_build_items` (~line 633): `elif _norm_email(email) in registered: item.blocker = "TARGET_EMAIL_ALREADY_REGISTERED"` — **before any device touch**. `registered = load_registered_tiktok_emails(tracking)` = emails whose tracking row has a non-empty Tik ID (col C).

- So the machine was never even opened; the handler refuses to run because the email already has a TikTok account recorded in the tracking workbook. Do NOT treat as a retry candidate for registration.

- **Stale-state trap**: a machine flagged ALREADY_REGISTERED in an old run may be absent from the CURRENT `_clean_targets.json` (detector output). As of 2026-08-07 active targets were only {30,34,36,38,39,54,55,57,66}; machines 19/45/49/50 sat flagged but were never scheduled again. Check `_clean_targets.json` before assuming a machine is being re-run.

- **Workbook columns** (taikhoan_dat_v2_updated .xlsx): A=Máy, B=Tik, C=ID (TikTok), D=PASS (TikTok), E=2FA, F=GMAIL, G=PASS MAIL, H=NGÀY SINH, I=NGÀY TẠO, J=device ID. Rows with empty C are unused slots (e.g. 150/357/358/389/390/397/398); 385 had ID but EMPTY pass TikTok.

- **What the reg script does if it DOES run an already-registered email** (social_reg_v1.py `detect_after_continue` ~1651, called after typing email + submit): TikTok never "goes straight in". Two outcomes, both handled:

  - `registered` (password field present in XML) → email kept only if preferred; `fill_password_and_login` (~4353) types the pass from Excel col D, reveals via eye icon to verify, then taps login. Non-preferred → BACK and try next candidate.

  - `registered_otp` (REAL_OTP_LOGIN_HINTS: "xac minh email", "verify email", "nhap ma", "gui lai ma", "resend code", "ma xac nhan", "ma xac minh", "verification code", "enter the code", "sent a code") → kept, `[7c]` fetches OTP from inbox (Gmail app / Outlook CDP) and enters it.

  - `verify_email_pending` (MAGIC_VERIFY_HINTS: "kiem tra email", "kiem tra hop thu", "check your email", "check email", "gui lai email", "resend email" → màn "Kiểm tra hộp thư của bạn"/"Gửi lại email sau 46 giây") → email CHƯA đăng ký, TikTok gửi magic link → kept, `[7c]` handle_tiktok_email_otp mở mail → tap link → trả `MAGIC_LINK`.

  - Detection order: password field → `_classify_after_continue_flat(flat)` (priority REAL_OTP TRƯỚC — cả 2 nhóm marker cùng xuất hiện → `registered_otp`) → "da co tai khoan" text → "tai khoan khong ton tai" (→new) → login-form markers → new-reg hints (birthday, "tao tai khoan"). Fallback unknown dùng CHUNG helper này (không duplicate marker list).



## Profile-vs-feed classifier false positive (Tiktok_Reg `social_reg_v1.py`)



**Triệu chứng:** runner tưởng đã vào profile nhưng thực tế còn trên feed → mở dropdown trên feed → `SWITCHER_ANCHOR_AMBIGUOUS` → loop relaunch. Máy 34, 2026-08-06/07.



**Root cause:** `_has_profile_header_marker` / `_is_personal_profile_screen_xml` match **substring** `"follower"` trong flat text — nút feed "Đăng lại cho follower" (share-to-followers) chứa substring → feed bị nhận là profile. Debug xác nhận: `has_header: True ← SAI`.



**Fix (commit `86c122d`):** match **node riêng** bằng regex trên từng node text, không match substring:

```python

follower_pattern = re.compile(r"^(?:[\d.,\s]*)?(?:nguoi dang follow|dang follow|followers?)$")

for node in root.iter("node"):

    t = (node.attrib.get("text") or "").strip()

    if t and follower_pattern.match(strip_accents(t).lower()):

        return True

```

Các nhánh khác cùng class bug: "đã follow/thích" và "chia sẻ video/tải lên" phải kèm `_has_profile_header_marker` (tên user clickable trong header y≤300, không số/stopword) — feed có cùng text nên không đủ.



**Verification pattern (ad-hoc, không cần máy):** dump XML thật từ máy (`uiautomator dump /sdcard/wd.xml` → `adb shell cat`), rồi inject node synthetic (`<node text="Follower" .../>` trước `</hierarchy>`) để test cả 2 chiều: feed→False, profile synthetic→True, "Đăng lại cho follower"→False, node "Người đang follow"→True.



**expected_marker phải là marker ĐẶC TRƯNG màn, không phải tab chung (2026-08-07, máy 34):** adapter `dump_ui(expected_marker="hồ sơ")` VÔ DỤNG — tab "Hồ sơ" xuất hiện trên MỌI màn TikTok kể cả feed → dump feed vẫn pass marker → core nhận feed → `SWITCHER_ANCHOR_AMBIGUOUS`. Fix đúng: marker = **display_name (tên user, vd "yobi")** — chỉ profile thật có. Adapter đọc qua `extract_profile_identity` rồi truyền làm marker; rỗng thì bỏ marker (dựa classifier). Live-proven: run 20260807-182529 máy 34 xuyên được profile → dropdown → Add account → email → OTP sau khi đổi marker sang tên user.



**Profile "không render" trên máy 34 — KIỂM TRA TẤT CẢ MÁY CÙNG ĐỊNH NGHĨA TRƯỚC/TRONG khi quy lỗi MÁY (2026-08-07, bài học lớn):** nhiều giờ ngộ nhận tap profile tab → dump feed "Tây Ninh" (không username) là do profile máy không render được (SM-G930K 3GB, TikTok 46.x), kể cả sau reboot. User đúng khi đẩy lại: cả farm cùng model + cùng độ phân giải, không có lý do gì 1 máy lỗi phần cứng. **Root cause thật (2 phần, đều KHÔNG phải lỗi máy):**

1. **Tap tọa độ hardcode (972,1857) nằm TRÊN tab "Hồ sơ".** Bounds thật từ dump: `Hồ sơ: [864,1864][1080,1903]`, center (972,**1883**). Tap y=1857 cao hơn 26px so mép trên (1864) → trúng frame trên thanh tab → không click → ở lại feed. Tap đúng (972,1883) mở profile ngay (screencap + vision xác nhận profile `yobi`).

2. **uiautomator dump stale:** `uiautomator dump` E=137 (atx-agent wedged) nhưng `cat /sdcard/wd.xml` trả **feed cũ** chứ không phải màn thật → XML nói dối, màn hình thật OK.

**Chẩn đoán đúng:** xem màn hình THẬT bằng `screencap` + vision_analyze (đừng tin XML stale); verify tọa độ tap với `bounds` thật của element từ dump. Chi tiết + boot normalize (LSPosed banner, tun0, chờ idle): `references/machine34-tap-coordinate-and-stale-dump.md`. **Đừng đổ lỗi máy/app khi cả farm đồng cấu hình — check tọa độ hardcode & XML stale trước.**



**Đường thắng khi máy ĐANG Ở MÀN LOGIN (dùng cho máy thật sự không vào được profile):** màn login TikTok (`SignUpOrLoginActivity`) → runner đi thẳng vào email entry flow, KHÔNG cần profile navigation (run 182529 thắng vì máy để lại màn login từ run trước). Hướng xử lý: (a) đưa máy về màn login (mở TikTok → logout qua UI, hoặc giữ màn login từ run trước) rồi chạy runner; hoặc (b) patch runner detect `SignUpOrLoginActivity` → skip profile navigation → vào email entry thẳng.



**atx-agent wedged → SIGKILL (pkill -9), SIGTERM vô dụng:** atx-agent treo `futex_wait_queue_me` (S-state) KHÔNG nhận SIGTERM (`pkill -f` không chết, dump mãi E=137). Recipe live-proven máy 34: `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` + `uiautomator quit` → dump E=0 ngay. Core 0.4.43 đã nhúng (`_recover_uiautomator` dùng `pkill -9 -f` cho cả atx-agent + uiautomator; test `test_ui_dump.py` phải cập nhật kỳ vọng `-9`). Consumer làm tay cũng dùng `-9`. KHÔNG ảnh hưởng account (chỉ kill process, không đụng app data/session) — live-proven.



**Orphan device-lock self-block (recovery-new-handler):** runner fail trước để lock trên đĩa (`machine_34.lock.json` + `serial_<serial>.lock.json`), runner mới thấy lock → `FINAL_BLOCKED DEVICE_LOCKED` trong ~39s, log rỗng, không đụng máy. Dọn: verify pid trong lock đã chết (`wmic process where "ProcessId=N"` trả rỗng — tasklist có thể silent-fail) → `rm -f` CẢ 2 file (machine + serial). Lock cũ ghi pid ≠ runner hiện tại, started_at = run trước.



**Gmail fast-path vẫn đọc code cũ nếu pull-refresh chưa chạy:** run 182529 fast-path đọc code timestamp 14:54 (mail CŨ) → nhập OTP sai → TikTok đóng màn OTP → `[otp-enter] TikTok OTP screen unavailable after Recents recovery` → FINAL_BLOCKED. Verify lại thứ tự trong file hiện tại: pull-refresh (swipe F5) phải nằm TRƯỚC preview-read trong `_try_get_otp_gmail_app` — đã patch trước đó nhưng phải xác nhận commit thật sự chứa (commit 2871 dòng lẫn thay đổi người khác dễ nuốt mất).



**Audit wrapper pitfalls (2026-08-07):** `invoke-command-code-9router-audit.ps1` có `#requires -Version 7.0` — `pwsh` trên PATH (`.codex\\shell\\pwsh`) CÓ THỂ vẫn là PS 5.1 → verify `$PSVersionTable.PSVersion` trước khi chạy hoặc dùng `C:\\Program Files\\PowerShell\\7\\pwsh.exe`. `invoke-gemini-9router-audit.ps1` trả 400 Invalid JSON body khi `context_files` rỗng (thiếu context payload). `invoke-opencode-audit.ps1` exit 1 non-quota (nemotron→ling cascade fail). Theo ladder AGENTS.md → fallback Codex reviewer độc lập (fresh, read-only, verdict `APPROVED|MINOR_FIXES|REJECT`).



**opencode CLI audit treo vô hạn → 9router API direct (2026-08-07):** `opencode run ... --model opencode/longcat-2.0-free` THÀNH CÔNG 2 lần (MINOR_FIXES) nhưng có thể treo 240s+ với file jsonl 0 bytes (queue/quota kẹt). Fallback nhanh: gọi 9router `/v1/chat/completions` TRỰC TIẾP bằng Python urllib, model **`deepseek-v4-flash` (combo, KHÔNG slash)** + yêu cầu `ANSWER DIRECTLY IN FINAL CONTENT, NO CHAIN-OF-THOUGHT` + `max_tokens≥2000` → trả verdict thật (`APPROVED with MINOR_FIXES` — dùng được). **Pitfall:** model có slash (`opencode/deepseek-v4-flash-free`) trả `reasoning_content` dài, `content` rỗng, `finish_reason=length` → vô dụng (phải parse JSON linh hoạt vì 9router có thể dính 2 object liên tiếp; `json.loads` fail → tìm object cuối cùng bằng đếm `{}` depth).



**Chi tiết session:** `references/atx-sigkill-profile-instability.md`



## Magic-link verify screen bị classify nhầm registered_otp (Tiktok_Reg `social_reg_v1.py`, 2026-08-07)



**Triệu chứng:** `detect_after_continue` trả `registered_otp` cho màn magic-link verify của email CHƯA đăng ký ("Kiểm tra hộp thư của bạn" + "Gửi lại email sau 46 giây" + "Đăng nhập bằng mật khẩu", live máy 34) → `fill_email_and_next` báo "Tat ca N email da co TK TikTok" dù email chưa reg.



**Root cause:** marker list cũ gộp chung magic-verify markers ("kiem tra email", "kiem tra hop thu", "gui lai email", "resend email") với OTP-login markers ("nhap ma", "gui lai ma", "verification code"…) vào một `otp_hints` → magic-verify bị trả `registered_otp`.



**Fix:** tách 2 nhóm marker module-level (`REAL_OTP_LOGIN_HINTS` vs `MAGIC_VERIFY_HINTS`) + helper chung `_classify_after_continue_flat(flat)` → `'registered_otp' | 'verify_email_pending' | None`, **priority real-OTP trước** (cả 2 nhóm cùng xuất hiện → registered_otp — màn OTP login thật thường kèm text "Kiểm tra email"). `detect_after_continue` trả state mới `verify_email_pending`. Caller `fill_email_and_next` thêm nhánh `result == "verify_email_pending"` (ĐẶT TRƯỚC `registered_otp`) → `return em, pw, dob` (giữ email) → flow đi tiếp 7c `handle_tiktok_email_otp` (đã có magic-link path → mở mail → tap link → `MAGIC_LINK`). Fallback unknown dùng chung helper, KHÔNG duplicate marker list (DRY), giữ `reg_fallback` cũ.



**Tests:** `tests/test_login_magiclink_classify.py` — 5 cases: magic-only → verify_email_pending, OTP-only → registered_otp, **negative** cả 2 → registered_otp (priority), resend-email-only → verify_email_pending, helper unit (priority + None). Mock pattern: `monkeypatch.setattr(social, "get_ui_xml", lambda _device: XML)` + `social.time.time` iterator `iter([0.0, 0.2, 1.1])` (loop 1 vòng, theo mẫu `test_detect_after_continue.py`). UI.md entry: `tiktok-reg-magiclink-verify-classify-20260807`. Chi tiết + verify command: `references/magic-link-verify-classifier-split.md`.



**Pitfall:** state `verify_email` của `_classify_post_auth` (~L4189-4191) KHÁC state mới `verify_email_pending` — đừng lẫn. `otp_screen_hints` bước 7c (~L9386+) giữ nguyên (đó là chờ OTP screen, không phải classifier registered/new).



**Gap tiếp theo — máy bắt đầu run Ở SẴN màn magic-link verify (2026-08-07, máy 34 run 235541):** máy từ run trước để lại màn "Kiểm tra hộp thư của bạn" + "Gửi lại email sau 41 giây". Bước 07 `fill_email_and_next` chỉ check màn nhập email (`wait_for_text(["Email hoac TikTok","Email","TikTok ID"])` fail) → log "✗ Khong thay man nhap email" → continue bỏ qua email → cuối "Tat ca N email da co TK TikTok" (SAI). Fix `6615ac4` chỉ xử lý màn magic-link SAU submit (`detect_after_continue`); gap là máy ĐANG ĐỨNG sẵn trên màn đó khi bước 07 bắt đầu. **Fix:** trong vòng lặp candidates `fill_email_and_next`, TRƯỚC khi log "Khong thay man nhap email" + continue → kiểm tra flat chứa MAGIC_VERIFY_HINTS (tái dùng `_classify_after_continue_flat`) → nếu là magic-link verify: giữ email `return em, pw, dob` (flow 7c sẽ vào handle_tiktok_email_otp mở mail → tap link → MAGIC_LINK); nếu email đang thử đã có TK trong tracking → bỏ qua như cũ. Chẩn đoán nhanh: dump UI thật lúc fail — nếu text chỉ có "Kiểm tra hộp thư của bạn"/"Gửi lại email sau N giây"/"Đăng nhập bằng mật khẩu" → màn magic-link, KHÔNG phải lỗi máy.



## Outlook magic-link fail-closed branch (STT30 2026-08-11, `handle_tiktok_email_otp` ~L10678+)



Contract: `prefer_magic_link=True` + non-Gmail (Hotmail/Outlook/Live) → KHÔNG dùng numeric readers.

- Helper `_read_outlook_magic_link_with_evidence(device_id, email, password, stt=)` chỉ trả `None | "MAGIC_LINK"` (evidence-backed: inbox verified → newest TikTok row → semantic/visual link action → tap → transition verified). `None` = thiếu link evidence → **fail closed**.

- Blocker: `if code != "MAGIC_LINK": _capture_tiktok_email_otp_final_blocked(device_id, stt, "OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")` — helper này RAISE RuntimeError vô điều kiện (định nghĩa ~L10177) nên flow KHÔNG bao giờ chạm env-gated refuse `SOCIAL_NO_OTP_RESEND` / shared `_request_and_read_fresh_tiktok_email_otp` / enter numeric. Browser fallback bị chặn thêm bằng `and not prefer_magic_link`.

- **Pitfall ordering**: blocker phải đứng TRƯỚC env-gated refuse; nếu `_capture_tiktok_email_otp_final_blocked` bị đổi thành không-raise thì shared resend sẽ nuốt nhánh Hotmail magic-link.

- Giữ nguyên: **numeric registered-OTP path (`prefer_magic_link=False` → `_try_get_otp_outlook_newest` → shared resend)** — KHÔNG còn dùng `_try_get_otp_outlook_cdp`/`_try_get_otp_browser` trong chuỗi numeric (xem section newest-mail reader bên dưới) — và Gmail magic-link path (qua `_read_gmail_otp_with_target_recovery(prefer_magic_link=...)`; Gmail vẫn được phép rơi xuống env-gated refuse/shared resend — chỉ Hotmail/Outlook/Live bắt buộc fail-closed).

- Tests: `tests/test_login_outlook_magiclink_branch.py`. **Gap test cũ**: chỉ `monkeypatch.delenv("SOCIAL_NO_OTP_RESEND")` (case unset) — thiếu case env=1. Bổ sung `test_hotmail_magic_link_unverified_blocks_regardless_of_resend_env` parametrize `{None,"1","0"}` → chứng minh "bất kể env". Pattern: helper→None → `pytest.raises(RuntimeError, match="OUTLOOK_MAGIC_LINK_ACTION_NOT_VERIFIED")` + assert `resend_calls == []` / `entered == []` / cdp/browser/find_text_tap rỗng.

- **Delegation pattern ("Sửa tiếp đúng một lỗi")**: task mô tả bug có thể khớp trạng thái TRƯỚC patch của worker trước (uncommitted). Đọc working tree TRƯỚC: nếu source đã fail-closed (raise block có sẵn) thì việc còn lại là test coverage, KHÔNG patch source thừa. Verify 2 lớp: suite pytest + ad-hoc temp script (source-ordering assert + behavioral mock.patch proof).

- Chi tiết + verify recipe: `references/outlook-magiclink-fail-closed-20260811.md`



## Numeric OTP Hotmail/Outlook: chỉ đọc từ mail TikTok MỚI NHẤT (`_try_get_otp_outlook_newest`, 2026-08-11)



**Triệu chứng (STT30, serial ce0217126cd4bc640c):** email ĐÃ verify qua deep-link, TikTok mở CommonFlowActivity "Nhập mã 6 chữ số". Script resume nhập OTP nhưng reject 2 lần liên tiếp: log `[otp-cdp] Fresh Outlook code found in background tab` → nhập → reject → tap "Gửi lại mã" → đọc lại vẫn code cũ → reject.



**Root cause:** `_try_get_otp_outlook_cdp`/`_try_get_otp_browser` quét DOM tab Chrome theo DOM-order tìm "tiktok"+6 số, KHÔNG có newest-mail guard. Nhiều tab mở CÙNG mail cũ (URL `.../id/AQQk...`, code 987307/335276) trong khi TikTok resend 21:15 gửi mail MỚI chưa được mở → đọc code cũ → reject.



**Fix tối thiểu (consumer-only `social_reg_v1.py`):** reader numeric mới `_try_get_otp_outlook_newest(device_id, email, password, *, stt=None, timeout=240)`:

1. `_open_outlook_inbox_verified(...)` → inbox XML (fail closed nếu None)

2. `_outlook_newest_tiktok_row(inbox_xml)` → row TikTok mới nhất theo time/order evidence (helper ĐÃ có cho magic-link — tái dùng, đừng viết mới)

3. `tap(device_id, *row["coord"], wait=D_MEDIUM)` → mở ĐÚNG mail TikTok mới nhất

4. Đọc code 6 số từ mail body vừa mở (`get_ui_xml` + `extract_otp_from_xml`, swipe nếu cần)

- Không xác định được newest row → `None` (**fail closed, không nhập code cũ**). Guard target không phải Hotmail/Outlook/Live → `None`.

- **Thay thế ở MỌI call site numeric non-Gmail**: nhánh `else` trong `handle_tiktok_email_otp` (bỏ fallback `_try_get_otp_browser` — reader đó quét DOM tùy tiện) VÀ `_request_and_read_fresh_tiktok_email_otp` (sau resend + sau swipe refresh — chính là path "Gửi lại mã → đọc lại code cũ" trong log live).

- Giữ nguyên định nghĩa `_try_get_otp_outlook_cdp`/`_try_get_otp_browser` (backward-compat, test trực tiếp gọi) nhưng KHÔNG dùng trong chuỗi OTP production nữa. Gmail + prefer_magic_link + registered OTP giữ nguyên.



**Pitfall test mock:** test handler-level phải mock `_try_get_otp_outlook_newest` (KHÔNG phải `_try_get_otp_outlook_cdp` như test cũ) — nếu không, flow chạy `_open_outlook_inbox_verified` thật (loop 240s). Kiểm tra `grep -n "_try_get_otp_outlook_cdp\|_try_get_otp_browser(" social_reg_v1.py` sau khi patch: chỉ còn định nghĩa + self-reference trong `_try_get_otp_browser`, call site production phải là `_try_get_otp_outlook_newest`.



**TDD evidence:** 3 test mới trong `tests/test_login_outlook_magiclink_branch.py` (inbox 2 mail → TAP row mới nhất + đọc code mail vừa mở; inbox không có row → None không tap; handler-level fail-closed không enter code cũ) + update test registered-OTP (assert cdp/browser KHÔNG gọi). 46 passed (43 baseline + 3 mới), health-fallback 16 passed (1 deselected pre-existing), `git diff --check` sạch. Chi tiết: `references/otp-outlook-newest-mail-reader-20260811.md`



## Core version bump workflow (venv + runner gate) — Tiktok_Reg



Khi cần nâng automation-core cho consumer (vd 0.4.42 → 0.4.43 pkill -9 SIGKILL fix):



1. Build wheel trong `D:\Taadaa\automation-core` (commit version bump trong pyproject.toml, `dist/automation_core-<v>-py3-none-any.whl`).

2. Cài đè sạch: `python -m pip install --force-reinstall --no-deps <wheel>`.

3. **Verify 2 lớp, không chỉ version:** `md.version('automation-core')` CÓ THỂ trả version cũ nếu venv còn dist-info cũ nằm lại (dual dist-info 0.4.42 + 0.4.43 → importlib.metadata ưu tiên cái cũ) → force-reinstall mới dọn. Sau đó **grep module đã cài** để chắc change thật sự có mặt: `inspect.getsource(automation_core.ui)` chứa `"pkill", "-9"`.

4. Nâng `REQUIRED_CORE_VERSION` trong runner consumer (vd `scripts/run_tiktok_recovery_new_handler.py` line ~61) lên đúng version.

5. Chạy gate: `_require_runtime_core_version()` → `{'version': '<v>', 'source': 'installed-distribution', 'lease_verifier': True}`.



**Pitfall — pytest treo vô hạn do test gọi ADB thật với serial giả:** `tests/test_profile_detection.py::test_account_dropdown_dismisses_overlay_before_canonical_navigation` treo vì `_try_open_account_dropdown_once` gọi `ensure_rotation_locked`/`shell`/`get_ui_xml` thật (serial-6 không tồn tại) — pre-existing, KHÔNG phải do fix classifier. Chẩn đoán: chạy test đó riêng, thấy `[adb warn] adb.exe: device 'serial-6' not found` lặp lại. Đừng đuổi theo — chạy các test khác trong file riêng lẻ (`-k` theo tên) cho nhanh.



**Chi tiết đầy đủ:** `references/profile-vs-feed-classifier-and-core-bump.md`



**Commit hygiene khi file mang thay đổi chưa commit của worker khác (2026-08-07, social_reg_v1.py):** Tiktok_Reg working tree thường có NHIỀU file modified sẵn từ trước session (worker/người khác để lại — AGENTS.md, CLAUDE.md, `_check_pids.py`...). Trước khi `git add <file>` hãy check: `git diff <file> --stat` — nếu diff phình to (hàng nghìn dòng) so với phần mình sửa → file có thay đổi người khác chưa commit. `git add <file>` + commit sẽ nuốt TOÀN BỘ diff (kể cả code người khác) → commit 2871 dòng lẫn lộn, khó review/revert. Xử lý: (a) hỏi user giữ hay tách; (b) nếu giữ, nói rõ commit chứa cả thay đổi pre-existing; (c) nếu tách — dùng `git add -p` chọn đúng hunks mình sửa (cùng file khó vì line-ending CRLF có thể làm mọi hunk "đổi"). Line-ending: file làm việc CRLF, git index LF → `file <path>` thấy CRLF còn git thấy LF → toàn file diff dù chỉ sửa vài dòng — chấp nhận được về chức năng (Python OK cả 2) nhưng nên biết trước.



## AdbKeyboard Patterns

- Broadcast `ADB_KEYBOARD_INPUT_TEXT` with base64 text extra

- On some devices (SM-G930W8), broadcast times out but text still enters → use `subprocess.Popen` fire-and-forget

- Alternative: `adb shell input text <plaintext>` works on most devices (no special chars)

- Enable: `ime enable com.github.uiautomator/.AdbKeyboard && ime set ...`



## VPN Integration Flow

1. Reconcile script needs `--proxy-mapping` argument

2. `reconcile_target` checks VPN after lock acquisition

3. After reboot, `_verify_vpn` waits for `tun0` (verification_timeout=300s for watcher's 30s poll)

4. When VPN is mapped, **skip the switcher-refresh reboot** — reboot kills VPN and the watcher may be disabled

5. Use `live_vpn_verifier=_check_tun0` in `acquire_device_lock` to bypass proxy readiness marker wait



## automation-core 0.2.40 API Migration

- `soft_reboot_and_wait(adb, serial=..., boot_timeout=..., proxy_timeout=...)` → removed

- New: `reboot_and_restore(adb, *, cleanup_before_reboot, recover_post_reboot, verify_post_reboot, boot_timeout=180, verification_timeout=120)`

- Callbacks are `Callable[[], object]` — no arguments, use closures to capture `adb`

- Example verify callback: `lambda: _verify_vpn(adb, target, proxy_mapping)`



## Coordinate Login Fallback

When Tiktok_Reg provider `login_one_account` fails (image nav), use coordinate-based flow:

```

Signup → "Bạn đã có TK? Đăng nhập" (540,1830)

→ "SDT/email/username" (561,851) → Tab Email (713,288)

→ input text <username> → Tiếp tục (540,1681)

→ input text <password> → Tiếp tục (540,1681)

→ dismiss security popup (996,923)

```

Use `adb shell input text` — broadcast may timeout.



## Pre-commit Checklist

- [ ] `python -m pytest tests/ -q` passes (ignore pre-existing `TIKTOK_REFERENCE_ROOT` failures)

- [ ] Entry added to `docs/ui-compatibility.md` with full contract

- [ ] Entry added to `reports/AUDIT_LOG.md`

- [ ] `git diff --check` clean

- [ ] All coordinate fallbacks have safety bounds (resolution check, marker verification)



## Background-process notifications: don't derail the active task



A background batch (e.g. `recovery-new-handler`, `run_tiktok_upload_batch`) that was launched **earlier in the session** will emit a `notify_on_complete` result when it exits. If the user has since moved on to a different topic (or is mid-investigation), the exit notification is **not** a request to pivot — acknowledge it in one line only if it needs a decision (FINAL_BLOCKED → ask whether to release the lock), and return immediately to what the user is actually working on. The user called this out explicitly (2026-08-06): "đang xử lý hermes mà tự nhiên nhắc task". Do not launch into a full status report of the background job when the user's active question is unrelated.





## RULE 3 BƯỚC FIX MỌI LỖI (2026-08-10, phủ all repo + core)



BẤT KỲ lỗi nào (UI dump/capture-invalid/popup/terminal, kể cả không phải UI) → TỰ chạy 3 bước fix NGAY, KHÔNG chờ user nhắc: B1 ATX-kill (chạy khi gặp lỗi bất kỳ) + B2 force-stop + B3 soft reboot (B2/B3 mỗi 1 lần/turn/máy) → lỗi lặp lại chỉ ATX-kill + coordinate fallback có evidence → fail MANUAL_REVIEW. Nguồn: PROJECT_RULES.md các repo Taadaa + automation-core/docs/ui-compatibility-contract.md (commit 2026-08-10).

