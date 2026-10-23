# Preflight Port 5038 Gate & Cảnh Báo "Mất Kết Nối ADB Ảo" (23/10/2026)

## Quy Tắc Bắt Buộc Khi Thấy >10 Máy Báo "Mất Kết Nối ADB/USB"
1. **Kiểm tra socket 5038 ngay lập tức:**
   - Khi có hiện tượng hàng loạt máy báo `device not found` trên cổng 5037, kiểm tra socket `127.0.0.1:5038`.
   - Nếu cổng 5038 đang LISTEN -> 100% do XiaoWei (牧卫/攸卫) tranh chấp pipe WinUSB và bão hòa băng thông USB 2.0 EHCI. CẤM báo cáo tuột cáp vật lý.
2. **Preflight Gate trong launcher:**
   - Trong `run-feed-session.ps1` và `pre_session_device_gate.py`:
     Kiểm tra `$xwListeners = @(Get-NetTCPConnection -LocalPort 5038 -State Listen -ErrorAction SilentlyContinue | Where-Object { $_ })`.
     Thực thi lệnh dọn `adb -P 5038 kill-server`. Nếu không giải phóng được, throw `PREFLIGHT_PORT_5038_BLOCKED`.
3. **Chi tiết kiến trúc & Closeout Gate:**
   - Xem chi tiết tại `android-farm-host-operations/references/xiaowei-port-5038-preflight-gate-and-false-usb-disconnect-20261023.md`.
