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

## 3. Đột phá kỹ thuật: Xóa sạch vĩnh viễn qua UI Long-Press & Active Modal
Mặc dù màn hình `WIFI_SAVED_NETWORK_SETTINGS` bị ẩn, màn hình chính `android.settings.WIFI_SETTINGS` hoàn toàn hiển thị SSID `Dat` và cho phép xóa sạch vĩnh viễn 100% không cần root theo 2 kịch bản đã được kiểm chứng thực tế:

### Kịch bản A: Khi mạng rác đang ngắt kết nối (nằm ở "MẠNG ĐANG CÓ")
- **Bẫy 1 chạm (Single-tap trap)**: Bấm 1 chạm vào SSID ngắt kết nối sẽ khiến Android hiểu là lệnh kết nối và bắt đầu dò DHCP ("Đang kiểm tra chất lượng..."), không hiện nút Quên mạng.
- **Kỹ thuật Long-press Context Menu**:
  1. `am force-stop com.android.settings` (bắt buộc đóng sạch popup/dialog cũ).
  2. `am start -a android.settings.WIFI_SETTINGS` và chờ 3s.
  3. **Nhấn giữ 1.2s** tại hàng 1 `(304, 820)`: `input swipe 304 820 304 820 1200`.
  4. Hệ thống bật Context Menu 3 mục -> Bấm chính xác vào mục **"Quên mạng"** tại tâm `(500, 1195)` (bounds `[374, 1171, 614, 1217]`).
  5. Profile rác lập tức bị xóa sổ vĩnh viễn khỏi `WifiConfigStore.xml`.
  6. Re-join AP quy hoạch (`admin 1` / `admin 2`) bằng `adbjoinwifi` và về Home.

### Kịch bản B: Khi mạng rác đang kết nối (nằm ở "MẠNG HIỆN TẠI")
- Tap vào dòng SSID đang kết nối tại `(300, 530)` để bật modal thông tin mạng (tốc độ, bảo mật, IP).
- Bấm nút **"QUÊN"** ở góc dưới phải tại tọa độ `(876, 1412)` (bounds `[828, 1389, 925, 1436]`).
- Profile bị xóa ngay lập tức -> Re-join AP quy hoạch.

## 4. Quy trình giành Lock an toàn (OPERATOR_PREEMPT)
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

## 5. Kỷ luật chạy song song đa luồng (Cấm cuốn chiếu khi dọn Wi-Fi)
Khi User chỉ đạo: *"K cuốn chiếu chạy song song luôn"*:
- **CẤM TUYỆT ĐỐI**: Chạy tuần tự cuốn chiếu (serial/rolling loop từng máy một).
- **LÝ DO KỸ THUẬT**: Khi ngắt kết nối và re-bind từng máy một trong cụm 15-20 máy, AP Aruba bị biến động RSSI cục bộ khiến các máy kế cận tự động kích hoạt quét mạng và nhảy roam sang các SSID rác phát xung quanh (`Dat`), gây ra hiện tượng bão roaming (re-roam storm) kéo dài thời gian xử lý lên 15–30 phút.
- **CHUẨN VẬN HÀNH**: 
  Sử dụng `ThreadPoolExecutor(max_workers=len(targets))` bắn lệnh song song đồng loạt trên tất cả các máy mục tiêu:
  ```python
  with ThreadPoolExecutor(max_workers=len(targets)) as executor:
      futs = {executor.submit(process_machine, m, s): m for m, s in targets}
      for f in as_completed(futs):
          results.append(f.result())
  ```
  Toàn bộ đợt xử lý 17-20 máy đồng loạt mở Settings -> Long-press -> Quên mạng -> Re-bind hoàn tất chỉ trong 20–30 giây, dập tắt triệt để mọi cơ hội bão roaming.

## 6. Kỷ luật chống thoái thác "Knox chặn nên bỏ qua" (Anti-Passive Resignation)
- **Bài học từ sự cố User chỉ trích**: *"Trong hình có wifi dat. Sao đéo bấm vào r bấm quên đi"*.
- **Nguyên tắc hành động**: Khi gặp rào cản hệ thống ở tầng shell (`SecurityException` trên Knox), Coordinator/Worker KHÔNG ĐƯỢC thụ động chấp nhận rủi ro rồi báo cáo "đành để lại profile ngầm". BẤT KỲ khi nào mục tiêu có hiển thị trực quan trên màn hình (UI surface), BẮT BUỘC phải chuyển hướng sang giải pháp UI Automation (Long-press Context Menu hoặc Modal Details) để xử lý dứt điểm tận gốc vấn đề!
