---

name: atx-agent-primary-ui-xml

description: Đưa atx-agent (port 7912) lên làm cơ chế PRIMARY đọc UI XML trên farm Android yếu (S7/Android 7) — khi shell uiautomator dump bị Killed (EXIT=137) và file fallback trả XML stale. Dùng khi flow reg/UI automation fail vì đọc nhầm màn cũ, type nhầm field, hoặc khi cần patch get_ui_xml/ui_xml ở bất kỳ repo automation nào.

---



# atx-agent primary UI XML capture

- **Gmail Onboarding Trap & Samsung Keyguard Recovery (2026-08-29)**: Xử lý chuỗi Onboarding Gmail mới (`dialog_wrapper`, `welcome_tour`, `action_done`) và phục hồi màn hình khóa Keyguard Samsung (`keyevent 224` + swipe unlock): `references/gmail-onboarding-and-keyguard-recovery-20260829.md` (trong skill `tiktok-registration-ops`).
- **ATX Session Stub Dead & Dynamic Forward Index Fix (2026-08-29)**: Chi tiết root-cause bug parse index forward port và cơ chế monkey fallback trong `reset_atx_agent`: `references/atx-stub-dead-and-dynamic-forward-index-fix-20260829.md`.
- **ATX Session Unavailable Triage & Takeover Canary**: Hướng dẫn xử lý `ATX_SESSION_UNAVAILABLE` (stub chết, agent sống), reset qua `automation_core.persistent_ui.reset_atx_agent` và chạy canary tiếp quản lock với `--full-scope-takeover`: `references/atx-session-unavailable-triage-and-takeover-recovery.md`.
- **Auto-Recovery trong Batch Runner**: Tích hợp `reset_atx_agent(adb_client)` khi gặp 502/RemoteDisconnected; recovery phải giữ foreground an toàn và không được dùng `monkey -p com.github.uiautomator`. Chi tiết: `references/atx-auto-recovery-runner-pattern.md` và `references/atx-control-endpoint-no-monkey.md`.
- **Cắt bỏ Fallthrough xuống UiAutomator khi ATX fail**: Chi tiết triage máy 23 và quy tắc fail-closed không fallthrough sang shell uiautomator: `references/feed-capture-atx-fallthrough-elimination-20260823.md`.
- **Pitfall `reset_atx_agent` dùng monkey làm mất focus TikTok**: Chi tiết lỗi văng sang màn hình UIAutomator phím tắt tiếng Trung khi restart stub: `references/atx-reset-monkey-focus-loss-pitfall-20260823.md`.
- **AdbKeyboard IME Socket Hang / Text Injection Stalled (2026-09-01)**: Khi `AdbKeyboard` broadcast `ADB_KEYBOARD_INPUT_TEXT` không inject được ký tự vào `EditText` (ô nhập text bị bỏ trống / giữ nguyên placeholder), nguyên nhân là daemon `atx-agent` hoặc UIAutomator stub bị treo socket ngầm. Xử lý: `pkill -9 -f atx-agent` & `am force-stop com.github.uiautomator` -> restart `/data/local/tmp/atx-agent server -d` -> kích hoạt lại stub `monkey -p com.github.uiautomator 1`.
- **`_atx_capture_ui_xml` API Change — signature đổi từ `remaining_timeout_fn` sang `timeout, restart_attempts` (2026-09-01)**: Bản cũ nhận `remaining_timeout_fn` (callable); bản mới nhận `timeout=float, restart_attempts=int`. Khi patch theo chuẩn `tiktok-luot nuoi acc`, phải đổi hàm signature đồng thời cập nhật MỌI test mock: `lambda _device, _remaining_fn` → `lambda _device, *a, **k`. Pitfall: test cũ mock positional arg thứ 2 sẽ PASS với lambda nhưng vỡ nếu test assert call signature chặt. Test chuẩn: `monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda _d, *a, **k: xml)`.
- **`get_ui_xml` total deadline nâng lên 60s (2026-09-01)**: `UI_XML_TOTAL_TIMEOUT = 35` không đủ để chạy 3 lần retry ATX (mỗi lần 15s cap) + `reset_atx_agent` (15s) + 2 lần retry sau reset. Nâng lên 60s và dùng deadline floating `local_deadline - time.monotonic()` thay vì `_remaining_timeout` fn để đảm bảo mỗi attempt được cap đúng.
- **Fast Login / One-tap screen phải xử lý TRƯỚC `wait_for_text` (2026-09-01)**: Trong `choose_email_login`, `wait_for_text` cũ tìm `["Đăng nhập", "Email", "Sign up"]` KHÔNG có `"Tiếp tục với tên"` → timeout 20s rồi raise RuntimeError trước khi `handle_fast_login_screen` kịp chạy. Fix: Gọi `handle_fast_login_screen` ngay đầu hàm (trước cả `wait_for_text`), thêm `"Tiếp tục với tên"`, `"Sử dụng tài khoản khác"` vào danh sách wait.
- **`automation_core/tiktok/fast_login.py` — module canonical (2026-09-01)**: Tách `handle_fast_login_screen` ra khỏi consumer script, đưa vào `automation_core.tiktok.fast_login`. API dùng adapter functions (`get_xml_fn`, `tap_fn`, `find_text_tap_fn`, `log_fn`) thay vì import trực tiếp consumer module. Consumer wrapper chỉ gọi core và giữ local fallback. Sau mỗi thay đổi core: `cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"`.
- **Hermes Cron "provider timeout" là false alarm khi batch script exit 1 (2026-09-01)**: Hermes cron báo "provider timeout" nhưng thực ra batch `_run_all_targets.py` đã chạy xong và exit 1 (do một số máy FAILED). Không phải LLM timeout. Kiểm tra artifact `D:\Taadaa\runtime\kibe\artifacts\runs\social-batch-all\<timestamp>\all_results.json` để xem kết quả thực tế.

## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

## Trigger

- Flow reg/login/UI automation fail vì `get_ui_xml`/`ui_xml` trả XML cũ/stale (màn không khớp — type email vào password field, tap trật nút)

- Shell `uiautomator dump` bị `Killed` (EXIT=137) hoặc timeout khi đổi app foreground

- Máy yếu (S7/SM-G930*, Android 7, RAM 3.6GB) — uiautomator service chết vĩnh viễn sau khi app foreground đổi nhiều lần (bug Android 7 accessibility: `UiAutomationShellWrapper.connect` fail)



## Vấn đề gốc (evidence máy 38, 2026-08-15)

- Shell `uiautomator dump /dev/stdout` → `Killed` (EXIT=137), kể cả `--compressed`, file /sdcard — mọi biến thể

- File fallback `/sdcard/window_dump.xml` → **XML STALE** (màn cũ) — flow đọc "Nhập địa chỉ email" trong khi màn thật "Tạo mật khẩu" → type email vào password field (lỗi "gõ quá 20 ký tự")

- atx-kill ladder (skill android-device-automation L387): `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` → phục hồi TẠM, không bền

- **`capture_ui_xml` (automation_core.ui) qua atx-agent service (TCP port 7912) SỐNG** — atx tự quản lý/restart UiAutomation, trả XML TƯƠI (len 43788/74319 vs shell 12244 stale)

- Tool 投屏 (数控安卓投屏/微卫安卓控屏 = **tool xiaowei**, ADB `C:\Program Files (x86)\xiaowei\tools\adb.exe`, XWCaptureScreen.jar) **luôn bật toàn farm** → atx-agent có trên mọi máy



## Patch chuẩn (mẫu `social_reg_v1.py::_atx_capture_ui_xml`)

```python

def _atx_capture_ui_xml(device_id, remaining_timeout_fn):

    try:

        from automation_core.adb import AdbClient

        from automation_core.ui_capture import ProvisioningPolicy

        from automation_core.ui import capture_ui_xml as _cap

        client = AdbClient(

            adb_path=ADB_PATH, serial=device_id,

            default_timeout=remaining_timeout_fn("atx", cap=45),

        )

        cap = _cap(

            client,

            timeout=remaining_timeout_fn("atx", cap=40),

            retries=1, retry_delay_seconds=0.8,

            provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED,

        )

        if cap is not None and cap.xml and "<hierarchy" in cap.xml:

            return cap.xml

        return None

    except Exception as e:

        log(f"   [ui-xml] atx exception {type(e).__name__}: {str(e)[:120]}")

        return None

```

Trong `get_ui_xml`/`ui_xml`/tương đương: **atx PRIMARY đầu hàm** (return ngay nếu OK) → shell exec-out → file fallback. atx fail KHÔNG raise — rơi xuống shell. `ADB_PATH` phải có sẵn.



## ATX session dump — tầng PRIMARY MỚI trong automation-core (0.4.46, commit e57436b, 2026-08-17)



Core `try_persistent` (ui.py) giờ chạy 3 tầng: **ATX session dump** (`persistent_ui.capture_atx_session_ui`,

backend `CaptureBackend.ATX_SESSION="atx_session"`) → persistent cũ `/jsonrpc/0` (`capture_persistent_ui`,

giữ làm fallback) → shell uiautomator → file. Consumer gọi `capture_ui_xml`/`dump_current_ui` KHÔNG cần

đổi gì — session tier tự chạy trước rồi rơi xuống đúng chuỗi cũ.



- Endpoint (verified live máy 31 ce0416041bdb271305, SM-G930F, 2026-08-16): **pid-scoped**

  `/session/<pid>:com.github.uiautomator/jsonrpc/0`, method `dumpWindowHierarchy` **params [true]**

  (full depth) → XML đầy đủ; `click(x, y)` → true. Forward `adb forward tcp:7912 tcp:7912` tương thích.

- Discovery pid: `ps -A` → ĐÚNG 1 process `com.github.uiautomator` (exact-match ` com.github.uiautomator ` có

  khoảng trắng 2 bên TRƯỚC; chỉ dùng `.test` khi không có exact — `.test` có thể cùng tồn tại và KHÔNG được

  shadow); ambiguity → fail closed xuống persistent, KHÔNG đoán pid.

- Forward: `forward --list` kiểm tra TRƯỚC và PHẢI match theo serial — entry chỉ reuse khi thuộc ĐÚNG máy

  đang xử lý. **Batch nhiều máy: mỗi máy 1 local port ĐỘNG riêng** (`adb forward tcp:0 tcp:7912`; adb forward

  tcp:0 KHÔNG in stdout → parse local port từ `forward --list` theo serial). Entry stale của máy khác →

  `forward --remove` rồi tạo mới.

  ⚠️ **Fix `9044b91` (2026-08-17)** — bản cũ reuse entry 7912 đầu tiên bất kể serial → chạy batch tuần tự,

  máy B/C/D gọi `127.0.0.1:7912` vẫn trỏ máy A → dump nhầm màn hình → `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND`

  đồng loạt 5 máy. Verify live: M75 port 55564, M76 port 55656 đều VERIFIED_HEALTHY dump đúng từng máy.

  Dùng chung 1 local port cho cả farm là race — KHÔNG bao giờ.

- `atx-agent server -d` chỉ chạy trên primary path khi `ps -A` chưa thấy agent — primary KHÔNG kill;

  kill ladder `_recover_uiautomator` vẫn là recovery riêng, ngoài tầng primary.



**Test update bắt buộc (MỞ RỘNG từ bản 08-15):** mọi test mock `capture_persistent_ui` giả lập máy

không-atx mà assert số `shell_calls`/`run_calls` phải mock THÊM `capture_atx_session_ui`

(`lambda *a, **k: PersistentCaptureResult(None, UNAVAILABLE, ({"failure_signature": "ATX_SESSION_UNAVAILABLE"},))`)

— session tier chạy ADB thật (ls/pm/ps/forward) trước khi rơi xuống mock persistent, phá assertions kiểu

`len(shell_calls) == trước` (VD `test_replay_verified_persistent_capture_then_serial_disappears...` phải patch 2026-08-17).



Chi tiết implement (discovery/forward/capability) + catalog test: `references/atx-session-primary-capture-20260816.md`.

Batch multi-máy + forward per-device + hotmail list-runner + token Graph OTP (2026-08-17): `references/batch-atx-forward-hotmail-token-20260817.md`.



### ⚠️ False-positive transport timeout làm ATX KHÔNG BAO GIỜ primary (fix `727b6d4`, 2026-08-17)



Triệu chứng: `capture_ui_xml`/`capture_atx_session_ui` báo `health=UNAVAILABLE` + `failure_signature=ADB_TRANSPORT_TIMEOUT`

dù atx-agent + stub chạy đầy đủ → rơi thẳng xuống uiautomator (bị OOM kill) → ATX primary vô hiệu trên MỌI máy S7.



**Root cause:** `classify_adb_transport_failure` dùng marker substring `"timeout"`, và **`ps -A` trên Samsung S7 in

`poll_schedule_timeout` ở gần như MỌI dòng kernel-thread** (sdp_cryptod, connfwexe, at_distributor, webview_zygote32,

wpa_supplicant, adbd...) → probe ATX capability match nhầm `ADB_TRANSPORT_TIMEOUT` → fail-closed.

Sửa (đã merge vào `ADB_TRANSPORT_FAILURE_MARKERS`): bỏ marker `"timeout"` lỏng, chỉ giữ `"adb command timed out"` / `"timed out"`.

**Quy tắc marker:** KHÔNG bao giờ dùng substring 1 từ chung (`timeout`, `error`, `fail`) cho transport-failure classification —

output `ps -A`/`dumpsys` chứa đủ thứ; phải là phrase riêng của adb (`device offline`, `timed out`, `device not found`).

Verify live máy 31 sau fix: `capture_atx_session_ui` → `VERIFIED_HEALTHY` xml 28-29KB; `capture_ui_xml` → `backend=atx_session`.



- **`ATX_SESSION_STUB_NOT_RUNNING` / `UIAUTOMATOR_BACKGROUND_START_DENIED` trên Android 8+**:
  - Triệu chứng: `SHELL_EXIT_137` khi rơi xuống shell dump, hoặc `Error: app is in background` khi `am startservice`.
  - Fix chuẩn trên Android 8: Kích hoạt stub bằng `adb shell "monkey -p com.github.uiautomator 1"` (tránh bị Android 8 background execution limit chặn).
  - Port động: Luôn dùng `adb forward tcp:0 tcp:7912` để PC cấp local port ngẫu nhiên cho từng máy, không bao giờ dùng chung 1 local port gây tranh chấp giữa 80 máy.

- **`ATX_SESSION_STUB_NOT_RUNNING` — agent chạy nhưng stub UiAutomationService không chạy (máy 19 row 5, 2026-08-17)**: `capture_atx_session_ui` trả `attempts` có `agent_running: true` (PID tồn tại, LISTEN 7912) NHƯNG `failure_signature: ATX_SESSION_STUB_NOT_RUNNING` + `stub_process_lines: []` (không tìm thấy `com.github.uiautomator` trong `ps -A`) → session dump không lấy được XML → rơi xuống shell uiautomator → `could not get idle state` (video đang animation) → flow báo OPEN_TIKTOK_FAILED/đọc UI fail. Chẩn đoán phân biệt: (a) agent CHẾT → `agent_running: false` → restart `atx-agent server -d`; (b) agent CHẠY nhưng stub CHẾT → restart atx-agent cũng cần force-stop + relaunch `com.github.uiautomator` (hoặc `_recover_uiautomator` ladder — kill cả atx-agent + uiautomator rồi warmup) — restart atx-agent `server -d` MỘT MÌNH không đủ vì stub là process `com.github.uiautomator` riêng. Khi BẢN THÂN ATX session cũng fail → screencap = ground truth (máy 19: ảnh feed đang chạy dù mọi backend dump fail) → đừng kết luận "máy kẹt splash" từ dumpsys.

- **Restart stub đã verify live (máy 19, 2026-08-17) — dùng `monkey`, KHÔNG dùng `am startservice`**: sau `am force-stop com.github.uiautomator`, chạy `adb shell "monkey -p com.github.uiautomator 1"` → stub chạy lại (PID mới trong `ps -A`) → `capture_atx_session_ui` trả XML OK. `am startservice com.github.uiautomator/.UiAutomatorService` → **fail `Error: Not found; no service started`** (service name không đúng) — đừng dùng. Nếu stub chạy nhưng session vẫn **HTTP 502 Bad Gateway** = atx-agent proxy tới stub thất bại (lệch handle) → kill CẢ HAI (`pkill -9 -f atx-agent` + force-stop uiautomator) rồi `atx-agent server -d` lại → stub snapshot mới. Pitfall probe tay: curl tới `/session/<pid>:com.github.uiautomator/jsonrpc/0` — PID phải lấy exact `ps -A | grep ' com.github.uiautomator '` (2 khoảng trắng, loại `.test`); rồi `adb forward tcp:7912 tcp:7912` riêng cho máy đang xử lý (forward --list có entry cũ của máy khác không đại diện).

- **Lọc `com.android.systemui` trong `get_focused_activity` khi dùng ATX XML**:
  - Khi đọc UI XML qua ATX-primary (`flows/observe.py::get_focused_activity`), node đỉnh màn hình `[0,0][1080,72]` chứa các icon pin/sóng/thông báo của `com.android.systemui`.
  - Nếu regex chỉ lấy package đầu tiên xuất hiện trong XML (`package="..."`), hàm sẽ trả về `com.android.systemui` khiến flow tưởng lầm TikTok bị mất focus và dừng máy (`preserve_blocker_screen`).
  - **Fix**: Luôn quét danh sách package trong XML, ưu tiên trả về package TikTok mục tiêu (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`) nếu tồn tại; nếu không có thì lọc bỏ `com.android.systemui` rồi mới lấy package chính.

- **`dumpsys window` CŨNG bị stale — get_focused_activity cần ATX-primary (máy 6, 2026-08-16)**



Nguồn stale KHÔNG chỉ là shell uiautomator dump: **`dumpsys window` (mCurrentFocus) báo SplashActivity CŨ trong khi feed đã render** — TikTok giữ window activity splash, chỉ đổi nội dung UI → flow nhìn dumpsys tưởng "kẹt splash" → manual-needed sai, recovery chạy vô ích. `screencap`/ATX XML cho thấy feed đầy đủ.



Fix (repo `tiktok-luot nuoi acc`, commit `1a33a14`, `flows/observe.py::get_focused_activity`): **ATX-primary đầu hàm** — gọi `automation_core.ui.capture_ui_xml(client, timeout=..., retries=1, retry_delay_seconds=0.8, provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)`; nếu `cap.xml` có `<hierarchy` → regex lấy `package="..."` → return ngay (package TikTok = app đã lên, dù window activity vẫn splash). dumpsys window/activity giữ làm fallback. Canary máy 6: hết kẹt splash, lướt 19 swipe success.



Pitfall kèm: **xác nhận màn hình thật bằng ảnh/ATX trước khi kết luận "máy kẹt"** — đừng tin mỗi `dumpsys window`; 2 cơ chế (window activity vs UI thật) lệch nhau trên TikTok.



## Test update bắt buộc khi chuyển atx lên PRIMARY

- **Test mock `capture_ui_xml` cũ bị vỡ khi consumer bỏ fallback chuyển sang 100% ATX session (2026-08-23, repo `tiktok-add-bao-mat-f2a`)**:
  - Khi consumer nâng cấp `dump_current_ui` loại bỏ hoàn toàn `capture_ui_xml` (chỉ gọi `capture_atx_session_ui` + `reset_atx_agent`), các test contract cũ kiểu `test_adapter_requires_provisioned_persistent_capture` (mock `core.ui_dump.capture_ui_xml` hoặc assert `ProvisioningPolicy.REQUIRE_PROVISIONED`) sẽ FAIL vì `capture_ui_xml` không còn được gọi.
  - Fix: Cập nhật test mock sang `automation_core.persistent_ui.capture_atx_session_ui` trả về `SimpleNamespace(xml="<hierarchy />")` để verify hàm trả về đúng XML từ ATX session.

Các test cũ mock `_exec_out`/`shell` (giả lập máy không atx, test shell fallback) sẽ FAIL vì atx-primary chạy TRƯỚC loop — `_atx_capture_ui_xml` gọi automation_core THẬT (exception → None, nhưng thứ tự gọi lệch). Fix chuẩn (đã áp dụng `tests/test_ui_xml_timeout.py`):

```python

monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda *_a, **_k: None)

```

thêm vào MỌI test giả lập máy không-atx trước khi gọi `get_ui_xml`. Assert thứ tự shell fallback giữ nguyên.



**Nuance (Hotmail 2026-08-17): nếu probe ATX đi qua `AdbClient.shell(...)` TRỰC TIẾP (không qua `run_adb`) thì test cũ mock `run_adb` KHÔNG vỡ** — probe với serial giả fail nhanh (adb trả lỗi → None) rồi rơi xuống fallback mà test mock vẫn assert đúng; test mới mock `AdbClient` + `requests.post` (demo: repo Hotmail `tests/test_atx_primary_ui.py`). Chỉ bắt buộc monkeypatch khi test mock ĐÚNG hàm probe dùng (vd `social_reg_v1` probe qua `_exec_out`/`shell` của consumer). Chọn đường probe theo repo: qua `run_adb` = dễ mock/test nhưng vỡ test cũ; qua `AdbClient.shell` = test cũ yên, test mới mock 2 lớp. Probe trực tiếp cũng giúp máy thật fail nhanh không treo (giữ timeout nhỏ: shell 20s, http 30s).



## Rollout toàn repo automation (user directive 2026-08-15)

Tool 投屏 (xiaowei/微卫安卓控屏) luôn bật toàn farm → atx-agent có trên MỌI máy → atx-primary an toàn cho tất cả repos. Quét phạm vi:

```bash

cd /d/Taadaa && grep -rln "uiautomator.*dump\|def get_ui_xml\|def ui_xml\|capture_ui_xml" --include="*.py" */ 2>/dev/null | grep -v test | grep -v .ai-runs | grep -v site-packages | grep -v node_modules | grep -v .codex-work | grep -v runs/

```

**CẢNH BÁO: grep toàn cây `*/` timeout (backup/worktree/venv quá nhiều)** — loop từng repo thay vì 1 lệnh toàn cây (danh sách 9 repo + kết quả chi tiết từng file: `references/rollout-20260815.md`).

Repos: `automation-core`, `tiktok-video`, `Tiktok_Reg`, `Hotmail`, `tiktok-follow`, `tiktok-log-in`, `tiktok-luot nuoi acc`, `tiktok-add-bao-mat-f2a`, `register gmail`. Mỗi repo: đọc AGENTS.md → phân loại hit → patch (chỉ khi cần) → regression → COMPAT entry → commit riêng. BỎ QUA `.ai-runs/`, `.codex-work/`, `runs/`, `build/lib`, `Temp/`, test files.



**Phân loại hit `uiautomator dump` (KHÔNG phải hit nào cũng cần sửa):**

- File ĐÃ gọi `capture_ui_xml(...)` → atx-primary sẵn (core tự persistent-first) → CHỈ verify + COMPAT entry, không sửa code

- Shell dump trong hàm đọc UI (get_ui_xml/dump_ui/ui_xml) → PATCH: thêm atx-primary đầu hàm, shell giữ làm fallback

- Recovery ladder handlers (VD `ADB_SHELL_FEED_*`/`ADB_SHELL_FEED_DUMP_BACKEND` trong capture_recovery.py) → fallback tầng cuối có scope riêng — KHÔNG đụng

- Debug tool độc lập (VD `tiktok-follow/tools/dump_selectors.py` có `_guard_read_only`) → shell có chủ đích — ngoài scope

- Shell dump còn lại BÊN TRONG `capture_ui_xml` (ui.py) → fallback hợp lệ — grep thấy ≠ cần sửa



## Chẩn đoán + restart atx-agent trong consumer (tiktok-video avatar, 2026-08-15)



Consumer đã dùng `capture_ui_xml(..., provisioning_policy=REQUIRE_PROVISIONED)` (persistent-first) mà vẫn fail

`PROFILE_ROOT_NOT_CONFIRMED` / `non_xml_ui_dump` / `uiautomator_null_root_node`, và log KHÔNG có dòng

persistent/ATX nào → nghi atx-agent chết/wedged chứ không phải thiếu cơ chế.



1. **Probe trực tiếp** bằng persistent API (không qua flow):

   ```python

   from automation_core.adb import AdbClient

   from automation_core.persistent_ui import capture_persistent_ui

   r = capture_persistent_ui(AdbClient(adb_path=..., serial=...), timeout=30)

   # health=UNHEALTHY + attempts có HTTPERROR = atx-agent wedged

   # (dù `ps -A | grep atx-agent` THẤY process ở futex_wait_queue_me/do_wait)

   ```

2. **Restart atx-agent — chạy RIÊNG một lệnh, không chain**:

   ```bash

   adb -s <serial> shell '/data/local/tmp/atx-agent server -d'   # → "atx-agent listening on :7912" rc=0

   ```

   `pkill -9 -f atx-agent; sleep 1; ... server -d` gộp chung 1 shell = RACE — không có process sống sót.

   Verify: `capture_persistent_ui` → `VERIFIED_HEALTHY` (xml có `<hierarchy`) rồi mới rerun batch.

3. **Pitfall: ladder B1 ATX-kill của chính workflow giết atx-agent** (`_recover_uiautomator` = pkill -9, chạy liên

   tục mỗi lỗi UI) → sau 1 run fail, atx-agent chết lại. Restart atx-agent TRƯỚC mỗi lần rerun.

   **Fix bền (in-code, Tiktok-video commit b9351b7):** wire `_restart_atx_agent(adb)` NGAY SAU mọi call

   `_recover_uiautomator` trong consumer (state_machine có 4 call sites) — helper chạy

   `["/data/local/tmp/atx-agent", "server", "-d"]` + sleep 1.5 + verify `capture_persistent_ui` trả

   `<hierarchy` → `ok`. Khi audit consumer diff thấy `pkill atx-agent` mà không có restart đi kèm → bug.

4. **Scope (đừng kỳ vọng quá):** restart atx chỉ cứu lỗi dump/provisioning — máy 26 PASS avatar sau restart.

   KHÔNG cứu: `VPN_REQUIRED_NOT_CONNECTED` (lỗi riêng — reboot máy + watcher tự reconnect, xem android-device-automation),

   hay "Restored TikTok subpage detected; Back recovery 12/12 fail" (lỗi logic account switcher — TikTok restore

   subpage sau switch, XML đọc được nhưng không phải profile root — cần debug `_leave_tiktok_subpages`, không phải dump).



## Cơ chế cài atx-agent + uiautomator trên máy mới (trả lời user 17/08: "khi cài máy mới làm sao bọn nó có")

Không cài tay — **automation-core `provisioning/` tự cài khi script chạy**:

- `bundle.py`: bundle chứa artifact `atx-agent` (binary ~10MB, kind="atx-agent") + `uiautomator.apk` (app `com.github.uiautomator` v2.4.0, kind="apk"), mỗi artifact kèm **sha256 + signer cert digest** (chống cài nhầm/giả). Bundle manifest mẫu: `automation-core/examples/provisioning/manifest.example.json`.
- `workflow.py`: `check(serial)` → dò máy đã có chưa (version/checksum); `provision(serial)` → chưa có thì push binary xuống `/data/local/tmp/atx-agent` + `am install` app uiautomator; `repair(serial)` → version lệch cài đè. Sau cài: `atx-agent server -d` → port 7912.
- `fleet.py`: `provision_all()` → quét + cài cả dàn máy 1 lần.
- Tool xiaowei (投屏 GUI, `C:\Program Files (x86)\xiaowei\`) KHÔNG chứa atx-agent — nó chỉ là bộ điều khiển; binary/app do provisioning core quản lý. Máy đã cài rồi nhưng stub process chết → xem mục `ATX_SESSION_STUB_NOT_RUNNING` (restart bằng `monkey -p com.github.uiautomator 1`).

## Git gotchas gặp khi commit loạt này

- `git add -A ':!/.codex_spreadsheet_tmp'` (pathspec exclude) KHÔNG stage gì trong git-bash MSYS → `nothing added to commit` sai lầm. Stage file RÕ RÀNG từng file.

- `git status --short` trả rỗng nhưng work chưa commit = session khác/đồng nghiệp ĐÃ commit tự động — check `git log --oneline -3` trước khi kết luận "mất work".

- `git diff HEAD --stat` rỗng = working tree sạch thật.



## Quy trình 3 bước fix UI (bắt buộc)

1. Patch handler (atx-primary hoặc fix cụ thể)

2. Regression test đầy đủ repo (Tiktok_Reg 69, Hotmail 152, + automation-core, tiktok-video)

3. COMPAT entry vào `docs/ui-compatibility.md` (ID: `atx-agent-primary-ui-xml-20260815`) + `git diff --check` sạch



## Pitfalls

- **Consumer BẮT BUỘC dùng `AdbClient` chuẩn của `automation_core.adb` (2026-08-27)**:
  - Khi consumer gọi `capture_atx_session_ui(adb_client)` hoặc `reset_atx_agent(adb_client)`, đối tượng `adb_client` **phải là instance của `automation_core.adb.AdbClient`** (hoặc triển khai đầy đủ phương thức `.run(cmd, ...)` bên cạnh `.shell()` và `.exec_out()`).
  - Lỗi gặp phải (repo `register gmail`): Tạo class giả lập `_CoreUiAdb` chỉ có `.shell()` và `.exec_out()` $\rightarrow$ ATX session dump ném `AttributeError: '_CoreUiAdb' object has no attribute 'run'` khi setup port forward động `forward tcp:0 tcp:7912` $\rightarrow$ capture trả về XML rỗng trong im lặng, làm sập toàn bộ preflight trên 15 máy.
  - Luôn khởi tạo: `adb_client = AdbClient(adb_path=ADB_EXE, serial=device_id, default_timeout=20)`.

- **CẤM fallback bấm tọa độ mù khi không tìm thấy node điều hướng trong XML (2026-08-21)**:
  - Khi điều hướng đáy (`Trang chủ`, `Hồ sơ`, v.v.), BẮT BUỘC chỉ click khi tìm thấy UI Node thật từ ATX XML (`bounds` chính xác).
  - TUYỆT ĐỐI KHÔNG dùng fallback tọa độ pixel/tỷ lệ màn hình (ví dụ `(540, 1800)` hay `(972, 1857)`) vì rất dễ bấm trúng nút Quay video (+) hoặc nút LIVE ở đáy màn hình khi có popup/modal đè.
  - Khi XML không có node hoặc modal che khuất: dừng an toàn hoặc gửi phím BACK đóng modal trước, không click mù.

- **Bắt buộc Word Boundary `\b` khi so khớp text/content-desc từ XML (2026-08-22, vụ máy 45 Closer)**:
  - Khi tìm element/nút đóng popup bằng text/desc (`_find_clickable_text`), TUYỆT ĐỐI KHÔNG dùng substring lỏng kiểu `term.lower() in value.lower()`.
  - Các từ khóa ngắn tiếng Anh/Việt như `"close"`, `"save"`, `"đóng"` sẽ bị va chạm chuỗi con (substring collision) với tên bài hát, video (ví dụ bài hát `"Closer"` có content-desc `"Âm thanh: Closer của hppr"` chứa `"close"` -> nhận nhầm nút đĩa nhạc là nút Đóng và click vào tâm node `(999, 1712)` làm văng sang trang chi tiết âm thanh Sound Detail).
  - Bắt buộc dùng regex word boundary `r"(?i)\b" + term + r"\b"` cho các từ khóa độc lập. Đồng thời đăng ký handler `sound_detail_overlay` (Back key) để tự phục hồi nếu vô tình chạm vào đĩa nhạc.

- **ATX control endpoint — cấm monkey và kiểm tra foreground (2026-08-24)**:
  - `monkey -p com.github.uiautomator 1` bị cấm trong recovery/test vì có thể mở UiAutomator lên foreground hoặc làm thiết bị rơi về Launcher.
  - Khi `ATX_SESSION_STUB_NOT_RUNNING`, chỉ được dùng control-plane nội bộ của atx-agent (`POST /uiautomator`), sau đó rediscover PID/forward và gọi pid-scoped `dumpWindowHierarchy([true])`.
  - Sau control call và sau capture bắt buộc verify package/activity; nếu foreground đổi ngoài dự kiến thì preserve-scene và fail-closed, không tự relaunch TikTok/HOME/BACK.
  - Thử nghiệm endpoint chỉ được chạy trên đúng một máy đã chứng minh rảnh bằng lock metadata; phải có pre/post focus + ATX health/XML evidence. Chi tiết: `references/atx-control-endpoint-no-monkey.md`.

- **ATX 100% và chính sách bỏ hoàn toàn shell uiautomator fallback (2026-08-22)**:
  - Toàn farm dùng `ProvisioningPolicy.REQUIRE_PROVISIONED` ưu tiên 100% `atx_session` qua JSON-RPC `dumpWindowHierarchy [true]` (port động `tcp:0` -> `tcp:7912`).
  - **TẮT HOÀN TOÀN SHELL UIAUTOMATOR FALLBACK Ở TẤT CẢ CONSUMER REPOS (FEED/REG/LOGIN/FOLLOW/VIDEO/MAIL)**: Tuyệt đối không cho phép fallback sang `uiautomator dump /dev/stdout` hoặc `/sdcard/window_dump.xml`. Việc rơi xuống shell dump khi ATX lỗi sẽ đọc phải file XML rác/stale hoặc bị kernel OOM-kill (137) gây khóa Accessibility Service.
  - **CẤM SÓT FALLTHROUGH XUỐNG LEGACY CAPTURE / UIAUTOMATOR RECOVERY (2026-08-23)**:
    - Khi cài đặt retry ATX 3 lần + `reset_atx_agent` + retry sau reset, nếu vẫn không lấy được XML, BẮT BUỘC fail-closed trực tiếp (raise `UIDumpError("ATX_SESSION_UNAVAILABLE")` hoặc trả rỗng).
    - TUYỆT ĐỐI KHÔNG để fallthrough rơi xuống `capture_ui_xml(lightweight=True)` hoặc các recovery ladder cũ (`recover_uiautomator_foreground_service`, `recover_uiautomator_direct_capture_after_shell_exit`, `recover_capture_stack`), vì sẽ kích hoạt shell uiautomator -> OOM kill (137) -> `UIAUTOMATOR_BACKGROUND_START_DENIED_FOREGROUND_RECOVERY_V2`.
    - Rà soát toàn bộ consumer repos (`tiktok-luot nuoi acc`, `tiktok-follow`, `tiktok-log-in`, `Tiktok-video`, `Hotmail`, `add mail khoi phuc`, `register gmail`, `tiktok-add-bao-mat-f2a`) đảm bảo không còn sót bất kỳ lời gọi fallback `capture_ui_xml` / `uiautomator dump` nào.
  - **Hàm chuẩn trong `automation_core.persistent_ui`**: `reset_atx_agent(adb, timeout=20)`
    - `am force-stop` các package stub (`com.github.uiautomator`).
    - `pkill -9 -f atx-agent` & `pkill -9 -f uiautomator` để giải phóng handle/socket kẹt.
    - Chạy `/data/local/tmp/atx-agent server -d`.
    - **Bắt buộc kích hoạt stub qua ADB monkey**: `monkey -p com.github.uiautomator 1` (Android 7/8). CẤM chỉ gọi `atx-agent curl POST /uiautomator` vì atx-agent có thể trả về `Already started <nil>` trong khi process stub thực tế đã chết trong RAM.
    - **Active polling chờ stub sẵn sàng**: Vòng lặp quét `ps -A` mỗi 0.5s (tối đa 8s) cho đến khi tìm thấy tiến trình `com.github.uiautomator` rồi sleep thêm 0.5s để bind socket JSON-RPC, tránh lỗi HTTP 502 do request quá sớm khi máy S7 lag.
  - **Mẫu chuẩn áp dụng ở consumer `get_ui_xml(adb)`**:
    ```python
    from automation_core.persistent_ui import capture_atx_session_ui, reset_atx_agent
    import time
    for _ in range(3):
        try:
            atx = capture_atx_session_ui(adb, timeout=15)
            if atx.xml and "<hierarchy" in atx.xml:
                return atx.xml
        except Exception:
            pass
        time.sleep(0.3)

    # Sau 3 lần fail -> hard reset ATX agent + stub
    reset_atx_agent(adb, timeout=15)
    time.sleep(1.0)
    try:
        atx = capture_atx_session_ui(adb, timeout=20, restart_attempts=1)
        if atx.xml and "<hierarchy" in atx.xml:
            return atx.xml
    except Exception:
        pass
    return ""
    ```
  - **Xử lý bottom sheet 'Chuyển đổi tài khoản' che thanh điều hướng đáy (`navigation target profile not found in XML`)**:
    - Khi bắt đầu phiên hoặc navigate Profile (`_navigate_profile_for_preflight`), nếu màn hình đang mở sẵn sheet Switcher, thanh bottom bar ở y>=1400 sẽ bị che khuất khiến XML thiếu tab Profile.
    - Phải có bước `_dismiss_account_switcher_if_open`: tap nút `X`/`Đóng` hoặc gửi phím `BACK` để hạ sheet trước khi tìm tab Hồ sơ.

- **CẤM truyền `lightweight=True` hoặc lightweight probe keys vào `capture_ui_xml` (2026-08-17, repo tiktok-follow)**: Trong `automation_core.ui:1420`, `capture_ui_xml` kiểm tra: nếu có `lightweight=True` hoặc bất kỳ key nào trong `lightweight_keys` (`deadline_seconds`, `max_local_recaptures`, `foreground_probe`, `expected_foreground`...) thì core **BỎ QUA TOÀN BỘ ATX PRIMARY / ATX SESSION** và ép chạy thẳng vào `_dump_current_ui_lightweight` (chính là shell `uiautomator dump`!) → dính ngay `ERROR: could not get idle state` khi TikTok đang phát video animation. Consumer gọi `capture_ui_xml(self._adb, timeout=..., provisioning_policy=ProvisioningPolicy.REQUIRE_PROVISIONED)` CHỈ truyền timeout + policy để core tự route qua ATX session primary (port 7912).

- **TikTok 46.x Account Switcher layout mới + verify nick ở Profile root (2026-08-17, máy 10; Case 72, 2026-09-02, máy 60; Case 77, 2026-09-03, máy 2)**: 
  1. TikTok layout mới: profile root chưa scroll thì tên nằm lệch TRÁI (x<300), không có anchor giữa đỉnh -> `find_switcher_anchor` báo `SWITCHER_ANCHOR_AMBIGUOUS`. Body username `id/sr3` ở $y=370..415$ chỉ là nút copy handle, TUYỆT ĐỐI KHÔNG fallback tap vào node này làm switcher anchor.
  2. Cách mở Switcher: Vuốt nhẹ vừa phải (từ y=0.65h lên y=0.42h, ~400px trong 200ms) -> tên `:id/pke` / `:id/pkh` nhảy lên sticky header chính giữa trên cùng ($y \le 250$, $300 \le x \le 780$) -> tap vào để bung bottom-sheet "Chuyển đổi tài khoản". CẤM vuốt quá mạnh (>1000px) làm tuột trang.
  3. So khớp danh tính fuzzy/prefix (`matches_switcher_identity`): UIAutomator trên màn hình chưa cuộn có thể nối thêm số badge vào display name/username (VD: `crystal.1.11` / `crystal.1.15`). Khi so sánh với text trên sticky header (`crystal.1.1`), bắt buộc dùng prefix/fuzzy matching để không bỏ sót anchor.
  4. Verify sau khi switch: Khi màn hình đang ở trạng thái scrolled thì username `@...` bị đẩy khuất lên trên (chỉ còn display name). Hàm `verify_selected_account` phải vuốt ngược nhẹ xuống (từ y=0.25h xuống y=0.75h) để đưa profile root về đỉnh thì mới đọc được text `@username` trong XML.
  5. Bounded recursion auto-login recovery: Khi gọi lại `verify_and_switch_profile` sau khi chạy login reconcile, bắt buộc truyền `allow_auto_reconcile=False` để chặn đệ quy vô hạn. Chi tiết: `references/profile-unscrolled-body-username-exclusion-and-fuzzy-header-20260902.md`.
  6. **Case 77 (2026-09-03, Máy 2) — Help Center Webview & Word-Boundary Filtering**: Tự động nhận diện & dismiss Webview Trợ giúp / "Tài khoản được đề xuất" (`inapp_browser_overlay`) qua nút back/close hoặc phím BACK. Khi loại trừ các anchor trợ giúp/đề xuất khỏi switcher (`_EXCLUDED_SWITCHER_TERMS`), BẮT BUỘC dùng regex word-boundary `\b` để tránh loại trừ nhầm các username hợp lệ (như `helpme123`, `shelper`). Chi tiết: `references/help-center-webview-and-switcher-word-boundary-20260903.md`.lại `verify_and_switch_profile` sau khi chạy login reconcile, bắt buộc truyền `allow_auto_reconcile=False` để chặn đệ quy vô hạn. Chi tiết: `references/profile-unscrolled-body-username-exclusion-and-fuzzy-header-20260902.md`.
    6. **Case 77 (2026-09-03, Máy 2) — Help Center Webview & Word-Boundary Filtering**: Tự động nhận diện & dismiss Webview Trợ giúp / "Tài khoản được đề xuất" (`inapp_browser_overlay`) qua nút back/close hoặc phím BACK. Khi loại trừ các anchor trợ giúp/đề xuất khỏi switcher (`_EXCLUDED_SWITCHER_TERMS`), BẮT BUỘC dùng regex word-boundary `\b` để tránh loại trừ nhầm các username hợp lệ (như `helpme123`, `shelper`). Chi tiết: `references/help-center-webview-and-switcher-word-boundary-20260903.md`.

- **CẤM tự gọi `uiautomator dump` trực tiếp bằng tay khi debug** (kể cả `adb shell uiautomator dump` / exec-out `/dev/stdout`) — user nhắc lại LIVE 2026-08-17 ("cấm dùng uiautomator trước, t cài trong rule r mà sao mày vẫn cứ xài"): debug UI phải qua ATX — `dumpWindowHierarchy` [true] endpoint session, hoặc `capture_ui_xml`/`capture_atx_session_ui` trong automation_core. uiautomator chỉ tồn tại làm fallback code, không phải công cụ debug tay. Khi dump UI bằng tay: dùng automation_core `capture_ui_xml` (qua venv farm + `env -u PYTHONPATH`), KHÔNG gõ `uiautomator dump` shell.
- **Live ATX PID/forward parsing must be column-aware and target-scoped**: `ps -A` output is whitespace-delimited and may not contain the exact spacing assumed by a regex. Parse columns, require the final process-name column to equal `com.github.uiautomator`, exclude `com.github.uiautomator.test`, and require exactly one match before using its PID. For forwarding, first inspect `forward --list`, match the exact target serial plus remote `tcp:7912`, and reuse that serial's dynamic local port. Never run `forward --remove-all` on a live farm merely to simplify discovery; stale forwarding cleanup must be serial-scoped.
- **Loại trừ Node Tiêu đề Sửa Tên (:id/pkh, :id/pke) khỏi Switcher Anchor (2026-09-02)**:
  - Khi tài khoản chưa đặt `@username` (chỉ có display name "Huy Mập") hoặc giao diện header giữa, `find_switcher_anchor` / `_find_sticky_profile_header` có thể nhận nhầm node tiêu đề tên `com.ss.android.ugc.trill:id/pkh` / `pke` làm switch anchor.
  - Tapping trúng node này kích hoạt trang "Đổi tên" (`tv_content_name`) và bật bàn phím ảo thay vì mở sheet Switcher $\rightarrow$ lặp dismiss/tap và dừng phiên.
  - Fix: Bắt buộc lọc bỏ các resource-id `:id/pkh`, `:id/pke`, `:id/pau`, `:id/s9b`, `tv_content_name` khỏi tập ứng viên switcher header.

- **Check Gmail Live qua ATX XML (2026-08-21):** Khi kiểm tra tài khoản Google/Gmail live (trong repo `add mail khoi phuc` hoặc flow login/reg), BẮT BUỘC dùng ATX session để đọc node *"Đăng nhập"* và *"TIẾP THEO"* lấy bounds chính xác, CẤM tap mù/tọa độ đoán để phát hiện chính xác màn reCAPTCHA ("Tôi không phải là người máy").

- **Atx query tay khi atx-agent chạy mà /wd/hub 404**: atx-agent 0.10.1 KHÔNG expose WebDriver /wd/hub — endpoint là JSON-RPC pid-scoped `/session/{pid}:com.github.uiautomator/jsonrpc/0`; method dump đúng = `dumpWindowHierarchy` params **[true]** (không phải `uiautomator.dump`/`dumpHierarchy` — trả "method not found"); `click(x,y)` OK; KHÔNG có method text — gõ qua `adb shell input text` sau khi tap focus. Khám phá method: gọi method sai → `-32601`; method đúng nhưng thiếu params → `-32602`.

- ⚠️ **ATX `click` là cách DUY NHẤT tap được nút WebView trong Outlook Reading Pane / mail HTML** (máy 75 2026-08-17, tốn cả buổi): `adb shell input tap <x,y>` KHÔNG ăn nút `<a href>` render trong OneAuth/Outlook WebView (intercept), dù tọa độ trúng bounds. ATX click (JSON-RPC `click`, đi qua UiAutomator) → `result: True` → link kích hoạt, foreground chuyển app (verified: nút "Xác minh email" resource-id `link` center (539,1631) → TikTok mở). ⚠️ ĐỪNG nhầm `find_text_tap`/`tap()` trong script consumer — chúng gọi `shell input tap`, KHÔNG phải ATX click; log "✓ tap ... (ATX)" có thể là nhãn SAI. Helper ATX click: lấy pid `com.github.uiautomator` từ `ps -A` → `adb forward tcp:7912 tcp:7912` → `POST /session/{pid}:com.github.uiautomator/jsonrpc/0 {"method":"click","params":[x,y]}` → check `result is True`. User rule 2026-08-17: "dùng atx trc r mà" — CẤM đề xuất uiautomator click, ATX là primary (uiautomator chỉ fallback).

- **Popup packageinstaller deny → verify focus quá sớm (0.8s → 2.5s, máy 19 2026-08-17)**: sau tap TỪ CHỐI trên dialog contacts/permission (core detect OK: resource-id `permission_message`/`permission_deny_button` + text "Cho phép TikTok truy cập vào danh bạ"), `_sleep_and_recapture` (flows/benign_popup.py) chỉ sleep 0.8s rồi capture → dialog chưa fade-out + app chưa kịp trả foreground → vẫn `com.android.systemui` → false "TikTok focus lost" (log: `dismiss_<popup> success` ngay sau `*_after_*_dismiss | observe | failed`). Fix: sleep 2.5s. Lỗi là TIMING sau deny, không phải detect/deny — đừng sửa nhầm handler popup.\n\n- **Consumer ép `lightweight=True` chặn ATX-primary (tiktok-luot nuoi acc `core/ui_capture.py::capture_required_ui_result`, 2026-08-17)**: hàm này gọi `capture_ui_xml(..., lightweight=True, deadline_seconds, max_local_recaptures, foreground_probe...)` → core (ui.py:1420) thấy lightweight keys là BỎ QUA toàn bộ ATX session primary, ép `_dump_current_ui_lightweight` (shell uiautomator) thẳng → dính idle_state_error khi video animation. Theo plan upgrade-atx-primary-all-repos: thêm ATX-primary block ĐẦU hàm TRƯỚC lightweight path — `capture_atx_session_ui(adb, timeout=bounded_deadline, restart_attempts=1)` → nếu xml có `<hierarchy` return ngay. ⚠️ CaptureResult constructor BẮT BUỘC đủ field (xml, backend, capture_id, attempts, artifact_path, diagnostics) — thiếu backend/capture_id → TypeError; `CaptureBackend.ATX_SESSION` tồn tại trong automation_core.ui_capture (giá trị "atx_session").\n\n- **Xử lý Màn hình khóa Samsung (Keyguard / Emergency Call) trước khi điều hướng (2026-08-28)**:
  - Khi thiết bị bị tắt/khóa màn hình Samsung Keyguard (`Vuốt màn hình để mở khóa`, `com.android.systemui:id/emergency_call_button`), lệnh `input keyevent 3` (Home) không thể mở khóa.
  - Phải gọi `prepare_android_for_automation(client)` ngay đầu `open_app()`, hoặc gửi `keyevent 224` (WAKEUP) + vuốt mở khóa `input swipe 540 1500 540 300 300` khi phát hiện text Keyguard để tránh bị kẹt không vào được tab Profile.

- **Giới hạn Timeout Bounded cho ATX Session Dump (2026-08-28)**:
  - CẤM để timeout một lần capture ATX quá dài (>30s) vì nếu socket bị nghẽn, nó sẽ ngốn hết tổng thời gian `UI_XML_TOTAL_TIMEOUT` trước khi kịp gọi `reset_atx_agent`.
  - Chuẩn: Giới hạn mỗi lần thử ATX tối đa 15-20s qua `capture_atx_session_ui(client, timeout=20)`. Sau 3 lần fail, gọi `reset_atx_agent(client, timeout=15)` rồi mới thử lại lần cuối trước khi fail-closed.

- **`UI_XML_TIMEOUT` + `uiautomator_null_root_node` khi chuyển app foreground (máy 78, 2026-08-21)**:
  - Triệu chứng: `social_reg_v1` / runner báo `[adb-timeout] UI_XML_TIMEOUT ... detail=attempt2:fallback-timeout:/data/local/tmp/_ui.xml` kèm `uiautomator_null_root_node` do `com.github.uiautomator` bị treo/crash khi chuyển từ Launcher sang TikTok splash.
  - Xử lý: (1) Diệt & khởi động lại ATX stub qua `adb shell "monkey -p com.github.uiautomator 1"` (hoặc restart ladder `pkill -9 -f atx-agent` + `am force-stop com.github.uiautomator` rồi `/data/local/tmp/atx-agent server -d`); (2) Dọn sạch stale device lock file trong `~/.codex/device-locks/` nếu tiến trình cũ bị ngắt đột ngột để giải phóng lock cho lượt chạy tiếp theo.

- **KHÔNG dùng file fallback làm nguồn chính trên máy yếu — luôn stale**

- atx fail phải fallback shell chứ không raise (máy không atx vẫn chạy)

- `capture_ui_xml` cần `ProvisioningPolicy.REQUIRE_PROVISIONED` (máy có atx-agent mới provision)

- **Cập nhật source ở repo KHÔNG tới được runtime batch (COPY install)**: venv farm `D:\Taadaa\python-envs\automation` cài automation_core dạng COPY (không editable) — `cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"` sau mỗi commit rồi mới chạy batch hoặc test các consumer repo.

- **Dynamic forward port assertion trong unit tests**: Core chuyển sang cấp port local động (`forward tcp:0 tcp:7912`) để tránh conflict giữa các máy farm chạy song song/tuần tự -> các mock `AdbClient.run` trong unit test cần assert `["forward", "tcp:0", "tcp:7912"]` thay vì port cứng `7912`.
  ⚠️ **Bug index parsing `adb forward --list`**: Chuỗi output có format `<serial> <local_port> <remote_port>` -> local port động nằm ở `parts[1]` (ví dụ `parts[1].split(":")[1]`), KHÔNG phải `parts[2]` (cổng remote `7912`). Parse nhầm `parts[2]` khiến request JSON-RPC gửi tới cổng 7912 sai lệch dẫn đến 502 Bad Gateway hoặc timeout.

- **Kích hoạt stub an toàn trong `reset_atx_agent`**:
  - `atx-agent curl POST /uiautomator` là cơ chế ban đầu, nhưng trên máy S7 (Android 7/8) nếu bị background restriction thì tiến trình `com.github.uiautomator` có thể không lên.
  - Phải có bước fallback: nếu sau 8s polling `ps -A` chưa thấy `com.github.uiautomator`, kích hoạt ngay bằng `adb shell "monkey -p com.github.uiautomator 1"` và poll tiếp 5s cho đến khi process xuất hiện trong `ps -A`.
  - Trong consumer `ui_capture.py`: sau khi reset, cho phép retry capture 3 lần với backoff 0.5s để đảm bảo socket JSON-RPC đã bind hoàn toàn.

- **Nguyên tắc "Fix máy" từ User**: Khi user yêu cầu "fix máy XX", BẮT BUỘC phải phân tích root-cause, sửa và lưu trực tiếp vào codebase/script (`automation-core`, consumer runners), cập nhật `docs/farm-automation-cases.md` (Gate 0.5), chạy test suite và live canary chứng minh script tự động xử lý được. TUYỆT ĐỐI KHÔNG chỉ chạy lệnh ad-hoc bằng tay cho qua phiên mà không lưu code fix.

- **Host-aware proxy mapping resolution**: `automation_core.preflight.resolve_proxy_mapping_path` là hàm chuẩn để lấy path file `PROXYgandienthoai.xlsx` theo `TAADAA_HOST_CONFIG` (fail-closed, không fallback kibe). Consumer repo cần import hàm này từ `automation_core.preflight`.\n- **`ime list -s` ≠ `ime list -a -s` khi verify AdbKeyboard**: `-a` liệt kê CẢ IME chưa enable → check nhầm tưởng đủ điều kiện, flow `type_text(sensitive=True)` check `-s` (enabled) vẫn fail `refusing unsafe password input`. Sau cài APK phải `ime enable com.github.uiautomator/.AdbKeyboard`; verify `ime list -s | grep AdbKeyboard` (case-sensitive, không lowercase).

- **`PYTHONPATH` env toàn cục của Hermes session override site-packages venv**: session Hermes set `PYTHONPATH=C:\\Users\\Kibe\\AppData\\Local\\hermes\\hermes-agent;...\\venv\\Lib\\site-packages` (không có trong .bashrc — do Hermes tự prepend). Hệ quả: chạy `D:/Taadaa/python-envs/automation/Scripts/python.exe` (venv farm) vẫn import `automation_core` từ HERMES venv (bản cũ — chạy `import automation_core; print(automation_core.__file__)` để phát hiện). Fix: `env -u PYTHONPATH D:/Taadaa/python-envs/automation/Scripts/python.exe ...` hoặc `PYTHONPATH="D:\\Taadaa\\automation-core\\src"` (path Windows, không MSYS). **Bắt buộc khi verify runtime ATX-primary** — nếu không, ATX mới không bao giờ chạy dù code core đã sửa.

- `capture_ui_xml` trả xml RỖNG (không raise UIDumpError) → vẫn phải fallback: `ui_xml` (Hotmail) cũ `return capture_ui_xml(...).xml` — capture trả `xml=""` (service sống nhưng dump rỗng) → return "" NGAY, bỏ qua exec-out fallback → provider đọc màn rỗng fail. Fix (đã merge `7267201`): check `captured is not None and captured.xml and "<hierarchy" in captured.xml` → có thì return; rỗng/None → rơi xuống exec-out retry 5×. Test: `test_ui_xml_empty_capture_falls_back_to_exec_out` mock capture trả `SimpleNamespace(xml="", ...)` + `run_adb` side_effect `["", "<hierarchy...>"]`. Cùng class: mọi wrapper `capture_ui_xml(...).xml` đều phải guard None/rỗng.

- 2 cơ chế đọc UI KHÁC NHAU: shell dump (chết) vs atx-agent (sống) — đừng kết luận "máy hỏng" khi 1 cơ chế fail

- BACK keyevent từ mail-detail Outlook = thoát app (dùng back-arrow in-app)

- Rotation: luôn `settings put system accelerometer_rotation 0` + `user_rotation 0` sau mỗi phiên



### Test trên consumer repos (nhầm import automation_core)

Consumer test thường import NHẦM `automation_core` từ hermes venv (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages` — bản cũ, thiếu symbol mới → ImportError khi collection). Chạy với:

```bash

PYTHONPATH="D:\\Taadaa\\automation-core\\src" /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/...

```

**BẮT BUỘC path Windows (`D:\...`) — MSYS `/d/...` bị mangling thành `D:\d\...` và không trỏ đúng.** venv `python-envs/automation` cài automation_core dạng COPY (không editable) nên local source change luôn cần PYTHONPATH.

**Chứng minh test fail/treo là pre-existing**: `git stash` → rerun → `git stash pop`. Fail cả khi stash = không do patch (áp dụng cả test fail lẫn test treo do atx path kết nối ADB thật trong test cũ không mock — test cũ mock `_exec_out`/`shell` nhưng atx-primary chạy automation_core THẬT trước loop). Test cũ như vậy cần `monkeypatch.setattr(social, "_atx_capture_ui_xml", lambda *_a, **_k: None)` — xem mục "Test update bắt buộc".



**`ZoneInfo("Asia/Ho_Chi_Minh")` trong consumer cần `tzdata` package trên Windows (proven 2026-08-15, tiktok-luot hermes_cron blocks/models):** Python Windows không ship IANA timezone data → module-level `TZ = ZoneInfo("Asia/Ho_Chi_Minh")` raise `ZoneInfoNotFoundError` tại COLLECTION khi chạy file lẻ (full suite chạy được vì conftest/cwd khác — triệu chứng phân mảnh). Fix: thêm `tzdata` vào `requirements-automation-core.txt` của consumer (không phải lỗi code). **Pitfall môi trường:** venv `python-envs/automation` có thể báo `pip show tzdata` OK nhưng `import tzdata; print(tzdata.__file__)` trỏ hermes venv (`...hermes-agent\venv\Lib\site-packages\tzdata`) → venv đó THỰC SỰ thiếu; chạy test với hermes python (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`, có tzdata) để verify, hoặc cài bằng absolute-path python.



### WIP của agent khác + commit chồng

- `git status --short` TRƯỚC khi sửa file; file đích có uncommitted changes (VD stash `codex-pre-integration-*` + device_lock/executor bẩn) → **HỎI user trước khi commit chồng**; được duyệt thì commit nguyên file + message minh bạch ghi rõ "gồm WIP <agent> + patch atx"

- Consumer có WIP đòi symbol core chưa merge (VD `DeviceLockNeedsUserDecision`) → test collection fail. **Resolution path (user-approved 2026-08-15):** tìm branch feature trong core worktrees (`for wt in automation-core-*-wt; do grep -rln "Symbol" $wt/src; done`) → HỎI user → được duyệt thì:

  1. **Dry-run conflict check TRƯỚC**: `git merge-tree --write-tree master <branch>` — ra tree hash (không có `<<<<<<<`) = merge SẠCH, an toàn. Verify tree giữ patch mình: `git show <treehash>:<file> | grep -c "capture_ui_xml"`.

  2. `core_merge_guard.py acquire --repo "D:\\..." --owner <who>` → merge --no-ff → test core (device_lock + user_lock_gate + usb_popup + ui_dump) → release guard.

  3. **Merge 3-way KHÔNG mất patch atx trên master**: branch fork từ trước patch, không sửa vùng đó so với merge-base → git giữ version master. Chỉ 3 file feature thay đổi.

  4. Consumer test chạy lại — fail còn lại là WIP test cũ đang cập nhật theo behavior mới → để chủ WIP hoàn tất, KHÔNG sửa thay.

  → **Trường hợp user nói "1 mình m làm thôi / xử lý hết"**: hoàn tất WIP luôn. Sau merge core, mọi consumer test device_lock vỡ theo catalog lặp lại (release_with_audit, lock_protocol_version, queued_v2, jitter, summary index, dismiss count) — xem catalog đầy đủ ở `automation-core-consumer` §"Consumer device_lock test migration khi core đổi behavior". Chạy full suite từng repo, phân loại từng fail theo catalog, sửa test, commit riêng từng repo. Bỏ qua untracked rác không phải mình (`_vpn_probe*.py`, `_wbmap.py`, `.hermes/plans/`, `reap-*.py`) — không commit.

- `tools/core_merge_guard.py` cũng cần `--repo "D:\\..."` native (git -C với MSYS path fail exit 128)

- `git stash show -p stash@{0} -- <file>` trả RỖNG qua MSYS path mangling → dùng `git diff HEAD stash@{0} -- <file>` để đọc nội dung stash

- `git diff --stat <file>` gồm cả uncommitted WIP có sẵn — phân biệt phần mình bằng `git diff <file> | grep capture_ui_xml|uiautomator|...`

- Bỏ shell dump → capture_ui_xml (không tạo file /sdcard tạm) → bỏ luôn `try`/`finally` rm-cleanup; KHÔNG để `finally` rỗng (IndentationError); nếu giữ `try` thì dedent toàn bộ thân hàm



## Verify

- `get_ui_xml(dev)` trả len lớn (43K-76K = màn thật) thay vì 12K (stale)

- Test: full pytest repo xanh, `git diff --check` sạch

- Evidence: log `[ui-xml] atx primary OK len=...` xuất hiện



## Sizing max_workers bằng load test ATX thật

Khi cần chọn số máy chạy song song (feed session multi-machine): test bằng ATX API thật (port 7912 `POST /uiautomator`) + mô phỏng phiên đầy đủ (mở TikTok + chờ load S7 ~8s + 15 lần đọc UI/swipe), KHÔNG dùng ping nhẹ hay shell uiautomator (farm chuyển ATX hết). Kết quả 16/08: 30 máy song song 0 lỗi → max_workers=30; 40 bắt đầu 2 lỗi. Recipe đầy đủ: `references/atx-load-test-max-workers.md`.

