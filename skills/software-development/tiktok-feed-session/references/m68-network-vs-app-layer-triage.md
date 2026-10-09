# M68 network-alert triage — proxy farm: phân biệt rớt mạng thật vs kẹt app-layer (2026-09-04)

Case: [MÁY 68] `Đã xảy ra lỗi / Thử lại`, serial ce12160cdb77582b05, nick thanhphuc45826.
Kết luận: hạ tầng sống, app kẹt ở SplashActivity — KHÔNG phải rớt WiFi/proxy.

## Checklist thay cho "ping 8.8.8.8 fail = mạng rớt"
1. `dumpsys connectivity` → tìm WIFI network active có `VALIDATED` + `SignalStrength` (M68: network{538} wlan0 192.168.10.78, RSSI -57).
2. `ping -c 2 192.168.10.254` (gateway) phải 0% loss (M68: 4-7ms) → WiFi/L2 sống.
3. `settings get global http_proxy` → proxy per-device (M68: 192.168.110.2:20068).
4. Từ PC: `Test-NetConnection 192.168.110.2:20068` + `curl -x http://<proxy> -I --max-time 15 http://connectivitycheck.gstatic.com/generate_204` → 204 = proxy sống (M68: 204 OK).
5. `ping -c 1 8.8.8.8` trên máy FAIL 100% là BÌNH THƯỜNG khi farm đi qua proxy HTTP — ICMP không qua proxy, không được dùng để kết luận TikTok mất mạng.
6. `dumpsys activity activities | grep -i -m 10 "mResumedActivity|Splash|MainActivity"` → M68 kẹt `SplashActivity`, chưa vào `MainActivity`; `uiautomator dump` bị `Killed` = máy chậm/treo lúc splash.
7. `screencap` + `dumpsys window windows | grep mCurrentFocus` để xác nhận overlay "Đã xảy ra lỗi / Thử lại" vs splash chậm trước khi kết luận.

## Code map (repo `tiktok-luot nuoi acc`)
- `python_runner/core/safety.py`: `NETWORK_SCREENS = {"network-error","retry"}` → `SAFETY_MANUAL_NEEDED` ("network/error/retry marker detected").
- `python_runner/flows/feed_swipe_smoke.py:3735-3771`: nhánh network chỉ recheck sau `NETWORK_RETRY_DELAY_SECONDS=2.0`, rồi gọi `_network_force_stop_recovery()` (line ~2145) — nhưng hàm này return None ngay khi `safety.allow_network_force_stop_recovery == False`. Nên "swipe 2 lần vẫn stuck" là behavior đúng, không phải bug swipe.
- Muốn auto-vượt overlay network phải mở flag / mở rộng recovery, không phải tăng số swipe.

## Pitfalls đã gặp
- `python D:/Taadaa/tools/inspect_machine.py <N>` hiện chỉ là stub in `adb devices` — không đủ hiện trường. Phải bổ sung ADB trực tiếp (connectivity, wifi, proxy, activity, screencap).
- `.ai-runs/latest/` không tồn tại; run mới nhất nằm ở dir timestamp (`ls -td .ai-runs/*/`). M68 artifact gần nhất (20260903-195710) chỉ là `skipped-device-locked`, không có log network tươi — đừng báo cáo log cũ như bằng chứng mới.
- `adb shell uiautomator dump /sdcard/*.xml` có thể bị Killed trên máy yếu và file `/sdcard/*.xml` cũ dễ gây đọc nhầm màn stale — đối chiếu `dumpsys activity` + screencap tươi.
