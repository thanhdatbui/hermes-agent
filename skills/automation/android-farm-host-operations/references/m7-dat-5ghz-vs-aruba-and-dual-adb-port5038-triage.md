# Bóc Tách Sự Cố M7: Mạng "Dat" (5GHz Kênh 100) vs Aruba, Ngưỡng Client Aruba & Xung Đột ADB Port 5037/5038 (19/10/2026)

## 1. Sự Thật Hiện Trường Về Mạng "Dat" vs Mạng Farm "kibe 1"
- **Hiện tượng:** Máy 7 (S7) không thể hoàn tất 4-way handshake vào SSID `kibe 1` (AP .253), nhưng khi thử kết nối vào SSID `Dat` thì ăn ngay trong 0 giây và ping được MikroTik `192.168.110.2`.
- **Bóc tách telemetry thực tế trên M7 (`dumpsys wifi`):**
  * `mWifiInfo SSID: Dat, BSSID: 28:d0:f5:2a:62:4b, State: COMPLETED, RSSI: -49 dBm, Link speed: 351Mbps, Freq: 5500MHz (Kênh 100 5GHz)`
  * `wlan0 inet: 192.168.110.40/24`
  * `ping 192.168.110.2: 0% packet loss (7.3 ms)`
- **Nguyên nhân kỹ thuật sâu:**
  * SSID `Dat` được phát từ Router Gateway chính của phòng (`192.168.110.1`, MAC `28:d0:f5:...`) cắm cùng subnet switch farm `192.168.110.x`, đồng thời cũng có profile `Dat` cấu hình trên cả 4 AP Aruba (`Zone: zone1,zone2,zone3,zone4`, `Band: all`).
  * Router Gateway phát 5GHz ở Kênh 100 (5500MHz) với công suất mạnh (-49 dBm) thẳng vào vị trí M7, card 5GHz của M7 bắt tay hoàn hảo với tốc độ 351 Mbps.
  * CẤM tra cứu tiền tố MAC OUI rồi tự ý gán nhãn thương hiệu lạ ngoài farm (như suy diễn thành "router Xiaomi" khi farm không hề có thiết bị đó).
  * Trong khi đó, AP Aruba `.253` (`kibe 1`) dù thử đổi sang Kênh 36, 149 hay 52, M7 vẫn gặp hiện tượng kén búp sóng hoặc suy hao ăng-ten đặc thù với AP Aruba này, khiến handshake bị reject.

## 2. Kiểm Tra Proxy Bằng Shell Trên Android 8 / Samsung S7
- Samsung S7 (Android 8) KHÔNG có sẵn binary `curl` hay `nc` chuẩn trong `/system/bin`.
- Kiểm tra proxy trực tiếp từ shell Android BẮT BUỘC dùng:
  `echo -e "CONNECT httpbin.org:80 HTTP/1.1\r\nHost: httpbin.org:80\r\n\r\n" | toybox nc -w 3 192.168.110.2 20007`
- Nhận phản hồi `HTTP/1.1 200 Connection established` xác nhận thông suốt 100%. CẤM gọi `curl` rồi thấy rỗng suy diễn đứt mạng.

## 2. Nguy Cơ Nghẽn Sóng Khi Bật Băng Tần 2.4 GHz Trên SSID Farm (RF Planning)
- **Quy tắc bắt buộc:** Toàn bộ 4 SSID vận hành farm (`admin 1`, `admin 2`, `kibe 1`, `kibe 2`) BẮT BUỘC giữ cấu hình **`Band: 5.0` (5GHz Only)**. TUYỆT ĐỐI KHÔNG mở `Band: all` (2.4GHz + 5GHz).
- **Lý do kỹ thuật (2 thảm họa RF khi mở 2.4GHz trên dàn phone farm):**
  1. *Hiện tượng Sticky Client Fallback:* Sóng 2.4GHz có bước sóng dài nên RSSI luôn cao hơn 5GHz từ 10–15 dBm. Android 8 (Samsung S7) có cơ chế chọn mạng ưu tiên sóng mạnh, sẽ kéo tụt 10–20 máy đang chạy 5GHz ngon lành rơi xuống 2.4GHz.
  2. *Bão hòa Airtime & Sập Proxy:* Kênh 20MHz trên 2.4GHz chỉ có thông lượng thực tế ~30–50 Mbps. Khi nhiều máy cùng stream video TikTok, kênh 2.4GHz bị nghẽn 100% (Airtime Saturation), độ trễ nhảy từ 7ms lên 1000ms+, gây rớt gói tin và đứt kết nối proxy MikroTik hàng loạt.

## 3. Ngưỡng Client Aruba: Khuyến Nghị 40 Máy vs Trần Cứng 64 Máy
- **Khuyến nghị airtime:** Con số 40 máy/AP là mốc phân bổ tải airtime khuyến nghị để đảm bảo 160 máy lướt video TikTok mượt mà không bị nghẽn vô tuyến.
- **Trần cứng kỹ thuật:** Trên Aruba Instant Virtual Controller, cấu hình thực tế thiết lập `Max Clients Threshold = 64` (phần cứng AP-325/315 hỗ trợ tới 256 client association).
- **Quy tắc điều phối:** CẤM ngụy biện coi 40 máy là trần cứng chặn kết nối khiến AP từ chối association.

## 4. Bẫy Xung Đột 2 ADB Server (Port 5037 vs Port 5038 / XiaoWei)
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
  5. Khi can thiệp thiết bị nằm trên port 5038, sử dụng `env["ADB_SERVER_SOCKET"] = "tcp:127.0.0.1:5038"` hoặc socket direct bridge tới port 5038 để thực thi tự động 100%.

## 5. Kỷ Luật Hành Vi Điều Phối: CẤM Đùn Việc Thủ Công Cho Người Dùng
- **User Correction (19/10/2026):** *"Là sao lại khóc lóc bắt t làm nữa??"*
- **Nguyên tắc bất biến:**
  * Khi máy đã có kết nối ADB (dù ở port 5037 hay port 5038), Coordinator BẮT BUỘC tự động bắn lệnh can thiệp (join Wi-Fi, toggle Wi-Fi, kiểm tra IP, screencap).
  * TUYỆT ĐỐI KHÔNG hướng dẫn người dùng tự mở app XiaoWei gõ mật khẩu, tự bấm kết nối tay hay tự thao tác trên điện thoại. Mọi thao tác phải được tự động hóa triệt để qua script/socket.
