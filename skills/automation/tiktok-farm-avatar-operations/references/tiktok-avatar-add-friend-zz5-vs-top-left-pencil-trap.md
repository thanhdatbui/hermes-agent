# TikTok Avatar: Header Add-Friend Icon vs TopLeftPencil False Positive & Deeplink Resolution

## 1. Ngữ cảnh & Triệu chứng lỗi (Context & Failure Mode)
- **Triệu chứng**: Khi chạy luồng `ENSURE_AVATAR` trên profile tài khoản TikTok mới (Layout C / biến thể top-right avatar), `profile_layouts` nhận diện sai giao diện thành `top_left_pencil` (`TopLeftPencilLayout`).
- **Hệ quả**: Script cố gắng tap vào tọa độ `(75, 150)` ở góc trên bên trái, nhưng đây thực chất là icon **Thêm bạn bè (Add Friend)** (`resource-id="com.ss.android.ugc.trill:id/zz5"` hoặc `id/pwb`), chứ không phải cây bút chì sửa hồ sơ.
- Sau khi tap trượt, script rơi vào fallback tap vào avatar nhưng avatar lại bị bong bóng trạng thái 24h che phủ, dẫn đến lỗi:
  `[AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên`

## 2. Phân biệt phần tử XML trên Profile Header
- **Icon Thêm bạn bè (Add Friend)**:
  - Class: `android.widget.ImageView` hoặc `android.widget.Button`
  - Resource ID: `com.ss.android.ugc.trill:id/zz5` hoặc chứa `pwb`
  - Vị trí bounds: `[24,96][126,204]` hoặc `[126,96][228,204]`
  - Text/Desc: Có thể rỗng (empty) trên một số bản dựng, nhưng luôn mang resource ID `zz5` hoặc `pwb`.
- **Icon Bút chì thật (Top-Left Pencil)**:
  - Chỉ xuất hiện trên một số layout cũ khi tài khoản chưa có nút Sửa hồ sơ lớn và không có icon Thêm bạn bè ở header.

## 3. Cách khắc phục chuẩn trong `top_left_pencil.py`
Trong hàm `matches(tree: UiTree)` của `TopLeftPencilLayout`:
```python
def matches(self, tree: UiTree) -> bool:
    # 1. Loại trừ classic text layout
    if tree.has_text("sửa hồ sơ", "chỉnh sửa hồ sơ", "edit profile"):
        return False

    # 2. BẮT BUỘC: Loại trừ header có nút Thêm bạn bè (zz5 / pwb)
    if tree.has_rid("zz5", "pwb") or tree.has_text("thêm bạn", "thêm người", "find friends", "add friends"):
        return False

    # 3. Tìm candidates bút chì
    cands = self._find_pencil_candidates(tree)
    return len(cands) > 0
```

## 4. Deep-link Fallback an toàn vào màn Sửa hồ sơ
Khi profile không có nút sửa hồ sơ và không có bút chì, có thể kích hoạt intent trực tiếp:
```bash
adb shell am start -a android.intent.action.VIEW -d "snssdk1233://profile/edit" -p com.ss.android.ugc.trill
```
Hoặc:
```bash
adb shell am start -a android.intent.action.VIEW -d "aweme://user/profile/edit" -p com.ss.android.ugc.trill
```
- **Lưu ý**: Sau khi bắn intent, cần sleep 2-3 giây và kiểm tra XML xem đã xuất hiện chữ `"Thay đổi ảnh"`, `"Sửa hồ sơ"` hay `"Edit profile"` chưa trước khi tiếp tục tap mở Photo Picker.

## 5. Quy tắc điều phối Coordinator vs Worker khi sửa script lõi
- **Chống chần chừ / đổ lỗi cho User**: Khi phát hiện script của repo có bug false-positive detector, Coordinator cần chủ động phân tích diff O(1) và dispatch Worker AG Gemini (`ag-gemini-pool-3`) vá ngay lập tức thay vì đứng im báo BLOCKED.
- **Contract O(1) chuẩn**: Khai báo rõ `TASK_KIND: EDIT`, `FILE: <path>`, `FOCUSED_TEST: python -m pytest <path>::<node>`, và cặp `OLD_STRING` / `NEW_STRING` duy nhất tuyệt đối (`c == 1`).
