# Samsung Galaxy S7 (Android 8) Wi-Fi Radio Driver Throttle vs Hardware Failure & Reboot Recovery Protocol

## 1. Hiện tượng & Vấn đề thực tế (Case Study Máy 7)

Trong quá trình debug lỗi mạng hoặc chạy gate Wi-Fi (`farm_network_gate.py`) trên dòng máy cũ Samsung Galaxy S7 (Android 8, SM-G930F):
- Khi gặp lỗi tầng L3 (chưa nhận IP) hoặc L4 (proxy probe timeout), nếu điều phối chạy vòng lặp retry quá nhanh và dồn dập (loop testing), mỗi vòng lặp đều gọi:
  ```bash
  svc wifi disable
  sleep 1.0
  svc wifi enable
  cmd wifi start-scan
  am start -n com.steinwurf.adbjoinwifi/.MainActivity ...
  ```
- **Hậu quả trên kernel/firmware:** Bật/tắt radio Wi-Fi liên tục ở tần suất cao khiến chip Broadcom/Wi-Fi driver trên Android 8 rơi vào trạng thái throttled / firmware panic / supplicant wedged:
  ```text
  Supplicant state: DISCONNECTED, RSSI: -127, Link speed: -1Mbps
  ```
  Lúc này máy hoàn toàn không quét được bất kỳ SSID nào, radio báo RSSI -127. Trạng thái này rất dễ bị chẩn đoán sai là **"hỏng phần cứng chip Wi-Fi"** hoặc **"máy bị gãy chân anten"**.

---

## 2. Tiêu chuẩn chẩn đoán phân biệt (Hardware Failure vs Driver Panic)

Trước khi kết luận máy hỏng chip Wi-Fi, bắt buộc đối chiếu 3 bằng chứng:
1. **Lịch sử lease DHCP trên Gateway (Ruijie):**
   - Đăng nhập Ruijie Gateway (`http://192.168.110.1/cgi-bin/luci/`), vào tab *DHCP Clients*.
   - Nếu thấy MAC của máy (ví dụ `ac:5f:3e:60:59:1b`) có tên `Galaxy-S7`, được cấp IP động và có thời gian lease còn lại -> **Chứng minh 100% chip Wi-Fi và anten đã liên kết L2/L3 thành công gần đây, phần cứng hoàn toàn nguyên vẹn**.
2. **Trạng thái Gate APPLIED trước đó:**
   - Nếu trong phiên hoặc trước đó vài phút, gate từng trả về `APPLIED` hoặc `NOOP_HEALTHY` -> Khẳng định phần cứng bình thường.
3. **Thao tác vật lý / nhiệt độ:**
   - Khi chip Wi-Fi xử lý liên tục các request quét mạng và kết nối, nhiệt độ tăng cao làm tăng packet loss và timeout socket.

---

## 3. Quy trình phục hồi dứt điểm (Deterministic Reboot Recovery)

Khi phát hiện chip Wi-Fi bị kẹt `Supplicant state: DISCONNECTED, RSSI: -127` sau nhiều lần join thất bại:

1. **DỪNG NGAY mọi lệnh can thiệp Wi-Fi dồn dập:**
   - Cấm tiếp tục spam `_join_wifi`, `cmd wifi start-scan`, hoặc toggle `svc wifi`.

2. **Thực thi Reboot cứu hộ sạch qua script chuẩn:**
   - Không reboot chay bằng adb trần. Luôn bọc qua công cụ cứu hộ chuẩn để đảm bảo lock an toàn và ghi nhận telemetry:
     ```bash
     python D:/Taadaa/tools/recover_stuck_s7.py --machine <N> --reboot
     ```
   - Script sẽ kiểm tra cooldown 5 phút (`reboot_cooldown_<serial>.json`) chống reboot loop, gửi lệnh reboot hệ điều hành và đợi thiết bị boot lên lại Launcher an toàn (~35s).

3. **Chờ ổn định radio sau boot:**
   - Sau khi máy boot vào Launcher, để máy nghỉ ngơi tối thiểu 15-30 giây để Android `ConnectivityService` nạp firmware radio và đồng bộ với AP Aruba.
   - Chạy gate kiểm chứng:
     ```bash
     python D:/Taadaa/tools/farm_network_gate.py <N> --force-preempt
     ```
   - Khi kết quả đạt `APPLIED`, lập tức chuyển sang chế độ kiểm tra thụ động `python D:/Taadaa/tools/farm_network_gate.py <N>` để nhận `NOOP_HEALTHY`, tuyệt đối không join lại gây đứt phiên.
