# ROM Mod, Battery Telemetry, & Device Integrity Inspection on Farm

## 1. Proactive Inspection Invariant
Khi user yêu cầu kiểm tra hiện trạng thiết bị, kiểm tra ROM mod hay đánh giá tình trạng phần cứng:
- Coordinator đang kết nối trực tiếp với 120+ máy (Kibe Local 1-80, Admin Remote 201-280).
- **CẤM TUYỆT ĐỐI** đùn đẩy việc cho user (không hỏi 'ném số máy qua đây' hay 'mày tự chạy lệnh ADB này đi').
- **BẮT BUỘC** chủ động lấy mẫu (ví dụ 3-5 máy đại diện mỗi cụm) bằng `python D:/Taadaa/tools/inspect_machine.py <N>` để đối chiếu và báo cáo kết quả thực tế ngay lập tức.

## 2. Bộ 6 chỉ số phân loại ROM Stock vs ROM Mod

| Chỉ số | ROM Stock Clean | ROM Stock Patch Pin (P30) | ROM LineageOS / AOSP |
| :--- | :--- | :--- | :--- |
| `ro.build.tags` | `release-keys` | `release-keys` | `test-keys` |
| `ro.boot.warranty_bit` (Knox) | `0` (Zin) | `1` (Đã nhảy Knox) | `1` |
| `ro.boot.verifiedbootstate` | `green` (Khóa boot) | `orange` / `yellow` | `orange` / `yellow` |
| `Launcher / Framework` | `com.sec.android.app.launcher` | `com.sec.android.app.launcher` | `org.lineageos.trebuchet` / `com.android.launcher3` |
| `Battery Telemetry` | Biến thiên theo tải thực | Kẹt cứng 25.0°C / 100% | Kẹt cứng hoặc mất sensor |
| `Default Route Net` | `wlan0` (Wi-Fi) / `rmnet` | `wlan0` | `eth0` (`TRANSPORT_ETHERNET`) |

## 3. Bản chất cơ chế Anti-Fraud của TikTok đối với ROM Box LAN / P30
1. **Lộ `TRANSPORT_ETHERNET` (`eth0`):** `ConnectivityManager` trên Box LAN để lộ kết nối mạng dây, điện thoại không có Wi-Fi/4G $\rightarrow$ Cờ bất thường cấp 1.
2. **Framework Mismatch:** Khai Samsung nhưng bên trong thiếu toàn bộ `com.samsung.android.*` và Knox framework.
3. **Mất Google Play Integrity:** Unlock Bootloader làm Knox nhảy `0x1`, rớt `MEETS_DEVICE_INTEGRITY`.
4. **Nhiệt động học phi lý:** Driver pin chế hardcode `temp = 250` (25.0°C) và `capacity = 100%` 24/7 dù CPU gánh tải nặng $\rightarrow$ TikTok SDK (`libmetasec_ml.so` / BdProtector) đọc được qua `BatteryManager` và gắn cờ thiết bị farm giả lập.
5. **ROM Auto ADB:** Sửa `ro.adb.secure=0` để bỏ popup xác thực RSA $\rightarrow$ Cờ nguy hiểm của môi trường eng/userdebug. Trên ROM gốc thật chỉ cần tích "Always allow from this computer" một lần duy nhất là nhớ vĩnh viễn.
