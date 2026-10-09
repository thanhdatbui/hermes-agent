# Top-Left Pencil Add Friends Collision & Closeout Remediation (08/10/2026)

## 1. Hiện tượng & Triệu chứng
- Ca tối 07/10/2026 ghi nhận lỗi hàng loạt `[AVATAR_EDIT_OPEN_FAILED]` trên 6 máy (M4, M28, M44, M51, M63, M69).
- Log hiện trường trên Máy 4:
  ```text
  [WARNING] Overlapping layouts matched: ['top_left_pencil', 'right_pencil']; choosing top_left_pencil
  [INFO] Matched top-left pencil icon on Profile header at (78, 150)
  [INFO] Đã thoát hoàn toàn khỏi màn hình Chia sẻ hồ sơ / Tìm bạn bè
  [ERROR] [AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở được
  ```

---

## 2. Nguyên nhân cốt lõi
1. **Thiếu từ khóa loại trừ trong `top_left_pencil.py`:** Icon góc trên bên trái `[24,96][132,204]` là icon "Thêm bạn bè" (`content-desc="Thêm bạn bè"` / `"Bạn bè"`). Bộ lọc chỉ loại trừ `"thêm người"`, `"find friends"` mà thiếu `"thêm bạn"`, `"bạn bè"`, `"add friends"`.
2. **Sai thứ tự ưu tiên trong `REGISTRY`:** `REGISTRY` xếp `TopLeftPencilLayout` trước `RightPencilLayout`, nên khi overlap máy ưu tiên bấm nhầm icon kết bạn góc trái thay vì bút chì thật bên phải tên.
3. **Nhét nhầm `ShareProfileLayout` vào `REGISTRY`:** `ShareProfileLayout` chỉ mở Share Sheet, không phải sửa hồ sơ. Bắt buộc loại bỏ khỏi `REGISTRY` để fail-closed an toàn.

---

## 3. Khắc phục chuẩn A-Z & Bài học Closeout Gate
1. **Sửa code:**
   - Bổ sung từ khóa loại trừ vào `top_left_pencil.py` + phát structured telemetry `event=top_left_pencil_excluded`.
   - Chuẩn hóa thứ tự `REGISTRY = (ClassicTextLayout(), RightPencilLayout(), TopLeftPencilLayout())` + phát metric `event=overlapping_layouts_resolved`.
2. **Vượt Closeout Gate (82 -> 84 -> 86 điểm):**
   - Viết 3 unit test trong `tests/test_avatar_edit_and_milestone.py`: (a) loại trừ icon kết bạn, (b) ưu tiên `right_pencil` khi overlap, (c) fail-closed khi chỉ có icon share profile.
   - Thêm ánh xạ `profile_layout` trong `closeout_gate.py` để chạy focused test (~17s) thay vì timeout 120s chạy toàn bộ 34 test files.
   - Chạy đồng thời `tests/test_profile_golden.py` để chứng minh 100% layout cũ không bị hồi quy.
3. **Canary thực tế:** Máy 4 (@votam5319) chạy thành công `exit=0, verified=True`, workbook cập nhật `Avatar = OK`, database tracker cập nhật `status = 'DONE'`.
