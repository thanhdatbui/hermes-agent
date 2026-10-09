# Root Cause & Recovery: VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED, CapCut Template Dismiss & SurfaceFlinger Protected Screencap

## 1. Hiện tượng & Triệu chứng
- **Mã lỗi:** `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Diễn biến:**
  - Quy trình đăng video (`Tiktok-video`) mở camera TikTok.
  - Camera mở ra ở chế độ LIVE hoặc xuất hiện màn hình CapCut creation template/hub (`Video mới`, `Mẫu`, `Trình chỉnh sửa ảnh`, nút `Đóng` / `h32`).
  - Hàm `_dismiss_capcut_template_surface` bấm nút thoát/back (tọa độ top-left hoặc `h32`).
  - App thoát khỏi template nhưng bị văng về màn hình Hồ sơ cá nhân (Profile) hoặc Trang chủ (Feed) thay vì giữ lại camera surface.
  - Bộ kiểm tra `_is_camera_surface_xml` phát hiện màn hình không còn là camera, lập tức trả về `False` khiến flow chuyển tiếp sang Soft Reboot.
  - Sau Soft Reboot hoặc khi tái kích hoạt recovery binding, flow bị chặn lại do handoff ledger mismatch hoặc timeout.

---

## 2. Nguyên nhân gốc rễ (Root Causes)

### 2.1. Lệch điều hướng sau khi dismiss CapCut template trong `state_machine.py`
- Khi dismiss template surface thành công, UI của TikTok trên một số thiết bị (như Samsung S7) rơi về Root tabs (Profile hoặc Feed).
- `_tap_visual_camera_upload_entry` chỉ kiểm tra `_is_camera_surface_xml(current_xml)`: nếu không còn là camera thì lập tức dừng (`return False`).
- **Giải pháp:**
  - Sau khi dismiss template, nếu `not _is_camera_surface_xml(current_xml)`, kiểm tra ngay xem có nút Tạo (+) ở thanh điều hướng dưới đáy (`_find_bounded_create_button`) hay không.
  - Nếu có nút Tạo (+), lập tức tap lại nút Tạo (+) để mở lại Camera / Media Picker trước khi kết luận thất bại.

### 2.2. Xung đột chữ ký Recovery trong `run_post.py`
- Trong hàm `_load_video_pick_recovery_binding`:
  - Tại dòng ~788: Cho phép prior run có chữ ký `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
  - Tại dòng ~873 và ~884: Handoff ledger lại kiểm tra cứng `candidate_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"` và `recapture_signature == "VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET"`.
- **Giải pháp:**
  - Khai báo tuple `valid_pick_signatures = ("VIDEO_PICK_PROFILE_VIDEO_ACTION_SHEET", "VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED")`.
  - Kiểm tra `candidate_signature in valid_pick_signatures` và `recapture_signature in valid_pick_signatures`.

### 2.3. Cạm bẫy rơi vào tab TẠO (CapCut Template Hub) & Tap nhầm Target Right (Case Máy 39 - 06/09/2026)
- **Cơ chế gây lỗi:**
  - Khi ấn nút `[+]` trên feed, TikTok có thể mở thẳng vào tab **`TẠO`** (CapCut Template Hub) hoặc tab **`LIVE`** thay vì Camera viewfinder (`CAMERA` / `Máy ảnh`).
  - Tab `TẠO` hiển thị danh sách video mẫu (Đề xuất, Bài hát lan truyền, Xu hướng), **hoàn toàn không có nút chụp và không có thumbnail tải lên**.
  - Logic cũ khi thấy LIVE tự động tap vào `"TẠO"`, hoặc khi visual fallback quét toạ độ lại ưu tiên target bên phải (`R`: `0.875 * width, 0.83 * height`).
  - Target `R` trên máy Samsung chính là nút Template / Mẫu CapCut. Khi tap trúng, TikTok mở preview mẫu -> code phát hiện template và dismiss -> văng về Home feed -> tạo vòng lặp vô tận chốt lỗi `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
- **Giải pháp khóa cứng 3 Tầng Bảo Vệ (3-Layer Hard Lock Architecture):**
  1. **Tầng 1 - Tab Normalizer Gate (Chuẩn hóa tab trước khi tap):**
     - Sau khi tap `[+]`, CẤM tìm nút Tải lên ngay. Bắt buộc gọi `_ensure_camera_viewfinder_mode`.
     - Mở rộng nhận diện Template Hub: Ngoài `selected="true"`, phải kiểm tra các text marker như `text="Mẫu"`, `text="Templates"`, `text="MẪU"`, `text="Video mới"`, `text="Đề xuất"`, `text="Bài hát lan truyền"`.
     - Ép chuyển sang tab `CAMERA` / `Máy ảnh` / `ĐĂNG` qua selector hoặc fallback tọa độ tỷ lệ độ phân giải `(int(width * 0.292), int(height * 0.948))`.
     - Nếu sau khi switch mode mà UI vẫn là Template Hub, **hủy ngay visual tap (`return False`)**, tuyệt đối không tap mù quáng.
  2. **Tầng 2 - Negative Spatial Gate & Strict Left Priority (Khoá vùng cấm tọa độ):**
     - **Negative Spatial Gate:** CẤM TUYỆT ĐỐI thuật toán visual fallback click vào bất kỳ tọa độ nào nằm trong dải `Y: 15% -> 75%` màn hình. Đây là vùng grid hiển thị các video card mẫu CapCut, click vào 100% văng app về feed.
     - **Whitelist Anchor Box:** Nút Gallery/Tải lên chỉ được phép nằm ở dải đáy `Y: 80% -> 95%`.
     - **Strict Left Priority:** Nếu cụm bên trái (`L`/`BL`: `0.145 * width, 0.82 * height` hoặc `0.11 * width, 0.95 * height`) có tín hiệu thumbnail thư viện (non-dark >= 0.20), BẮT BUỘC loại bỏ 100% target bên phải (`R`) để tránh click nhầm shortcut Template/Mẫu.
  3. **Tầng 3 - Circuit Breaker & Direct Share Intent Fallback (Bypass Camera hoàn toàn):**
     - **Circuit Breaker:** Giới hạn tối đa 2 lần tap thumbnail (`max_taps = 2`). Lần 1 thất bại -> dọn sạch, lần 2 thất bại -> `am force-stop` và đưa vào recovery có bounded retry, cấm loop vô tận kéo dài hàng tiếng.
     - **Direct Share Intent:** Khi giao diện Camera/Template bị A/B test phân mảnh nặng, kích hoạt share thẳng video qua ADB intent vào TikTok:
       ```bash
       am start -a android.intent.action.SEND -t video/mp4 --eu android.intent.extra.STREAM "content://media/external/video/media/<ID>" -p com.ss.android.ugc.trill
       ```
       (Bỏ qua 100% giao diện Camera/CapCut/Picker, nhảy thẳng vào Editor).

---

## 3. Cạm bẫy SurfaceFlinger `FB is protected: PERMISSION_DENIED` (12-byte Null Screencap)

### Triệu chứng:
- Lệnh ADB `screencap -p` hoặc `exec-out screencap -p` trả về returncode = 0, nhưng output chỉ có đúng **12 bytes null** (`b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'`).
- `PIL.Image.open()` ném ngoại lệ `UnidentifiedImageError: cannot identify image file`.
- Logcat xuất hiện cảnh báo: `SurfaceFlinger: FB is protected: PERMISSION_DENIED`.

### Bản chất:
- Khi TikTok đang mở camera surface hoặc hiển thị SurfaceView có overlay bảo mật / DRM video playback, Android Framebuffer chuyển sang chế độ protected. Lệnh screencap của ADB shell không đủ quyền đọc trực tiếp frame buffer phần cứng này.
- Khiến các hàm capture screenshot (`_capture_video_pick_surface`) lưu file rác 12 bytes, dẫn tới `after is None` hoặc crash khi phân tích pixel.

### Nguyên tắc xử lý:
1. **Kiểm tra size screenshot:** Luôn kiểm tra `path.stat().st_size > 100` và header byte PNG (`b'\x89PNG'`) trước khi chuyển cho PIL đọc. Tránh crash không bắt được.
2. **Không cố screencap khi camera đang protected:** Dựa vào UIAutomator XML hierarchy (qua port ATX 7912 `/dump/hierarchy` hoặc fallback ADB dump) vì XML hierarchy vẫn đọc được cấu trúc các node UI (`video_record_new_scene_root`, `TẠO`, `ĐĂNG`, `Đóng`).
3. **Giải phóng protected surface khi chụp ảnh proof:** Đóng ứng dụng TikTok về Home (`adb shell am force-stop com.ss.android.ugc.trill && adb shell input keyevent 3`) trước khi gọi screencap để thu thập ảnh bằng chứng sạch.
