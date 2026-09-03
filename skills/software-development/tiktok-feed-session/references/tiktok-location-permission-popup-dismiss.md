# TikTok Location Permission Popup Dismiss Pattern

## Bối cảnh & Hiện tượng (2026-08-25, Máy 42)
Trong quá trình lướt feed hoặc khi điều hướng về tab Profile để verify tài khoản, TikTok có thể hiển thị popup hệ thống/in-app yêu cầu bật quyền vị trí thiết bị:
- **Tiêu đề / Nội dung**: *"Xem nội dung phù hợp và địa điểm lân cận"*, *"Mở cài đặt thiết bị của bạn và truy cập Vị trí > Trong khi sử dụng ứng dụng. Bạn có thể tắt bất cứ lúc nào."*
- **Các nút bấm**:
  - `Hủy` (hoặc `Cancel` / `Không phải bây giờ` / `Not now`, resource-id `android:id/button3`)
  - `Mở cài đặt` (hoặc `Cài đặt` / `Settings` / `Open settings`, resource-id `android:id/button1`)

## Triệu chứng lỗi khi chưa xử lý
- Popup che khuất toàn bộ màn hình khiến flow không tìm thấy tab điều hướng Profile (`Hồ sơ`) ở thanh bottom navigation.
- Gây lỗi dừng phiên: `profile verification navigation-failed: navigation target profile not found in XML` hoặc `manual-needed:popup`.

## Quy tắc xử lý chuẩn (Farm Policy)
- **Quy tắc an toàn**: Farm TikTok **tuyệt đối không cấp quyền Location** cho TikTok để tránh lộ vị trí thực tế của farm / thiết bị.
- **Cách xử lý**: Popup này là dạng **benign popup (cho phép tự động đóng)**. Hệ thống **BẮT BUỘC bấm nút "Hủy"** để đóng popup ngay lập tức, đưa màn hình trở lại Feed / Profile, không được xem là `manual-needed:popup` làm dừng phiên nuôi acc.

## 4 Tầng Xử lý Bắt buộc trong Consumer (`tiktok-luot nuoi acc`)

### 1. Phục hồi tại bước Điều hướng đáy màn hình (`tap_navigation_target` trong `calibrate_screens.py`)
- **Nguyên nhân gốc máy 42 bị lại**: Popup vị trí xuất hiện ngay khi vừa kết thúc swipe loop và bắt đầu chuyển tab sang `Hồ sơ`. Hàm `tap_navigation_target` trước đây chỉ quét text tab; khi không thấy thì chỉ gửi phím `KEYCODE_BACK`.
- **Pitfall `KEYCODE_BACK` không đóng được System Dialog**: Đối với dialog modal yêu cầu cấp quyền vị trí, bấm phím `BACK` không làm tắt dialog (bắt buộc phải tap trúng nút "Hủy").
- **Fix**: Trong `tap_navigation_target`, khi `point is None`, trước khi gửi phím `BACK` phải gọi `find_matching_handler(xml_text, "")` từ registry để tự động tap nút "Hủy", sau đó recapture XML và tìm lại tab điều hướng.

### 2. Blind Popup Rule trong Feed Swipe Loop (`GEMPHONEFARM_BLIND_POPUP_RULES` trong `feed_swipe_smoke.py`)
Đăng ký rule để bắt popup và tap nút "Hủy" ngay trong chu kỳ vuốt video, baseline và preflight:
```python
GemPhoneFarmBlindPopupRule(
    # Popup yêu cầu cấp quyền vị trí ("Xem nội dung phù hợp và địa điểm lân cận") — bấm Hủy
    "location_permission_cancel",
    '//node[@text="Xem nội dung phù hợp và địa điểm lân cận" or @text="See nearby content" or contains(@text, "địa điểm lân cận") or contains(@text, "truy cập Vị trí")]',
    "tap",
    '//node[@text="Hủy" or @content-desc="Hủy" or @text="Cancel" or @content-desc="Cancel" or @resource-id="android:id/button3"]',
    loop=True,
),
```

### 3. Benign Popup Registry Handler (`_dismiss_location_prompt` trong `benign_popup_registry.py`)
- **Pitfall `UIElement.bounds` vs `parse_bounds`**: Trong `automation_core.ui`, `UIElement.bounds` đã là tuple `(left, top, right, bottom)` và `UIElement.center` là tuple `(cx, cy)`. Nếu truyền `el.bounds` vào `parse_bounds(value)` (hàm mong đợi string định dạng `"[x1,y1][x2,y2]"`) sẽ gây `TypeError: expected string or bytes-like object, got 'tuple'`. Ưu tiên lấy trực tiếp `el.center`.
- **Pitfall `DeviceContext` không có `ctx.tap`**: Đối tượng `ctx` (`DeviceContext`) trong runner chứa `ctx.adb` (gọi `ctx.adb.shell(["input", "tap", str(cx), str(cy)])`), không có sẵn phương thức `ctx.tap()`. Handler dismiss bắt buộc phải hỗ trợ chuỗi fallback đa kênh: `ctx.tap` ➔ `ctx.adb.shell(["input", "tap", ...])` ➔ `ctx.actions.tap` ➔ `send_device_back_key`.

```python
def _dismiss_location_prompt(ctx: Any) -> Any:
    from .benign_popup import PopupDismissResult, send_device_back_key
    before_attempt = {"screen": "location_permission_popup"}
    action_performed = False
    try:
        xml_tree = None
        if hasattr(ctx, "dump_hierarchy"):
            try:
                xml_str = ctx.dump_hierarchy()
                if xml_str:
                    from automation_core.ui import parse_xml
                    xml_tree = parse_xml(xml_str)
            except Exception:
                pass
        
        tap_target = None
        if xml_tree is not None:
            from automation_core.ui import iter_elements
            for el in iter_elements(xml_tree):
                text = (getattr(el, "text", "") or (el.attrib.get("text") if hasattr(el, "attrib") else "") or "").strip().lower()
                desc = (getattr(el, "content_desc", "") or (el.attrib.get("content-desc") if hasattr(el, "attrib") else "") or "").strip().lower()
                res_id = (getattr(el, "resource_id", "") or (el.attrib.get("resource-id") if hasattr(el, "attrib") else "") or "").strip().lower()
                if text in {"hủy", "cancel", "không phải bây giờ", "not now"} or desc in {"hủy", "cancel"} or "button3" in res_id or "cancel" in res_id:
                    if getattr(el, "center", None):
                        tap_target = el.center
                        break
                    bounds_val = getattr(el, "bounds", None) or (el.attrib.get("bounds") if hasattr(el, "attrib") else None)
                    if isinstance(bounds_val, (tuple, list)) and len(bounds_val) == 4:
                        tap_target = ((bounds_val[0] + bounds_val[2]) // 2, (bounds_val[1] + bounds_val[3]) // 2)
                        break

        if tap_target is not None:
            if hasattr(ctx, "tap"):
                ctx.tap(tap_target[0], tap_target[1])
                action_performed = True
            elif hasattr(ctx, "adb") and hasattr(ctx.adb, "shell"):
                ctx.adb.shell(["input", "tap", str(tap_target[0]), str(tap_target[1])])
                action_performed = True
            elif hasattr(ctx, "actions") and hasattr(ctx.actions, "tap"):
                ctx.actions.tap(tap_target[0], tap_target[1])
                action_performed = True
        else:
            if not send_device_back_key(ctx):
                action_performed = False
            else:
                action_performed = True
...
```

### 4. Tự động giải phóng tại bước đối soát Profile (`_verify_profile_after_session` trong `feed_swipe_smoke.py`)
Khi vào bước `verify_profile`, nếu XML capture thấy popup location còn tồn tại, `find_matching_handler` trong registry sẽ tự động giải phóng trước khi đối soát username profile.
