---

name: android-device-automation

description: Patterns for automating Android devices — VPN preflight, TikTok login flows, UI popup handling, AdbKeyboard input, and reconcile workflows across consumer repos.

---



# Android Device Automation


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

General patterns for automating Android devices (Samsung SM-G930 series) in consumer

repos that depend on `automation-core`. Covers TikTok login, account inventory,

VPN/proxy preflight, popup dismissal, and the reconcile workflow.



## VPN / Proxy Preflight (MANDATORY)



Before ANY device interaction after a reboot, the VPN must be connected. The

workbook `PROXYgandienthoai.xlsx` maps serials to proxy requirements.



```python

from automation_core.preflight import require_android_vpn, serial_is_mapped_in_workbook

from automation_core.adb import AdbClient



adb = AdbClient(adb_path, serial, default_timeout=20)

require_android_vpn(

    adb,

    required=serial_is_mapped_in_workbook(

        proxy_mapping_path, serial,

        serial_headers=("phoneId", "deviceId", "serial"),

    ),

)

```



This check MUST run:

- After acquiring device lock, before any device action

- In the `verify_post_reboot` callback of `reboot_and_restore`



If the proxy watcher (`gan-proxy/scripts/vi_c`) holds a lock, the device is NOT

ready — skip or wait; never force-run without VPN.



### Vichanger (vn.vichanger.app) quirk — refs `references/vichanger-vpn.md`



- Popup "No LSPosed access !!!" khi mở app = NHIỄU, kệ nó (máy VPN OK cũng không

  có LSPosed trong `pm list packages`).

- Blocker thật khi workflow fail `ACQUIRE_LOCKS` / `live VPN verifier failed ...

  tun0 does not exist` = VPN chưa connect; recovery 3-bước UI KHÔNG cứu được.

- "Invalid API Key!!!" = trường API Key trống, key là secret của user → báo

  blocker + hỏi, không tự nhập đại.

- User rule: kệ popup app, mở TikTok chạy upload TRƯỚC, recovery chỉ SAU khi

  workflow báo lỗi thật; không pre-dismiss / tự sửa VPN bằng tay.

- BẪY ORIENTATION: screencap có thể ra 1920x1080 (landscape) khi tưởng portrait

  → mọi `input tap` tọa độ portrait trượt. Đọc `img.size` (PIL) TRƯỚC khi suy

  tọa độ; nếu tap trượt nhiều lần → crop vùng nghi có nút + vision_analyze hỏi

  tọa độ, map ngược về ảnh gốc.



## Target Identity Reconciliation (Mandatory for Recovery)



A machine number is not sufficient target identity: workbook mappings can change

between a failed run and a later manual check. Before inspecting, resuming, or

running recovery from an artifact:



1. Read the incident artifact's recorded target/serial.

2. Resolve the **current** machine-to-device-ID mapping from the approved

   config/workbook, reading only the required mapping fields.

3. Compare them before acquiring or using a lock. If they differ, stop recovery:

   report `MACHINE_SERIAL_MAPPING_MISMATCH` with redacted identifiers and treat

   the old artifact as a different target until an operator reconciles it.

4. A read-only status probe may confirm the current mapped device is online, but

   must never be presented as evidence that it is the device in the old artifact.



This prevents replaying a capture/UiAutomator recovery against a different phone

that happens to have the same machine label.



### Farm rollout identity and naming



Machine numbers are the user-facing canonical labels. Never invent labels such

as "machine 337" from a serial suffix; resolve the number from

`taikhoan_run_safe.xlsx` (`May` + `Device ID`) and report that number. For a

farm-wide rollout, build and persist a complete machine→serial manifest first,

verify the expected range/count (for example 1–80), and use that same manifest

for mutation and final verification. The current `adb devices` count is only the

live-connectivity snapshot, not proof that the configured fleet is complete.



Before bulk installation, inventory `pm path <package>` on every mapped serial

and exclude devices that already have the target package. If a rollout is

interrupted, stop only its own process tree, re-inventory, and retry only missing

machines. A successful `install` exit code is not final evidence: verify package

presence and expected version per machine, with exactly one status row per mapped

machine.



Windows/Git Bash guardrails: strip trailing CRLF from mapping serials before

passing them to native `adb.exe`; redirect device-scoped ADB commands from

`/dev/null` so they cannot consume the mapping loop's stdin; avoid fragile

`xargs` positional-variable assumptions. A CRLF/stdin bug can falsely report an

entire valid farm as offline or process only the first row.



## Farm-wide APK rollout and completeness audit



When rolling out an APK across the farm, the machine mapping workbook is the scope authority. Do not treat the current `adb devices` count as the farm total: build the complete machine-to-serial set from `taikhoan_run_safe.xlsx` (`May` + `Device ID`), confirm the expected machine range/row count, then inspect every mapped serial. Before installing, query `pm path <package>` per explicit serial and exclude machines that already have the package. Use bounded concurrency, Windows-style paths for native Windows ADB, and per-serial result logs.



Acceptance is row-count preserving: every mapped machine must end as `OK`, `MISSING`, `OFFLINE`, or `WRONG_VERSION`, and the result file must contain exactly one row per mapped machine. For parity, compare a small explicit required app set against the reference machine; do not use the entire third-party/system package list as the definition of farm completeness because carrier/system apps legitimately differ. Current core set: Gmail `com.google.android.gm`, Outlook `com.microsoft.office.outlook`, Chrome `com.android.chrome`, WhatsApp `com.whatsapp`, TikTok `com.ss.android.ugc.trill`, and ViChanger `vn.vichanger.app`.



Shell pitfalls observed on Windows/Git Bash: strip CRLF from serials before passing to ADB; redirect each ADB command's stdin from `/dev/null` so it cannot consume the mapping file; avoid fragile `xargs` positional-variable assumptions. If a rollout is interrupted, stop only that rollout's process tree, re-inventory packages, and retry only missing targets. Never restart gateway/proxy-watcher/schedulers, touch live locks, force-stop TikTok, reboot, or clear data merely to install an unrelated APK.



Detailed procedure: `references/farm-apk-rollout-and-completeness.md`.



## Consent / Popup Dismissal



After TikTok data-clear or fresh install, multiple popups can appear:



### UniversalPopupActivity (consent popup)

- **PopupRule marker tuple = AND (tất cả markers phải có mặt) — đừng gộp 2 biến thể text vào 1 rule** (proven 2026-08-16, automation-core `tiktok_popup.py`): system dialog "Cho phép TikTok truy cập vào danh bạ" vs in-app "Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ..." — nếu gộp `("truy cập vào danh bạ", "kết nối với những người bạn biết")` vào 1 rule, dialog system không có cụm thứ 2 → AND fail → popup không đóng. Fix: tách thành 2 rule riêng (`contacts_permission_vi` + `contacts_permission_vi_connect`), mỗi rule 1 marker, cùng `_find_button` candidates set (`{"location_permission_vi", "contacts_permission_vi", "contacts_permission_vi_connect"}`). Khi thêm marker: nhớ cập nhật CẢ rule lẫn set xử lý nút.- **Activity**: `UniversalPopupActivity`

- **Detection**: use `dumpsys activity activities` (NOT `uiautomator dump` — it hangs on Samsung)

- **Dismissal**: swipe up from bottom



```python

activities_text = str(adb.shell(["dumpsys", "activity", "activities"]).stdout)

if "UniversalPopupActivity" in activities_text:

    adb.shell(["input", "swipe", "540", "1600", "540", "400", "300"])

```



### Google Sign-In Popup

- **Activity**: `AssistedSignInActivity` (package `com.google.android.gms`)

- **Dismissal**: back key



### Google Play Post-Install Popups (2026-07-29)

After `force-stop` + `monkey start`, Google Play Store may show on devices where it hasn't been fully initialized (first-time setup after factory reset):

1. **ToS**: `com.android.vending/...TosActivity` — "Điều khoản dịch vụ" with "Chấp nhận"/"Từ chối". Tap "Chấp nhận".

2. **PlayCore**: `com.android.vending/...PlayCoreAcquisitionActivity` — "TikTok cần tải các tệp bổ sung". Tap "Tải xuống qua Play".



Detection: check `current_package == "com.android.vending"` in the startup wait loop. After dismissing, re-issue `monkey -p <pkg> 1`. Handled by `_dismiss_play_popups()` in `account_inventory.py`.



### Profile Navigation Fallback (DEPRECATED -> ENFORCE STRICT XML-FIRST)

**CẤM TAP TỌA ĐỘ MÙ ĐIỀU HƯỚNG DƯỚI ĐÁY MÀN HÌNH (2026-08-21):**
- Thanh Bottom Navigation TikTok (1080x1920): Tab 1 Trang chủ [0,1794][216,1920], Tab 2 Cửa hàng, Tab 3 NÚT TẠO (+) CHÍNH GIỮA [432,1794][648,1920] (Tâm 540, 1857), Tab 4 Hộp thư, Tab 5 Hồ sơ [864,1794][1080,1920].
- BẤY TỌA ĐỘ RƠI VÀO CAMERA/LIVE: Khi fallback tap mù (972, 1857) hoặc swipe shade xuất phát tại Y=1800, nếu tab bar lệch hoặc có overlay/lag, cú chạm rơi thẳng vào nút Tạo (+) hoặc LIVE Studio -> popup "Để phát LIVE, bạn cần" / kẹt Camera.
- **Quy tắc bắt buộc:**
  1. Điều hướng Tab: BẮT BUỘC parse XML, tìm đúng Node UI (`text="Hồ sơ"`, `content-desc="Profile"`), lấy tâm từ `bounds` thật. Nếu không thấy Node -> fail-closed an toàn (`not-found`), TUYỆT ĐỐI CẤM fallback tọa độ mù.
  2. Lệnh swipe đóng thanh thông báo (Shade dismiss): Bắt đầu tại `Y <= 1540` (vd: `540, 1540 -> 540, 300`), CẤM xuất phát tại Y >= 1700 (đè nút +).
  3. AI Auto-Recovery: Ép runtime XML-first — trước khi `tap (x, y)`, đối soát (x, y) có nằm trong `bounds` của Node UI nào trong live dump XML không. Nếu không có node khớp -> TỪ CHỐI tap mù, fallback phím BACK (Keyevent 4).

### Camera / Creation Mode Classifier Invariants (2026-08-21)
- CẤM match substring từ đơn `"ảnh"`, `"tạo"`, `"đăng"` trên toàn màn hình — video feed có caption dạng "Ảnh" hoặc nhãn AI "Có chứa nội dung do AI tạo" sẽ bị classifier nhận nhầm là màn hình quay camera -> dừng máy oan.
- Nhận diện Camera chuẩn: Quét các element ở vùng cận đáy (`Y >= 1000`), yêu cầu EXACT match và phải xuất hiện ít nhất 2 chế độ quay KHÁC NHAU (`distinct modes >= 2`) gồm: `{"15s", "60s", "10 phút", "văn bản", "10m", "templates", "photo", "camera"}`. Bọc `try/except` an toàn cho `parse_bounds`.

### Follow Friends Popup Rule (2026-08-21)
- Gặp popup "Follow bạn bè của bạn" / "Follow friends suggestion": Quét và click toàn bộ các nút "Follow lại" / "Follow back" để tăng follow chéo tự nhiên, sau đó mới bấm "X" / BACK thoát về feed.



## TikTok UI Versions



| Version | Signup → Login path |

|---------|-------------------|

| 46.x (legacy) | Account switcher → Add account → "Sử dụng số điện thoại/email/tên người dùng" → Email tab |

| 44.2.3 (newer) | Account switcher → Add account → "Bạn đã có tài khoản? Đăng nhập" → "Sử dụng số điện thoại/email/tên người dùng" → Email tab |

| 37.x (machine 7) | Signup screen → back once → "Tiếp tục với email/tên người dùng" |



**Rule**: The `choose_login_method` code in the adapter must NOT hardcode one path.

Always check for text presence and fall through. The signup screen has both

"Tiếp tục với email" (signup) and "Bạn đã có tài khoản? Đăng nhập" (login link at bottom).



## AdbKeyboard & ADB Shell Text Input

- **IME**: `com.github.uiautomator/.AdbKeyboard`
- **APK source**: `D:\Taadaa\tiktok-luot nuoi acc\.ai-runs\*\app-sync\source_60\apks\com.github.uiautomator\00_base.apk`
- **Send text**: `am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64>`
- **Pitfall with AdbKeyboard**: On SM-G930W8, broadcast returns `result=-1` and ADB shell hangs after broadcast. Text IS entered successfully though — use fire-and-forget with short timeout (5-8s), don't wait for shell exit.
- **Alternative & ADB `input text` / `human_type` Rules (CRITICAL)**:
  - `adb shell input text <string>` splits arguments by shell whitespace on the device (`/system/bin/input text Hoang Tuoc` receives 3 args). Android's `input text` requires exact arguments; unescaped spaces cause the binary to abort or drop trailing words, leaving input fields empty (`firstName=""`) and triggering form validation errors (e.g. *"Hãy nhập tên"* / `STILL_ON_NAME`).
  - **`input_text(device_id, text)` Standard**:
    1. Tokenize text around `@` and `#` via `re.split(r'([@#])', str(text))`.
    2. Convert all spaces in non-symbol chunks to `%s` (`chunk.replace(" ", "%s")`).
    3. Send `@` as `keyevent 77` (`KEYCODE_AT`) and `#` as `keyevent 18` (`KEYCODE_POUND`).
  - **`human_type(device_id, text)` Standard**:
    1. Type char-by-char with random delay (60–220ms).
    2. Send `' '` (space) as `keyevent 62` (`KEYCODE_SPACE`).
    3. Send `@` as `keyevent 77` and `#` as `keyevent 18`.
    4. Escape shell metacharacters (`\`, `$`, `&`, `*`, `(`, `)`, `;`, `'`, `"`, `<`, `>`, `|`, `~`, `^`, `!`, `?`) with `\` prefix (e.g. `f"\\{ch}"`) to prevent command injection or syntax errors.
  - **Password Symbol Pool**: Limit generated password symbols to safe sets (`["@", "#", "!", "$"]`) verified against ADB shell escaping and OEM IME keyboards.
  - **Samsung Keyboard Tutorial Dismiss**: When `find_text_tap("BỎ QUA")` dismisses the first-run tutorial, do not execute dangling picker logic; cleanly re-tap the target field.



## 2FA / TOTP



TikTok accounts may require 2FA. The TOTP secret is stored in the tracking workbook

column `2FA`. Use `pyotp` to generate codes:



```python

import pyotp

code = pyotp.TOTP(totp_secret).now()

```



Codes expire every 30s — generate and submit immediately (don't generate ahead of time).



## Post-Login Popups



After successful login, dismiss these popups in order:

1. "Cho phép TikTok truy cập vào danh bạ?" → tap "TỪ CHỐI"

2. "Hãy cùng kiểm tra bảo mật nhanh nhé" → tap "Đóng" (top-right corner)

3. Privacy policy (`SparkActivity`) → scroll to bottom, tap "Agree"/"Đồng ý" (rendered in WebView, not detectable by uiautomator — use coordinate taps at y=1700-1850 after heavy scrolling)



## Reconcile Script Patterns



The reconcile script (`scripts/reconcile_tiktok_accounts.py`) does:

1. Acquire device lock

2. VPN preflight (with `--proxy-mapping`)

3. Inventory device accounts via `collect_device_inventory`

4. Compare with workbook

5. Login missing accounts

6. Verify



If inventory fails with a rebootable error, soft-reboot and retry. The `_soft_reboot`

function MUST pass `proxy_mapping` to `reboot_and_restore`'s `verify_post_reboot`

callback, which calls `require_android_vpn`.



### Parent-held lock across reboot



If reconcile intentionally retains the machine+serial lock across reboot, it must not merely wait for a proxy watcher that needs the same lock. Use `reboot_and_restore(..., wait_for_proxy_ready_after_reboot=...)` so the parent invokes the existing proxy provider under its own lease, then verify `tun0` plus Android VPN. The provider must verify the parent PID/host/machine/serial/lock-id before loading the scoped mapping; never expose the proxy through argv/logs.



When using `acquire_device_lock(..., live_vpn_verifier=fn)`, ensure the core version propagates `fn` into `wait_for_proxy_ready`. A stale `proxy_pending` marker plus `verifier_calls=[]` is evidence of a propagation regression. Fix in isolated automation-core worktree, use the merge guard, bump from the current version, run tests with `PYTHONPATH=src`, build/verify/install the wheel between live runs, then live-probe lock acquisition.



## automation-core API Notes (v0.2.40+)



- **User rule (2026-08-12): LUÔN ưu tiên lấy từ automation-core nếu có — profile/account-switcher navigation không tự viết lại.** Core canonical module: `automation-core/src/automation_core/tiktok/account_switcher.py` (duck-typed adapter `dump_ui`/`_tap`/`_back`, replay-testable từ UI XML). Dùng: `open_profile_root(adapter)` (vào tab Hồ sơ), `find_switcher_anchor(...)`, `open_switcher(...)`/`open_account_switcher(...)`, `select_exact_account(adapter, account)`, `verify_selected_account(...)`, `list_accounts(xml)`, `leave_profile_subpage(...)`, `recover_navigation_failure(adapter, failure, attempts=)`; fail-closed qua `AccountSwitcherError(code, message)`. Trước khi viết navigation mới trong consumer: grep core `tiktok/` + `ui.py` trước, chỉ tự viết phần consumer-specific (selector chốt từ dump thật, business flow).

- `reboot_and_restore(adb, *, cleanup_before_reboot, recover_post_reboot, verify_post_reboot, boot_timeout=180)` — all 3 callbacks are REQUIRED keyword-only args

- `wait_until_unlocked(adb)` — use as `recover_post_reboot`

- `prepare_device(adb)` — returns `DeviceReadiness`; use inside `verify_post_reboot` (or wrap with VPN check)

- `soft_reboot_and_wait` was REMOVED in v0.2.40; use `reboot_and_restore` instead

- **`AdbClient` is per-device — create one per serial for every device-scoped call.** A client built with `serial=None` (e.g. for `list_devices()`) MUST NOT be reused for `check_android_vpn`/`require_android_vpn`/`shell`. Unscoped commands on the multi-device farm fail `adb.exe: more than one device/emulator`, which surfaces as `tun_up=false, vpn_connected=false` for EVERY machine and looks like a farm-wide VPN outage (verified 2026-08-12, tiktok-follow probe: 78/78 machines "VPN failed" before the fix, all passed after). Fix: construct `AdbClient(adb_path, serial=<serial>)` inside the per-machine loop.

- `DeviceLockLease.release_with_audit().released_paths` elements are `str`, not `Path` — `[p.name for p in audit.released_paths]` raises `AttributeError: 'str' object has no attribute 'name'` AFTER release already succeeded; only the formatting crashed. Format with `str(p)`. When a release print crashes, verify the lock dir before assuming release failed.



## SM-G930 Model Differences



| Model | Behavior |

|-------|----------|

| SM-G930F | Standard. Broadcast works normally. |

| SM-G930W8 | Broadcast hangs shell. Swipe-unlock pattern may differ. |



## Reference Files



- `references/anti-bot-profile-generation-patterns.md` — Anti-bot profile generation standards for farm registration: natural Vietnamese name combinations (2-word, 3-word, 4-word with middle names), 10+ humanized username styles with dot-separators/suffixes, and distributed password entropy without static suffixes (@Ks).
- `references/anti-detect-jitter-standards.md` — Anti-detect jitter standards: UI pixel tap/swipe variance (±1..6px with boundary clamp [0, 2400]), timing sleep jitter, and continuous scheduling jitter to prevent cluster burst on 80-200 machine farm.
- `references/tiktok-coordinates.md` — exact coordinates, resource-ids, workbook paths, and popup dismissal patterns (verified 2026-07-29)

- `references/gmail-otp-magic-link.md` — Gmail OTP/magic-link reading for TikTok reg: TikTok sends a link not a code, search-loop bugs + fixes, auto-sync OFF root cause, Gmail live-check on OTP timeout (incl. identity-verify classifier gap), CAPTCHA-dead mailbox delete flow via add-mail repo, existing-account login, MACHINE_DEVICES int/str key pitfall

- `references/vichanger-vpn.md` — Vichanger VPN app (vn.vichanger.app): tun0 verifier, LSPosed popup = noise, "Invalid API Key" = user secret, orientation trap, config machine: copy-paste error
- `references/stock-rom-audit-and-auto-boot-patterns.md` — Stock ROM vs Mod ROM audit recipes across farm devices, ADB getprop non-destructive fleet checks, Knox bit interpretation, and auto-boot on power plug-in (LPM) rules.

- `references/apk-harvest.md` — clean APK harvest: pull installed apps to a bank for reimaging (adb pull directory-preexists bug, Windows-path bug, split-APK recipe, farm package map)

- `references/gan-proxy-watcher-ops.md` — gan-proxy watcher ops: tray→watcher respawn stack, `schtasks /End`+`/Run` restart, XML `-ProxyMapping` update, protocol-v2 lock/takeover semantics, mapping-workbook Excel-lock diagnosis, watcher-generation-bound readiness proof, structured post-reboot owner ACK, and soft-reboot auto-assign testing

- `references/navigation-only-one-shot-smoke.md` — audited one-shot Android navigation smoke: canonical persistent UI capture, run-global restart budget, exact 8-byte verdict binding, pre-mint live lock gate, launch-ledger binding, zero-business-action proof, and verified `FAILED_LOCKED` retention.



## Avatar-farm batch (2026-08-15) — multi-nick devices, recents-escape, rule 3-bước per-signature



### Mỗi máy có 2 nick (Tik1 + Tik2), CÙNG device

- Workbook Tik1.xlsx / Tik2.xlsx là nguồn sự thật: mỗi máy (1-80) có 1 dòng/nick, cùng `device ID` nhưng ID account + Folder Video khác nhau. Muốn up avatar/đăng nick nào → chạy `run_tiktok_upload_avatar.ps1 -Tik <N>` đúng workbook nick đó. **KHÔNG tự suy luận nick từ config-machine-N.yaml** (config chỉ là default; flag `-Tik` thắng).

- Ví dụ máy 39: Tik1=`thanh.huyn4934` folder 305, Tik2=`tachau1704` folder 306 — chạy 2 lần riêng cho 2 nick.

- `AVATAR_SOURCE_MISSING: D:\video goc\<folder>` = thiếu avatar trong `video goc` (chỉ có ở `TIKTOK-videonuoinick`) → copy `D:\TIKTOK-videonuoinick\<folder>\avatar.jpg` sang `D:\video goc\<folder>\avatar.jpg` rồi retry. Không phải thiếu ảnh gốc.

- `Missing required fields: ID TikTok` = workbook cột `ID` trống (None) cho máy đó → KHÔNG chạy được, báo user điền ID / xác nhận bỏ qua. Rà cột ID trước batch.

- Manifest: `resources` phải khớp `-ForceAvatarMachineList`; lệch → `INVENTORY_ERROR: assignment preflight failed` ngay.



### COMPAT-RECENTS-ESCAPE-001 — thoát màn Recent apps khi uiautomator chết

Nhiều máy kẹt ở Recent apps (App Switcher) sau B3 reboot: `close_all_recent_apps` cần uiautomator dump để tìm nút clear-all, nhưng uiautomator chết (non_xml_ui_dump) → fail → app không launch → `AVATAR_UPLOAD_MENU_MISSING`. **Fix: probe focused activity trước mỗi relaunch; nếu là recents → bấm HOME (`keyevent 3`) thoát (không cần dump) rồi mới launch.** Đã encode vào `_handle_open_tiktok` (state_machine.py, COMPAT-RECENTS-ESCAPE-001). Dấu hiệu nhận diện: focused activity chứa `recents`/`recent` (vd `.recents.RecentsActivity`).



### Rule 3 bước — B1 LIÊN TỤC, B2/B3 bounded PER-SIGNATURE (user xác nhận 2026-08-15)

- **B1 ATX-kill: chạy LIÊN TỤC mỗi lần gặp lỗi UI/dump, kể cả giữa các retry attempt cùng state — không giới hạn số lần.** (Đã thêm `_recover_uiautomator` vào `_execute_with_ui_retry` trước mỗi attempt; mọi handler đi qua state loop duy nhất → phủ toàn repo.)

- **B2 relaunch / B3 reboot: TỐI ĐA 1 lần / signature** (per-signature, không phải 1 lần/tổng turn). Cùng chỗ fail lần 2 → KHÔNG reboot nữa; chỗ KHÁC (signature khác) → vẫn được reboot. Bỏ giới hạn tổng `soft_reboot_recovery_max_total`.

- CONNECT_DEVICE startup fail (`DEVICE_STARTUP_FAILED: non_xml_ui_dump`) phải chạy đủ B1→B2→B3 trước MANUAL_REVIEW (trước đây chỉ B1 rồi return False).

- Reboot máy lỗi VPN: watcher tự reconnect sau boot; `adb reboot` rồi đợi boot (`get-state` = device), chờ ~60s cho VPN, rồi chạy lại batch. Chỉ làm khi user yêu cầu (VPN vốn do watcher quản lý, CẤM probe/chỉnh tay).



### Verify nick thật trên máy (avatar profile)

Mở TikTok: `am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity` (MainActivity có thể `Error type 3`). Vào profile: tap tab Hồ sơ bottom-right ~(960,1830). Màn Profile có nút `+ Thêm tiểu sử`, username `@...`. Verify avatar: ảnh người thật (không placeholder xám/camera icon). Lưu ý: tap (540,1840) là nút + → composer, KHÔNG phải profile. Màn hình Recent apps (App Switcher) nhìn thấy card TikTok nhưng KHÔNG phải app đang mở — phải tap card hoặc HOME trước.



## Upload-picker identity and fail-closed selection



When an Android media picker hides filenames, a successful push/MediaStore index is only proof that the target exists on-device; it is **not** proof that a visual tile represents that target. Never select a tile solely because it is newest, top-left, has a duration overlay, or is visually plausible.



Safe order for upload selection:

1. Prefer a dedicated album/path where the exact filename is exposed and verify the filename before tapping.

2. If filenames are hidden, use source-thumbnail/frame matching only when the match is unique, above a documented threshold, and has a clear margin over the next candidate; capture and recapture evidence around the selection.

3. If identity is ambiguous, return a target-unverified/manual-review result before tapping. Do not trade correctness for a higher apparent completion rate.



After a post tap timeout, treat submission as UNKNOWN/at-most-once until an independent published-surface verifier proves success. Do not repost merely because the workbook count is unchanged; do not update the workbook on unverified success. Keep target identity bound to machine + serial + account + video number throughout recovery so another machine (for example 30 vs 74) cannot be accidentally acted on.



## Narrowly scoped orientation repair (settings-only)



When the user explicitly authorizes restoring screen rotation for a fixed list of

serials, treat this as a device-state repair, not a TikTok workflow:



1. Before touching ADB, check the live process table for `social_reg` and

   `_run_all_targets`; if either is running, stop and report the blocker. Do not

   infer safety from the repo path alone.

2. Use the explicitly requested/approved ADB binary and an explicit `-s <serial>`

   on every command. Confirm all requested serials appear as `device` in one

   `adb devices` snapshot. Never broaden the target set from a machine/STT label.

3. Capture per-serial before evidence using only read-only commands:

   `settings get system accelerometer_rotation`, `settings get system user_rotation`,

   `wm size`, and `dumpsys input`'s `DisplayViewport` orientation/logical frame.

4. Apply only Android-safe rotation settings:

   `settings put system accelerometer_rotation 0` and

   `settings put system user_rotation 0`. Do not open apps, launch Chrome/Gmail,

   read mail, retry registration, or reboot. Use `wm set-user-rotation lock 0`

   only if the requested settings do not produce portrait on verification.

5. Re-read both settings and the viewport. Portrait evidence requires

   `accelerometer_rotation=0`, `user_rotation=0`, viewport `orientation=0`, and a

   portrait logical frame (height > width, e.g. `1080x1920`). Report before/after

   values separately for every serial; if any target remains non-portrait, report

   the exact blocker and do not add recovery actions.



This procedure is intentionally narrower than the normal workflow/lock/VPN

orchestration. A successful ADB exit code alone is not proof; the post-change

settings and viewport are the acceptance evidence. Session-specific command and

output details are in `references/orientation-repair.md`.



## Progressive live-flow authorization and truthful progress



When the user says “run the real flow and ask me when you reach each step,” do not remain in repeated offline audit or ask about hypothetical later screens. Finish the offline gate once, then run the **canonical production path** through the currently authorized non-destructive stage and stop only at the next real protected boundary (business mutation such as Follow/Post, identity ambiguity, OTP/2FA/CAPTCHA/secret, permission/payment prompt, reboot/destructive recovery, or foreign/retained lock).



- Authorization remains layered: launch/Feed proof does not imply profile navigation, account switching, Follow/Post, reboot, or lock takeover. The latest user wording may broaden the operational sequence, but never silently broadens protected actions.

- Never describe delegation acceptance as a live action. Use evidence states: `worker_dispatched` (no device proof yet), `preflight_complete`, `device_action_started` (real target process/owned lease/first live artifact), then `state_reached` (package/activity/UI proof).

- If a worker has an API/transport failure, reconcile the exact target process, **both** machine+serial lock aliases, and new artifacts before retrying. All absent means `zero device action`; anything ambiguous blocks a parallel retry.

- Parse `--machine` as an exact numeric argument; substring matching machine `1` also matches `10` and gives false process-conflict evidence.

- If a canonical per-machine config path is absent, an approved fallback may read only machine/serial mapping fields from safe sources and require agreement; never print the full serial or read unrelated account/credential columns.

- Status replies lead with the boundary: `Chưa vào Follow`, `Đã tới Feed`, or `Dừng tại <boundary>`; test history is secondary.



Detailed execution and evidence recipe: `references/progressive-live-flow-boundaries.md`.



## Read-only probe orchestration (lock → VPN preflight → capture → release)



For read-only UI probes (mode2 selector calibration, "check the real screen" rule)

that must NOT tap/swipe/keyevent/force-stop/relaunch/reboot/clear-data:



1. **Selection loop** over machines in workbook order (first-row serial per machine):

   - Skip offline serials (not in `adb devices`).

   - Skip live-locked machines: read `machine_<N>.lock.json`/`serial_<S>.lock.json`

     with `owner_active=true` AND owner pid alive (verify with `wmic process where

     "ProcessId=N" get ProcessId`); also skip machines targeted by a live

     `tiktok_workflow` process (`wmic ... get CommandLine` + regex `--machine N`).

   - For each candidate: acquire own `DeviceLock` → run VPN preflight → if not

     allowed, release and try next machine; first machine that passes = target.

2. **Lock with `bypass_proxy_readiness=True`** to avoid the 180s

   `wait_for_proxy_ready` stall, then run the VPN check YOURSELF immediately after

   (mandatory ordering: lock check → VPN preflight). Use non-raising

   `check_android_vpn(adb, required=serial_is_mapped_in_workbook(...))` for a probe

   (records `tun_up`/`vpn_connected` evidence) instead of raising

   `require_android_vpn`.

3. **Capture while holding the lock**: run the repo probe tool

   (`tools/dump_selectors.py` in tiktok-follow) as a subprocess, plus `dumpsys

   activity activities`/`dumpsys window` for current activity evidence.

4. **Release in `finally`** via `lease.release_with_audit(...)`; verify the lock

   dir afterwards contains only pre-existing foreign locks.

5. Report: machine number, serial suffix (4 chars) only, online/activity/VPN/lock

   evidence, artifact absolute paths, and blockers (e.g. foreground = launcher not

   TikTok → selector inference deferred, no launch allowed in read-only scope).



**`am start` rc=0 KHÔNG phải bằng chứng launch — đọc stdout/stderr** (live 2026-08-12,

tiktok-follow máy 1): `am start -W -n com.ss.android.ugc.trill/.main.MainActivity`

trả rc=0 nhưng stdout chứa `Error type 3` + `Activity class {...} does not exist`

→ component không tồn tại/không exported, launch KHÔNG xảy ra (màn vẫn launcher).

Trong probe/read-only scope: KHÔNG thử component khác (relaunch bị cấm) — ghi

blocker `TIKTOK_NOT_FOREGROUND`. Trước launch nên resolve activity thật bằng lệnh

read-only `adb shell cmd package resolve-activity --brief <pkg>` (hoặc sử dụng

`monkey -p <pkg> 1` khi được phép launch) — `.main.MainActivity` không phải lúc nào

cũng là launchable activity trên mọi bản TikTok của farm. TikTok 46.3.3: launcher

thật = `com.ss.android.ugc.aweme.splash.SplashActivity`.



**`am start -W` trả `Status: timeout` KHÔNG = fail:** splash TikTok render >10s

(`WaitTime: 10149`), nhưng `mResumedActivity` đã là TikTok ngay sau đó. Sau launch

phải poll `dumpsys activity activities` cho tới khi `mResumedActivity` chứa pkg;

splash kéo dài = dump còn ít nodes (~58 như launcher) → chờ thêm rồi capture lại

(189 nodes khi vào feed). Khi splash vẫn ở foreground sau 60s: ghi

`TIKTOK_SPLASH_STUCK` + evidence, không recovery trong scope read-only.



Feed marker evidence (từ dump thật 2026-08-12 máy 1, TikTok 46.3.3, parse XML — vision 401 không chặn

được vì XML là nguồn evidence chuẩn): feed có `Trang chủ`, `Tìm kiếm`, `Hồ sơ`, `Hộp thư` + header

`Đã follow`/`Bạn bè`/`Đề xuất` (feed filter — KHÔNG phải follower evidence). Muốn chốt selector

Follower tab phải có dump màn Profile + Follower list; đứng ở feed chỉ ghi evidence + defer.



**Phân quyền device mutation theo MỨC, không gộp (user gating 2026-08-12):** user cho "launch TikTok máy 1 để probe"

KHÔNG tự suy ra quyền tap điều hướng (mở tab Hồ sơ/Follower) hay follow. Mỗi lớp mutation (launch → tap navigate

→ follow) phải clarify riêng; clarify 60 phút không phản hồi = DỪNG, lưu evidence + blocker, không hành động tiếp

và KHÔNG gọi lại worker probe tự ý mở rộng scope.



**Máy có thể rớt khỏi `adb devices` ngay sau probe** (dump treo/wedge): ghi evidence

offline/disconnect, không recovery trong scope read-only. Trước khi chạy probe tiếp

trên máy cũ: `adb devices` lại; nếu device decline/offline, chọn sau khi máy back online.



Full recipe + session detail: `references/read-only-ui-probe-orchestration.md`.



### Audited navigation-only one-shot smoke



When a live smoke may launch/tap/type/back but must never execute the protected business action, do **not** transplant the shell-dump/private-recovery recipes from ad-hoc diagnostics. Use the public persistent capture API, a run-global one-restart budget, exact-byte audit binding, and a final live lock preflight **after audit but before authorization minting**. A live foreign owner on either machine or serial alias is terminal `BLOCKED_SAFE`: do not mint, kill, release, or broaden takeover. On failure after lease acquisition, retain and independently verify `failed_locked`; on success, release only after destination + final-Feed + watcher gates. Full design and regression matrix: `references/navigation-only-one-shot-smoke.md`.



**Probe có navigation (tap tab Hồ sơ/Follower) — cấp mutation thứ 2 (2026-08-12, tiktok-follow):**

khi user authorize riêng "tap điều hướng" (khác launch, khác follow), giữ nguyên dàn

lock → VPN → dump gates, nhưng tap PHẢI semantic từ dump thật (parse dump → chọn node

fullmatch text/content-desc → tap center từ bounds → chờ render → dump_selectors recapture),

KHÔNG coordinate mù. Bằng chứng navigation thành công = activity marker qua `dumpsys

activity` (vd màn Follower list = `com.ss.android.ugc.trill/com.ss.android.ugc.profile.

business.ur.following.ui.FollowRelationTabActivity`) + dump PROBE_OK ở màn đích. Feed có

thể chứa 2 node cùng nhãn (vd bottom-nav "Hồ sơ" fullmatch vs avatar node

content-desc "Hồ sơ <username>") — luôn chọn node fullmatch, không substring.



**Crash sau khi dump PROBE_OK → rebuild manifest từ artifact, KHÔNG chạy lại probe**

(2026-08-12): nếu probe crash ở khâu ghi manifest (vd `TypeError: unsupported operand

type(s) for +: 'WindowsPath' and 'str'` khi `OUT_DIR/"manifest_"+TS` — phải

`OUT_DIR / f"manifest_{TS}.json"`), mọi dump đã PROBE_OK vẫn còn nguyên — viết script

ngắn đọc lại các file `.json`/`.xml` dump thật + log stdout để tái dựng manifest + node

evidence, KHÔNG re-run toàn bộ probe (tránh tap trùng lần 2 lên máy thật — vi phạm

nguyên tắc không đụng máy nhiều lần và có thể đổi trạng thái màn hình).



## Live upload acceptance (bắt buộc)



- Unit/full tests chỉ chứng minh code không regression; **không phải bằng chứng live thành công**. Khi user yêu cầu sửa lỗi upload, phải chạy một live canary đúng target sau khi test xanh, trừ khi user nói rõ chỉ review.

- Chỉ báo upload thành công khi có đủ bằng chứng độc lập: report `status=SUCCESS`, `post_verified=True`, profile tile count tăng đúng baseline + 1, workbook **đúng path mà config runtime dùng** đã tăng counter, và machine+serial locks đã release. Exit code 0 một mình không đủ.

- Trước khi verify workbook, đọc `workflow_workbook`/`device_mapping_workbook` từ config live. Không được kiểm tra file legacy khác path rồi kết luận thất bại/thành công; nếu report và workbook lệch nhau phải reconcile path trước khi báo.

- Sau Post tap timeout, coi submission là `UNKNOWN`/at-most-once cho đến khi published-surface verifier chứng minh. Không repost chỉ vì workbook chưa tăng.



## Upload-picker identity và fail-closed selection



- Push thành công/MediaStore index chỉ chứng minh target tồn tại trên thiết bị, **không chứng minh tile hình ảnh là target**.

- Thứ tự an toàn: album/path riêng có filename -> visual source-frame match duy nhất với threshold + margin -> nếu mơ hồ trả `VIDEO_PICK_TARGET_UNVERIFIED` trước khi tap. Không dùng newest, top-left, duration overlay hoặc tile “trông giống” làm identity.

- **Pitfall metric fail trên thumbnails bị crop/overlay/nén (2026-08-13, máy 45)**: correlation pixel 64x64 grayscale ra 0.09-0.18 (< threshold 0.35) dù tile picker GIỐNG HỆT frame video (vision xác nhận cùng nhân vật/cảnh). Nguyên nhân: thumbnail picker = crop 1:1 vuông + badge thời lượng + vòng tròn chọn + nén mạnh — phá tín hiệu pixel với video có emoji/sticker nội dung (render-script random). Push/MediaStore/tile đều ĐÚNG. **Khi data đúng mà corr thấp → đổi metric sang feature match (ORB/SIFT + ratio test hoặc HSV histogram), không retry/tuning ADB.** Đo lại ngoài luồng phải self-crop tile từ grid screenshot theo bounds thật (scan hàng trắng tìm tile; KHÔNG so full-screen artifact với frame). Chi tiết + số đo: tiktok-consumer-automation `references/video-pick-metric-render-random-20260813.md`.

- Sau khi sửa handler, phải có regression test cho ambiguous picker không tap; sau đó bắt buộc live canary và verify profile/workbook/lock như mục acceptance trên.

- Target identity phải giữ xuyên suốt recovery: machine + serial + account + video number; không để nhầm máy (ví dụ 30/74).



## Recovery lock handoff



- `MANUAL_REVIEW` có thể giữ lease trạng thái `handoff` dù process đã chết. Xác minh PID cùng host trước khi reclaim.

- Với protocol-v2, ưu tiên cơ chế takeover/reclaim có audit của core; không hand-delete lock sống hoặc xóa lock chỉ vì `tasklist` rỗng. Nếu phải xử lý legacy stale lock, xác minh bằng `wmic process where "ProcessId=N" get ProcessId,CommandLine` và xử lý **cả** machine + serial lock.



## Pitfalls

- **Wi-Fi Toggle, Provisioning & Public IP Inspection on Non-Rooted S7 Devices (2026-08-29 / 2026-08-30)**:
  - **Wi-Fi Provisioning & Connecting via UI / atx-agent**:
    - Stock S7 (Android 8.0/7.0) KHÔNG có `wpa_cli` (`wpa_cli: not found`) và `cmd wifi` (`No shell command implementation`). Lệnh `am start -a android.settings.WIFI_SETTINGS` chỉ mở màn hình quét chứ không tự nhập pass / kết nối SSID mới.
    - **Quy trình kết nối Wi-Fi tự động chuẩn**:
      1. Wakeup + HOME + Vuốt mở khóa (`keyevent 224` + `keyevent 3` + `input swipe 540 1500 540 300 300`).
      2. Start daemon atx-agent: `/data/local/tmp/atx-agent server -d` + port-forward `18000+may` -> `7912`.
      3. Bật Wi-Fi `svc wifi enable` + mở Cài đặt `am start -a android.settings.WIFI_SETTINGS`.
      4. Vuốt về đầu danh sách (`input swipe 540 500 540 1500 300`), gọi JSON-RPC `dumpWindowHierarchy` lấy tọa độ node `text="<SSID>"` -> `input tap cx cy`.
      5. BẮT BUỘC đối soát `alertTitle` khớp SSID (tránh tap nhầm khi list cập nhật vị trí). Nếu lệch: bấm THOÁT (`android:id/button2`), vuốt và tìm lại.
      6. Khi hiện `com.android.settings:id/password`: `input text <pass>` -> tap `KẾT NỐI` (`android:id/button1` / tâm `853, 897`).
      7. Poll `dumpsys wifi` kiểm tra `mWifiInfo` có `SSID: <target_ssid>` và `Supplicant state: COMPLETED`.
      8. Nhấn HOME (`keyevent 3`) thoát màn hình Cài đặt sạch sẽ.
  - **Wi-Fi Toggle & Reconnect**: Dùng `adb shell "svc wifi disable"` và `adb shell "svc wifi enable"`. Chờ 5-8s để supplicant hoàn tất state `COMPLETED` và DHCP cấp IP cho `wlan0`.
  - **Kẹt Wi-Fi Chip (UNINITIALIZED / ApStaDisabledState / No such device wlan0) & Chẩn đoán Phần cứng vs Reset Cài đặt Mạng (2026-08-30)**:
    - **Dấu hiệu nhận biết**: Màn hình Cài đặt kẹt ở "Đang bật…", `dumpsys wifi` báo `Wi-Fi is unknown state` hoặc `ApStaDisabledState`.
    - **Chữ ký lỗi phần cứng (Hardware Failure Signatures)**:
      1. Logcat HAL: `android.hardware.wifi@1.0-service: Could not read interface state for wlan0 (No such device)`, `Failed to set WiFi interface up`, `Failed to start legacy HAL: UNKNOWN`, `HalDeviceManager: configureChip error: 9 (unknown)`.
      2. Kernel Interfaces: `ip link` hoàn toàn không có interface `wlan0` (kernel không phát hiện thiết bị trên bus SDIO/PCIe).
      3. Bluetooth Combo Chip: `dumpsys bluetooth_manager` bị `ENABLE_TIMEOUT` khi bật (chip combo Wi-Fi + BT Broadcom/Murata trên mainboard S7 bị chết IC hoặc bong chân do nhiệt độ cao).
    - **Quy trình Reset Cài đặt Mạng loại trừ phần mềm qua ADB**:
      - Mở menu Đặt lại: `am start -n com.android.settings/.Settings\$PrivacyResetSettingsActivity` -> tap "Đặt lại" -> tap "Khôi phục cài đặt mạng" -> tap "XÓA CÁC CÀI ĐẶT" -> `reboot`.
      - Nếu sau reboot lỗi `wlan0 (No such device)` vẫn tái diễn -> 100% hỏng phần cứng IC, không thể cứu bằng phần mềm.
    - **Xử lý vận hành an toàn**:
      - Tắt loop quét driver để giảm tải CPU & nhiệt: `adb shell svc wifi disable`.
      - **Tương thích Box LAN**: Trong hệ thống Box LAN (cấp mạng qua cáp `eth0` và điều khiển qua ADB over IP/LAN), máy hỏng Wi-Fi vẫn hoạt động bình thường 100%, không cần thay hay sửa chip Wi-Fi. Với Box USB hiện tại, ưu tiên dùng máy làm node render video offline hoặc cất dự phòng chờ chuyển Box LAN.
  - **Routing / Gateway Limit**: Dàn Samsung S7 chạy ROM gốc không có `su` (`/system/bin/sh: su: not found`, `adbd cannot run as root in production builds`). Lệnh `ip route change/add` từ shell bị chặn `Permission denied`. Mọi can thiệp Gateway/DNS bắt buộc cấu hình từ DHCP Server (MikroTik/Router/AP) hoặc gán Static IP trong Android Settings, không thể can thiệp bằng `su -c 'ip route ...'`.
  - **Kiểm tra Public IP khi không có `curl` trong shell (CDP / Abstract Socket)**: Thiết bị Android không có sẵn binary `curl`. Cách đọc IP ngoại mạng tin cậy 100%:
    1. Mở trang IP bằng Samsung Internet hoặc Chrome: `adb shell am start -n com.sec.android.app.sbrowser/.SBrowserMainActivity -d https://api.ipify.org`
    2. Forward socket DevTools: `adb forward tcp:<port> localabstract:Terrace_devtools_remote` (hoặc `chrome_devtools_remote`).
    3. Kết nối WebSocket tới DevTools page endpoint và gửi `{"method": "Runtime.evaluate", "params": {"expression": "document.body.innerText"}}` để đọc chính xác địa chỉ IP public của thiết bị.
    4. Xóa forward port và bấm HOME (`keyevent 3`) để trả máy về trạng thái sạch.

- **Gmail App Onboarding / Setup Wizard Blocker (2026-08-29)**:
  Khi mở App Gmail (`com.google.android.gm`) sau khi thêm tài khoản hoặc trong các phiên mới, app thường bị chặn bởi 3 màn hình Onboarding:
  1. *"Mới có trong Gmail"* (`welcome_tour_got_it`) -> tap nút `"OK"` (tâm `540, 1836`).
  2. *"Bạn có thể sử dụng ứng dụng này với tất cả địa chỉ email..."* (`action_done`) -> tap nút `"ĐƯA TÔI TỚI GMAIL"` / `"TAKE ME TO GMAIL"` (tâm `540, 1836`).
  3. *"Google Meet hiện đã có trong Gmail"* (`next_button`) -> tap nút `"Đã hiểu"` / `"Got it"` (tâm `848, 1614`).
  Nếu không vượt qua onboarding này, luồng kiểm tra `_gmail_mailbox_state` sẽ không thấy danh sách hòm thư và tưởng nhầm là tài khoản chưa được đăng nhập (`target_account_not_verified`). Bắt buộc bọc helper `_dismiss_gmail_onboarding` tự động bấm qua các màn hình này ngay sau khi mở Gmail.

- **Samsung Keyguard Screen-Lock, Post-Reboot Revert & Permanent Disable (2026-08-29 / 2026-09-03)**:
  Khi thiết bị Android (Samsung S7 / SM-G930 series) khởi động lại (reboot rạng sáng, watcher restart, crash loop, sụt nguồn), hệ thống Android tự động nạp lại giá trị mặc định từ ROM: `screen_off_timeout = 600000` (10 phút) và bật lại màn hình khóa (`lockscreen.disabled = 0`).
  Nếu chỉ set tạm `screen_off_timeout` trước đó mà không khóa cấp hệ thống, sau khi reboot thiết bị nằm trong queue chờ (ví dụ `queued_v2`) quá 10 phút sẽ tự tắt màn hình -> rơi vào màn hình khóa Samsung Keyguard (`com.android.systemui`, *"Vuốt màn hình để mở khóa"* / `showing=true`, focus về `StatusBar`), làm worker nhấc máy bị mất focus và kẹt phiên.
  - **Mở khóa khẩn cấp ngay lập tức qua ADB**: `adb shell "wm dismiss-keyguard; input keyevent 82"` (`keyevent 82` = MENU/Unlock, lập tức giải phóng Keyguard về Home/App).
  - **Quy trình khóa vĩnh viễn màn hình khóa & chống tắt màn hình sau reboot (MANDATORY)**:
    1. `adb shell "locksettings set-disabled true"` (Khóa cấp hệ thống Android).
    2. `adb shell "settings put secure lockscreen.disabled 1"` (Vô hiệu hóa secure keyguard).
    3. `adb shell "settings put system screen_off_timeout 2147483647"` (Max Int - không bao giờ tắt màn hình).
    4. `adb shell "settings put global stay_on_while_plugged_in 7"` (Luôn sáng màn hình khi cắm cáp USB/AC/Wireless).
    5. `adb shell "settings put secure lock_screen_lock_after_timeout 2147483647"`.

- **ShopClone7 / CloneFBIG Supplier API Truncation vs Web UI (2026-08-29)**:
  Khi mua tài khoản Hotmail Graph API qua endpoint API của ShopClone7 / CloneFBIG (`/api/buy_product`), dữ liệu JSON trả về có thể bị cắt cụt trường `refresh_token` (chỉ còn ~101 ký tự thay vì ~457 ký tự chuẩn MSA Artifacts do serializer của shop giới hạn độ dài chuỗi). Để lấy token chuẩn đầy đủ 100%, hãy trích xuất dữ liệu trực tiếp từ Web UI (bảng đơn hàng / thuộc tính `data-checkbox` qua Chrome CDP).

- **Google Add Account Webview `ERR_CONNECTION_RESET` / "Đã xảy ra sự cố" (2026-08-29)**:
  Khi vào Cài đặt Android / Gmail -> Thêm tài khoản Google và bị báo lỗi ngay *"Đã xảy ra sự cố. Vui lòng quay lại và thử một lần nữa"* kèm logcat `E Auth: [MinuteMaidActivity] Error from MinuteMaidFragment: net::ERR_CONNECTION_RESET`:
  1. **Không kết luận vội là do IP/Proxy**: Proxy vẫn có thể sống và mở được web bên ngoài bình thường.
  2. **Kiểm tra cách ly**: Thử mở `https://accounts.google.com` bằng Chrome trên máy xem có tải được không.
  3. **Xử lý nhanh**: Force-stop toàn bộ tiến trình Google Services và Chrome trên máy:
     `adb shell am force-stop com.google.android.gms; adb shell am force-stop com.google.android.gsf; adb shell am force-stop com.android.chrome`
  4. **Mở lại luồng đăng nhập**: Gọi `adb shell am start -a android.settings.ADD_ACCOUNT_SETTINGS -e account_types '[\"com.google\"]'` hoặc vào Cài đặt -> Tài khoản -> Thêm tài khoản -> Google. Màn hình `Đăng nhập - Tài khoản Google` sẽ nạp lại bình thường.

- **Quy tắc xử lý nick TikTok bị đình chỉ/ban nhưng giữ Gmail (2026-08-29)**:
  Khi tài khoản TikTok bị đình chỉ vĩnh viễn cần xóa bỏ:
  1. **Excel & Database**: Xóa TikTok ID, Pass, 2FA trong `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx`, `Tik*.xlsx`. BẮT BUỘC GIỮ LẠI cột `GMAIL` và `PASS MAIL` trong `taikhoan_dat_v2_updated .xlsx` (không xóa trắng cả dòng).
  2. **Device**: Xóa tài khoản TikTok trong TikTok app (hoặc bỏ qua khi app không còn lưu). BẮT BUỘC GIỮ NGUYÊN hoặc đăng nhập lại Google Account (Gmail) trên thiết bị Android để phục vụ nhận OTP/mail khi cần.
  3. **Script Reg Eligibility**: Kiểm tra `gmail_clean_v2.xlsx` để chắc chắn mail đó không nằm trong danh sách cấp reg mới (`_detect_clean.py`), tránh việc bot tự động lấy lại mail đã từng reg để đăng ký tiếp.

- **ADB Command Timeout — Bounded Retry & Single Soft Reboot (2026-08-23, automation-core >=0.4.47)**:
  Khi gặp lỗi `adb command timed out` (như lệnh `input swipe`, `GET_IP` bị treo transport):
  1. KHÔNG chỉ tăng `wait timeout` mù quáng (khiến worker ngâm treo lâu hơn nếu transport đã chết).
  2. `AdbClient` trong `automation-core` tự động retry có chặn (`connection_retry_attempts=3`) kèm `wait-for-device`.
  3. Nếu vẫn timeout và `allow_device_reboot_recovery=True`, `AdbClient` kích hoạt tối đa **1 lần soft reboot** cho đúng serial, chờ `wait-for-device` + `sys.boot_completed=1` (timeout 120s), rồi retry lại đúng command 1 lần duy nhất.
  4. Lệnh không có serial hoặc cờ reboot tắt sẽ fail-closed ngay sau vòng retry để bảo vệ toàn farm. Các lỗi app thông thường (exit code != 0) tuyệt đối không bị reboot.
  5. CẤM restart ADB server hoặc `pm clear` khi gặp timeout.

- **UI XML dump contains mixed packages (System UI / Notification leak) → MUST filter by `APP_PACKAGE` (2026-08-22)**:
  `uiautomator dump` extracts the full display tree, including system notification popups / status bar items from `com.android.systemui` (e.g. "Thông báo của Dịch vụ Google Play: Yêu cầu đăng nhập", "Không có điện thoại nào."). A naive `strip_accents(xml).lower()` or `root.iter("node")` matches words like "đăng nhập" or "điện thoại" in system notifications, falsely classifying the screen as a TikTok login modal or phone-login tab and breaking the flow.
  **Fix**: Always filter UI search by target package (e.g. `com.ss.android.ugc.trill` for TikTok):
  1. Helper `_iter_package_nodes(root, package)`: recursively walk nodes tracking inherited `package` attribute from parent nodes down to children.
  2. Helper `_package_flat_text(xml, package)` / `_tiktok_flat_xml(xml)`: only concatenate `text`, `content-desc`, `resource-id` from nodes belonging to `package`.
  3. Pass `package=APP_PACKAGE` into `find_node_in_xml`, `find_text_tap`, `wait_for_text`, `list_edittext_nodes`, and state classifiers.

- **Hermes/git-bash shell exports `PYTHONPATH` that bleeds into ANY venv python you launch** — on this host the Hermes session's `PYTHONPATH` prepends `C:\Users\<user>\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`, so `<venv>\Scripts\python.exe -m pip install ...` can install into the HERMES venv while `import automation_core` resolves there too (silently "succeeds" with the wrong version; `importlib.metadata.version()` still shows the stale one). Before ANY venv install/verify/inspect: `env -u PYTHONPATH 'D:/Taadaa/python-envs/automation/Scripts/python.exe' ...`. Always verify after install: `automation_core.__file__` AND `importlib.metadata.version('automation-core')` must both point at the target venv's `site-packages`.

- **Verify the core function signature from the target venv BEFORE restarting a long-lived watcher.** Version drift crashes the watcher at its first event with a confusing event-machine code: core 0.4.43 lacked `watch_device_reconnect(..., auto_enable_wifi=...)` → consumer calling `auto_enable_wifi=True` died with `TypeError: ... got an unexpected keyword argument` surfaced as `WATCH_CORE_READINESS_FAILURE`. 0.4.44 added `auto_enable_wifi: bool = False` + `wifi_enable_probe_timeout`. After installing the wheel: check `inspect.signature(watch_device_reconnect)` contains the new param, pin the wheel in the consumer's requirements file, THEN restart the watcher — never restart blind after an install.

- **`automation_core.adb.AdbResult` has `exit_code` and `.ok`, NOT `returncode`** (`returncode` belongs to `subprocess.CompletedProcess`). Result handling written for CompletedProcess crashes right AFTER `adb.run([...])` succeeded — and the crash can leak the device lock you were about to release. Check `AdbResult.__dataclass_fields__` before writing result handling; release locks in `finally`.

- **Reading central device locks from a git-bash-launched venv python: prefer `os.path` over re-wrapping core's `WindowsPath`.** `Path(p).exists()` intermittently returned False for `C:\Users\...\machine_30.lock.json` even though the file existed (double-backslash repr in tracebacks). Reliable: `import os; if os.path.exists(s): json.load(open(s, encoding='utf-8'))` with the plain string. Never delete/recreate a lock based on a misread — re-stat via `os.path` first.

- **Protocol-v2 device locks (`lock_protocol_version: 2`) are reclaimed atomically by core takeover — do NOT hand-delete dead-PID locks.** Observed live 2026-08-12: a control script crashed after `adb reboot` and leaked both machine+serial locks with its own dead PID; the watcher's per-event `_acquire_watch_lock` (FULL_SCOPE takeover) reclaimed them via `_takeover_payload` (owner_active=False + PID dead), processed the reconnect event, and released. The `_takeover_payload` rules (core 0.4.44): takeover needs `allow_takeover=True` + `takeover_authorized=True` + scope (`FULL_SCOPE_TAKEOVER`/`SAME_PROJECT_RECOVERY`) + non-empty reason; `POST_REBOOT_PROXY_RECOVERY` mode additionally requires a non-empty `takeover_proof` dict; `temporarily_skipped` owners are NEVER reclaimable; SAME_PROJECT requires the owner's `project` field to match. The older "remove BOTH lock kinds before re-running" advice below applies to pre-protocol-v2 locks only.

- **NEVER `pm clear` OR `pm clear --cache-only` for TikTok `com.ss.android.ugc.trill` without an explicit user command.** User fury incidents 2026-08-07 AND 2026-08-16 (rule viết rõ "CẤM xóa Dữ liệu TikTok" trong memory từ lâu — vi phạm dù ở dạng `--cache-only` vẫn chửi thẳng): full `pm clear` wiped every account/session on the device (machine 34 lost someone else's accounts; máy 4 2026-08-16 data rỗng hẳn → app reset về onboarding). `pm clear --cache-only` cũng destructive: cache mất → TikTok kẹt SplashActivity với logcat `memoryError: cannot find cached buffer` (app mất resource/cache assets, không render được feed) → dễ bị cám dỗ leo thang sang full `pm clear` = xoá data. **Kẹt splash sau clear-cache KHÔNG fix bằng pm clear nữa** — force-stop + relaunch (monkey launch) thử; data đã mất thì phải login lại nick theo lệnh user. To switch/remove a TikTok account: use in-app logout, or ask the user. This rule is also written into `Tiktok_Reg/AGENTS.md` and `add mail khoi phuc/AGENTS.md` (Safety And Ownership).

- **uiautomator dump hanging (E=137 / "Killed" / "Bad file descriptor") = atx-agent wedged.** Force-stopping `com.github.uiautomator*` packages alone does NOT release the UiAutomationService handle — the helper process holds it. **Use `pkill -9` (SIGKILL), NOT plain `pkill` (SIGTERM)** — a wedged atx-agent parks in `futex_wait_queue_me` (S-state) and silently IGNORES SIGTERM (pkill exits 0 but the process survives, dump stays E=137 forever, runner stuck in a transport-recovery loop). `pkill -9 -f atx-agent` kills it hard and dump returns to exit 0 immediately (live-proven SM-G930F/W8; machine 34 2026-08-07: SIGTERM E=137 persisted, SIGKILL → E=0 instantly). A wedged `uiautomator dump` child additionally needs `pkill -9 -f uiautomator` ("could not get idle state" persists after atx kill alone; may return "Operation not permitted" for the u0_a196 app — harmless, atx kill + `uiautomator quit` suffice). This is NOT a reason to reboot. Core logic: `_recover_uiautomator` in automation-core ≥0.4.43 uses SIGKILL (markers `ATX_AGENT_PROCESS_MARKER`, `UIAUTOMATOR_PROCESS_MARKER`). Manual one-shot: `adb shell pkill -9 -f atx-agent; adb shell am force-stop com.github.uiautomator; adb shell uiautomator quit; uiautomator dump` → E=0.

  - **atx-agent "respawns" with cmdline `atx-agent server -d --stop` — a stuck STOP-process, not a live agent** (live 2026-08-15, máy 38, tool 数控安卓投屏 mirroring): after a successful `pkill -9 -f atx-agent` + dump E=0, a NEW atx-agent process appears minutes later with `server -d --stop` (the stop command itself hanging in `futex_wait_queue_me`/`do_wait`), and uiautomator dies again. The farm mirror tool (数控安卓投屏 / xiaowei) on the PC keeps issuing `atx-agent server --stop` over ADB while it mirrors the machine — killing it by hand is a treadmill while the tool is up. Check `cat /proc/<pid>/cmdline | tr '\0' ' '` to tell `--stop` (zombie, respawn) from a real `server` (live). Fix: user closes the mirror tool → kill once more → stays dead (verified). Do NOT conclude "atx kill doesn't work" — it's the external tool respawning it.

  - **Repeated kill cycles degrade the service permanently: `am force-stop com.github.uiautomator` stops killing the process, dump E=137 on every screen, only reboot helps (temporarily)** (live 2026-08-15, máy 38 after ~6 kill cycles in 90 min): the `com.github.uiautomator` process (PID persists, `SyS_epoll_wait`) survives force-stop, `pkill -9 -f uiautomator` returns `Operation not permitted` (harmless), dump E=137 even on launcher. Reboot restores it but only for ~1 provider run — opening Outlook (heavy WebView app) foreground kills UiAutomationService again. **Evidence it is NOT RAM**: force-stop TikTok freeing 621MB (MemFree 355MB, MemAvailable 2.1GB) still E=137. Practical ladder: try atx-kill first (1-2 rounds), then reboot, and if the flow needs the Outlook app open, plan to read the mailbox immediately after reboot in the stable window — do not loop code changes for this machine-level limit.

- **`_recover_uiautomator` kills atx-agent but does NOT restart it — after a B1 ATX-kill the persistent UI backend is dead (HTTPERROR), and shell `uiautomator dump` on weak S7s is also dead → `PROFILE_ROOT_NOT_CONFIRMED` / `non_xml_ui_dump` / `uiautomator_null_root_node` (live 2026-08-15, machines 23/26/29).** Fix (now canonical in tiktok-video `state_machine.py`, commit `b9351b7` + `850e883`): (1) after EVERY `_recover_uiautomator` call, run a restart+verify helper — `adb shell /data/local/tmp/atx-agent server -d` (the daemon form; logs `atx-agent listening on :7912`, rc=0 — do NOT use `/data/local/tmp/atx-agent -d` which fails `unknown short flag '-d'`), sleep 1.5s, then `capture_persistent_ui(adb)` and require `"<hierarchy"` in xml (VERIFIED_HEALTHY). (2) Make the UI dump path persistent-first: try `capture_persistent_ui` (XML tươi qua HTTP JSON-RPC 7912) BEFORE `capture_ui_xml`/shell dump — this is the Tiktok_Reg `_atx_capture_ui_xml` mechanism (atx tự quản lý UiAutomation, sống khi uiautomator shell chết). Gotchas: kill + `server -d` in ONE compound shell command races (no process after) — run them as separate calls with `sleep 1` between; a restarted-but-unverified agent still leaves `capture_persistent_ui` UNHEALTHY — always probe after restart. `capture_persistent_ui` returning `UNHEALTHY` with attempts showing `HTTPERROR` = atx-agent HTTP layer broken (not a dump problem); after restart the same probe returns `VERIFIED_HEALTHY`. Log marker to confirm the persistent path ran: none by default (0 `persistent`/`atx` lines in a run's execution.log means the lightweight/shared path was used — grep the log BEFORE assuming ATX was in play).\n- **Restarting atx-agent after a kill/reboot**: `adb shell /data/local/tmp/atx-agent -d` FAILS (`unknown short flag '-d'`) — the correct start command is `adb shell "nohup /data/local/tmp/atx-agent server >/dev/null 2>&1 &"` (listen on 7912). After starting the process you must ALSO start the uiautomator service via `curl -X POST http://127.0.0.1:7912/uiautomator` (port-forwarded) — until it returns `{"running":true}`/`Already started`, core `capture_ui_xml` with `provisioning_policy=REQUIRE_PROVISIONED` keeps failing with `DEVICE_NOT_PROVISIONED` even though `get_ui_xml` (shell dump) works. Symptom pattern to recognize: shell `uiautomator dump` returns E=0 but the consumer flow still logs `automation-core failed code=DEVICE_NOT_PROVISIONED` — that's the persistent-uiautomator service, not the shell dump, and not a real provisioning problem.

- **automation-core ≥0.4.38 REMOVED the old transport-recovery API** (`AndroidTransportRecoveryError`, `MissingVpnRecoveryError`, `recover_android_transport`, `recover_missing_android_vpn` from `device_recovery`). Consumer runners importing those break with `ImportError` right after upgrade. **RESOLVED 2026-08-07 — the 4 symbols + 2 result dataclasses were merged verbatim from wheel 0.4.32 into source** (`automation-core/src/automation_core/device_recovery.py`) → core **0.4.42** (legacy API + expected_marker) → **0.4.43** (pkill -9 SIGKILL). No more venv cherry-pick; upgrade path is now `pip install --force-reinstall --no-deps <new-wheel>` + bump `REQUIRED_CORE_VERSION` in the runner (else `AUTOMATION_CORE_VERSION_MISMATCH:expected=...;actual=...` at import). If you hit the old-API ImportError on a stale venv, reinstall ≥0.4.42. (Signature note: 0.4.32-era `AndroidTransportRecoveryError.__init__(serial, state_path, reason)` — positional, NOT kwarg-only `state_path=`.)

- **A logged-in TikTok session on S7 is device-bound and survives `pm clear` + android_id reset + GMS clear.** TikTok binds server-side via firmware-level ID. TikTok 46.x profile exposes no Settings/Add-account node in the a11y tree, so scripted UI logout is not possible. If the bound account isn't yours, factory reset (`adb shell recovery --wipe_data`) is the only clean path — confirm with the user first (loses all accounts/config). Do NOT assume the visible @handle is the target email's account (machine 34 was logged into someone else's `@skiperenok`).

- **Google `AssistedSignInActivity` overlay after TikTok data-clear**: with Google accounts on the device, relaunching TikTok can land on `com.google.android.gms/.auth.api.credentials.assistedsignin.ui.AssistedSignInActivity` over the TikTok profile, blocking `[02_profile]`/`[04_add_account]` → `TIKTOK_STARTUP_NOT_FOREGROUND`. Dismiss with BACK (`input keyevent 4`); it may reappear while the stale session persists.

- **Farm accessibility is OFF (`settings get secure accessibility_enabled` = 0, `enabled_accessibility_services` = null).** Chrome/WebView then exposes ONLY `url_bar` in the hierarchy — form fields (`loginfmt`, `i0116`, `i0118`, `passwordEntry`) and page text are invisible to `ui_xml`/`uiautomator dump` (returns 0 nodes). A login flow that "found the email field then can't find the password field" on this farm is usually this, not a selector bug. Screen is actually fine (screenshot shows the Microsoft login page); the tree just has no content. Workarounds: reset the tab and re-run (fresh render sometimes re-exposes), pick a machine whose Chrome session is clean, or use coordinate/screenshot-based fallbacks. Do NOT change shared selectors for this.

  - **Chrome 138 makes this worse and semantic fallbacks fail too**: `uiautomator dump` returns 0 nodes and `tap_text`-style semantic taps can't see buttons ("Could not select Keep me signed in: Yes"). **Coordinate fallback is the reliable escape**: pixel-scan the screenshot for the Microsoft blue button (b>140, 0<r<120, 60<g<140), tap the centroid. Verified on 1080x1920: keep-signed-in "Có/Yes" blue region x=[80,1000] y=[1000,1680], centroid `(540,1593)` → after tap, URL proof `outlook.live.com/mail/0/inbox` and login SUCCEEDS. TalkBack service is absent on the farm (`pm list services` empty) so enabling accessibility isn't an option.

- **Samsung OneUI task-switcher (RecentsActivity) can get stuck on top of Chrome.** Detection: `dumpsys activity top` shows `DecorView@...[RecentsActivity]` + `button_cancel`/`button_done` while `mResumedActivity` says Chrome; Back (`keyevent 4`) and HOME (`keyevent 3`) don't dismiss it. Fix: `am force-stop com.sec.android.app.launcher`, then `input keyevent 3`, then `am start -a android.intent.action.VIEW -p com.android.chrome -d <url>` to re-open Chrome cleanly. Run the automation again from the clean state.

- **TikTok home feed is misclassified as the personal profile by naive marker checks** (machine 34, 2026-08-07): `_is_personal_profile_screen_xml` returned True on the FEED, so the runner believed it was on the profile and called `open_account_switcher` on the feed → `SWITCHER_ANCHOR_AMBIGUOUS` → endless force-stop/relaunch loop. Feed false-positive sources and the fixes that work:

  - "Đã follow"/"Thích" appear in the feed bottom tabs → before accepting the follower-tab triple, require an extra header marker.

  - "Chia sẻ" ("chia se video") matches the feed share button → same header-marker requirement.

  - "follower" as SUBSTRING matches the feed share button "Đăng lại cho follower" → match follower count as a DEDICATED node with regex `^(?:[\d.,\s]*)?(?:nguoi dang follow|dang follow|followers?)$`, never substring.

  - Creator names (non-@, no-space, 3-30 chars, e.g. "Thanh Thượng Tiên") appear in the feed → profile-name detection requires `clickable=true` AND header region (bounds y1 ≤ ~300); creator names sit mid-screen (y>1000) and are `clickable=false`.

  - Also check the header marker BEFORE the home-feed guard inside `_is_personal_profile_screen_xml` (a stale dump can carry both feed and profile markers).

- **TikTok 46.x account dropdown opens by tapping the profile NAME, not a "switch account" marker**: profile header shows `text='yobi' bounds=[435,117][645,183]` (center ~540,150) with a notification badge (9+) covering the chevron; tapping the name node opens "Chuyển đổi tài khoản" + account list (yobi1965/xuanpham81/lyvy981...) + "Thêm tài khoản". Core `find_switcher_anchor` only finds it when the dump is fresh (kill atx first — see atx pitfall) and `identity` values include the display name (not just the @username).

- **`expected_marker` in core `capture_ui_xml` must be a state-UNIQUE marker**: passing "hồ sơ" (Profile) is useless — the "Hồ sơ" bottom-tab text exists on EVERY TikTok screen including the feed, so marker-miss never fires and the atx-kill retry never triggers. Pick a marker only present on the target state (e.g. the profile username, or "sửa hồ sơ"/"edit profile").

- **Some devices never render the TikTok Profile tab (machine 34 SM-G930K, TikTok 46.x):** tap profile tab → splash → back to feed, even right after reboot with fresh TikTok; dump stays feed ("Tây Ninh") while the log claims "profile selected" (that's `is_profile_tab_selected` false-positive on tab-selected+feed markers). The only proven winning path (run 182529: profile → dropdown → Add account → email → OTP) was when the machine was ALREADY on the TikTok login screen (`SignUpOrLoginActivity`) — the runner never needed the profile. **Fix: detect a login surface up front (`_is_login_method_surface_xml` / `_has_email_form`) and skip profile/dropdown entirely, falling straight through to `fill_email_and_next`** (step 7). Don't return early and don't call `continue_email_signup_from_entry` (that helper only matches `registration_entry` state, i.e. a logged-out profile, NOT a login screen). Note `SignUpOrLoginActivity` is NOT exported — `am start -n ...SignUpOrLoginActivity` fails with Security exception, so you cannot deep-link to it; and never log out a logged-in account to reach the login screen without asking the user (device-bound session is lost).

- **A crashed batch leaks BOTH `machine_<N>.lock.json` AND `serial_<SERIAL>.lock.json`** with the same dead PID (2026-08-07, machine 34). The next runner cleans one kind but still hits the other → `DEVICE_LOCKED` FINAL_BLOCKED in ~39s. Remove BOTH lock kinds before re-running. Verify PID death with **`wmic process where "ProcessId=N" get ProcessId,CommandLine`** — `tasklist //FI "PID eq N"` can silently return EMPTY even when the process is alive on git-bash, which would make you delete a live runner's lock. (A fresh runner may also create its own serial lock and still get blocked by the stale machine lock — clean both.)

- **Never** use `uiautomator dump` to check for popups in startup loops — it hangs on Samsung when UiAutomation service is busy. Use `dumpsys activity` instead.

- **Never** run device actions without VPN preflight after a reboot. The proxy watcher needs time to assign proxy.

- **Never** tap "Tiếp tục với email" on the signup screen — that's for creating NEW accounts. Tap "Bạn đã có tài khoản? Đăng nhập" at the bottom.

- ADB `keyevent 26` is POWER — toggles screen ON/OFF. Use `keyevent 82` (MENU) to wake without risk of turning screen off.



- **`adb pull <remote_dir> <local_dir>` writes NOTHING if `local_dir` already exists** (verified 2026-08-13, farm host): adb prints `N files pulled, 0 skipped` with a real byte total but the destination stays empty. Root cause: a prior `mkdir -p` (bash) created the dir, so adb sees it existing and silently no-ops the copy. **Fix: pull to a NON-EXISTENT destination** — `rmdir` the empty dir first, or use a fresh name. Single-file `adb pull <file> <existing_dir>/<name>` works fine; only the directory form is broken. For split-APK apps (TikTok = 325 files), harvest the whole directory, not individual splits.

- **adb.exe (native Windows) needs Windows-style paths, NOT MSYS `/d/...`** (verified 2026-08-13): passing `/d/Taadaa/apk-bank/...` to `C:\Program Files (x86)\xiaowei\tools\adb.exe` silently fails (no file written / pull no-ops). Pass `D:\Taadaa\apk-bank\...` (backslashes). In bash build it as `BANKWIN="D:\\Taadaa\\apk-bank"` then `"$BANKWIN\\$dir"`. Both MSYS `ls` and `cmd` see `D:`, but only the Windows form works for adb — verify the pull with `cmd /c "dir D:\Taadaa\apk-bank\..."`.

- **Harvesting many apps in a bash `for`+`while read`+`tr` loop SILENTLY writes nothing** (verified 2026-08-13): `pm path | while read | tr` builds the destination path inside a subshell and MSYS path-converts the `$BANKWIN`/`$dir`/`$f` concat so adb no-ops — adb prints `1 file pulled` but no file lands anywhere (not even the root). **Fix: pull each file with an explicit direct `adb pull` command (no loop, no `while read`, no `tr`)**, then `mv` (local op, reliable) the `*.apk` into the per-app subfolder. The source app dir `/data/app/<pkg>-<hash>==` is per-install — capture it fresh from `pm path` each run. Full recipe + workaround: `references/apk-harvest.md`.

- **Clean APK harvest (clone installed apps to a bank for reimaging phones)**: pull the device's own installed APK (bit-exact, never download from the web). Recipe: `appdir=$(adb shell pm path <pkg> | sed 's/^package://; s:/base\.apk$::')` → `rmdir "$BANK/<pkg_>"` (must not pre-exist) → `adb pull "$appdir" "D:\Taadaa\apk-bank\<pkg_>"`. Reinstall with `adb install-multiple <dir>\*` (split apps) or `adb install <dir>\base.apk` (single-APK like ViChanger). Farm map: TikTok=`com.ss.android.ugc.trill`, ViChanger=`vn.vichanger.app`, WhatsApp=`com.whatsapp`, Gmail=`com.google.android.gm` (NOT `com.google.android.gms` = Play Services). GemPhone is NOT a phone app on the connected farm (scan found no `gem`/`farm` package; likely Windows PC software). Full steps + bank layout + provenance check: `references/apk-harvest.md`.

- **Mất kết nối hàng loạt USB/ADB sau khi PC sập nguồn đột ngột (Kernel-Power 41 / X99 Huananzhi host)**: Sau khi PC sập nguồn bất ngờ, các bộ điều khiển USB 3.0 chính (`Intel USB 3.0 eXtensible Host Controller`) rơi vào trạng thái `CM_PROB_PHANTOM` trong Device Manager (chỉ còn 1 chip USB phụ nhận ~7 máy, 73 máy còn lại mất kết nối). Rút cắm lại dây USB vào PC không có tác dụng do Host Controller đã chết trong Windows.
  - **Xử lý chuẩn**: Bắt buộc **Restart Windows** (khởi động lại sạch). Fast Startup đã tắt (`HiberbootEnabled=0`) để mọi lần boot đều nạp lại toàn bộ PCIe Host Controller.
  - **Quy tắc an toàn box nguồn (user chốt 21/08)**: Khi cần reset kết nối thiết bị, **chỉ rút cắm lại dây USB data** kết nối từ Box vào PC — **CẤM tắt công tắc nguồn nuôi Box** (tránh làm sập nguồn 80 điện thoại đang chạy).
  - **Dàn S7 ROM gốc không tự bật máy khi sập nguồn (21/08)**: Nếu cả phòng/ổ cắm bị sập điện, Samsung S7 chạy ROM gốc sẽ tắt ngúm (hoặc rơi vào màn hình sạc LPM), không tự khởi động lại vào Android $\rightarrow$ sau khi PC bật lại chỉ thấy vài máy online. Phải bật nguồn thủ công từng máy nếu chưa mod LPM.
  - **Quy hoạch nguồn điện Farm chống sập PC (21/08)**: PC Dual Xeon + 4 Box S7 ăn tải 800W - 1500W $\rightarrow$ CẤM cắm chung 1 ổ chia thông thường (gây sụt áp/move chớp tắt sập PC). Dây nguồn PC phải cắm trực tiếp vào ổ tường riêng, 4 Box dùng ổ chia chịu tải riêng.

