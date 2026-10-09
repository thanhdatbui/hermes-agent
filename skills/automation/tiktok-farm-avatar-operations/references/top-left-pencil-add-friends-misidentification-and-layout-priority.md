# Pitfall: Top-Left Pencil Misidentifies "Thêm bạn bè" (Add Friends) & Layout Registry Priority

## 1. Hiện tượng & Triệu chứng
Khi chạy avatar-only runner (`run_tiktok_upload_avatar.ps1` hoặc `tiktok_workflow` với `--avatar-smoke`), tiến trình báo lỗi fail-closed:
`[AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở`

Kiểm tra `execution.log` thấy:
```
[WARNING] tiktok_workflow.profile_layouts: [PROFILE_LAYOUT] Overlapping layouts matched: ['top_left_pencil', 'right_pencil']; choosing top_left_pencil
[INFO] tiktok_workflow.state_machine: [PROFILE_EDIT] Matched top-left pencil icon on Profile header at (78, 150)
[INFO] tiktok_workflow.state_machine: [POPUP] Đã thoát hoàn toàn khỏi màn hình Chia sẻ hồ sơ / Tìm bạn bè
[INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Các nhánh profile không mở; thử fallback deep-link cuối
[ERROR] tiktok_workflow.state_machine: Workflow error: [AVATAR_EDIT_OPEN_FAILED] ENSURE_AVATAR: Màn Sửa hồ sơ không mở
```

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Thiếu từ khóa loại trừ tiếng Việt trong `TopLeftPencilLayout`:**
   - Trên nhiều phiên bản TikTok của Samsung Galaxy S7 (như Máy 4), nút sửa hồ sơ thật là `RightPencilLayout` (nút icon cây bút chì nằm ngay bên phải tên hiển thị).
   - Ở góc trên bên trái (`top-left`, bounds `[24,96][132,204]`, center `(78, 150)`) là icon **"Thêm bạn bè"** (Add friends).
   - Hàm `_find_pencil_candidates` trong `top_left_pencil.py` kiểm tra `combined_desc`:
     ```python
     if any(k in combined_desc for k in ("thêm người", "find friends", "quay lại", "back", "thông báo", "menu", "chia sẻ")):
         return False
     ```
     Danh sách loại trừ có `"thêm người"` nhưng **thiếu** `"thêm bạn"`, `"bạn bè"`, và `"add friends"`. Do đó, node "Thêm bạn bè" lọt qua bộ lọc và bị nhận diện nhầm thành icon cây bút chì!

2. **Thứ tự ưu tiên sai trong `REGISTRY`:**
   - Trong `profile_layouts/__init__.py`:
     ```python
     REGISTRY: tuple[ProfileLayout, ...] = (
         ClassicTextLayout(),
         TopLeftPencilLayout(),
         RightPencilLayout(),
     )
     ```
   - Khi cả `TopLeftPencilLayout` và `RightPencilLayout` đều match trên cùng một màn hình, cơ chế overlap resolution chọn `matched[0]`. Vì `top_left_pencil` đứng trước `right_pencil`, nó đè lên nút sửa hồ sơ thật, dẫn đến việc tap nhầm vào icon Thêm bạn bè mở ra màn hình "Chia sẻ hồ sơ / Tìm bạn bè"!

3. **`ShareProfileLayout` không được nằm trong `REGISTRY`:**
   - `ShareProfileLayout` chỉ dùng cho kiểm tra đặc thù, nếu cho vào `REGISTRY` sẽ làm fail 2 bài unit test trong `test_avatar_edit_and_milestone.py` (`test_find_profile_edit_button_matches_share_profile` và `test_layout_registry_fails_closed_on_unresolved_layout[share_profile]`).

## 3. Quy tắc khắc phục chuẩn (Fix Contract)
1. **Cập nhật `top_left_pencil.py`:**
   Bổ sung đầy đủ các biến thể từ khóa kết bạn vào tuple loại trừ:
   ```python
   if any(k in combined_desc for k in ("thêm người", "thêm bạn", "bạn bè", "find friends", "add friends", "quay lại", "back", "thông báo", "menu", "chia sẻ")):
       return False
   ```

2. **Cập nhật `__init__.py`:**
   Đưa `RightPencilLayout()` lên trước `TopLeftPencilLayout()`, và loại bỏ `ShareProfileLayout()` khỏi `REGISTRY`:
   ```python
   REGISTRY: tuple[ProfileLayout, ...] = (
       ClassicTextLayout(),
       RightPencilLayout(),
       TopLeftPencilLayout(),
   )
   ```

3. **Regression Test Gate bắt buộc (34/34 PASS):**
   Chạy offline pytest độc lập:
   ```bash
   python D:/Taadaa/run_unit_tests.py
   # hoặc:
   D:/CodexRuntime/tiktok-video/venv-core024/Scripts/pytest.exe D:/Taadaa/Tiktok-video/tests/test_avatar_edit_and_milestone.py -q
   ```
   Bắt buộc xác nhận 34/34 tests passed (exit code 0) trước khi đẩy lên thiết bị thật.

4. **Lưu ý Selector Guard Hook (Rule R2):**
   Khi commit thay đổi trong `profile_layouts/`, hook `guard_selector.py` yêu cầu kèm theo:
   - Cập nhật tài liệu `docs/farm-automation-cases.md`.
   - Bổ sung golden dump XML tương ứng vào `tests/golden/profile/`.
