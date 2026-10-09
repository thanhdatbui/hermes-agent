# TikTok Camera Mode Tab Switching Pitfalls & Rules

## Bối cảnh & Hiện tượng
Khi mở camera upload TikTok (`[+]` create button trong `VIDEO_PICK`), thanh chuyển chế độ (bottom mode bar) ở đáy màn hình thường có các tab:
- `CAMERA` / `Máy ảnh` (tọa độ khoảng x: 217..414, y: 1805..1839, tâm ~ 315, 1820 trên màn 1080x1920)
- `TẠO` (Active/Selected mặc định trên một số build/account, x: 494..585, y ~ 1820)
- `LIVE` (x: 668..761, y ~ 1820)

## Pitfall Nghiêm trọng: Tab "TẠO" là CapCut Templates Hub
- Tab "TẠO" KHÔNG phải là camera quay chụp thông thường và KHÔNG có nút Gallery / Tải lên.
- Nếu switch nhầm sang tab "TẠO" (hoặc nếu script gặp LIVE mode rồi fallback tap `TẠO` thay vì `CAMERA`), màn hình sẽ rơi vào CapCut Templates Hub.
- Visual thumbnail scanner sẽ nhận nhầm các template thumbnail là gallery tile, tap vào mở màn hình Template Preview ("Thử mẫu này").
- Khi `_dismiss_capcut_template_surface` đóng template, app thường bị văng về Feed/Home -> Lặp lại vòng lặp `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

## Quy tắc bắt buộc trong `state_machine.py`
1. **Target Tab Camera:** Luôn luôn target `"CAMERA"`, `"Camera"`, `"Máy ảnh"`, `"ĐĂNG"`.
2. **Tuyệt đối không tap "TẠO":** CẤM tap `"TẠO"` làm đích đến khi chuyển khỏi tab LIVE hoặc khi tìm camera viewfinder.
3. **Chuyển tab từ TẠO sang CAMERA:**
   - Nếu màn hình đang ở tab "TẠO" hoặc CapCut Template Hub nhưng có thanh bottom mode bar:
   - Ưu tiên tap text `"CAMERA"` hoặc `"Máy ảnh"` qua `adapter._tap_if_found`.
   - Fallback coordinates: `adapter.tap(315, 1820)` (trên độ phân giải chuẩn 1080x1920).
   - Đợi 2s để UI settle cho viewfinder camera thật xuất hiện (shutter button + thumbnail upload ở góc).
