# TikTok Screen Calibration & Bottom Sheet / Popup Recovery Patterns

## 1. Context: Screen Calibration & Navigation Recovery
Trong flow điều hướng và cân chỉnh màn hình (`calibrate_screens.py`), hệ thống thường dùng cơ chế kiểm tra `is_home_or_feed` để tránh gửi nhầm phím `KEYCODE_BACK` làm văng app ra Android launcher.

### Pitfall: False Positive khi màn hình Feed bị che bởi Bottom Sheet / Dialog Overlay
Nếu app đang ở Feed / Home nhưng phía trước đang hiển thị một bottom sheet (ví dụ: gợi ý kết bạn "Đã follow chung", bottom sheet chia sẻ, permission dialog,...), class classifier hoặc các marker (`home_selected`, `for_you_selected`) vẫn có thể nhận diện màn hình là Feed.
- Hậu quả: `is_home_or_feed` bị đánh giá là `True` → bỏ qua recovery bằng `KEYCODE_BACK`.
- Kết quả: Các tab / navigation controls bị overlay che khuất không thể click được, dẫn tới navigation timeout hoặc calibration failure.

### Solution: Overlay Guard
Trước khi kết luận `is_home_or_feed = True`, phải kiểm tra sự hiện diện của overlay / dialog:
```python
current_classification = classify_tiktok_screen(current_root)
if current_classification.screen in {"home", "for-you", "following", "friends"}:
    has_overlay = any(
        (el.attrib.get("content-desc") or "").strip() == "Trang tính dưới cùng"
        or "g1i" in (el.attrib.get("resource-id") or "")
        or "dialog" in (el.attrib.get("class") or "").lower()
        for el in current_root.iter()
    ) if current_root is not None else False

    if not has_overlay:
        is_home_or_feed = True
```
Nếu `has_overlay == True`, giữ `is_home_or_feed = False` để cho phép `KEYCODE_BACK` đóng overlay và đưa app về trạng thái clean feed.

---

## 2. Benign Popup: "Đã follow chung" / Bottom Sheet Friends Suggestion
Trong `benign_popup.py`:
- **Detect Markers**: Bổ sung `"Đã follow chung"`, `"Follow chung"` vào danh sách markers của `detect_follow_friends_suggestion_popup`.
- **Title Control**: Nhận diện title node bắt đầu bằng `"đã follow chung"` hoặc `"follow chung"` để xác định vị trí header của sheet.
- **Close Button Bounds**: Nút đóng dạng `ImageView` / `ImageButton` ở góc trên bên phải sheet (`bounds[0] >= 800` và `abs(bounds[1] - t_bounds[1]) <= 150`) cần được ưu tiên trả về làm control đóng semantic để dismiss sheet chuẩn xác.
