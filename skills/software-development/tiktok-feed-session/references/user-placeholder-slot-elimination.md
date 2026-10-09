# Slot Elimination & Fallback Label Text cho User Placeholder Switcher

## Ngữ cảnh
Khi chuyển đổi tài khoản (switcher bottom sheet) trong TikTok flow (`_find_user_placeholder_switch_options` trong `feed_swipe_smoke.py`), nếu tài khoản kẹt tên dạng placeholder (`user\d+`) hoặc display name lạ không khớp username mong đợi:
- TikTok switcher có thể hiển thị username đã đổi sang tên hiển thị (display name) thay vì handle gốc, hoặc node dạng `android.widget.Button`.

## Quy tắc thực hiện

### 1. Slot Elimination & Decoupling
- **Decoupled caller injection**: Cho phép hàm nhận tham số tùy chọn `known_other_accounts: list[str] | None = None`. Khi được truyền vào (từ caller hoặc unit test), sử dụng trực tiếp mà không cần đọc I/O từ disk.
- **Dynamic Config Discovery**: Nếu không truyền `known_other_accounts`, tìm kiếm config linh hoạt qua biến môi trường (ví dụ `os.environ.get("TAADAA_RUNTIME_ROOT", "D:/Taadaa/runtime")`) thay vì hardcode user path như `kibe`.
- **Loại trừ chính xác**: Lọc trừ các nick đã nhận diện được trong UI switcher. Các button/option còn lại sau khi loại trừ chính là ứng viên của tài khoản mong muốn.

### 2. Telemetry & Strategy Separation
- Phân biệt rõ ràng giữa chọn placeholder chuẩn (`user\d+`) và slot elimination:
  - Khi tap placeholder `user\d+`: log action `try_user_placeholder_account`, extra `strategy="placeholder"`.
  - Khi tap ứng viên qua loại trừ slot: log action `try_slot_elimination_account`, extra `strategy="slot_elimination"`.
- **Cảnh báo bẫy hàm chưa định nghĩa (NameError Trap)**:
  - Khi kiểm tra `placeholder_label` là placeholder hay slot elimination, KHÔNG gọi hàm chưa khai báo như `_looks_like_user_placeholder` nếu chưa định nghĩa.
  - Sử dụng helper đã định nghĩa hoặc inline regex: `bool(re.match(r"^user\d+$", str(val).strip()))`.

### 3. Fallback Label Text
- Trên UI Android / XML dump, element button có thể đặt text trong thuộc tính `text` hoặc `content-desc`.
- Bắt buộc fallback:
  ```python
  val = (cd or t).strip()
  UIElement(
      text=n.attrib.get("text") or val,
      content_desc=n.attrib.get("content-desc") or val,
      resource_id=n.attrib.get("resource-id", ""),
      bounds=(x1, y1, x2, y2),
      attrib=dict(n.attrib),
  )
  ```

### 4. Unit Test Verification Checklist
- Luôn duy trì test case trong `python_runner/tests/test_user_placeholder_switcher.py`:
  1. `test_find_user_placeholder_found`: Nhận diện `user\d+` truyền thống.
  2. `test_find_multiple_user_placeholders`: Danh sách nhiều placeholder `user\d+`.
  3. `test_find_user_placeholder_not_found`: Trả về rỗng khi không có placeholder và không bật slot elimination.
  4. `test_find_user_placeholder_empty_or_invalid_xml`: Khả năng chịu lỗi XML rỗng/hỏng.
  5. `test_find_user_placeholder_slot_elimination`: Lọc loại trừ dựa trên cấu hình máy/danh sách tài khoản khác.
  6. `test_slot_elimination_decoupled_known_accounts`: Kiểm tra inject trực tiếp `known_other_accounts` không phụ thuộc file config trên ổ đĩa.
  7. `test_slot_elimination_all_known_returns_empty`: Kiểm tra khi toàn bộ options trong UI đều thuộc tài khoản khác đã biết thì trả về rỗng, tránh click nhầm.
- Chạy `pytest` xác thực pass 100%.
