# AI Auto-Recovery Code Patch Architecture & Dispatcher Registration Pattern

## Root Cause of Duplicate / Dead-Code Recovery Handlers
Khi hệ thống phone farm chạy AI Auto-Recovery tự động vá lỗi kẹt màn hình:
1. **Blind Append Defect**: `code_patcher.py` chèn hàm mới bằng cách đọc file `benign_popup.py` và nối đuôi `+ "\n\n\n" + code_patch.strip()`.
2. **Dispatcher Unaware**: Luồng nuôi acc chính (`feed_swipe_smoke.py` / `multi_machine_feed_session.py`) gọi tập trung qua `classifier.py` hoặc `dismiss_any_popup`. Các hàm chỉ nằm ở đuôi file `benign_popup.py` mà không được đăng ký vào Dispatcher/Registry trở thành **dead code**.
3. **Infinite Re-Patch Loop**: Máy A kẹt màn hình X (VD: camera) ➔ AI sinh `dismiss_camera_1` (nối đuôi) ➔ Máy B sau đó cũng kẹt màn hình X ➔ Bộ phân loại vẫn không nhận diện được ➔ AI sinh tiếp `dismiss_camera_2` (nối đuôi tiếp). Dẫn đến hàng chục hàm duplicate (`dismiss_camera_creation_screen`, `dismiss_tiktok_camera_screen`, `detect_location_permission_prompt`, v.v.).

## Correct Architecture & Fix Guidelines

### 1. Centralized Popup/Screen Registry Pattern
Thay vì để các hàm rời rạc không được gọi, `benign_popup.py` cần có `BENIGN_POPUP_REGISTRY`:
```python
POPUP_HANDLERS = [
    (detect_tiktok_camera_screen, dismiss_tiktok_camera_screen),
    (detect_location_permission_prompt, dismiss_location_permission_prompt),
    (detect_featured_creators_popup, dismiss_featured_creators_popup),
    # ...
]

def dismiss_any_popup(ctx: DeviceContext, ...):
    xml_root = ctx.dump_hierarchy()
    for detector, dismisser in POPUP_HANDLERS:
        if detector(xml_root):
            return dismisser(ctx)
```

### 2. Prompt & Patcher Enforcement for AI Recovery
1. **Vision Client Prompt (`vision_client.py`)**:
   - Yêu cầu AI không chỉ sinh hàm mà phải xuất dạng `(detector_func, dismisser_func)` hoặc đăng ký vào bảng `POPUP_HANDLERS`.
2. **Code Patcher (`code_patcher.py`)**:
   - Khi patch, kiểm tra xem hàm đã tồn tại tên hoặc logic tương đương chưa (AST search / grep).
   - Tự động chèn cặp `(detector, dismisser)` vào `POPUP_HANDLERS` thay vì chỉ `read_text() + code`.
3. **Deduplication Audit**:
   - Định kỳ chạy script kiểm tra `benign_popup.py` để phát hiện và gộp các hàm trùng lặp (`def duplicate_functions`).
