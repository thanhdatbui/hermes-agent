# Core Device Readiness: USB popup, Wi-Fi gate, clean env (2026-08)

Session evidence: máy 74 (SM-G930F farm) — wifi drop + Samsung USB popup chặn
avatar/upload flow. Root causes + fixes shipped to `automation-core`.

## 1. Samsung USB popup `MtpApplication/USBConnection`

- Xuất hiện bất kỳ lúc nào sau PC sleep/bật lại (cắm USB → dialog chọn MTP).
- **Chặn cả uiautomator dump** (`uiautomator dump` fail) — nhưng `dumpsys
  activity activities` vẫn đọc được. Detect phải qua ActivityManager.
- Popup này KHÁC `com.android.systemui.usb.UsbDebuggingActivity` (Allow USB
  debugging) — module `usb_debugging.py` cũ không match.
- Fix (core 0.4.22, commit `1933c24`): `automation_core/usb_popup.py`
  - `usb_popup_activity_present(adb)`: scan active/resumed/focused fields của
    `dumpsys activity activities`, marker `mtpapplication/usbconnection`.
  - `dismiss_usb_popup_shell(adb)`: dùng shell thuần — tap `button_cancel`
    bounds (evidence máy 74: center 270,81) qua `input tap`, fallback
    `input keyevent 4`; **verify bằng ActivityManager probe lại** sau mỗi
    action (KHÔNG dùng uiautomator — chính popup chặn nó → recapture
    `unavailable` = false-negative).
  - `prepare_device()` gọi dismiss sau swipe_unlock → mọi consumer tự bỏ qua
    popup ("kệ mẹ nó" pattern). `DeviceReadiness.usb_popup_dismissed` optional.
- Consumer cũ import `dismiss_usb_popup` ở 4 chỗ (profile-root, switcher,
  avatar) — giờ dư vì `prepare_device` đã lo, nhưng harmless.

## 2. Wi-Fi gate sau reboot (WIFI_NOT_READY)

- Máy 74: wifi văng tự nhiên (wlan0 DORMANT/NO-CARRIER, no IP, ping
  unreachable); `adb reboot` KHÔNG tự lên wifi — phải toggle tay.
- `watch_device_reconnect` cũ gán proxy ngay khi unlock → VPN tun0 có nhưng
  không internet.
- Fix (core 0.4.23, commit `c58f87a`): `automation_core/device_recovery.py`
  - `wait_for_wifi(adb, timeout=120, poll_interval=5, stop_event=None)`:
    quan sát `ip addr show wlan0` — `"inet "` + (`state up` HOẶC `state
    unknown`; ROM khác nhau), fallback `ping -c 1 -W 3 8.8.8.8`. KHÔNG mutate
    device.
  - `watch_device_reconnect` thêm `wifi_timeout: float = 120` (0 = tắt gate);
    wifi chưa lên → **không gọi on_ready**, log `[WIFI_NOT_READY]` 1
    lần/reconnect (cờ `pending_notified`), loop tiếp tục.
  - `pending_reason` giữ reason ổn định qua gate (boot_id_changed không hạ
    thành reconnect); `wifi_poll_interval`/`wifi_probe_timeout` tham số hóa.
- Consumer gan-proxy không cần sửa — tự phủ qua `watch_device_reconnect`.

## 3. Chạy automation venv sạch (Windows, tránh hermes venv lẫn)

Python automation (`D:\Taadaa\python-envs\automation`) bị hermes venv chèn
vào sys.path → numpy/PIL/automation_core import sai bản. Pattern chuẩn:

```bash
env -i PATH="/c/Windows/system32:/c/Windows:/d/Taadaa/python-envs/automation/Scripts:/c/Users/Kibe/AppData/Local/Programs/Python/Python312" \
  HOME="C:\\Users\\Kibe" USERPROFILE="C:\\Users\\Kibe" \
  PYTHONPATH="D:\\Taadaa\\automation-core\\src;D:\\Taadaa\\Tiktok-video\\scripts" \
  /d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest tests/ -q
```

- `env -i` thiếu HOME/USERPROFILE → `RuntimeError: Could not determine home
  directory`. Luôn set cả 2.
- PYTHONPATH trỏ `automation-core\src` để test chạy bản source chưa commit
  (site-packages có thể là wheel cũ).
- Cài wheel mới: `pip install --force-reinstall <wheel>`; dist-info mới nhưng
  file thiếu = bản cài dở dang → `--force-reinstall`.

## 4. PS 5.1 pitfall: `[Convert]::ToHexString` không tồn tại

`[Convert]::ToHexString` cần .NET 5+/PowerShell 7. Trên Windows PowerShell
5.1 → `MethodInvocationException`, script fail-closed exit 21 oan. Fix:
```powershell
$hexBytes = $sha256.ComputeHash($identityBytes)
if ('ToHexString' -in [System.Convert].GetMethods().Name) {
    $accountContextId = [Convert]::ToHexString($hexBytes).ToLowerInvariant()
} else {
    $accountContextId = [BitConverter]::ToString($hexBytes).Replace('-', '').ToLowerInvariant()
}
```
