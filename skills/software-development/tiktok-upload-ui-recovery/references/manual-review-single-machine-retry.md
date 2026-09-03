# MANUAL_REVIEW single-machine retry ladder (tiktok_workflow upload worker)

Runbook hoàn chỉnh khi 1 background `tiktok_workflow` worker exit ≠ 0 / MANUAL_REVIEW.
Verify 2026-08-08 trên coord `manual-coord-52-65-69` (máy 65 `ce12160c4a45432204`, máy 69 `ce12160c386c913101`; máy 52 cùng run DONE bình thường).

## Timeline thực (máy 65) — pattern điển hình

```
17:45  worker trước đó screencap thấy TikTok feed BÌNH THƯỜNG (app + network OK)
17:48  worker relaunch: force-stop + relaunch TikTok → WAIT_FEED 90s
17:50  UI dump fail (uiautomator_idle_state_error) + visual gate dark=1.000
17:50  "Soft reboot recovery disabled by config for OPEN_TIKTOK" x3 → MANUAL_REVIEW, giữ lease
17:52  screencap: về launcher (app tự thoát sau kẹt splash) — dumpsys trước đó vẫn SplashActivity
```
SN quyết định: **UI-dump stall là transient toàn-farm** (75 máy ADB cùng 1 host); soft-reboot bị tắt bởi config
cho state OPEN_TIKTOK — đó là fail-closed ĐÚNG THIẾT KẾ, không phải lỗi cần patch skill/code.
COMPAT-UI-DUMP-002 (docs/tiktok-ui-mpatibility.md:981) chỉ có nhánh soft-reboot ở `DISMISS_POPUPS`.

## Ladder (thứ tự bắt buộc)

### 1. Đọc log worker
```bash
tail -40 /d/CodexRuntime/tiktok-video/manual-coord-*/worker-<N>.log
```
Xác định signature: `UI_DUMP_FAILED` / `uiautomator_idle_state_error` / `non_xml_ui_dump` / `PROXY_*` / lock.

### 2. Probe device (read-only — an toàn chạy ngay, đúng quy tắc "giữ màn hình lỗi + dumpsys trước retry")
```bash
ADB="/c/Program Files (x86)/xiaowei/tools/adb.exe"; S=<serial>
"$ADB" devices | grep "$S"
"$ADB" -s $S shell dumpsys activity activities | grep -iE "mResumedActivity|mFocusedApp"
"$ADB" -s $S shell dumpsys power    | grep -iE "mWakefulness"
"$ADB" -s $S shell "timeout 15 uiautomator dump /sdcard/wd.xml >/dev/null 2>&1 && echo DUMP_OK || echo DUMP_FAIL"
```
`DUMP_OK` sau 1-3 phút cooldown = uiautomator tự hết treo → retry hợp lệ.

### 3. Screencap thật + cross-check (dumpsys có thể lệch thời điểm)
```bash
"$ADB" -s $S exec-out screencap -p > "/c/Users/Kibe/AppData/Local/Temp/m<N>.png"   # KHÔNG dùng /tmp (vision_analyze không resolve)
```
vision_analyze path Windows thật. Nếu thấy launcher trong khi Tiktok cần cho flow → app đã tự thoát; retry sẽ relaunch lại.

### 4. Proxy/VPN gate (verify 4 lớp — skill android-proxy-Watcher)
```bash
"$ADB" -s $S shell "pidof vn.vichanger.app; ip addr show tun0 2>/dev/null | grep -c 'inet '"
H=$(python -c "import hashlib;print(hashlib.sha256('$S'.encode()).hexdigest()[:24])")
cat "$HOME/.codex/device-readiness/$H.json"     # phải "proxy_ready"
# watcher event cuối (runtime gan-proxy):
RT=/d/CodexRuntime/codex_gmail_debug-gan-proxy; D=$(ls -dt $RT/*/ | head -1)
tail -3 "$D/machine-<N>/watch-events.jsonl" | grep -o '"status":"[^"]*"' | tail -1   # phải WATCH_EVENT_VERIFIED_SUCCESS
```

### 5. Không ai khác giữ máy (bắt buộc — nếu scheduler đã tự spawn, KHÔNG retry, xem §8b)
```bash
wmic process where "Name='python.exe'" get ProcessId,CommandLine | grep -iE "tiktok_workflow|machine <N>"
find /d/CodexRuntime/tiktok-video ~/.codex -maxdepth 4 \( -name "machine_<N>*" -o -name "serial_<S>*" -o -name "*<N>*.lock*" \)
```

### 6. Retry — đúng lệnh coordinator (cơ lock timeout trong config, không cần manifest)
```bash
cd /d/CodexRuntime/tiktok-video && echo "YES" | PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
  /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -m tiktok_workflow \
  --config "D:\CodexRuntime\tiktok-video\config-machine-<N>.yaml" --machine <N> --no-dry-run \
  > /d/CodexRuntime/tiktok-video/manual-coord-<...>/worker-<N>-retry.log 2>&1
```
Background + notify_on_complete. Sau khi xong: đọc `runs/run_<serial>_<ts>/report.json` — kiểm tra
`post_submission_state` (xem SKILL §7: ACCEPTED = đã đăng, KHÔNG retry; None = retry hợp lệ).

## Cảnh báo
- Đừng retry khi `wmic` còn worker `tiktok_workflow` → sẽ tạo thêm report fail phụ (fail-closed lock active).
- Đừng vội reboot khi dump chỉ treo tạm — đợi cooldown, probe lại: reboot mất VPN + lock + thời gian.
- Máy 69 fail sớm hơn (CONNECT_DEVICE `close_all_apps_start failed`) cùng signature class — vẫn xử lý ladder như trên.