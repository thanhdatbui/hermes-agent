# CapCut Template Preview & Creation Hub Auto-Dismiss (Case 81)

## Bối cảnh & Nguyên nhân lỗi
Khi mở camera TikTok hoặc chuyển đổi chế độ camera (từ `LIVE` sang `ĐĂNG`/`TẠO`), thanh trượt chế độ dưới đáy camera có thể bị chạm nhầm hoặc trượt vào tab `MẪU` (Templates / CapCut Hub).
Khi đó, TikTok sẽ mở:
1. **Template Preview:** Video mẫu xem trước kèm nhạc và nút đỏ `"Thử mẫu này"` (`use_template` / `id/use_template`), có nút Back `<` tại top-left (`:id/bq3`).
2. **Template Creation Hub:** Màn hình các công cụ tạo mẫu CapCut (`Video mới`, `Mẫu`, `AutoCut`, `Trình chỉnh sửa ảnh`, `Phụ đề`, `AI Self`, `Tách nền`), có nút `Đóng` tại top-left (`:id/h32` / `content-desc="Đóng"`).

Các màn hình này đè lấp toàn bộ camera và che mất nút mở Media Picker / Thư viện ảnh, dẫn tới kẹt timeout tại `VIDEO_PICK` và trả về `upload_subprocess_nonzero`.

## Quy tắc xử lý chuẩn trong Codebase
1. **Nhận diện chuẩn (`_is_capcut_template_surface`):**
   - Không chỉ bắt keyword đơn lẻ; kiểm tra cả Template Preview CTA (`Thử mẫu này`, `Use this template`, `id/use_template`) và Creation Hub (`matched_tools >= 2` kèm `has_hub_title` hoặc `has_hub_nav`).
   - Luôn loại trừ nếu đã ở trong Media Picker (`_is_verified_media_picker_xml`).

2. **Dismiss đa tầng có giới hạn (`_dismiss_capcut_template_surface`):**
   - Quét nút back top-left `<` (`:id/bq3`) hoặc nút `Đóng` (`:id/h32` / `content-desc="Đóng"`) ở vùng `top <= 400`.
   - Fallback bằng `adapter.back()` có bounded `max_attempts=4`.
   - Nếu sau 4 lần dismiss mà màn hình mẫu vẫn còn -> fail-closed an toàn.

3. **Chuyển tab Camera từ LIVE an toàn:**
   - Khi phát hiện camera mở ở chế độ LIVE, chỉ định tap đích danh vào nhãn `ĐĂNG` hoặc `TẠO`.
   - Ưu tiên mở thẳng Thư viện bằng Upload Thumbnail icon (`view_bg2` hoặc visual fallback) thay vì thao tác trượt ngang thanh chế độ camera.
