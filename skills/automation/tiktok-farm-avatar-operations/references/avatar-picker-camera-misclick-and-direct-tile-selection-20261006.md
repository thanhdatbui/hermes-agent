# Avatar Picker Camera Misclick & Direct Recent Tile Selection (2026-10-06)

## 1. Hiện tượng & Triệu chứng lỗi (Failure Signature)
Khi chạy runner upload avatar (`-AvatarOnly` / `--avatar-smoke`):
- Log ghi nhận:
  ```
  [INFO] tiktok_workflow.state_machine: [ENSURE_AVATAR] Đã mở album ảnh: Ảnh
  [ERROR] tiktok_workflow.state_machine: [AVATAR_PICKER_NO_MATCH] ENSURE_AVATAR: Avatar picker không có tile ảnh nào
  ```
- File chụp màn hình lỗi `avatar-picker-no-match.png` hiển thị màn hình đen kịt với popup hệ thống:
  ```
  Cảnh báo: Máy ảnh lỗi.
  ```

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Thừa thãi mở Dropdown Album:**
   - Trong luồng chuẩn (`COMPAT-AVATAR-007` & `COMPAT-AVATAR-011`), media gallery được dọn sạch trước khi đẩy 1 file avatar duy nhất vào `/sdcard/Pictures/` và quét MediaStore.
   - Khi TikTok photo picker mở ra, tab mặc định là "Gần đây" (Recent) đã hiển thị ngay ô ảnh avatar vừa push ở vị trí đầu tiên.
   - Code cũ không kiểm tra xem lưới ảnh hiện tại đã có candidate hay chưa, mà **mặc định luôn tap vào "Gần đây" để xổ menu chọn album**.
2. **Khớp nhầm nút "Chụp ảnh" (Camera):**
   - Danh sách nhãn album ảnh chứa `photo_album_labels = ("Pictures", "Camera", "Hình ảnh", "Images", "Ảnh")`.
   - Hàm tìm album sử dụng `adapter._tap_if_found(album_xml, text_contains=label)`.
   - Trên giao diện TikTok tiếng Việt, nút mở Camera hệ thống có text là **"Chụp ảnh"**.
   - Chuỗi `"Ảnh"` trong `photo_album_labels` đã khớp với `"Chụp ảnh"` qua `text_contains="Ảnh"`.
   - Kết quả: Thay vì mở thư mục ảnh, script bấm nhầm vào nút Camera hệ thống $\rightarrow$ Camera bị lỗi trên máy farm/ảo $\rightarrow$ Màn hình đen $\rightarrow$ Không có tile ảnh nào $\rightarrow$ Văng `AVATAR_PICKER_NO_MATCH`.

## 3. Giải pháp chuẩn hóa (Fixed Pattern)
Trong `_select_avatar_from_download` (`scripts/tiktok_workflow/state_machine.py`):
1. **Kiểm tra Candidate trước khi mở Menu:**
   - Ngay khi picker mở (`xml_text`), gọi `self._avatar_picker_candidates(xml_text)`.
   - Nếu đã có candidate (`media_type in ("image", "unknown")`), **chọn thẳng candidate đó** mà không cần mở dropdown album.
2. **Loại bỏ Camera & cấm `text_contains="Ảnh"`:**
   - Bỏ `"Camera"` khỏi danh sách `photo_album_labels`.
   - Khi duyệt label `"Ảnh"`, bắt buộc so khớp chính xác (`text="Ảnh"`), cấm dùng `text_contains="Ảnh"` để không bao giờ chạm vào nút "Chụp ảnh".
3. **Cập nhật Test Regression:**
   - Giữ vững `test_avatar_edit_and_milestone.py` và `test_tiktok_workflow -k avatar_picker` (pass 100%).
