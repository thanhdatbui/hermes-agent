# Avatar Edit Screen Recovery, Share Card Dismiss & Launcher Filtering (2026-09-04)

## 1. Gỡ bỏ bắt buộc Manifest trong Avatar Launchers
- **Vấn đề:** `run_tiktok_upload_avatar.ps1` có `if (-not $AssignmentManifest -or -not $WorkerId) { throw ... }` ép buộc người vận hành phải tạo file manifest JSON trung gian rườm rà và dễ sai lệch.
- **Giải pháp:**
  - Thiết lập default value `$AssignmentManifest = ""` và `$WorkerId = ""` trong `run_tiktok_upload_avatar.ps1`.
  - Dùng PowerShell splatting (`@splat`) chỉ truyền `-AssignmentManifest` và `-WorkerId` khi có chỉ định rõ ràng; nếu không, chạy thẳng vào `run_tiktok_upload_batch.ps1` với `-ForceAvatarMachineList` và `-AvatarOnly`.

## 2. Lọc danh sách máy mục tiêu trong `run_tiktok_upload_batch.ps1`
- **Vấn đề:** Khi truyền `-ForceAvatarMachineList "1,8,14..."`, `$targetMachines` và `$eligibleMachines` từ inventory vẫn lấy toàn bộ 80 máy của workbook, dẫn đến việc batch launcher khởi chạy tất cả các máy thay vì chỉ chạy danh sách được chọn.
- **Giải pháp:**
  - Lọc `$targetMachines = @($targetMachines | Where-Object { $forceAvatarMachines -contains $_ })` và `$eligibleMachines = @($eligibleMachines | Where-Object { $forceAvatarMachines -contains $_ })` ngay sau khi load inventory.

## 3. Khắc phục lỗi `AVATAR_EDIT_OPEN_FAILED` trong `state_machine.py`
Khi quy trình up avatar không mở được màn hình Sửa hồ sơ, có 4 nguyên nhân gốc rễ và cơ chế recovery chuẩn:

### A. Màn hình Profile bị cuộn lửng (Scrolled Header)
- **Hiện tượng:** Sau bước `ACCOUNT_READY` quét video grid, màn hình Profile bị cuộn xuống khiến avatar circle và nút sửa bị đẩy lên đỉnh khuất ngoài viewport.
- **Xử lý:** Tự động vuốt nhẹ xuống (`adapter._adb.shell(["input", "swipe", "540", "500", "540", "1500", "300"])`) để kéo header về vị trí đỉnh trước khi tìm nút sửa hoặc tap avatar.

### B. Bẫy thẻ "Chia sẻ hồ sơ" / "Tìm Bạn bè" che khuất
- **Hiện tượng:** TikTok mở màn hình Chia sẻ hồ sơ ("Thẻ hồ sơ", "Sao chép Liên kết", "Nhấn vào nền để thay đổi phong cách", "Tìm kiếm theo tên hoặc tên người dùng") kèm bàn phím ảo Samsung IME che kín màn hình.
- **Xử lý:** Mở rộng `_dismiss_simple_close_popup` nhận diện các từ khóa `tìm bạn bè`, `chia sẻ hồ sơ`, `thẻ hồ sơ`, `sao chép liên kết`, resource-id `vst`, `vsi`, `e6w` và thực hiện chuỗi back an toàn để đóng bàn phím và thoát overlay về Profile root.

### C. Fallback Tap trực tiếp Avatar Circle
- **Hiện tượng:** Giao diện TikTok không có nút "Sửa hồ sơ" text hoặc resource-id lạ.
- **Xử lý:** Tìm node `resource-id="bm2"`, `content-desc="Ảnh hồ sơ"`, `text="Thêm ảnh"` hoặc fallback tap tâm avatar `(540, 336)` để mở bottom sheet "Chọn từ Thư viện".

### D. Mở rộng bộ nhận diện màn hình Edit trong `_wait_for_avatar_edit_screen`
- **Hiện tượng:** Khi tap avatar, TikTok mở bottom sheet ("Chọn từ Thư viện", "Chụp ảnh", "Tải ảnh lên") nhưng hàm chờ edit chỉ kiểm tra "Sửa hồ sơ" -> timeout báo `AVATAR_EDIT_OPEN_FAILED`.
- **Xử lý:** Bổ sung các text `"Chọn từ Thư viện"`, `"Tải ảnh lên"`, `"Select from gallery"`, `"Chụp ảnh"` vào `_wait_for_avatar_edit_screen` để nhận diện ngay bottom sheet làm edit surface hợp lệ.
