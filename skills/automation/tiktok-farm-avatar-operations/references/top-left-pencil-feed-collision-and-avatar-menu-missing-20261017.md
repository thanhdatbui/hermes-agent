# Top-Left Pencil Feed Collision & Avatar Menu Missing Error (2026-10-17)

## 1. Triệu Chứng Hiện Trường
- Khi chạy runner upload avatar độc lập (`run_tiktok_upload_avatar.ps1 -Tik <N> -ForceAvatarMachineList "<M>"`), quy trình chạy đến bước `ENSURE_AVATAR` thì crash với mã lỗi:
  ```text
  [ERROR] tiktok_workflow.state_machine: Handler workflow error (attempt 1): [AVATAR_UPLOAD_MENU_MISSING] ENSURE_AVATAR: Không tìm thấy Tải ảnh lên
  ```
- File dump XML ghi lại hiện trường lúc lỗi (`~/AppData/Local/Temp/avatar_menu_dump.xml`) cho thấy package đang hiển thị trên thiết bị là:
  ```xml
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.sec.android.app.launcher" ... bounds="[0,0][1080,1920]">
  ```
  Tức là thiết bị đã bị văng hoàn toàn về Samsung Home Launcher, nhưng state machine vẫn cố tap `(540, 400)` trên màn hình Home để tìm nút "Tải ảnh lên".

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)
1. **Va Chạm Bút Chì Góc Trên Trái (Top-Left Pencil Collision)**:
   - Module `scripts/tiktok_workflow/profile_layouts/top_left_pencil.py` dùng class `TopLeftPencilLayout` để phát hiện icon bút chì Sửa hồ sơ ở header.
   - Bounding box được nới lỏng quá rộng: `0 <= n.l <= 45` và `w, h <= 170`.
   - Khi TikTok chuyển trạng thái từ Feed sang Profile (hoặc khi Feed chưa kịp đóng hết), icon ở góc trên bên trái màn hình Feed (icon LIVE / Camera / Tìm bạn `[0,75][168,243]` hoặc `[24,96][126,204]`) có `text=""` và `desc=""` trùng khớp với điều kiện bounding box này.
2. **Sai Lầm Điều Hướng Gây Văng App**:
   - `resolve(xml_text)` nhận định nhầm màn hình Feed là `top_left_pencil` với tọa độ tâm `(75, 150)` hoặc `(84, 159)`.
   - Lệnh `adapter.tap(*edit_button["center"])` bấm trúng icon LIVE / Camera trên Feed, dẫn đến app bị mở màn hình ngoài hoặc crash/văng về Launcher.
   - Khi văng về Launcher, hàm `_wait_for_avatar_edit_screen` không nhận diện được màn hình chỉnh sửa, sau đó chuyển sang fallback tap `(540, 400)` trên màn hình Launcher Samsung và văng ngoại lệ `[AVATAR_UPLOAD_MENU_MISSING]`.

---

## 3. Giải Pháp Kỹ Thuật (Fix Contract O(1))
1. **Thắt chặt Bounding Box trong `top_left_pencil.py`**:
   - Khôi phục giới hạn kích thước chặt chẽ: `10 <= n.l <= 45`, `70 <= n.t <= 130`, `50 <= n.w <= 130`, `50 <= n.h <= 130`.
   - Loại trừ hoàn toàn node ở `n.l == 0` (icon mép sát viền trái của Feed header).
2. **Bổ sung Feed Surface Guard**:
   - Chặn khớp layout nếu màn hình chứa các chỉ báo video feed:
     ```python
     if tree.has_rid("long_press_layout") or tree.has_text("đề xuất", "for you"):
         logger.debug("[PROFILE_LAYOUT] [METRIC] event=top_left_pencil_excluded reason=feed_surface")
         return False
     ```
3. **Kiểm Chứng Focused Test**:
   - Chạy kiểm thử đơn vị:
     ```bash
     python -m pytest tests/test_avatar_edit_and_milestone.py -q
     ```
   - Xác nhận toàn bộ 39 tests pass và không có regression trên các layout profile khác.
