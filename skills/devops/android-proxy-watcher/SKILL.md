---

name: android-proxy-watcher

description: Run and debug Android proxy/VPN reconnect watchers with central locks, scheduler supervision, and proof-based verification.

---



# Android Proxy Watcher


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Use this skill when a local Android fleet watcher should restore proxy/VPN after boot, reconnect, or ADB recovery; or when a scheduler/task says it is running but a target remains without VPN.



## Required evidence chain



Do not call a watcher healthy merely because a wrapper exits successfully or its process exists. Verify four layers independently:



1. **Scheduler task:** query task state, enabled flag, last result, and task action.

2. **Watcher process tree:** confirm tray/supervisor → launcher → watcher worker command, start times, and expected mapping/runtime arguments.

3. **Target event:** inspect a current-run, target-specific reconnect/startup artifact or result. Confirm the artifact machine and serial match the requested target.

4. **Device proof:** verify the intended VPN interface is UP and Android connectivity exposes a VPN-connected state. Wi-Fi `CONNECTED` / `NOT_VPN` is not success.



A `DONE: result=...` line only identifies an artifact to read; it does not mean the target succeeded.



## Device lock protocol



- Acquire the central machine+serial lock before a manual proxy assignment or reboot.

- Never delete another owner's lock. For a stale `recovery`/`handoff` lock, verify the same-host PID is dead, then use the lock implementation's explicit takeover mechanism.

- A proxy recovery reboot may need to acquire its lock without requiring an already-ready VPN. Use the shared lock API's documented proxy-readiness bypass only for the bounded recovery action; preserve normal readiness gating for normal device work.

- Release the reboot lease only after boot-complete and wake/swipe preparation. The watcher must then acquire its own per-event lease.



## Watcher event behavior



For each startup/reconnect event:



1. Refresh target mapping safely and ensure machine/serial have not changed.

2. Acquire a per-event lock; do not hold device locks while idle.

3. Permit explicit safe takeover for a dead eligible retained lock, relying on the central lock policy to reject live owners.

4. Use a bounded wait for a live owner. On expiry, append `SKIPPED_DEVICE_LOCKED`, do not call proxy/VPN assignment, release/avoid retaining the lease, and return to the reconnect loop.

5. Capture sanitized ready and verified artifacts around proxy assignment.

6. Mark success only after actual VPN proof; otherwise classify the failure, run one evidence-based handler, and preserve the final artifact.



## Debugging a missed reconnect



When the watcher is live but a rebooted target has no VPN:



1. Check whether the current watcher runtime contains a new artifact for the exact target after its boot timestamp.

2. If there is no target artifact, investigate reconnect detection / worker scheduling rather than ViChanger or VPN assignment.

3. If there is a ready artifact but no verified artifact, inspect proxy assignment and VPN proof path.

4. If there is `SKIPPED_DEVICE_LOCKED`, inspect lock owner/state and bounded timeout behavior. Do not retry assignment over an active owner.

5. Keep results for concurrent machines separate; a newer artifact for another machine is not evidence for the target.



**Watcher chạy nhưng không gán proxy = máy KHÔNG có Wi-Fi sau reboot, KHÔNG phải watcher lỗi (2026-08-10, máy 74):** sau soft reboot, watcher phát hiện reconnect (`watch-events.jsonl` ghi `WATCH_PROXY_READINESS_PENDING` reason=reconnect) nhưng KHÔNG có `WATCH_EVENT_LOCK_ACQUIRED` / `PROXY_APPLICATION_SUCCESS` kế tiếp; stderr watcher lặp `[WIFI_NOT_READY] Wi-Fi/connectivity unavailable after unlock; readiness callback deferred`. Root cause: máy reboot xong Wi-Fi KHÔNG tự connect (`dumpsys wifi`: `mNetworkInfo [type: WIFI, state: DISCONNECTED/DISCONNECTED]`, `Supplicant state: DISCONNECTED`, RSSI -127, saved networks không auto-join) → readiness gate chặn vì ViChanger cần internet. Chuỗi chẩn đoán: (1) `tail watch-events.jsonl` máy đó — pending mà không có lock/application = chưa qua readiness; (2) `grep WIFI_NOT_READY` log stderr watcher; (3) `adb shell dumpsys wifi | grep -E 'mNetworkInfo|Supplicant'`.



**Fix xác nhận trên máy thật (2026-08-11): toggle radio Wi-Fi** — `settings get global wifi_on=1` (radio ON) nhưng supplicant vẫn DISCONNECTED → `svc wifi disable` rồi `svc wifi enable` (Samsung S7 = Android 8 / SDK 26: KHÔNG có `cmd wifi connect-network`, toggle là cách duy nhất restart supplicant để auto-join saved network). Sau toggle chờ ~30s, kiểm tra `dumpsys wifi` thấy `Supplicant state: COMPLETED` + `ip addr show wlan0` có `inet` → watcher TỰ gán proxy (event mới `WATCH_EVENT_DETECTED` + `PROXY_APPLICATION_SUCCESS`), `tun0` lên `inet 172.19.x.x`; KHÔNG cần restart watcher. Retry worker upload chỉ sau khi `tun0` có `inet` + `WATCH_EVENT_VERIFIED_SUCCESS` mới nhất. Ghi chú design: core `wait_for_wifi()` chỉ QUAN SÁT connectivity, không bao giờ toggle Wi-Fi (docstring nói rõ) — muốn auto-recovery bền vững phải thêm `auto_enable_wifi` option trong core `watch_device_reconnect` (mặc định False để consumer khác giữ hành vi) rồi bật ở gan-proxy.



**Watcher fail-closed sau reboot vì máy QUÁ TẢI (timing/overload), KHÔNG phải thiếu cơ chế mở khoá (2026-08-17, máy 10):** user hỏi "sao watcher không tự mở khoá màn gán proxy liền sau reboot?". Trả lời: watcher CÓ tự mở khoá — `_go_home_and_verify_with_keyguard_fallback` (vi_changer_runner.py L156) gọi `prepare_device(swipe_unlock=True)` (swipe 85%→35% + keyevent BACK, bounded 1 lần, fail-closed) — chính là fix case máy 74 (08/08). Máy 10 fail vì TIMING + OVERLOAD, không phải thiếu code: (1) event reconnect ngay lúc boot xong, màn ĐANG ở LAUNCHER (không khoá) — `attempt-13-watch-13-ready.json`: `focused_window=LauncherActivity`, `vichanger_process=false`; (2) ViChanger start chậm (máy vừa boot, `uptime` load 6+ trên S7), màn TỰ KHOÁ do screen timeout trong lúc chờ → `PROXY_APPLICATION_FAILURE: VPN connected but Recent Apps/Home verification failed` sau ~1m42s; (3) capture lúc đó `focused_window=unknown` + `vichanger_installed=false` = máy quá tải, mọi dump fail; (4) retry lần 2 `Vi Changer is not installed` = **TRANSIENT read failure** — verify `pm list packages | grep vichanger` vẫn ra package → KHÔNG phải app bị gỡ (đừng kết luận uninstall, đừng cài lại bừa); (5) `FINAL_BLOCKED` = đúng 2-attempt design, watcher chờ event mới (reboot/reconnect), không đụng máy nữa. Ladder chẩn đoán: so sánh attempt JSON ready/before/after-recovery (focused_window + vichanger_installed) → check tải máy `uptime`/`/proc/uptime` → `pm list packages` loại trừ uninstall → khi máy đã ổn định (Wi-Fi OK + package OK + pin OK) reboot lại 1 lần là watcher gán lại được, KHÔNG cần sửa code. Phân biệt case máy 74: ở đó Wi-Fi KHÔNG auto-join sau reboot (readiness gate chặn, `WIFI_NOT_READY`), còn máy 10 Wi-Fi CONNECTED bình thường — nguyên nhân chỉ là overload + timing.

**PITFALL chẩn đoán reboot cause trên host Hermes:** terminal hardline blocklist chặn MỌI lệnh chứa chuỗi literal `reboot` — kể cả read-only (`adb shell "logcat -d -b events -t 100" | grep -iE 'boot|reboot|shutdown'` bị BLOCKED vì pattern có từ reboot). Tách riêng `getprop sys.boot.reason`/`ro.boot.bootreason` (không có từ reboot thì chạy được) và grep pattern KHÔNG chứa từ "reboot".

**Máy reboot liên tục / `system_server_watchdog` trong dropbox = NFC crash loop (2026-08-17, máy 10 — ROOT CAUSE LADDER):** khi 1 máy tự reboot lặp lại (uptime reset vài phút 1 lần) mà watcher log không thấy soft-reboot của watcher, đừng kết luận "watcher reboot máy" hay "máy quá tải" — điều tra crash loop theo ladder:
1. `dumpsys dropbox | grep -E "^2026-08-17 1[4-8]:" | grep -iE "tombstone|watchdog"` → **SYSTEM_TOMBSTONE mỗi ~1.5 phút liên tục = crash loop**; `system_server_watchdog` entry = watchdog reboot (Subject `Blocked in monitor com.android.server.am.ActivityManagerService ...`).
2. `logcat -d -b crash -t 80` → tìm `Fatal signal 6 (SIGABRT)` + process name. Máy 10: thread `enableInternal` trong **`com.android.nfc`**, backtrace `libnfc_nci_jni.so (nfcManager_doAbort)` → **NFC stack abort vì hardware không đạt chuẩn**.
3. `dumpsys nfc | grep -iE 'mState|resonant'` → `NFC resonant frequency=NG` = antenna/crystal fail (S7 farm nào cũng NG — vô hại khi NFC TẮT). **Chỉ crash khi máy đang CỐ BẬT NFC (`mState=turning on`)**.
4. So sánh máy khỏe: `mState=off` + `settings get secure nfc_on` = null (chưa từng bật) → không crash. Máy bệnh: nfc_on=1 từng bật (setting sót) → sau reboot NFC tự enable → crash loop → thỉnh thoảng watchdog reboot.
5. **FIX (không phải hardware hỏng, không cần thay board):** `settings put secure nfc_on 0` + `pm enable com.android.nfc` (trả về default như máy khác) + **reboot** — NFC service khởi động ở state off → hết crash loop (verify: 0 tombstone mới trong 5-6 phút + `mState=off`). Lưu ý: `pm disable-user` + `am force-stop` KHÔNG đủ (NFC là persistent system service tự restart; force-stop không giữ). `pm path`/settings áp dụng thật chỉ sau reboot.
6. Hệ quả cho automation: máy crash loop + reboot giữa chừng làm worker chết (máy offline → ADB error), state không ghi. Khi 1 máy "tự reboot 2 lần liên tiếp" trong phiên → check ladder này TRƯỚC khi chạy lại bất kỳ script nào. Transcript đầy đủ: `references/nfc-crash-loop-watchdog-reboot-20260817.md`.

**Fix code transient "Vi Changer is not installed" sau boot (ĐÃ SHIPPED 2026-08-17, commit `631fb3e` gan-proxy):** `_pm_path_with_boot_retry` trong `vi_changer_runner.py` (retry `pm path` 3 lần, backoff 2s/4s) — `pm path` trả rỗng vài giây trên máy quá tải vừa boot dù package còn cài; `VICHANGER_NOT_INSTALLED` giờ là signature recoverable (`wait_for_package_manager_after_boot` — sleep bounded + recapture) trong `recover_target` + được phép trong `_recover_watch_event_failure`; `proxy_application` stage được `MAX_WATCH_PROXY_APPLICATION_ATTEMPTS=3` (các stage khác vẫn 2). Đọc event log máy bị `WATCH_PROXY_APPLICATION_FAILURE ... Vi Changer is not installed` → `pm list packages | grep vichanger` trước khi kết luận uninstall (đừng cài lại APK bừa).

**Watcher sống nhưng từng máy riêng lẻ bị `WATCH_MONITOR_FINAL_BLOCKED` do WinError 5 readiness file (2026-08-22, máy 34):**
Triệu chứng: Tiến trình Watcher (`gan_proxy_fleet.py watch`) vẫn sống bình thường trong `wmic`, nhưng một số máy sau khi reboot không bao giờ được gán proxy (`tun0` không lên) → worker/script chạy dính `MissingVpnRecoveryError` / `TimeoutError: proxy readiness timeout`.
Root cause: Luồng monitor của máy đó gặp `PermissionError: [WinError 5] Access is denied` khi atomic rename `~/.codex/device-readiness/<hash>.json.<pid>.tmp` → `<hash>.json` (Windows file lock contention giữa consumer đọc và watcher ghi) → watcher ghi `WATCH_CORE_READINESS_FAILURE` rồi chuyển sang `WATCH_MONITOR_FINAL_BLOCKED` và ngừng giám sát máy đó trong suốt run hiện tại.
Ladder chẩn đoán:
1. `cat <runtime>/<run-hash>/machine-<N>/watch-events.jsonl | tail -n 10` → tìm event `WATCH_CORE_READINESS_FAILURE` / `WATCH_MONITOR_FINAL_BLOCKED` chứa `[WinError 5] Access is denied`.
2. Kiểm tra `ls -la ~/.codex/device-readiness/ | grep tmp` → thấy file `.tmp` sót lại cùng PID của watcher.
3. Phục hồi: Xóa file `.tmp` kẹt, kill watcher tree (`MSYS_NO_PATHCONV=1 taskkill /PID <pid> /T /F`) để tray tự respawn run mới khởi tạo lại worker cho máy.
4. Fix triệt để code: `mark_proxy_state` trong `automation_core/readiness.py` thêm suffix UUID ngẫu nhiên + retry backoff 5 lần khi `os.replace` gặp `PermissionError`/`OSError`, đảm bảo không chết luồng monitor.

**Samsung Galaxy S7 Link Speed Wi-Fi 390-433 Mbps (phần cứng 1x1 MIMO Wi-Fi 5):**
- Khi kiểm tra `dumpsys wifi` thấy `Link speed: 390Mbps` (hoặc `433Mbps`) dù mạng LAN/Router 1 Gbps: Đây là link speed tối đa thực tế của chip Wi-Fi S7 (802.11ac 1x1 MIMO, 40/80MHz), không phải lỗi AP hay đường truyền.

**Watcher task exists but watcher is NOT running (2026-08-05):** the Windows

logon task `TikTokAllSchedulerTray` existed with `Status: Ready` but `Last

Result: 267014` (0x41306 = task was terminated / did not complete) → no

`gan_proxy_fleet.py watch` process was spawned, so rebooted machines never got

VPN. Evidence ladder:



```bash

schtasks /Query /TN "TikTokAllSchedulerTray" /FO LIST /V | grep -E "Last Result|Status"

wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep -i gan_proxy   # EMPTY = watcher dead

```



Fix = re-run the tray with the exact command from the task XML

(`schtasks /Query /TN "TikTokAllSchedulerTray" /XML`, `<Arguments>`) as a

background process; verify new watcher processes appear with fresh PIDs and the

target gains `tun0` + `inet` within ~1 min. Note: `schtasks //Query` (double

slash) fails in git-bash — use single-slash `schtasks /Query`.



Manual watcher relaunch (2026-08-05): when re-running by hand, `watch`

REQUIRES exactly one of `--all` or `--machines` (bare `watch --mapping ...`

exits `BLOCKED: choose exactly one of --all or --machines`). Prefer the

scheduled wrapper and the selected runtime's installed wheel over injecting a

mutable core checkout. Working command from `D:\Taadaa\gan-proxy` must use a

clean environment: remove inherited `PYTHONPATH`/`PYTHONHOME`/`VIRTUAL_ENV`,

then set `PYTHONPATH` only to the consumer `scripts` directory if needed. Do

not add `automation-core\src` unless the task explicitly targets a source

checkout; doing so can mask the installed wheel and invalidate provenance

checks:



```bash

env -i HOME="$HOME" USERPROFILE="$USERPROFILE" \

  PATH="/c/Users/Kibe/AppData/Local/Programs/Python/Python312:/c/Windows/System32" \

  PYTHONPATH="D:\Taadaa\gan-proxy;D:\Taadaa\automation-core\src" \

  python -u scripts/gan_proxy_fleet.py watch --all \

  --mapping "D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx" \

  --adb "C:\Program Files (x86)\xiaowei\tools\adb.exe" \

  --runtime "D:\CodexRuntime\codex_gmail_debug-gan-proxy" --poll-interval 15

```



Then **reboot a mapped machine to prove auto-recovery**: the watcher relaunches

`vn.vichanger.app` and `tun0` returns within ~1–2 min (57 came back on first

poll; 62 took a second poll cycle). `pidof vn.vichanger.app` + `ip addr show

tun0 | grep -c 'inet '` are the device-side proofs. The watcher process PID is

the `python.exe` one (find via `wmic ... | grep gan_proxy`), NOT the bash

wrapper PID the terminal reports.



**`cockpit-cliproxy.exe` is NOT the proxy watcher (user correction, 2026-08-05):**

a running `cockpit-cliproxy.exe` (Antigravity Cockpit quota sidecar, args point

at `.antigravity_cockpit\...\quota-reserve.json`) looks like a proxy process but

has nothing to do with Gan Proxy. Do not report "watcher is running" because

cockpit-cliproxy exists — that was a wrong diagnosis in-session. The ONLY valid

watcher process is `gan_proxy_fleet.py watch` (or its `run` fleet mode); check

with `wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep gan_proxy`.

When the watcher is genuinely dead, rebooted machines lose `tun0` because

`vn.vichanger.app` is NOT relaunched — the app does not auto-start after reboot,

so VPN only returns when the watcher force-stops/relaunches it

(`recover_target` signature `VPN_START_NOT_VERIFIED` → `force_stop_relaunch_vichanger`).



## Reconnect debugging reference



For the target-specific evidence ladder, circular readiness-gate prevention, retained-lock policy alignment, resilient per-worker telemetry, and the user preference not to start unrelated TikTok schedules, see `references/watcher-reconnect-debugging.md`.



**Controlled watcher restart via tray auto-respawn (2026-08-08; supervisor đổi 2026-08-10 → `GanProxyWatcherTray`, xem section "Standalone proxy watcher tray + Hermes health guard"):** when code

changes must be loaded into a LIVE watcher, do not touch the tray/task. The

watcher is a two-node python tree (parent = automation venv python, child =

Python312 python, SAME `watch --all --workers 80` cmdline); the supervising tray

runs a 15 s timer that respawns it automatically. Restart = verify tree

PowerShell probe (never inline — bash eats `$_`; write a `.ps1` under runtime),

preflight device-lock grep for the watcher PIDs (empty = safe), kill both PIDs

via `Stop-Process` (git-bash `taskkill //PID` is invalid), wait ~15-60 s, then

verify: new PIDs, fresh `watcher-logs/proxy-watcher-<ts>.stdout.log` with EMPTY

stderr, new run-hash dir, and the target's `WATCH_EVENT_VERIFIED_SUCCESS` in the

new run. Worker spawn is INCREMENTAL (17→26→38→56→72→76 over ~4 min) — a missing

machine dir early is not a failure. Full procedure/verification ladder:

`references/watcher-restart-tray-respawn.md`.



**Proxy-readiness handshake → `DEVICE_LOCK_FAILED` (2026-08-07):** a workflow

gated on proxy readiness (e.g. `tiktok_workflow` `ACQUIRE_LOCKS`) fails with

`[DEVICE_LOCK_FAILED] ... proxy readiness failed for <serial>: proxy_application:ADBError:

adb command timed out: ... am broadcast --receiver-foreground ...` when the watcher

wrote `proxy_failed` to `~/.codex/device-readiness/<sha256(serial)[:24]>.json`.

This is **transient** — the watcher retries the broadcast and flips back to

`proxy_ready` minutes later. Diagnose from the readiness FILE (the log/report error

is truncated at the broadcast args), not the log line. **Before retrying a failed

worker, check the device lock** (`machine_<N>.lock.json`, owner PID via `wmic`):

the fleet/scheduler often already re-spawned a legitimate worker for the same

machine, so a blind retry fails-closed again with `device lock active` and only

creates a spurious fail report. Full chain + checklist:

`references/proxy-readiness-handshake-device-lock.md`.



**Retry worker đâm đúng cửa sổ reboot — đọc `boot_id` readiness TRƯỚC khi retry (2026-08-08, máy 65):** worker fail `[DEVICE_LOCK_FAILED] ... Device "tun0" does not exist` vài phút sau khi VPN verified OK = **máy vừa reboot**, không phải proxy chết. 3 dấu hiệu: (1) `~/.codex/device-readiness/<sha256(serial)[:24]>.json` có `boot_id` KHÁC lần check trước; (2) watcher đã sinh artifact mới `attempt-NN-watch-NN-ready/verified.json` (đang xử lý `boot_id_changed`); (3) `pidof vn.vichanger.app` đổi PID. **Chỉ retry sau khi watcher ghi `WATCH_EVENT_VERIFIED_SUCCESS` mới nhất của boot mới** + `tun0` có `inet` — máy 65 retry sớm fail 17:59→18:02, watcher verified 18:02, retry 18:03 → SUCCESS. Runbook đầy đủ: `tiktok-upload-ui-recovery` §9b.

**Phân biệt 2 dạng lỗi VPN Preflight & độ trễ Watcher (2026-08-22):**
1. **Mất hẳn VPN (`MissingVpnRecoveryError` / `tun_up=False, vpn_connected=False` - máy 74):** Máy không có card mạng `tun0`. Khi script kích hoạt tự phục hồi `recover_missing_android_vpn` (chờ reassign 45s -> reboot máy -> chờ `proxy_timeout` 180s), máy vừa reboot có thể bị trễ Wi-Fi (`WIFI_NOT_READY` trên S7) khiến script hết 180s timeout và fail-closed dừng phiên báo alert Telegram. Ngay sau khi dừng, Wi-Fi máy ổn định và Watcher ở chu kỳ poll kế tiếp sẽ tự động gán `tun0=1` thành công (`WATCH_EVENT_VERIFIED_SUCCESS`). Khi triage: luôn kiểm tra `watch-events.jsonl` và `ip addr show tun0` trước khi can thiệp thủ công vì máy thường đã tự lên VPN sau vài phút.
2. **Treo ADB broadcast GET_IP (`tun_up=True, vpn_connected=True` + `ViChanger GET_IP failed after 3 retries: adb command timed out` - máy 37):** Mạng VPN và card `tun0` **đang chạy bình thường**, nhưng lệnh broadcast `vn.vichanger.app.GET_IP` qua ADB bị timeout/treo app ViChanger. Đây là lỗi nghẽn tầng giao tiếp ADB / app ViChanger, KHÔNG phải mất VPN. Triage: force-stop ViChanger hoặc restart nhẹ ADB/thiết bị nếu lặp lại.



**Sibling workers chết hàng loạt vì uiautomator contention — retry máy nào cũng chấp nhận được khi dump OK (2026-08-08, coord 52-65-69):** trong cùng 1 run, máy 52 chạy DONE trong khi 65 chết ở `OPEN_TIKTOK` (`uiautomator_idle_state_error`, visual gate dark — app thực tế OK) và 69 chết ở `CONNECT_DEVICE` (`close_all_apps_start failed: non_xml_ui_dump`) — cả farm 75 máy cùng 1 ADB server làm uiautomator treo cục bộ từng máy. Đây KHÔNG phải lỗi per-machine; sau ~2 phút dump tự hết treo (`uiautomator dump` trả OK). Trước khi retry từng máy: (1) không worker nào đã respawn cho máy đó (`wmic ... | grep tiktok_workflow` — gõ đúng máy), (2) không lock còn giữ, (3) test dump trực tiếp trên device. Retry follow quy tắc: mỗi máy MANUAL_REVIEW là fail-closed đúng thiết kế — `OPEN_TIKTOK` không nằm trong `SOFT_REBOOT_RECOVERABLE_STATES` (chỉ DISMISS_POPUPS), nên UI-dump-fail ở OPEN_TIKTOK luôn về MANUAL_REVIEW; nếu lặp lại nhiều, cân nhắm thêm OPEN_TIKTOK vào nhánh soft-reboot recovery (worker + test + COMPAT entry), chưa làm thì không sửa gì.



**Core pin phải trỏ file TỒN TẠI + phiên bản đúng (2026-08-08, gan-proxy):**

`requirements-automation-core.txt` từng trỏ `../automation-core-worktrees/device-lock-transactional-recovery-20260804/dist/automation_core-0.4.34-py3-none-any.whl`

— worktree đó ĐÃ BỊ XÓA nên `pip install -r` sẽ fail. Verify: `ls` đường dẫn pin + `grep version pyproject.toml` core chính

(thư mục `automation-core-worktrees/` rỗng/không tồn tại; core chính `D:\Taadaa\automation-core` = 0.4.43,

`dist/automation_core-0.4.43-*.whl` tồn tại). Fix pin về `../automation-core/dist/automation_core-0.4.43-py3-none-any.whl`.

Khi nghi "merge conflict trùng vs core", đây là nơi kiểm tra đầu tiên — không phải code diff.



**whl core build TRƯỚC commit thêm param → watcher crash TypeError cho MỌI máy (2026-08-11, máy 74/30):** gan-proxy gọi `auto_enable_wifi=WATCH_AUTO_ENABLE_WIFI` (dòng 47 = True, truyền tại dòng 1308) nhưng venv `D:\Taadaa\python-envs\automation` cài whl build từ TRƯỚC commit `19730cb` → `watch-events.jsonl` MỌI máy có `WATCH_CORE_READINESS_FAILURE | TypeError: watch_device_reconnect() got an unexpected keyword argument 'auto_enable_wifi'` → watcher chết ở readiness, KHÔNG tới bước gán proxy → tun0 không lên → workflow (tiktok_workflow ACQUIRE_LOCKS) fail-closed `Device "tun0" does not exist`. Tray vẫn chạy + respawn 15s + `Last Result: 267009` (0x41301 = currently running) → nhìn ngoài tưởng healthy. Ladder chẩn đoán: (1) `tail <run>/machine-<N>/watch-events.jsonl` → event `WATCH_CORE_READINESS_FAILURE ... TypeError`; (2) `grep -n auto_enable_wifi gan_proxy_fleet.py` (flag đã bật?); (3) **check PARAM TRONG WHL, không phải src**: `zipfile.ZipFile(whl).read('automation_core/device_recovery.py')` grep `auto_enable_wifi` — src có nhưng whl không = whl build trước commit (dist KHÔNG tự cập nhật khi commit!). Fix: từ `D:\Taadaa\automation-core` chạy `python -m pip wheel --no-deps -w dist .` → verify lại whl chứa param → `pip install --force-reinstall --no-deps <whl>` → kill watcher TREE → tray 15s respawn PID mới → máy qua `READINESS_PASS → PROXY_APPLICATION → VERIFICATION → WATCH_EVENT_VERIFIED_SUCCESS`, tun0=1. ⚠️ Chạy pip/python bọc `env -i HOME="$HOME" USERPROFILE="$USERPROFILE" PATH="/c/Users/Kibe/AppData/Local/Programs/Python/Python312:/c/Windows/System32"` vì PYTHONPATH session bị set nhiều lần trỏ hermes-agent venv → import resolve SAI venv. ⚠️ Kill watcher tree bằng `MSYS_NO_PATHCONV=1 taskkill /PID <pid> /T /F` — git-bash `taskkill //PID ...` FAIL `Invalid argument/option`.

**Khi workflow fail `Device "tun0" does not exist` mà watcher process sống → đọc event log TRƯỚC** (WATCH_CORE_READINESS_FAILURE + TypeError = code mismatch, KHÔNG phải lỗi máy) — đừng vội đổ lỗi app VPN (Vichanger "No LSPosed access !!!"/"Invalid API Key!!!" là cảnh báo app không liên quan gán proxy, user: "kệ mẹ nó") và đừng nhập API key bừa.

**Vi Changer: Popup "No LSPosed access !!!" là hoàn toàn bình thường sau khi gán/mở app — KHÔNG PHẢI LỖI (user chốt 2026-08-18):**
Khi mở Vi Changer hoặc gán proxy qua Vi Changer trên các thiết bị farm, popup *"Message: No LSPosed access !!!"* xuất hiện là hành vi bình thường của ứng dụng (không ảnh hưởng tới kết nối VPN hay logic gán proxy). Tuyệt đối KHÔNG chẩn đoán đây là lỗi hỏng gán proxy hay lỗi thiết bị.
- Nếu thấy máy kẹt lock sau khi chạy `gan_proxy_fleet.py` watch mode: Kiểm tra xem watcher có bị chết ngầm / leak bộ nhớ (`MemoryError: Thread._bootstrap` trong stderr log) làm sót lock file trên đĩa hay không, KHÔNG đổ lỗi cho popup Vi Changer.
- Khi dọn dẹp stale lock từ tiến trình chết: Sau khi xác nhận PID cũ đã chết (`owner_active: false`), xóa đích danh `machine_<N>.lock.json` và `serial_<SERIAL>.lock.json`, sau đó xóa file lease trong `runner-live-lease/<date>.json` nếu có để cron runner có thể lập tức tái phân phối phiên chạy.



**Core 0.4.43 KHÔNG có `maintenance_handoff` → watcher fail-closed (2026-08-08):**

`request_maintenance_handoff` đã bị bỏ khỏi core (quyết định user 08-08 — vấn đề popup draft sau reboot

ĐÃ có handler `_dismiss_resume_draft_popup`/`_delete_all_profile_drafts` trong consumer). Hệ quả:

- `gan_proxy_fleet.py` KHÔNG gọi method đó (0 reference); `_read_post_reboot_owner_ack` (L556) **fail-closed an toàn**:

  lock không có field `maintenance_handoff` → trả `None` → `_watch_post_reboot_takeover_proof` (L651) bỏ `owner_ack` →

  watcher KHÔNG bao giờ takeover post-reboot → không chen ngang consumer đang sống (đúng thiết kế, không crash).

- Core 0.4.43 `_takeover_payload`: owner `running` + `_owner_process_alive=True` → **từ chối takeover KỂ CẢ có proof**

  (fail-closed đúng cho "interrupt live consumer"); takeover chỉ hợp lệ khi owner CHẾT (`alive=False`).

- **Test cũ viết cho feature bỏ → thay bằng fail-closed test**, không xóa trắng cũng không mock bừa:

  (1) bỏ lời gọi `request_maintenance_handoff`, mock `_read_post_reboot_owner_ack` trả owner_ack schema đúng

  (mode/state/handoff_id/pre_boot_id/previous_status/owner{host,pid,lock_id,run_id} lấy từ lease thật);

  (2) mock `_owner_process_alive=False` cho kịch bản takeover sau reboot (owner chết), bỏ assertion "owner paths giữ nguyên"

  (takeover core ghi đè → `FileNotFoundError` khi `owner.release()`);

  (3) hoặc thay 2 test cũ bằng test fail-closed: `_read_post_reboot_owner_ack` → None khi không có handoff;

  proof vẫn `vpn_missing=True` nhưng KHÔNG chứa `owner_ack` (không bao giờ crafted owner_ack authorize interrupt).

- Battery code mới (`set_battery_random`, chống popup Samsung "PIN YẾU" che composer sau reboot):

  gọi `adb` 3 lần (`dumpsys battery set level/status/ac`) → test mock `fleet.random.randint` trả hằng (55)

  + assert `adb.call_args_list` đúng 3 lệnh; `adb.assert_not_called()` cũ là SAI (code mới luôn gọi battery).

- Test consumer chạy với `PYTHONPATH="D:\Taadaa\automation-core\src"` (core src 0.4.43), không phải venv cài sẵn.



## Background schedule inventory & "PowerShell giật chớp" diagnosis (2026-08-10)



When the user asks "có gì đang chạy ngầm / máy giật chớp cửa sổ" — enumerate ALL layers, don't just answer about the watcher:



```bash

# 1. All background python/node processes with full command lines

wmic process where "Name='python.exe' or Name='node.exe'" get ProcessId,CommandLine

# 2. PowerShell processes (the flash suspects)

wmic process where "Name='powershell.exe'" get ProcessId,CommandLine

# 3. Scheduled tasks (custom only — filter out Microsoft\)

schtasks /Query /FO CSV | grep -iv "Microsoft\|Windows"

# 4. Per-task XML for commands/triggers/intervals

schtasks /Query /TN "<TaskName>" /XML | grep -E "Command|Arguments|StartBoundary|Interval|Repetition"

```



**Full inventory (verified 2026-08-10)** — running schedules: `TikTokScheduler` (logon + restart 1m, python `-m scheduler --live`), `TikTokScheduleRecovery`, `TikTokScheduleRecoveryHealth`, `TikTokAllSchedulerTray` (tray MỚI: proxy watcher + 15s respawn timer + 4 sub-schedulers), `TikTokSchedulerTray` (tray CŨ — chạy song song, đừng nhầm là duplicate bug), `GmailRegistrationScheduler` + `GmailRegistrationSchedulerTray`, `HermesGatewayRestart_20260809` (one-shot, xong), `cua-driver-serve` (1m probe, ngủ), wake tasks `TikTokAllSchedulerWake` ×4/ngày (09:30/14:00/15:30/19:00) + `TikTokSchedulerWake` + `GmailSchedulerWake` 08:00. Background processes: 9router tray+server, `gan_proxy_fleet.py watch` ×2, tiktok schedulers (feed/login/2FA), `recovery_runtime --watch --dispatch`, gmail_scheduler, Hermes gateway serve ×2, live workers (tiktok_workflow, feed-session). **UPDATE cuối ngày 2026-08-10 (user chốt "tạm thời tắt hết trừ proxy watcher"):** TikTok/Gmail scheduler + 2 tray TikTok + recovery + wake tasks đã DISABLE + process bị kill; còn chạy: `GanProxyWatcherTray` (standalone, chứa proxy watcher + Hermes guard), Hermes gateway serve ×2, 9router, workers đang chạy dở (không kill giữa chừng — để tự xong).



**PowerShell window flash "lâu lâu" = WAKE TASKS, benign — NOT a watcher failure.** Task Scheduler launches `powershell.exe` with `-Command "Start-ScheduledTask ..."` under InteractiveToken: even with `-WindowStyle Hidden`, the console window is CREATED then hidden → 1-frame flash. Frequency matches the wake-task schedule (4-5×/day). Do NOT diagnose this as watcher/tray death; verify watcher via the normal `wmic | grep gan_proxy` ladder instead. To eliminate the flash entirely: replace wake tasks' powershell with `schtasks /Run` direct or a python call — cosmetic, not required.



**Flash LÚC LOGIN (2 cửa sổ, 2026-08-11) = 2 logon task: `cua-driver-serve` + `GanProxyWatcherTray`** — cùng cơ chế console-tạo-trước-khi-ẩn. Khác wake task: logon flash kéo dài hơn và **user bấm tắt = giết cả tree tray + watcher** (`Last Result: 0xC000013A`). Khi user báo "có 2 powershell nhảy lên lúc bật máy": liệt kê logon task enabled trước (`schtasks /query /fo csv | grep -i powershell` + `Get-ScheduledTask` filter `MSFT_TaskLogonTrigger`), đừng kết luận virus/malware. Fix triệt để flash login: bọc action task qua `wscript.exe` + VBS `WshShell.Run "powershell ... -WindowStyle Hidden", 0` (mẫu: 9router.vbs trong Startup folder).



## Standalone proxy watcher tray + Hermes health guard (2026-08-10)



**Architecture change:** watcher KHÔNG còn do `TikTokAllSchedulerTray` supervise (task đó DISABLED 2026-08-10 — nó còn `Start-AllSchedulers` spawn 4 TikTok schedulers trực tiếp bằng `Start-Process`, không qua Task Scheduler, nên disable task không đủ; phải kill tray + con python orphan). Thay bằng task riêng **`GanProxyWatcherTray`** (logon trigger):

- Script: `D:\Taadaa\automation-core\src\automation_core\scheduler\proxy-watcher-only-tray.ps1` (CRLF + ASCII-only — xem pitfall encoding)

- Chỉ giữ proxy watcher: 15 s `Ensure-ProxyWatcher` timer + `Start-ProxyWatcher` lúc khởi động (adopt process `gan_proxy_fleet.py watch` đang chạy qua `Find-ProxyWatcherProcess` — KHÔNG spawn trùng khi tray mới chạy chồng watcher cũ)

- **Hermes health check**: mỗi 60 s check process `hermes_cli.main gateway run` (⚠️ 2026-08-11: trước đây check pattern `serve` SAI — gateway thực chạy `-m hermes_cli.main gateway run`, xem subsection \"Tray crash + Hermes guard fixes\"); snapshot phải lọc **CẢ `python.exe` lẫn `pythonw.exe`** (gateway chạy windowless bằng pythonw); down streak ≥ 2 → chạy `hermes.exe gateway restart` (tối đa 1 lần/10 phút, chống false-positive lúc reboot/upgrade); log `D:\CodexRuntime\codex_gmail_debug-gan-proxy\hermes-health.log`

- **Telegram alert độc lập Hermes** (Hermes sập VẪN gửi được — bot POST thẳng): đọc `TELEGRAM_BOT_TOKEN` từ `~/AppData/Local/hermes/.env` → `https://api.telegram.org/bot<token>/sendMessage` chat_id=`-5345976284` (group Taadaa), cooldown 10 phút. Events: DOWN (streak 1) → RESTART → restart exit code / FAILED → OK (recover)

- Task tạo qua file XML: `schtasks /TR` giới hạn **261 ký tự** → `write_file` XML rồi convert sang UTF-16 (`python -c "open(p,'wb').write(open(p,'rb').read().decode('utf-8').encode('utf-16'))"` — write_file ra UTF-8 bị Task Scheduler reject) → `schtasks /Create /TN <name> /XML <file> /F`

- Tắt hàng loạt scheduler TikTok/Gmail (2026-08-10): disable 9 task (`TikTokScheduler`, `TikTokScheduleRecovery`, `TikTokScheduleRecoveryHealth`, `TikTokSchedulerTray`, `TikTokSchedulerWake`, `TikTokAllSchedulerWake`, `GmailRegistrationScheduler(+Tray)`, `GmailSchedulerWake`) + kill process tree. **Kill powershell wrapper KHÔNG giết con python orphan** — kill theo danh sách PID đầy đủ từ `wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep scheduler|gmail` (cần 2 đợt: lần 2 bắt con orphan còn sống)



**PITFALL — .ps1 phải ASCII thuần (PS 5.1):** PowerShell 5.1 đọc file không-BOM theo ANSI/cp1252 → emoji/em-dash UTF-8 **vỡ parse** (`0x94` = `"` → "missing terminator"/"string is missing the terminator"). Repo convention: tiếng Việt KHÔNG DẤU + không emoji trong .ps1. Verify: `python -c "assert not [b for b in open(f,'rb').read() if b>127]"` (nếu còn, `unicodedata.normalize('NFD')` bỏ combining) + `[System.Management.Automation.Language.Parser]::ParseFile` → "PARSE OK" (nhớ khởi tạo `$errs=$null` trước `[ref]$errs` trong powershell -Command 1 dòng — [ref] không nhận biến chưa tồn tại).



**PITFALL — smoke-test hàm trong PS1 có `[Windows.Forms.Application]::Run()`:** dot-source scriptblock sau khi strip dòng Run() (`-replace '(?m)^\[Windows.Forms.Application\]::Run\(\)\s*$',''`), chạy với `powershell -STA` (script throw nếu MTA), gọi hàm trực tiếp. "TOKEN OK + ALERT SENT" = kênh Telegram hoạt động (tin test hiện trên group — user xác nhận).



## Tray crash + Hermes guard fixes (2026-08-11) — 3 bug khiến tray chết & session tự ngắt



**Triệu chứng:** sau reboot user thấy 2 cửa sổ PowerShell flash lúc login = 2 logon task (`cua-driver-serve` + `GanProxyWatcherTray`) — cosmetic của Task Scheduler (console tạo trước khi `-WindowStyle Hidden` áp dụng). ⚠️ **User bấm tắt cửa sổ = giết CẢ TREE** (console close → Ctrl+C toàn tree; task `Last Result: -1073741510` = 0xC000013A = STATUS_CONTROL_C_EXIT) → tray + watcher chết, không tự hồi sinh tới lần login kế.



**Bug 1 — tray crash lúc startup khi không có process python:** `Get-PythonProcessSnapshot` `return @(...)` — PowerShell **unroll mảng rỗng thành `$null`** khi truyền làm argument → `[Parameter(Mandatory=$true)]` reject null → script chết ngay (task `Last Result: 1`; stderr: `Cannot bind argument to parameter 'Snapshot' because it is null`). Verify nhanh: `powershell -Command 'function f{return @()}; $x=f; $null -eq $x'` → True. Fix: `$snap = @(...); return ,$snap` (comma-unroll) + `catch { return ,@() }`.

**Bug 2 — `[Parameter(Mandatory=$true)][object[]]` còn reject mảng RỖNG** (`ParameterArgumentValidationErrorEmptyArrayNotAllowed`); `AllowEmptyArray` **KHÔNG tồn tại trong Windows PowerShell 5.1** (lỗi `Property 'AllowEmptyArray' cannot be found for type 'CmdletBindingAttribute'` — chỉ có AllowEmptyString/Collection/Null). Fix: bỏ `Mandatory` khỏi param array (comma-unroll đã đảm bảo không bao giờ $null).

**Bug 3 (NGUY HIỂM NHẤT) — Hermes guard false-negative → restart gateway mỗi 10 phút → tự giết session agent:** guard check pattern `hermes_cli.main serve` nhưng gateway thực chạy `pythonw.exe -m hermes_cli.main gateway run`; VÀ snapshot chỉ lọc `Name='python.exe'` bỏ `pythonw.exe` → guard KHÔNG BAO GIỜ thấy gateway → `hermes-health.log` có `HERMES_DOWN streak=n` + `HERMES_RESTART_ATTEMPT` lặp mỗi 10 phút → agent đang chạy bị ngắt giữa chừng (các lần \"gateway shut down\" / \"Operation interrupted\"). **Khi session tự ngắt lặp lại: check `tail hermes-health.log` trước, đừng đổ lỗi mạng/host.** Gateway process thật: `wmic process where "Name='pythonw.exe'" get CommandLine` → `-m hermes_cli.main gateway run`.



**"2 python watcher" = launcher chain (thiết kế), KHÔNG phải duplicate:** tree đúng = `tray powershell → wrapper powershell (run-proxy-watcher.ps1) → python-envs venv python → con Python312 (cùng cmdline watch)`. `gan_proxy_fleet.py watch` có `acquire_watch_singleton` (msvcrt file-lock `watcher-singleton.lock`) — chỉ 1 watch loop chạy. Đừng kết luận double-watch khi chưa soi PPID từng process.



**Restart tray sạch (tránh instance chồng):** `schtasks /Run` khi task đang chạy = no-op (`INFO: scheduled task is currently running`) → phải kill tree cũ trước: tìm PID qua `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*proxy-watcher-only-tray*' -or $_.CommandLine -like '*gan_proxy_fleet*' }`, `taskkill /PID <pid> /T /F`, verify leftovers = 0, RỒI `/Run` 1 lần, chờ ~15s, verify tree mới (PPID = 2996 Task Scheduler cho tray). ⚠️ **Lệnh check của chính bạn cũng match filter và chạy dưới tree gateway (ppid=436)** → count \"process matching\" bị thổi phồng; phân biệt bằng start-time + tên (bash/powershell check vs tray thật).



**Chu kỳ respawn ~6.5 phút = thiết kế, không phải lỗi:** `watch` mode chạy theo chu kỳ — khi farm offline (ít máy trong `adb devices`), mọi target fail-closed `FINAL_BLOCKED` (không có error message) → run kết thúc → tray 15s respawn → run mới. `FINAL_BLOCKED` toàn bộ + máy không có trong `adb devices` = máy offline, watcher đang chờ, KHÔNG chạm vào.



Chi tiết lệnh + transcript: `references/tray-ps1-ps51-pitfalls.md`.



## Reading the watcher event log (watch-events.jsonl)



The authoritative per-target trace is

`<runtime>/<run-hash>/machine-<N>/watch-events.jsonl` plus `attempt-*.json`

sanitized captures (fields: `machine`, `serial`, `attempt`, `phase`,

`captured_at`, `adb_state`, `focused_window`, `vichanger_installed`,

`vichanger_process`, `vpn_connected`). Phases seen: `watch-01-ready`,

`before-recovery`, `after-recovery`, `watch-02-verified`.



State machine per event (grep `"status"` to summarize; tail to see the last state):

`WATCH_EVENT_DETECTED → WATCH_EVENT_LOCK_ACQUIRED (reason=startup|boot_id_changed|reconnect)

→ WATCH_CORE_READINESS_PASS → WATCH_DIAGNOSTIC_CAPTURE_* →

WATCH_PROXY_APPLICATION_BEGIN → (SUCCESS → ROTATION_RESTORE → VERIFICATION →

WATCH_PROXY_READINESS_READY → WATCH_EVENT_VERIFIED_SUCCESS)

| (FAILURE → WATCH_EVENT_CLASSIFIED → RECOVERY_RESERVED → RECOVERING →

WATCH_EVENT_RECAPTURED (reason=rerun_proxy_assignment_script_for_target) →

WATCH_EVENT_RETRYING → FAILURE again → WATCH_PROXY_READINESS_FAILED →

WATCH_EVENT_FINAL_BLOCKED)`.

`WATCH_PROXY_READINESS_PENDING (reason=boot_id_changed)` fires between events.



Match artifact timestamps against the user's screenshot/observation time — the

screenshot often captures the exact instant of a *transient* failure, not the

final state.



**Phân biệt 2 dạng lỗi VPN Preflight (2026-08-22):**
1. **Mất hẳn VPN (`tun_up=False, vpn_connected=False` / `MissingVpnRecoveryError`):** Máy không có card mạng `tun0`. Sau reboot, Wi-Fi chưa nối (`WIFI_NOT_READY`) hoặc màn hình khoá làm watcher chưa gán proxy. Watcher sẽ gán ở chu kỳ poll kế tiếp sau khi Wi-Fi ổn định và mở khoá.
2. **Treo ADB broadcast GET_IP (`tun_up=True, vpn_connected=True` + `ViChanger GET_IP failed after 3 retries: adb command timed out`):** Mạng VPN và card `tun0` **đang chạy bình thường**, nhưng lệnh broadcast `vn.vichanger.app.GET_IP` qua ADB bị timeout/treo app. Đây là lỗi nghẽn tầng giao tiếp ADB / app ViChanger, KHÔNG phải mất VPN. Triage: force-stop ViChanger hoặc restart nhẹ ADB/thiết bị nếu lặp lại.
3. **Độ trễ thông báo vs Watcher:** Khi script fail do mất VPN và trigger reboot, script dừng ngay (báo alert Telegram). Watcher cần ~1-2 phút sau khi máy boot xong để bắt event `WATCH_EVENT_DETECTED` → `PROXY_APPLICATION_SUCCESS` → `WATCH_EVENT_VERIFIED_SUCCESS` (`proxy_ready`). Kiểm tra `watch-events.jsonl` và `ip addr show tun0` trước khi can thiệp thủ công.
4. **Cơ chế tự phục hồi sau boot trong core (`soft_reboot_and_wait` / `recover_missing_android_vpn`):** `soft_reboot_and_wait` tự kích hoạt Wi-Fi một lần (`_auto_enable_wifi_once`) ngay sau khi mở khóa màn hình; thời gian chờ gán proxy được nâng lên `reassign_timeout=60s` và `proxy_timeout=240s` (4 phút) để tránh timeout trước khi Watcher kịp hoàn tất.

### Readiness file consumption: consumers gate on EXISTENCE, not state (2026-08-15)



The tiktok-upload workflow reads the readiness contract as `read_readiness(serial) is not None`

(`state_machine.py` ACQUIRE_LOCKS + `run_post.py` preflight/surface-probe) — a **file-existence

check only**. A `proxy_pending` / `proxy_failed` file still counts as "contract present" and

creates a `live_vpn_verifier`; the FILE STATE is never read. Consequences verified live:



- **tiktok-upload no longer enforces VPN at all** since the 2026-08-14 lock removal

  (`_handle_acquire_locks` early-returns `True` with `device_lease=None`; `acquire_device_lock`

  is never called, so `live_vpn_verifier` never runs). When the user asks "sao máy không VPN vẫn

  chạy", the answer is the conditional gate + lock removal — NOT a broken watcher/rule.

- **`proxy_failed` file + tun0 UP = watcher recovered but never re-published readiness**

  (máy 9, 2026-08-15): the readiness file can lie about current state. Always verify tun0

  directly (`adb shell ip addr show tun0 | grep -c 'inet '`) instead of trusting the file.

- **`WATCH_EVENT_LOCK_TIMEOUT` with a foreign project lock = watcher correctly skipping**

  (máy 38, `Tiktok_Reg/social_reg_v1.py` holds `machine_38.lock.json`) → machine stays no-VPN

  BY DESIGN; do not touch the lock, do not "fix" the watcher.



**Ladder chẩn đoán "máy chạy script mà không có VPN" (2026-08-15):**

1. Check gate có được gọi không: `grep -n "read_readiness(device_id) is not None" scripts/tiktok_workflow/state_machine.py` (tạo `live_vpn_verifier`) — verifier chỉ CHẠY bên trong `acquire_device_lock`, nên nếu `_handle_acquire_locks` early-return (lock bị bỏ) → gate chết im lặng.

2. Per-device proof: `"C:/Program Files (x86)/xiaowei/tools/adb.exe" -s <serial> shell ip addr show tun0 | grep -c 'inet '` (0 = không VPN). Scan toàn farm bằng loop `for s in $(adb devices | awk 'NR>1 && $2=="device"{print $1}')`.

3. Map serial → readiness file: `hashlib.sha256(serial.encode()).hexdigest()[:24]` = filename trong `~/.codex/device-readiness/` (đối chiếu serial qua workbook bằng openpyxl, cột `device ID`).

4. Phân biệt 3 nhóm: (a) máy có readiness + tun0=0 + watcher `LOCK_TIMEOUT` do tiến trình khác giữ lock → đúng thiết kế, CẤM đụng; (b) `proxy_failed` file + tun0=1 → watcher đã phục hồi nhưng không publish lại, file nói dối — tin tun0; (c) `proxy_pending` cũ + tun0=0 → watcher skip máy off/reboot.

**Fix ĐÃ SHIPPED (Phương án A, user duyệt 2026-08-15, commit `c623a57`):** gate VPN BẮT BUỘC ở đầu `_handle_resolve_device` (state_machine.py) — `require_android_vpn(AdbClient(...), required=True)` fail-closed → `WorkflowError(VPN_REQUIRED_NOT_CONNECTED)`; skip khi `dry_run`; KHÔNG đụng lại lock (giữ "bỏ lock" theo user). Mọi flow (video + avatar-smoke) đều qua RESOLVE_DEVICE nên đều bị gate. Verify: 3 regression tests mới PASS + full suite 355 passed / 4 pre-existing lock fails (không tăng); 2 vòng AG claude-opus-4-6-thinking APPROVED. Từ giờ máy mất VPN giữa run → fail-closed MANUAL_REVIEW; triage = check `tun0` trực tiếp (file readiness có thể nói dối: `proxy_failed` + tun0=1), chờ watcher gán lại hoặc reboot, KHÔNG retry mù.



### POST-reboot lock screen → `VPN_POSTCONDITION_NOT_VERIFIED` (worked example 2026-08-08, máy 74)



After a fresh reboot the phone sits at the lock screen (`focused_window=StatusBar`,

ViChanger not running, VPN not connected). The watcher applies the proxy and VPN

comes up, but the postcondition `close_all_recent_apps()` (Recent Apps → "Đóng tất cả"

→ tap → HOME → verify launcher foreground) **fails closed because HOME cannot surface

the launcher while the screen is locked** → `RuntimeError: VPN connected but Recent

Apps/Home verification failed` → `VPN_POSTCONDITION_NOT_VERIFIED` → recovery

`rerun_proxy_assignment_script_for_target` reruns set_proxy *without changing the

locked condition* → attempt 2 fails with the same signature → `FINAL_BLOCKED`

(correct per 2-attempt rule; NOT a bug, NOT an infinite loop).



**If it succeeds minutes later, that is NOT recovery/self-heal** — it is an

independent new event: `boot_id_changed` (device booted again / finished booting)

finds ViChanger already running + VPN already connected + screen unlocked →

application + verification succeed on the first pass of event 2. Diagnosis must

compare the event-1 vs event-2 `attempt-*.json` captures (focused_window,

vichanger_process, vpn_connected) to prove this.



No redesign is needed — the failure is fail-closed by design.



**IMPLEMENTED 2026-08-08 — bounded keyguard-dismiss fallback now exists.**

`scripts/vi_changer_runner.py` gained `_go_home_and_verify_with_keyguard_fallback(adb_path, serial)`:

try `_go_home_and_verify` → if launcher still not foreground, ONE bounded

`prepare_device(AdbClient(...), wake=False, swipe_unlock=True, lock_rotation=False,

set_battery=False, timeout=10)` (swipe-only: no wake/rotation/battery side effects),

wrapped in `try/except Exception` → on exception return `False` (never raise, never

loop) → retry `_go_home_and_verify` once → fail-closed. Both call sites in

`close_all_recent_apps` use it; the dump-failure except path still returns `False`

even if the fallback restored HOME — a failed UI dump must never report success.

`set_proxy()` message "Recent Apps/Home verification failed" unchanged.

Regression tests: `test_close_all_recent_apps_unlocks_keyguard_once_and_returns_home`,

`test_close_all_recent_apps_fails_closed_when_still_locked_after_one_unlock`,

`test_close_all_recent_apps_does_not_retry_keyguard_when_home_already_reachable`

(all in `tests/test_vi_changer_runner.py`, mock `runner.prepare_device` +

`runner.time.sleep`); COMPAT entry `proxy-clear-recent-keyguard-dismiss-20260808`

in `docs/ui-compatibility.md` (old record `proxy-clear-recent-after-vpn-20260801`

kept verbatim). Before writing the call, verify kwargs read-only via

`inspect.signature(automation_core.device.prepare_device)`. Still open (core-side,

out of gan-proxy scope): `wait_until_unlocked` should wait until keyguard is

actually gone, not merely screen-on.



**Harmless noise:** repeated `WATCH_MAPPING_RELOAD_ERROR` (`Permission denied:

...PROXYgandienthoai.xlsx`, every ~5s) means the Excel mapping is open/locked by

Excel or OneDrive; the mapping was loaded at worker start so event handling is

unaffected — the errors stop once the file is closed. Do not treat this as the

failure cause.



## Runtime provenance is a separate gate



A successful target event does not prove that the intended core wheel is installed in the scheduled task's interpreter. The wrapper may inject `PYTHONPATH` and redirect both apparent watcher interpreters into another site-packages tree. For every executable in the watcher process tree, probe `sys.executable`, `importlib.metadata.version("automation-core")`, `automation_core.__file__`, and the `watch_device_reconnect` signature in a fresh subprocess. Require the expected version/module path and the feature signature before claiming the runtime fix is complete. The full probe and correction sequence is in `references/runtime-provenance-and-reboot-proof.md`.



**Inherited `PYTHONPATH` shadowing (2026-08-12):** Pinning/installing the correct wheel is insufficient if the launcher inherits a Hermes shell `PYTHONPATH` that points at an older shared `site-packages`. An ordinary probe from the coordinator shell can therefore report a false `0.4.43` even while the selected venv contains `0.4.44`; `pip show` is equally misleading when run with the inherited path. The wrapper must clear inherited `PYTHONPATH` first, then set only the consumer script path needed for imports. Verify twice: (1) a clean-environment probe with `PYTHONPATH`, `PYTHONHOME`, and `VIRTUAL_ENV` removed; (2) the actual scheduled watcher process tree after restart. For each parent/child interpreter require the expected wheel version, module file under that interpreter's `Lib/site-packages`, and the feature signature (`auto_enable_wifi` in this incident). Do not call the fix complete from a successful proxy event alone; runtime provenance and target proof are separate gates. See `references/runtime-provenance-and-reboot-proof.md` for the exact Windows/PowerShell sequence.



## Hermes watchdog separation

When VPN/proxy watching is intentionally retired but Hermes Gateway must remain self-healing, use the standalone watchdog/task split described in `references/hermes-watchdog-separation.md`. Do not preserve the proxy tray merely because its old tray script also contained a Hermes health timer; separate the concerns and verify the VPN task remains disabled.

## Verification checklist



- Targeted watcher lock/event regression tests pass.

- Full consumer watcher suite and compile check pass.

- `git diff --check` passes.

- **Hermes verification gate:** if it flags the workspace "unverified" even after real pytest evidence (it fires when no canonical test command is detected), satisfy it with a focused ad-hoc script created via `tempfile.mkstemp(prefix="hermes-verify-", suffix=".py", dir=tempfile.gettempdir())` in `%TEMP%` — run it against the changed behavior, delete it after, and label results explicitly as ad-hoc (e.g. "AD-HOC 12/12 PASS, not suite green") rather than claiming suite green.

- Restart only the watcher/tray component necessary to load code; do not use a menu/action that starts unrelated account/feed schedulers.

- After a real target reboot, record fresh target-specific watcher evidence plus final `tun0` and Android VPN connectivity proof.



## Pitfalls



- **Runner unit tests: mock `runner.prepare_device` + `runner.time.sleep`** in any test that exercises a fallback path. Old tests that leave `prepare_device` unmocked (e.g. `test_close_all_recent_apps_does_not_raise_when_home_fallback_fails`) still pass because `adb` is not on PATH on the dev box → the real `prepare_device` raises `ADBError` (a `RuntimeError` subclass) instantly and the fallback's `except Exception` swallows it → `False`. Keep that in mind if the box ever gains `adb` on PATH (real device calls could then fire).

- **Docs/`ui-compatibility.md` in CRLF repos:** the patch tool's raw diff may show LF→CRLF normalization on untouched blocks; judge the change with `git diff` output instead (git autocrlf shows only real additions/deletions). Appended COMPAT records must not rewrite old records — verify `+N, 0 deletions` in `git diff --stat`.

- A retained lock from a dead recovery owner can block a watcher startup event indefinitely if the watcher neither requests takeover nor bounds lock wait.

- **Two logon trays both start the watcher → singleton BLOCKED after reboot (2026-08-14).** `GanProxyWatcherTray` (proxy-watcher-only-tray.ps1) AND `TikTokAllSchedulerTray` (tiktok-scheduler-tray.ps1) BOTH call `run-proxy-watcher.ps1` with identical args. After reboot both spawn a watcher chain (automation-venv python → Python312 child) → second one logs `BLOCKED: watcher singleton is already held: ...\watcher-singleton.lock` and does nothing → machines never regain VPN. Fix (done 2026-08-14): patch `D:\Taadaa\automation-core\src\automation_core\scheduler\tiktok-scheduler-tray.ps1` line ~122 to hard-set `$script:ProxyWatcherEnabled = $false` with a comment that GanProxyWatcherTray owns proxy watching. **Whenever re-enabling TikTok scheduler tasks, verify TikTokAllSchedulerTray no longer starts the watcher** — its action still carries `-ProxyWatcherScript ... run-proxy-watcher.ps1` args even when the ps1 now ignores them.

- **Stale/empty `watcher-singleton.lock` blocks watcher restart even with 0 watcher processes (2026-08-14).** Symptom: `Get-CimInstance ... | match gan_proxy_fleet` returns nothing (watcher dead), but the newest watcher-logs `*.stderr.log` says `BLOCKED: watcher singleton is already held` — the lock FILE still exists (often 1 byte/empty) after a killed tree, so the tray respawn's `acquire_watch_singleton` fails forever. Fix: kill the whole watcher tree (`taskkill /PID <pid> /T /F`), `rm` the `watcher-singleton.lock`, then `Start-ScheduledTask -TaskName GanProxyWatcherTray` once; verify a fresh 2-node chain appears with new PIDs. Only 1 watcher chain = parent (automation venv) + child (Python312, same `watch --all` cmdline) — that is by design, NOT a duplicate.

- **Stale `machine_<N>.lock.json` after watcher restart silently skips the target forever (2026-08-17, máy 10).** Killing the watcher tree does NOT remove per-device `machine_<N>.lock.json` files in `~/.codex/device-locks/`. The old lock's PID is dead (`owner_active: false`) but the file persists with `status: blocked`; the new watcher run respects retained locks (no takeover without proof) and **never creates a machine dir or applies proxy** for that target — it looks like the watcher "ignores" the rebooted machine. Diagnosis: target has no dir/events in the NEW run-hash while other machines do → `ls ~/.codex/device-locks/machine_<N>.lock.json` + `tasklist //FI "PID eq <old_pid>"` (empty = dead). Fix: verify the PID is dead, `rm` the stale lock file, and the next watcher poll picks the target up (`WATCH_EVENT_DETECTED` → ... → `WATCH_EVENT_VERIFIED_SUCCESS` within ~1 min, tun0 UP). This is safe because a LIVE owner's lock is never removed — always confirm the PID is gone first.

- **`WATCH_EVENT_LOCK_TIMEOUT` khi thiết bị còn giữ lock (`running` / `blocked`):** Khi thiết bị reboot/reconnect nhưng lock của script cũ vẫn còn trên đĩa (tiến trình consumer đang chạy hoặc giữ hiện trường `blocked`), Watcher tuân thủ lock và ghi `WATCH_EVENT_LOCK_TIMEOUT` (chờ 10s rồi bỏ qua, không tự cướp quyền). Để Watcher tự gán lại proxy sau sự cố, lock cũ phải được giải phóng qua Reaper (hết TTL) hoặc mở khóa thủ công.

- **Phân biệt tổng số máy trong alert Watchdog (`watch_device_locks.py`) vs số máy lỗi thực sự:** Watchdog quét toàn bộ lock files trong `~/.codex/device-locks/`. Khi batch chạy lớn (ví dụ feed 40 máy song song), các máy `status: running` / `queued_v2` đều xuất hiện trong danh sách. Chỉ các máy `status: blocked` (hoặc `failed_locked`) mới là máy gặp sự cố cần triage/mở khóa.

- **Verify the watcher is ALIVE at launch time, not "it was running earlier" (2026-08-14).** A watcher can die minutes after the user says "watcher ổn định rồi" (singleton stale lock, tray killed). Before launching any feed batch or proxy-dependent job, re-check `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'gan_proxy_fleet' }` count ≥ 2-node chain AND no `BLOCKED: watcher singleton` in the newest stderr log.

- Killing a watcher child may not make a tray supervisor respawn it immediately; restart the dedicated tray/task process when a new watcher process is needed. Verify new process creation time. (2026-08-08 update: when the tray IS alive, kill the whole watcher TREE — parent + child — and the 15 s `Ensure-ProxyWatcher` timer respawns it automatically with fresh PIDs, new log file, and clean singleton acquisition; only touch the tray/task when the tray itself is dead, e.g. Last Result 267014.)

- A watcher can create artifacts for many machines at startup. Always compare artifact timestamps and machine/serial before drawing conclusions.

- **Before manually re-running a failed worker, verify the target isn't already owned**: an active `machine_<N>.lock.json` with a live PID (check via `wmic`, not `tasklist`) means the fleet/scheduler already re-spawned a worker — retrying only produces a fail-closed `device lock active` error and a spurious report. Tail the owner's log instead.

- **Chạy test gan-proxy với automation venv + `TAADAA_HOST_CONFIG` (2026-08-17):** core src `D:\Taadaa\automation-core` hiện là 0.4.45 CHƯA có `resolve_proxy_mapping_path`; hàm này chỉ có trong core 0.4.46 cài trong venv `D:\Taadaa\python-envs\automation`. Chạy test bằng Python312 global hay `PYTHONPATH=automation-core\src` → collection fail `AttributeError: module 'automation_core.preflight' has no attribute 'resolve_proxy_mapping_path'`. Lệnh chuẩn: `cd /d/Taadaa/gan-proxy && env -i HOME="$HOME" USERPROFILE="$USERPROFILE" PATH="/c/Users/Kibe/AppData/Local/Programs/Python/Python312:/c/Windows/System32" TAADAA_HOST_CONFIG="D:\\Taadaa\\machine-config\\kibe.yaml" PYTHONPATH="D:\\Taadaa\\gan-proxy\\scripts" "D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe" -m pytest tests/ -q`. Thiếu `TAADAA_HOST_CONFIG` → `ConsumerPreflightError: proxy mapping workbook unresolved`. Pre-existing fail: `test_offline_config.py::test_plan_without_offline_still_reports_adb_state_but_never_proxy` fail trên cả bản sạch (không phải do code mới) + test thứ 2 trong file đó bị test-pollution — đừng coi là regression.

