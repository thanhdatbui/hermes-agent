# Bóc Tách Sự Cố M7: Mạng "Dat" (5GHz Kênh 100) vs Aruba, Ngưỡng Client Aruba & Xung Đột ADB Port 5037/5038 (19/10/2026)

## 1. Sự Thật Hiện Trường Về Mạng "Dat" vs Mạng Farm "kibe 1"
- **Hiện tượng:** Máy 7 (S7) không thể hoàn tất 4-way handshake vào SSID `kibe 1` (AP .253), nhưng khi thử kết nối vào SSID `Dat` thì ăn ngay trong 0 giây và ping được MikroTik `192.168.110.2`.
- **Bóc tách telemetry thực tế trên M7 (`dumpsys wifi`):**
  * `mWifiInfo SSID: Dat, BSSID: 28:d0:f5:2a:62:4b, State: COMPLETED, RSSI: -50 dBm, Link speed: 325Mbps, Freq: 5500MHz (Kênh 100)`
  * `wlan0 inet: 192.168.110.40/24`
  * `ping 192.168.110.2: 0% packet loss (7.3 ms)`
- **Nguyên nhân cốt lõi:**
  * SSID `Dat` này phát từ router ngoài (BSSID `28:d0:f5:...`), KHÔNG PHẢI từ cụm Aruba (`b0:b8:67:...` hay `20:a6:c0:...`).
  * Router này được cắm bridge thẳng vào switch farm (cùng subnet `192.168.110.x`), phát 5GHz ở Kênh 100 với công suất cực mạnh hướng thẳng vào M7 (-50 dBm).
  * Trong khi đó, con AP Aruba `.253` (`kibe 1`) phát ở Kênh 36 (5180MHz), đặt ở vị trí mà M7 chỉ hứng được -70 dBm (yếu hơn máy M8 bên cạnh tới 15 dBm). Khi M7 phát ngược gói Message 2 lên AP .253, tín hiệu bị suy hao dẫn đến timeout và failed handshake.

## 2. Ngưỡng Client Aruba: Khuyến Nghị 40 Máy vs Trần Cứng 64 Máy
- **Khuyến nghị airtime:** Con số 40 máy/AP là mốc phân bổ tải airtime khuyến nghị để đảm bảo 160 máy lướt video TikTok mượt mà không bị nghẽn vô tuyến.
- **Trần cứng kỹ thuật:** Trên Aruba Instant Virtual Controller, cấu hình thực tế thiết lập `Max Clients Threshold = 64` (phần cứng AP-325/315 hỗ trợ tới 256 client association).
- **Quy tắc điều phối:** CẤM ngụy biện coi 40 máy là trần cứng chặn kết nối khiến AP từ chối association.

## 3. Bẫy Xung Đột 2 ADB Server (Port 5037 vs Port 5038 / XiaoWei)
- **Triệu chứng:**
  * Lệnh `adb devices` trên cổng mặc định 5037 chỉ thấy 77 thiết bị, mất dấu M7.
  * Windows Device Manager (PnP) vẫn nhận thiết bị composite `USB\VID_04E8&PID_6860\9885F63030454D3055` (`Status: OK`).
  * Người dùng vẫn điều khiển được M7 mượt mà trên phần mềm Tiểu Vi (XiaoWei).
- **Bản chất kỹ thuật:**
  * Trên Windows host đang chạy song song 2 daemon ADB:
    1. Port 5037: daemon mặc định của hệ thống.
    2. Port 5038: daemon thứ hai (`PID 10084`) do Tiểu Vi quản lý hoặc spawn riêng.
  * M7 (cùng một số máy khác như M18, M30) bị gắn kết nối WinUSB độc quyền (exclusive interface claim) vào daemon port 5038.
- **Kỷ luật chẩn đoán O(1) chống phán bừa "rút cáp":**
  1. Khi `adb devices` mất máy, CẤM TUYỆT ĐỐI kết luận người dùng rút cáp hoặc sập nguồn.
  2. Kiểm tra PnP: `Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "*<SERIAL>*" }`.
  3. Kiểm tra các port ADB đang listen: `netstat -ano | findstr "5037 5038"`.
  4. Truy vấn ADB port 5038:
     ```python
     env = os.environ.copy()
     env["ADB_SERVER_SOCKET"] = "tcp:127.0.0.1:5038"
     res = subprocess.run(["adb", "devices"], env=env, capture_output=True, text=True)
     ```
  5. Nếu máy online trên port 5038: sử dụng `ADB_SERVER_SOCKET=tcp:127.0.0.1:5038` để can thiệp O(1) hoặc dùng lệnh `adb -P 5038 kill-server` khi cần đồng bộ toàn farm về port 5037.
