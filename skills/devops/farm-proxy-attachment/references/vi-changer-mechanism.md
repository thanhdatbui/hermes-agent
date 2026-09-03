# ViChanger proxy mechanism — condensed reference

Source repo: `D:\Taadaa\gan-proxy` (canonical). Recovery worktrees under `D:\CodexRuntime\gan-proxy-*`.

## Package & broadcast API
- Package: `vn.vichanger.app`
- Receiver: `vn.vichanger.app/.AdbCaller`
- Actions: `vn.vichanger.app.GET_IP`, `GET_MODEL`, `START_VPN`, `STOP_VPN`
- `GET_IP` / `GET_MODEL` are read-only; used by `probe` to report status + current external IP.

## `scripts/vi_changer_runner.py` (file:line)
- `PACKAGE = "vn.vichanger.app"` (line 25); action constants (26-29).
- `set_proxy(adb_path, serial, proxy, timeout=30)` (208-230):
  - `colon_count == 1` → `adb shell settings put global http_proxy <proxy>` then read back; raise if mismatch (212-216). **Bypassable by TikTok.**
  - else → `pm path` check installed, `monkey -p` launch, broadcast `START_VPN -e proxy <proxy>`, loop up to `timeout` checking `vpn_connected()` (218-230).
- `vpn_connected(adb_path, serial)` (109-114): true only if `ip addr show tun0` has `UP|LOWER_UP` AND `dumpsys connectivity` has `NetworkAgentInfo.*[VPN.*CONNECTED/CONNECTED`. (Replaced an earlier false-positive verifier that matched Wi-Fi `CONNECTED`.)
- `remove_proxy` (233-241): `settings put global http_proxy :0`, `delete global http_proxy`, `delete global_http_proxy_host`, `delete global_http_proxy_port`, then `ACTION_STOP`.
- Postcondition: after `set`/`remove`, writes `settings put system accelerometer_rotation 0` (portrait, auto-rotate off) (278).
- `close_all_recent_apps` (182-205): opens Recent Apps (keyevent 187), taps semantic clear-all from UI dump, sends HOME, verifies launcher foreground. Only called AFTER VPN verified.

## `scripts/gan_proxy_fleet.py`
- Imports `set_proxy`, `vpn_connected`, `DeviceLock`, `PACKAGE` from `vi_changer_runner` (line 30).
- `Target.proxy_kind` (63): `"authenticated_http" if self.proxy.count(":") >= 3 else "http"`.
- Mapping source: Excel `D:\OneDrive\codex_gmail_debug\PROXYgandienthoai.xlsx`; reads machine/device/proxy; requires all three populated (138-141, 197).
- `watch` owns post-reboot proxy assignment; publishes `proxy_pending` → `proxy_ready` (after apply + rotation restore + verification) or `proxy_failed`.

## Evidence the app is real (not a placebo)
- `CHANGELOG.md:14`: "Recovered GemPhoneFarm 3.0.9's exact local proxy implementation from the installed application" — replaced unverified `CHANGE` path with working `START_VPN`/global-setting behavior.
- `tasks/2026-07-16-standalone-vi-changer-machine-1.md`:
  - (18) Vi Changer UI first reported missing **LSPosed** access then requested an **API key**.
  - (25) Working path does NOT use the API-key UI or `CHANGE` action.
  - (27-31) After `set`: `tun0` UP, VPN connected, "VPN Connected" notification, `GET_IP` changed, auto-rotate `0`. Relaunch via `monkey` after manual close also succeeded.
- `HANDOFF.md:114`: package installed, advertises `GET_IP`/`GET_MODEL`/`START_VPN`/`STOP_VPN`.

## How to verify on a live device (read-only)
1. `python scripts/vi_changer_runner.py probe` → note `get_ip_broadcast`.
2. `set` with authenticated proxy → `probe` again → `GET_IP` must differ (proxy IP).
3. `adb shell dumpsys package vn.vichanger.app | grep -i installer` → `com.android.vending` = Play Store install; `null` = sideloaded (trust caveat).

## Plain-vs-auth rule of thumb
- `user:pass@host:port` (≥2 colons) → ViChanger VPN tunnel (safe).
- `host:port` (1 colon) → `adb settings http_proxy` (TikTok can bypass → unsafe for farm).
- Fix: ensure Excel mapping uses authenticated form.
