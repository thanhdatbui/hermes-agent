# Password Screen ATX Dump Overload & Bottom-Sheet Swipe Trap (2026-10-21)

## 1. Hiện Tượng & Triệu Chứng

### Sự cố 1: `STOPPED: [08] Không tìm thấy EditText password`
- Trong hàm `fill_password_and_login` (`social_reg_v1.py`), vòng lặp kiểm tra màn hình mật khẩu đã nhận diện được màn hình password và lưu vào `xml_pw_check` (node EditText tại `[138, 564][852, 624]`).
- Tuy nhiên ngay sau đó, code gọi:
  1. `save_ui_xml(device_id, ...)` -> kích hoạt `get_ui_xml()` dump lần 2.
  2. `wait_for_edittext(device_id, ...)` -> kích hoạt `get_ui_xml()` dump lần 3.
- Trên dòng máy Samsung S7 (Android 8, RAM 4GB), việc dump XML liên tiếp trong thời gian ngắn (<1.5s) khiến `atx-agent` bị nghẽn socket / wedged, trả về chuỗi rỗng `""`.
- Khi `xml` rỗng, `wait_for_edittext()` không tìm thấy node nào và ném `RuntimeError("[08] Không tìm thấy EditText password")` dù trên màn hình máy thật ô mật khẩu đang hiển thị rõ ràng.

### Sự cố 2: `STOPPED: [04_add_account] Không tìm thấy: ('Thêm tài khoản', ...)`
- Khi Account Switcher đã có 7 tài khoản, nút `"Thêm tài khoản"` nằm ở vị trí đáy danh sách (bounds: `[0, 1680][1080, 1896]`).
- Điều kiện cũ `if y1 > 1650 or y2 >= 1880:` ngộ nhận nút bị khuất nên gọi `swipe(540, 1600, 540, 1100, 300)`.
- Nhưng bottom sheet đã mở hết cỡ và danh sách không thể cuộn thêm được nữa. Cú vuốt trở thành no-op, lặp lại 3 lần rồi thoát vòng lặp và báo lỗi không tìm thấy nút.

---

## 2. Giải Pháp Khắc Phục Chuẩn O(1)

### Khắc phục sự cố 1: Tái sử dụng XML & 2 tầng Fallback cho Password Field
1. Thay vì gọi `save_ui_xml(device_id, ...)`, dùng `save_xml_blob(xml_pw_check, ...)` để lưu lại XML đã dump sẵn mà không gọi thêm lệnh ADB/ATX nào.
2. Nếu `wait_for_edittext()` trả về rỗng do ATX dump chập chờn, kích hoạt fallback 1 đọc lại chính `xml_pw_check`:
   ```python
   if not pass_nodes and xml_pw_check:
       pass_nodes = list_edittext_nodes(xml_pw_check)
   ```
3. Fallback 2: Nếu cả 2 đều không có node, gán tọa độ cứng an toàn của ô Password trên Samsung S7 (1080x1920):
   ```python
   if not pass_nodes:
       pass_nodes = [{"coord": (495, 594), "x1": 138, "y1": 564, "x2": 852, "y2": 624, "rid": "", "password": True}]
   ```

### Khắc phục sự cố 2: Loại bỏ Swipe thừa & Safe-Point Upper-Third Tap
1. Khi nút `"Thêm tài khoản"` đã xuất hiện trong UI XML dump, không thực hiện `swipe` mù.
2. Áp dụng công thức Safe-Point Tap với giới hạn cứng `clamp y <= 1835`:
   ```python
   safe_x = (x1 + x2) // 2
   safe_y = min(y1 + max(1, (y2 - y1) // 3), 1835)
   log(f"   ✓ tap Add account safe row point ({safe_x}, {safe_y}) bounds={row_bounds}")
   tap(device_id, safe_x, safe_y, wait=D_MEDIUM)
   return
   ```
3. Bấm xong `return` ngay lập tức để chuyển sang màn hình nhập phương thức đăng nhập, tránh chờ modal bị miss hoặc loop cuộn.
