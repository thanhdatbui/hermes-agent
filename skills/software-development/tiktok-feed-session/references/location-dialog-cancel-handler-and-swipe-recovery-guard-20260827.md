# Location Permission Dialog Dismissal & Swipe Recovery Guard (2026-08-27)

## 1. Bản chất sự cố
- Khi TikTok hiển thị dialog yêu cầu cấp quyền vị trí: *"Xem nội dung phù hợp và địa điểm lân cận"*, với hai nút *"Hủy"* (`android:id/button3`) và *"Mở cài đặt"* (`android:id/button1`).
- Mặc dù hệ thống đã có logic bấm nút *"Hủy"*, nhưng trên thực tế xảy ra 2 lỗi kết hợp:
  1. **Thiếu nguồn XML trong `_dismiss_location_prompt`**: Handler trong `benign_popup_registry.py` chỉ kiểm tra `ctx.dump_hierarchy()`. Tuy nhiên trên đối tượng `DeviceContext` tiêu chuẩn của repo, phương thức này không tồn tại, khiến hàm không parse được cây XML và không tìm được tọa độ của nút *"Hủy"*, phải rơi vào fallback phím BACK hoặc fail.
  2. **False-Positive trong `_swipe_recovery_on_stuck`**: Khi flow gặp màn hình kẹt và kích hoạt swipe cứu kẹt 1-2 lần, hàm kiểm tra `detected` sau swipe với danh sách loại trừ thiếu các màn hình popup (`manual-needed:popup`, `generic_popup`, `manual-needed:sponsored-ad-feedback`). Dù popup vẫn che toàn màn hình, hàm vẫn coi là đã vượt qua và gán `SUCCESS` ("swipe recovery passed stuck screen"), khiến popup tiếp tục tồn tại sang các bước tiếp theo.

## 2. Quy tắc xử lý chuẩn

### A. Fallback nguồn XML an toàn trong handler popup
Trong mọi handler popup thuộc `benign_popup_registry.py`, khi cần XML để tìm tọa độ tap:
```python
xml_str = None
if hasattr(ctx, "dump_hierarchy"):
    try:
        xml_str = ctx.dump_hierarchy()
    except Exception:
        pass
if not xml_str:
    from .feed_swipe_smoke import _capture_xml_text
    try:
        xml_str = _capture_xml_text(ctx, "dismiss_location_prompt")
    except Exception:
        pass
if xml_str:
    from automation_core.ui import parse_xml
    xml_tree = parse_xml(xml_str)
```

### B. Chặn Swipe Recovery báo Pass giả khi Popup còn tồn tại
Trong `_swipe_recovery_on_stuck`, chỉ công nhận recovery thành công khi màn hình sau swipe là feed/profile hợp lệ, tuyệt đối loại trừ mọi trạng thái popup/dialog:
```python
if detected and detected not in {
    "manual-needed:login",
    "manual-needed:verification",
    "manual-needed:captcha",
    "manual-needed:security",
    "manual-needed:manual_challenge",
    "manual-needed:popup",
    GENERIC_POPUP_SCREEN,
    SPONSORED_AD_FEEDBACK_SCREEN,
    "unknown",
}:
    row["status"] = ExitStatus.SUCCESS.value
    ...
```
