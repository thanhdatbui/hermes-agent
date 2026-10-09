# TikTok Camera Mode Tab Switching Pitfalls & Rules

## Bối cảnh & Hiện tượng
Khi mở camera upload TikTok (`[+]` create button), thanh chuyển chế độ (bottom mode bar) ở đáy màn hình thường có các tab:
- `CAMERA` / `Máy ảnh` (tọa độ khoảng x: 217..414, y: 1805..1839, tâm ~ 315, 1820 trên màn 1080x1920)
- `TẠO` (Active/Selected mặc định trên một số build/account, x: 494..585, y ~ 1820)
- `LIVE` (x: 668..761, y ~ 1820)

## Pitfall Nghiêm trọng: Tab "TẠO" là CapCut Templates Hub
- Tab "TẠO" KHÔNG phải là camera quay chụp thông thường và KHÔNG có nút Gallery / Tải lên.
- Nếu switch nhầm sang tab "TẠO" (hoặc nếu script gặp LIVE mode rồi fallback tap `TẠO` thay vì `CAMERA`), màn hình sẽ rơi vào CapCut Templates Hub.
- Visual thumbnail scanner sẽ nhận nhầm các template thumbnail là gallery tile, tap vào mở màn hình Template Preview ("Thử mẫu này").
- Khi `_dismiss_capcut_template_surface` đóng template, app thường bị văng về Feed/Home -> Lặp lại vòng lặp `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## Quy tắc bắt buộc
1. **Target Tab Camera:** Luôn luôn target `"CAMERA"`, `"Camera"`, `"Máy ảnh"`, `"ĐĂNG"`.
2. **Tuyệt đối không tap "TẠO":** CẤM tap `"TẠO"` làm đích đến khi chuyển khỏi tab LIVE hoặc khi tìm camera viewfinder.
3. **Chuyển tab từ TẠO sang CAMERA:**
   - Nếu màn hình đang ở tab "TẠO" hoặc CapCut Template Hub nhưng có thanh bottom mode bar:
   - Ưu tiên tap text `"CAMERA"` hoặc `"Máy ảnh"` qua `adapter._tap_if_found`.
   - Fallback coordinates: `adapter.tap(315, 1820)` (trên độ phân giải chuẩn 1080x1920).
   - Đợi 2s để UI settle cho viewfinder camera thật xuất hiện (shutter button + thumbnail upload ở góc).

## Patch Contract & Mock Compatibility Pitfalls
1. **Legacy Bug Pattern trong State Machine:**
   - Cả `_tap_visual_camera_upload_entry` và state `VIDEO_PICK` trước đây có đoạn code lỗi:
     `if not adapter._tap_if_found(xml_text, text="ĐĂNG"): adapter._tap_if_found(xml_text, text="TẠO")`
   - Đoạn fallback tap "TẠO" này trực tiếp vi phạm quy tắc, đẩy UI từ LIVE sang CapCut templates hub.
   - Patch Contract chuẩn: Phát hiện `LIVE` hoặc `('TẠO', 'Mẫu')` đi kèm `('CAMERA', 'Máy ảnh')`, lặp qua target list `("CAMERA", "Camera", "Máy ảnh", "ĐĂNG")`. Nếu không tap được bằng selector, fallback tap tọa độ `(315, 1820)`.

2. **MockAdapter Unit Test Pitfall:**
   - Khi gọi `adapter._tap_if_found(...)` trong `state_machine.py`, lưu ý nhiều mock classes trong `tests/test_tiktok_workflow.py` (`MockAdapter`, `CameraSurface`, `StubbornCameraSurface`) chỉ định nghĩa `dump_ui` và `tap`, KHÔNG có `_tap_if_found`.
   - Cần kiểm tra an toàn `getattr(adapter, "_tap_if_found", None)` hoặc dùng helper tương thích để tránh `AttributeError` khi chạy test suite.

3. **Canary Verification Evidence:**
   - Đã verify thành công trên máy 39 (serial `ce0117113818c4d30c`):
     Script phát hiện `[VIDEO_PICK] Non-camera mode detected (LIVE/TẠO); switching to CAMERA/Máy ảnh/ĐĂNG tab`, chuyển sang CAMERA mode, mở thumbnail và vào upload picker screen thành công.

