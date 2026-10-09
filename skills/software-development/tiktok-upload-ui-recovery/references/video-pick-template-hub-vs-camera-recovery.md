# Video Pick: Template Hub vs Camera Viewfinder Recovery (VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED)

## 1. Triệu chứng
- Mã lỗi: `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- Log xuất hiện chuỗi cảnh báo:
  - `[CAMERA] Template surface opened instead of media picker; dismissing template surface`
  - `[CAPCUT_TEMPLATE] Tapping top back/close button at (84, ...)`
  - `Sau khi dismiss template màn hình không còn là camera surface; dừng tap alternative thumbnail để luồng ngoài định hướng lại`

## 2. Nguyên nhân cốt lõi (Root Cause)
1. **Giao diện thanh Mode dưới đáy sau khi ấn [+]**:
   - TikTok trên Samsung / các build mới có thanh mode: `CAMERA` (x ~ 315) | `TẠO` (x ~ 540) | `LIVE` (x ~ 715) tại y ~ 1820 (màn 1080x1920).
   - Tab **"TẠO"** là **CapCut Templates Hub** (chứa danh sách video mẫu, video card CapCut: "Đề xuất", "Bài hát lan truyền", "Xu hướng"). Tab này **KHÔNG CÓ** nút chụp (shutter) và **KHÔNG CÓ** nút Tải lên/Gallery.
2. **Sai lệch switch mode và visual fallback:**
   - Khi TikTok mở ở chế độ `LIVE` hoặc mở mặc định vào `TẠO`, code cũ switch sang tab "TẠO" thay vì "CAMERA" / "Máy ảnh" / "ĐĂNG".
   - Code fallback visual thumbnail ưu tiên tọa độ bên phải `R` `(945, 1593)` trước bên trái `L` `(156, 1574)`.
   - Khi tap vào `R` trong Template Hub hoặc Camera, TikTok mở Template preview. Logic `_dismiss_capcut_template_surface` back ra đẩy văng TikTok về Home Feed (`Trang chủ`), làm vòng lặp recovery cạn số lần thử -> `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## 3. Quy chuẩn Khắc phục (Scope Lock trong StateMachine)
1. **Chuẩn hóa hàm `_ensure_camera_viewfinder_mode`**:
   - Nhận diện khi đang ở `LIVE` (text 'Phát LIVE', 'Trung tâm LIVE', 'LIVE') HOẶC ở `Template Hub` (`_is_capcut_template_surface(xml_text)` hoặc node `text="TẠO"` có `selected="true"`).
   - Chuyển sang tab đích theo thứ tự nhãn: `("CAMERA", "Camera", "Máy ảnh", "ĐĂNG")`.
   - Kiểm tra an toàn duck-typing `getattr(adapter, "_tap_if_found", None)`. Fallback tọa độ tab `(315, 1820)` chỉ kích hoạt trên device thật (`hasattr(adapter, "serial")`) để không gây lệch tap counter trong `MockAdapter` của unit test suite.
2. **Đảo thứ tự ưu tiên Visual Thumbnail Candidates**:
   - Trên camera viewfinder thật của Samsung, thumbnail album nằm ở góc dưới bên trái (`L`/`BL`) với tỷ lệ non-dark pixel rất cao (~95%), trong khi bên phải (`R`) là nút CapCut Template shortcut.
   - Luôn sắp xếp danh sách `left_targets` (`L`, `BL`) lên trước `right_targets` (`R`).
3. **Chống văng về feed sau khi dismiss Template**:
   - Nếu sau khi dismiss template mà màn hình rơi về Home Feed (`not _is_camera_surface_xml`), tự động tìm `_find_bounded_create_button` để tap lại dấu `+` vào lại camera thay vì fail-closed ngay lập tức.
