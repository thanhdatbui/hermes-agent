# Samsung Korean ROM (SM-G930S) Saved Network UI & Preemption Playbook

## 1. Hiện tượng ẩn danh sách mạng trên ROM Hàn (SM-G930S / Knox)
Khi cố gắng mở giao diện Cài đặt mạng đã lưu trên dòng Samsung Galaxy S7 Hàn Quốc (SK Telecom / KT / LG U+):
```bash
adb shell am start -a android.settings.WIFI_SAVED_NETWORK_SETTINGS
```
- Màn hình `Settings$SavedAccessPointsSettingsActivity` chỉ hiển thị thanh tiêu đề `CÁC MẠNG ĐÃ LƯU` (hoặc `SAVED NETWORKS`).
- Toàn bộ danh sách mạng lưu bên dưới hoàn toàn rỗng/trắng, không hiển thị bất kỳ SSID nào (kể cả khi `dumpsys wifi` ghi nhận có Net ID 0, 1, 2...).
- **Nguyên nhân gốc**: Cơ chế bảo mật Knox kết hợp gói tùy biến của nhà mạng Hàn Quốc phân loại các mạng Wi-Fi được nạp bởi system services hoặc apps thành private/system-managed và ẩn khỏi màn hình Saved Networks của người dùng thông thường nếu không có chứng chỉ quản trị Knox tương ứng.
- **Hệ quả**: Không thể thực hiện tự động hóa UI qua accessibility / ATX / uiautomator để bấm nút "Quên mạng" (Forget Network) trên màn hình này.

## 2. Shell Permission Denial & Rào cản File System
- Lệnh binder `service call wifi 14 i32 <net_id>` bị từ chối với lỗi:
  `SecurityException: Neither user 2000 nor current process has android.permission.CHANGE_WIFI_STATE`
- File lưu trữ `/data/misc/wifi/WifiConfigStore.xml` có quyền `0660 wifi:wifi`, quyền shell ADB (UID 2000) không thể đọc/ghi trực tiếp (thiết bị farm không có root `su`).
- **Giải pháp tối ưu & an toàn**: 
  * Không thực hiện "Đặt lại cài đặt mạng" (Reset network settings) vì thao tác này làm mất toàn bộ chứng chỉ và cấu hình VPN proxy.
  * Áp dụng giải pháp **Re-bind cưỡng bức**: Dùng app `com.steinwurf.adbjoinwifi` (app đã được cấp sẵn `CHANGE_WIFI_STATE`) để ép thiết bị kết nối cố định vào SSID mục tiêu (`admin 1`, `admin 2`, `kibe 1`, `kibe 2`).
  * Runner (`vpn_preflight.py`) duy trì cơ chế fail-closed: nếu thiết bị roam sang `Dat` (dải `192.168.10.x`), Runner phát hiện lệch subnet và tự động kích hoạt `adbjoinwifi` kéo thiết bị về lại đúng AP Aruba farm (`192.168.110.x`).

## 3. Quy trình giành Lock an toàn (OPERATOR_PREEMPT)
Khi User/Operator phát lệnh giành lock (ví dụ: *"Giành lock đi. Ca nuôi nick hết luôn r thì phải"*):
- **CẤM TUYỆT ĐỐI**: Không tự tiện dùng Python xóa file `rm -f ~/.codex/device-locks/*.lock.json` vì sẽ phá vỡ tính toàn vẹn của lock protocol version 2 và gây race condition nếu có tiến trình khác đang ghi.
- **CHUẨN VẬN HÀNH**: 
  Sử dụng tham số `force_preempt=True` của `automation_core.device_lock`:
  ```python
  with operator_device_lock(
      machine=machine,
      serial=serial,
      project="batch_wifi_clean",
      timeout=15.0,
      bypass_proxy_readiness=True,
      force_preempt=True
  ):
      ...
  ```
  Khi `force_preempt=True`, hàm `acquire_device_lock` tự động thiết lập:
  - `allow_takeover = True`
  - `takeover_scope = TAKEOVER_SCOPE_OPERATOR_PREEMPT`
  - `takeover_authorized = True`
  - `takeover_reason = "operator force preempt"`
  Điều này cho phép tiến trình bảo trì giành lại quyền điều khiển thiết bị một cách hợp lệ, lưu lại đầy đủ audit trail trong lịch sử lock.
