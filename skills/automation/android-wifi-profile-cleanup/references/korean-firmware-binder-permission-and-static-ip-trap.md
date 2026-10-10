# Korean Firmware Binder Permission & Static IP Traps (Android 8 / Samsung S7)

## 1. Phân hóa Firmware: G930F (Global) vs G930S/L/K (Hàn Quốc)
Trong quá trình gỡ bỏ profile Wi-Fi lạ (`service call wifi 14 i32 <net_id>`):
- **SM-G930F (`heroltexx-user`)**: Transaction 14 (removeNetwork) của `IWifiManager` cho phép UID 2000 (`shell`) thực thi trực tiếp, trả về `Result: Parcel(00000000 00000001)`.
- **SM-G930S/L/K (`herolteskt-user`)**: Bản vá bảo mật cuối 2020 chặn UID 2000, ném lỗi:
  ```text
  SecurityException: Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE
  ```
- **Xử lý an toàn**: Không cố gắng cấp quyền `pm grant` cho `com.android.shell` (sẽ bị SecurityException vì shell không declare permission này). Thay vào đó, dùng `com.steinwurf.adbjoinwifi` (app đã có `CHANGE_WIFI_STATE`) để ép re-bind sang đúng SSID quy hoạch (`admin 1`, `admin 2`, `kibe 1`, `kibe 2`).

## 2. Bẫy Static IP Subnet Mismatch (`192.168.10.x` vs `192.168.110.x`)
- **Hiện tượng**: Máy đã kết nối đúng SSID `admin 1`, nhưng vẫn không thể ping hoặc kết nối tới MikroTik Proxy `192.168.110.2:100xx` (`dial tcp: network is unreachable`).
- **Nguyên nhân gốc**: Máy bị lưu cấu hình `IP assignment: STATIC` trong `WifiConfigStore.xml` với IP dải cũ `192.168.10.x` (từ mạng Dat trước đó).
- **Cách nhận diện O(1)**:
  ```bash
  adb shell dumpsys wifi | grep "IP assignment"
  adb shell ip -4 addr show wlan0
  ```
- **Khắc phục**:
  1. Xóa profile STATIC qua `service call wifi 14 i32 <NET_ID>`.
  2. Ép re-join qua `adbjoinwifi` để tạo lại profile mới với `IP assignment: DHCP`.
  3. Kiểm tra lại IP wlan0 đảm bảo thuộc dải `192.168.110.x` và ping thông `192.168.110.2`.

## 3. Shell Quoting Trap trong adbjoinwifi
- Lệnh gọi qua ADB shell:
  - **SAI (Cắt cụt tên SSID)**:
    `am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid admin 1 -e password_type WPA -e password ...`
    -> Android shell tách `admin 1` thành `ssid="admin"` và đối số phụ `"1"`. Kết quả tạo ra profile rác tên `admin` (Net ID mới với Priority 100), gây lặp vòng roam liên tục!
  - **ĐÚNG (Bọc nháy chuẩn)**:
    `am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "admin 1" --es password_type WPA --es password "..."`
