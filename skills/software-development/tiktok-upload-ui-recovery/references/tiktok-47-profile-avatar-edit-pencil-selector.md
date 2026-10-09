# TikTok 47.x Profile Avatar Edit & Top-Left Pencil Selector Fix

## Triệu chứng
Khi chạy runner upload hoặc `-AvatarOnly`, bot dừng hoặc kết thúc mà không đổi được avatar:
```
[ENSURE_AVATAR] Thử tap vào Ảnh hồ sơ / Avatar circle trên Profile
[ENSURE_AVATAR] UI cũ không mở; thử bút chì của UI mới
[ENSURE_AVATAR] Các nhánh profile không mở; thử fallback deep-link cuối
[ENSURE_AVATAR] TikTok báo hoạt động sửa avatar không có sẵn trên profile phụ; safe-skip để tiếp tục flow
avatar_status: SKIPPED_AVATAR_EDIT_UNAVAILABLE
```

## Nguyên nhân gốc rễ
1. **Bẫy vòng tròn Avatar**:
   - Trên TikTok phiên bản mới (47.x), bấm vào vòng tròn avatar hoặc icon dấu cộng nhỏ ở góc dưới avatar (bounds `[708,300][1080,636]` hoặc center `(894, 468)` / `(540, 336)`) sẽ mở màn hình **"Thêm vào Nhật ký" (Story Media Picker)**, hoàn toàn không mở màn "Sửa hồ sơ".
2. **Selector Bút Chì góc trên bên trái**:
   - Trên TikTok 47.x (Samsung S7 màn hình 1080x1920), nút mở "Sửa hồ sơ" nằm ở **góc trên cùng bên trái của Profile Header**:
     - Class: `android.widget.ImageView`
     - Bounds: `[24,96][126,204]`
     - Center: `(75, 150)` (bên trái nút mã QR `[126,96][228,204]`).
3. **Bẫy điều kiện Bounds quá hẹp trong codebase cũ**:
   - Hàm `_find_new_profile_pencil` cũ yêu cầu `0 <= left <= 50` và `80 <= top <= 120`, nhưng lại nằm ở nhánh fallback sau khi đã tap trúng vòng tròn avatar (lúc này màn hình đã chuyển sang Story picker nên XML không còn là Profile root nữa).

## Giải pháp đã triển khai & Kiểm chứng
Trong `scripts/tiktok_workflow/state_machine.py`:
1. Mở rộng biên độ bounds cho `_find_new_profile_pencil`:
   ```python
   if 0 <= left <= 100 and 60 <= top <= 220 and 60 <= (right - left) <= 160 and 60 <= (bottom - top) <= 160:
       return ((left + right) // 2, (top + bottom) // 2)
   ```
2. Đưa kiểm tra bút chì lên đầu hàm `_find_profile_edit_button`:
   ```python
   pencil = StateMachine._find_new_profile_pencil(xml_text)
   if pencil:
       return {"center": pencil}
   ```
3. Sau khi tap vào tọa độ `(75, 150)`, app mở ngay màn hình `Sửa hồ sơ` với nút `Thay đổi ảnh` (`[396,552][683,609]`).
4. Runner mở picker thư viện, chọn ảnh, cắt crop và lưu ảnh đại diện thành công đạt `verified=True`.

## Cảnh báo hồi quy quan trọng (Case 103):
- Tuyệt đối KHÔNG gỡ bỏ `_find_new_profile_pencil` khỏi `_find_profile_edit_button`.
- CẤM dùng layout detector `right_pencil_button` với vùng `[750, 450][950, 650]` vì trên TikTok mới nó sẽ match nhầm nút dấu cộng "Tạo một Nhật ký" (Story) tại `[931,499][1080,636]`.
- Chi tiết xem: `references/avatar-profile-pencil-story-trap-and-scrolled-grid-case103.md`.
