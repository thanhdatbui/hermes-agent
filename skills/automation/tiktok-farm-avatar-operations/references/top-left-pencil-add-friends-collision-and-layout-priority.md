# Top-Left Pencil vs "Thêm bạn bè" Icon Collision & Profile Layout Priority

## 1. Hiện tượng & Triệu chứng (Machine 4 Tik 2 `@dinhlan24076`)
Trong quá trình chạy avatar-only runner (`run_tiktok_upload_avatar.ps1` / `tiktok_workflow`):
- Máy đăng nhập và switch vào đúng tài khoản `@dinhlan24076` trên màn hình Profile.
- Bước sang `ENSURE_AVATAR`, log cảnh báo:
  ```
  [WARNING] tiktok_workflow.profile_layouts: [PROFILE_LAYOUT] Overlapping layouts matched: ['top_left_pencil', 'right_pencil']; choosing top_left_pencil
  [INFO] tiktok_workflow.profile_layouts: [PROFILE_LAYOUT] [METRIC] event=layout_resolved layout=top_left_pencil center=(78, 150) reason=top-left pencil icon above username at bounds [24,96][132,204]
  [INFO] tiktok_workflow.state_machine: [PROFILE_EDIT] Matched top-left pencil icon on Profile header at (78, 150)
  ```
- Sau đó máy bung màn hình *"Chia sẻ hồ sơ / Tìm bạn bè"*, log ghi:
  ```
  [INFO] tiktok_workflow.state_machine: [POPUP] Đã thoát hoàn toàn khỏi màn hình Chia sẻ hồ sơ / Tìm bạn bè
  [ERROR] tiktok_workflow.state_machine: Workflow error: [AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở
  ```

---

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Thiếu từ khóa loại trừ tiếng Việt trong `TopLeftPencilLayout`:**
   - Trên TikTok Android, icon ở góc trên bên trái header thường là nút **"Thêm bạn bè"** (hình người kèm dấu `+`) hoặc icon sự kiện (Rewards `P`).
   - Thuộc tính `content-desc` của icon này là `"Thêm bạn bè"` hoặc `"Bạn bè"`.
   - Bộ lọc `is_top_left_pencil` chỉ loại trừ `("thêm người", "find friends", "quay lại", "back", "thông báo", "menu", "chia sẻ")`, hoàn toàn **bỏ sót** các chuỗi tiếng Việt thực tế: `"thêm bạn"`, `"bạn bè"`, và `"add friends"`.
   - Dẫn đến việc nút "Thêm bạn bè" bị nhận diện nhầm thành cây bút chì góc trên bên trái (`top_left_pencil`).

2. **Thứ tự ưu tiên sai trong `REGISTRY` (`profile_layouts/__init__.py`):**
   - Đăng ký cũ:
     ```python
     REGISTRY: tuple[ProfileLayout, ...] = (
         ClassicTextLayout(),
         TopLeftPencilLayout(),
         RightPencilLayout(),
         ShareProfileLayout(),  # SAI: ShareProfileLayout không được nằm trong registry
     )
     ```
   - Khi cả 2 layout cùng match (do nút Thêm bạn bè match nhầm `top_left_pencil`, trong khi cây bút chì cạnh tên match `right_pencil`):
     Hàm `resolve()` mặc định chọn `matched[0]`. Vì `TopLeftPencilLayout` đứng trước `RightPencilLayout`, hệ thống đã ưu tiên click vào icon Thêm bạn bè ở góc trái thay vì icon bút chì thật ở bên phải tên hiển thị!
   - Ngoài ra, việc đưa `ShareProfileLayout` vào `REGISTRY` vi phạm unit test hồi quy `test_find_profile_edit_button_matches_share_profile` (yêu cầu fail-closed trả về `None`).

---

## 3. Quy tắc khắc phục chuẩn (Canonical Remediation)

### A. Chuẩn hóa bộ từ khóa loại trừ trong `top_left_pencil.py`:
```python
# Bổ sung đầy đủ các biến thể tiếng Việt và tiếng Anh của nút Thêm bạn bè
if any(k in combined_desc for k in (
    "thêm người", "thêm bạn", "bạn bè", "find friends", "add friends",
    "quay lại", "back", "thông báo", "menu", "chia sẻ"
)):
    return False
```

### B. Chuẩn hóa thứ tự ưu tiên trong `profile_layouts/__init__.py`:
1. `ClassicTextLayout`: Nút chữ "Sửa hồ sơ" rõ ràng nhất (ưu tiên số 1).
2. `RightPencilLayout`: Nút bút chì bên phải tên hiển thị (bố cục chuẩn đa số nick farm hiện nay, ưu tiên số 2).
3. `TopLeftPencilLayout`: Biến thể bút chì góc trên bên trái (chỉ dùng cho một số dòng máy đặc thù khi không có `right_pencil`).
4. **LOẠI BỎ HOÀN TOÀN `ShareProfileLayout`** khỏi `REGISTRY`.

### C. Kỷ luật kiểm thử môi trường Windows (Pytest Subprocess Environment Isolation):
Khi chạy `pytest` từ Python subprocess trên máy Windows host, **BẮT BUỘC xóa `PYTHONPATH` và `PYTHONHOME`** khỏi môi trường con (`env.pop("PYTHONPATH", None)`). Nếu không, tiến trình pytest sẽ kế thừa venv của agent host dẫn đến lỗi `ImportError: cannot import name '_console_main' from '_pytest.config'` và không chạy được test suite.
