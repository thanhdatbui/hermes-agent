# Pitfall: Visual Camera Upload Target Inversion (VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)

## Triệu chứng & Bối cảnh
- **Lỗi:** `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Thiết bị thường gặp:** Máy Samsung / camera-first (ví dụ Máy 39 `ce0117113818c4d30c`, Máy 45).
- **Hiện trường:** TikTok mở Camera sau khi tap `[+]`, nhưng không vào được thư viện ảnh/video, sau đó bị văng về Home feed (`Trang chủ`) và treo 50s timeout.

## Cơ chế lỗi cốt lõi (Root Cause)
1. **Camera-first XML thiếu node:** Màn hình Camera TikTok không hiển thị các resource ID quen thuộc (`view_bg2`, `cwr`, `upload_work`) trong XML uiautomator. Flow chuyển sang `_tap_visual_camera_upload_entry`.
2. **Visual target ordering:** Logic visual quét độ sáng ở 2 vùng:
   - `R` (bên phải nút chụp: `width * 0.875, height * 0.83`)
   - `L` (bên trái nút chụp: `width * 0.145, height * 0.82`)
   Khi append theo thứ tự mặc định `R` trước `L`, script sẽ tap vào `R` trước.
3. **Nhầm lẫn giữa Gallery Upload và CapCut Template:**
   - Trên các build Samsung hiện tại, nút bên phải nút chụp là nút mở **CapCut Template / Mẫu**, còn thumbnail thư viện nằm ở bên trái (`L`).
   - Tọa độ `R` mở ra giao diện CapCut Template Hub/Preview.
4. **Dismiss template làm thoát Camera:**
   - Khi phát hiện template, `_dismiss_capcut_template_surface` bấm nút close/back ở `(84, 150)`.
   - Hành động đóng template này đẩy TikTok thoát hẳn khỏi Camera và quay về **Home Feed** (`Trang chủ`).
   - `_tap_visual_camera_upload_entry` thấy không còn ở Camera nên dừng retry thumbnail và trả về `False`.
   - Vòng lặp ngoài chờ picker trong 50s trên Home feed, fail attempt 1, gọi bounded create-entry recovery. Recovery lại bấm `[+]` -> lặp lại chu kỳ -> soft reboot timeout -> fail-closed `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## Quy tắc xử lý & Khắc phục
1. **Ưu tiên target L trước R trong visual camera entry:**
   - Đảo thứ tự `valid_targets`: quét và ưu tiên `L` (hoặc `BL`) trước `R`, hoặc sắp xếp theo độ tương phản sáng (`non_dark_l` thường đạt > 90% khi có thumbnail media vừa push).
2. **Loại trừ target gây mở template:**
   - Khi một target tap vào dẫn đến `_is_capcut_template_surface`, sau khi dismiss phải loại bỏ vĩnh viễn tọa độ đó khỏi `valid_targets` của phiên chạy.
3. **Phát hiện rơi về Home feed sau dismiss:**
   - Nếu sau khi dismiss template mà màn hình rơi về `_is_tiktok_root_surface` (Home feed), không chờ vô ích mà re-enter create entry ngay với target `L`.
