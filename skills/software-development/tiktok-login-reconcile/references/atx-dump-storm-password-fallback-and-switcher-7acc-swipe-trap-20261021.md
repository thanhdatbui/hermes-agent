# Bẫy Bão Dump XML (ATX Dump Storm), Bẫy Vuốt Nút Đáy Switcher 7 Nick & Xung Đột Lock Cron Rename (2026-10-21)

## 1. BẪY BÃO DUMP XML (ATX DUMP STORM) LÀM ĐƠ ACCESSIBILITY TẠI BƯỚC NHẬP PASS

### Hiện tượng:
- Khi `fill_password_and_login` (`social_reg_v1.py`) phát hiện màn hình mật khẩu, log ghi nhận:
  ```text
  [auth] round 1/6
  [8] Fill password
  🗾 UI XML: D:\Taadaa\runtime\kibe\artifacts\ui_dumps\debug_24_pass_screen_101359.xml
  ✗ timeout waiting password field
  [ui-xml] atx-agent dump attempt 1/3 failed on ce0117112b2a0e3a04, retry in 0.3s...
  ...
  STOPPED: [08] Không tìm thấy EditText password
  ```
- Kiểm tra file `debug_24_pass_screen_101359.xml`: Node `EditText` mật khẩu (`t='Mật khẩu'`, bounds `[138,564][852,624]`) **HOÀN TOÀN CÓ MẶT**.

### Nguyên nhân:
- Sau khi vòng lặp `while time.time() < deadline` dump được XML (`xml_pw_check`) và thấy màn mật khẩu, hàm lập tức gọi:
  1. `save_ui_xml(device_id)` $\rightarrow$ Gọi lại `get_ui_xml()` dump lần 2.
  2. `wait_for_edittext(device_id)` $\rightarrow$ Gọi tiếp `get_ui_xml()` dump lần 3.
- Trên các máy Samsung S7 (Android 8, RAM 4GB), việc gọi `atx-agent` dump XML 3 lần liên tiếp trong vòng 1-2 giây làm quá tải Accessibility Service / socket bị nghẽn, dẫn đến các lần dump sau bị timeout và trả về chuỗi rỗng `""`.
- Kết quả: `wait_for_edittext` nhận XML rỗng và ném lỗi `Không tìm thấy EditText password` dù màn hình mật khẩu đang hiển thị sờ sờ.

### Khắc phục chuẩn O(1):
1. **Tránh bão dump**: Dùng `save_xml_blob(xml_pw_check, ...)` để lưu chuỗi XML đã có, không gọi lại `save_ui_xml`.
2. **Fallback từ XML đã có**: Nếu `wait_for_edittext` trả về rỗng, lập tức lấy `pass_nodes = list_edittext_nodes(xml_pw_check)`.
3. **Fallback tọa độ chuẩn**: Nếu vẫn không có node, fallback tọa độ tâm chuẩn trên màn hình Samsung S7 (1080x1920): `pass_nodes = [{"coord": (495, 594), "x1": 138, "y1": 564, "x2": 852, "y2": 624, "rid": "", "password": True}]`.

---

## 2. BẪY VUỐT NÚT ĐÁY "THÊM TÀI KHOẢN" KHI SWITCHER CÓ 7 NICK (INFINITE SWIPE TRAP)

### Hiện tượng:
- Khi máy đã có 7 nick, nút "Thêm tài khoản" nằm ở vị trí đáy: bounds `[0, 1680][1080, 1896]`.
- Script báo lỗi:
  ```text
  [add-account] Nút ở sát mép dưới (1680-1896), cuộn lên trước khi tap
  [add-account] Nút ở sát mép dưới (1680-1896), cuộn lên trước khi tap
  [add-account] Nút ở sát mép dưới (1680-1896), cuộn lên trước khi tap
  STOPPED: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)
  ```

### Nguyên nhân:
- Điều kiện cũ: `if y1 > 1650 or y2 >= 1880:` cho rằng nút bị che nên cố `swipe(540, 1600, 540, 1100, 300)`.
- Tuy nhiên trên TikTok v47.x Samsung S7, Bottom Sheet của Switcher khi có 7 nick đã bung kịch trần, không thể cuộn thêm được nữa. Lệnh vuốt hoàn toàn vô hiệu.
- Vòng lặp `attempt in range(3)` bị đốt hết bởi 3 lần vuốt vô ích mà không bao giờ thực hiện cú tap.

### Khắc phục chuẩn O(1):
- Khi node "Thêm tài khoản" đã hiện diện đầy đủ trong XML, **CẤM vuốt cuộn mù**.
- Áp dụng Safe-Point Tap lệch lên 1/3 phía trên và clamp an toàn:
  `safe_x = (x1 + x2) // 2`
  `safe_y = min(y1 + max(1, (y2 - y1) // 3), 1835)`
- Tap ngay vào `(540, 1752)` và `return` để luồng đi tiếp vào form đăng nhập, không lặp lại vòng lặp.

---

## 3. XUNG ĐỘT DEVICE LOCK VỚI CRONJOB ĐỔI TÊN CUỐN CHIẾU (`tiktok-rolling-rename-watchdog`)

### Hiện tượng:
- Khi nạp bù nick thiếu (`tiktok_login_v1.py`), script bị văng với exit code 2:
  ```text
  [device-lock] NEEDS_USER_DECISION: device lock active: path=...machine_24.lock.json pid=... project=tiktok-rename command=D:\Taadaa\tools\do_rename_canonical_runner.py ...
  ```

### Nguyên nhân:
- Cronjob `tiktok-rolling-rename-watchdog` (chạy định kỳ 15 phút) tự động quét thấy tài khoản chưa đổi tên trên máy và kích hoạt tiến trình đổi tên chiếm device lock 1-2 phút.
- Hai tiến trình cùng tranh chấp thiết bị làm luồng cứu hộ bị từ chối.

### Khắc phục:
- Khi thực hiện can thiệp cứu hộ nạp bù trên một máy cụ thể, kiểm tra và tạm dừng cronjob đổi tên cuốn chiếu (`cronjob pause 35e94bb43979`).
- Chờ tiến trình đổi tên hiện tại thoát tự nhiên và xác nhận `machine_<N>.lock.json` biến mất.
- Sau khi cứu hộ xong thì kích hoạt lại cronjob (`cronjob resume 35e94bb43979`).
