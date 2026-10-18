# Aruba WPA2 Integrity Check Failure & Cluster Password Desync

## Bối cảnh & Hiện tượng
- Khi máy farm (đặc biệt Samsung S7) đặt rất gần Access Point Aruba (ví dụ M7 nằm ngay cạnh AP `kibe 1`), nhưng không thể kết nối Wi-Fi, không nhận IP, `dumpsys wifi` báo `Supplicant state: UNINITIALIZED` hoặc `DISCONNECTED`.
- Logcat trên Android:
  ```text
  wpa_supplicant: Trying to associate with B0.F8.B0 (SSID='kibe 1' freq=5180 MHz)
  wpa_supplicant: CTRL-EVENT-ASSOC-REJECT bssid=B0.F8.B0 status_code=1
  wpa_supplicant: wlan0: CTRL-EVENT-SSID-TEMP-DISABLED id=0 ssid="kibe 1" auth_failures=1
  WifiStateMachine: Assocation Rejection event: bssid=b0:b8:67:5b:f8:b0 reason code=1 timedOut=false
  ```
- Cạm bẫy chẩn đoán sai: Đổ lỗi cho "sóng yếu", "lưng máy tì khung sắt", hoặc "cần đổi hướng anten máy" trong khi máy đặt ngay sát AP.

## Bản chất kỹ thuật trên Aruba Virtual Controller
- Kiểm tra log hệ thống trên Aruba Virtual Controller (`192.168.110.251:4343`, lệnh `show log system`):
  ```text
  cli[6136]: <341004> <WARN> |AP ... cli| AP 192.168.110.253: Client ac:5f:3e:60:59:1b authenticate fail because integrity check failure in encrypted message
  ```
- `integrity check failure in encrypted message`: Đây là lỗi Message Integrity Check (MIC) trong quá trình bắt tay 4 bước WPA2 (4-Way Handshake, EAPOL Message 2).
- Nguyên nhân: Thiết bị gửi Key MIC được tính toán bằng Pre-Shared Key (PSK) sai lệch so với AP.

## Quy hoạch mật khẩu Wi-Fi Farm Taadaa
Tra cứu file nguồn chân lý `D:/Taadaa/machine-config/farm_wifi_profiles.json`:
- **M01 – M40:** SSID **`kibe 1`** -> Mật khẩu: **`23102025`** (QUY HOẠCH RIÊNG).
- **M41 – M80:** SSID **`kibe 2`** -> Mật khẩu: **`19051995`**.
- **M201 – M240:** SSID **`admin 1`** -> Mật khẩu: **`19051995`**.
- **M241 – M280:** SSID **`admin 2`** -> Mật khẩu: **`19051995`**.

> **CẢNH BÁO:** Tuyệt đối không mặc định lấy mật khẩu `19051995` áp dụng cho toàn farm. Dàn `kibe 1` (M1–M40) bắt buộc phải là `23102025`.

## Quy trình khắc phục
1. Giữ lock thiết bị: `with operator_device_lock(machine=N, serial=SERIAL, timeout=120.0):`
2. Đánh thức màn hình: `input keyevent 224` và set `stay_on_while_plugged_in = 3`.
3. Đóng các app cài đặt treo: `am force-stop com.steinwurf.adbjoinwifi` và `am force-stop com.android.settings`.
4. Dọn sạch cấu hình cũ mang mật khẩu sai:
   ```bash
   for i in $(seq 0 9); do
       service call wifi 14 i32 $i
   done
   ```
5. Re-join với đúng SSID và password theo `farm_wifi_profiles.json`:
   ```bash
   am start -S -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "kibe 1" --es password_type WPA --es password 23102025
   ```
6. Đợi 8–10 giây cho WPA2 handshake và xin cấp lease DHCP từ Ruijie Gateway (`192.168.110.1`), sau đó đưa về Home: `input keyevent 3`.
7. Kiểm tra readback:
   - `ip -4 addr show wlan0` có IP `192.168.110.x`.
   - `dumpsys wifi` xác nhận `Supplicant state: COMPLETED`, `Link speed` đạt 100+ Mbps.
