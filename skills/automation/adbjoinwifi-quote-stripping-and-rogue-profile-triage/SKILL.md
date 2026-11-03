---
name: adbjoinwifi-quote-stripping-and-rogue-profile-triage
description: "Triage & fix lỗi lột nháy shell (quote stripping) khi gọi adbjoinwifi sinh mạng rác và quy trình purge sạch mạng rác trên Farm."
---
# Triage & Bản Vá: Bẫy Lột Nháy Shell Khi Gọi adbjoinwifi & Sinh Mạng Rác

## 1. Hiện Tượng & Dấu Hiệu Nhận Biết
- Trên dàn farm, các máy Android đột ngột xuất hiện các cấu hình Wi-Fi lạ không mật khẩu:
  - Cụm Admin xuất hiện SSID `admin` (bảo mật `NONE`, priority 100).
  - Cụm Kibe xuất hiện SSID `kibe` (bảo mật `NONE`, priority 100).
- Hệ quả nghiêm trọng:
  - Khi máy chập chờn sóng hoặc tải AP tăng, Android supplicant kích hoạt auto-roam và liên tục nhảy qua nhảy lại (flapping) giữa SSID chính (`admin 1` / `kibe 1`) và SSID rác ảo (`admin` / `kibe`).
  - Hàng loạt máy bị rớt kết nối đồng loạt trong ca chạy: một nhóm báo `dumpsys connectivity: Wi-Fi not connected`, nhóm khác bị kernel Android hủy route wlan0 trong khi đang mở TCP socket, ném mã lỗi POSIX `ENETUNREACH` (`dial tcp 192.168.110.2:202xx: connect: network is unreachable`).
  - Coordinator thiếu kinh nghiệm dễ rơi vào bẫy đổ thừa "nghẽn tải tải đỉnh / race condition" hoặc "router quá tải".

## 2. Nguyên Nhân Gốc Rễ Kỹ Thuật (The Quote Stripping & Parameter Splitting Bug)
1. **SSID có khoảng trắng:** Quy hoạch mạng Farm sử dụng các tên SSID chuẩn có dấu cách: `"kibe 1"`, `"kibe 2"`, `"admin 1"`, `"admin 2"`.
2. **Cơ chế gọi lệnh ADB:**
   Trong các script tự cứu (`vpn_preflight.py` hoặc `farm_wifi_auto_healer.py`), lệnh được xây dựng dạng:
   ```python
   cmd = f'am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "{ssid}" --es password_type WPA --es password "{password}"'
   adb.shell(cmd)
   ```
3. **Quá trình bóc tách chuỗi lệnh:**
   - Khi truyền qua `AdbClient.shell()`, chuỗi `cmd` đi qua `shlex.split(cmd)`. Thư viện shlex bóc bỏ cặp dấu nháy kép `"..."`, biến token thành `admin 1` trần trụi.
   - Khi client `adb.exe` gửi lệnh sang daemon `adbd` trên Android, chuỗi lệnh thực thi trong `/system/bin/sh` là:
     `am start ... --es ssid admin 1 --es password_type WPA --es password ...`
   - Tiến trình `am` của Android phân tích tham số:
     * Cặp cờ: `--es ssid admin` $\rightarrow$ Nhận SSID = `"admin"` (bị cắt cụt mất số `"1"`).
     * Token `1` đứng trơ trọi làm xô lệch toàn bộ cặp cờ phía sau: `--es password_type WPA` và `--es password` bị trôi, mật khẩu bị gán thành `null`.
4. **App `adbjoinwifi` tạo mạng ảo:**
   - App nhận lệnh nối vào mạng `"admin"` bảo mật mở (không mật khẩu). Nó gọi API Android và tạo ra profile mới lưu vào `WifiConfigStore.xml`:
     `ID: <N> SSID: "admin" NONE Priority: 100 autoReconnect: 1`
   - Cứ mỗi lần watchdog hoặc runner chạy preflight thử cứu máy là lại đẻ ra thêm cấu hình rác này.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
