# Korean Firmware Binder Permission & Static IP Traps (Android 8 / Samsung S7)

## 1. Phân hóa Firmware: G930F (Global) vs G930S/L/K (Hàn Quốc)
Trong quá trình gỡ bỏ profile Wi-Fi lạ (`service call wifi 14 i32 <net_id>`):
- **SM-G930F (`heroltexx-user`)**: Transaction 14 (removeNetwork) của `IWifiManager` cho phép UID 2000 (`shell`) thực thi trực tiếp, trả về `Result: Parcel(00000000 00000001)`.
- **SM-G930S/L/K (`herolteskt-user`)**: Bản vá bảo mật cuối 2020 chặn UID 2000, ném lỗi:
  ```text
  SecurityException: Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE
  ```
- **Xử lý an toàn & Cơ chế xóa qua UI Settings (Triệt tiêu tận gốc không cần root)**:
  Không cố gắng cấp quyền `pm grant` cho `com.android.shell` (sẽ bị lỗi). Trên dòng máy Hàn, `WIFI_SAVED_NETWORK_SETTINGS` bị ẩn danh sách, nhưng mở `android.settings.WIFI_SETTINGS` thì vẫn thao tác được:
  1. **Tọa độ nút "QUÊN" (Forget) theo 2 loại modal thực tế (Samsung S7 Android 8)**:
     - **Modal Disconnected Network (khi tap mạng đã lưu dưới "MẠNG ĐANG CÓ")**: Modal ngắn gọn, nút "QUÊN" nằm tại bounds `[828, 1201, 925, 1248]`, tâm tap: **`(876, 1225)`**.
     - **Modal Connected Network (khi tap mạng đang active dưới "MẠNG HIỆN TẠI")**: Modal dài có hiển thị tốc độ/bảo mật/IP, nút "QUÊN" nằm tại bounds `[828, 1389, 925, 1436]`, tâm tap: **`(876, 1412)`**.
  2. **Chiến lược Active-Promote O(1) chống trượt tọa độ do RSSI biến động**:
     Danh sách "MẠNG ĐANG CÓ" liên tục đảo vị trí dòng theo sóng (RSSI). Giải pháp tối ưu tuyệt đối:
     - Gọi `adbjoinwifi` ép kết nối tạm thời vào `<ROGUE_SSID>` (ví dụ `Dat`) -> mạng lập tức nhảy lên vị trí cố định "MẠNG HIỆN TẠI" (`Y ~ 530`).
     - Tap `(300, 530)` mở modal connected network.
     - Tap **`(876, 1412)`** bấm "QUÊN" để xóa vĩnh viễn cấu hình khỏi `WifiConfigStore.xml`.
     - Lập tức gọi `adbjoinwifi` kéo máy về lại AP quy hoạch cứng (`admin 1` / `admin 2` với pass WPA) và nhấn HOME.
  3. **Kỷ luật chạy song song (Parallel-First Invariant)**:
     User chỉ đạo: **CẤM chạy cuốn chiếu (rolling/sequential)** khi xử lý dọn dẹp Wi-Fi trên farm rảnh. BẮT BUỘC dùng `ThreadPoolExecutor(max_workers=N)` bắn song song toàn bộ máy đích cùng lúc để hoàn tất trong 20-30s.
  4. **Giành Lock Preempt (`--preempt`)**:
     Khi ca nuôi đã kết thúc nhưng tiến trình cũ chưa nhả lock, dùng cờ `force_preempt=True` (scope `OPERATOR_PREEMPT` của `automation_core.device_lock`) để chiếm lock ngay mà không chờ timeout.

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
