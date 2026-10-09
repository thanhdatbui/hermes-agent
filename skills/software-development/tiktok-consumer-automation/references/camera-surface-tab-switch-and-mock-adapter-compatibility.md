# Camera Surface Tab Switch & Mock Adapter Compatibility

## Pitfall: Mock Adapter Missing Helper Methods in State Machine
Trong các flow automation (như `state_machine.py`), các helper method mới bổ sung thường gọi trực tiếp các method của `TikTokAdapter` thực tế (ví dụ: `adapter._tap_if_found(...)`).
Tuy nhiên, trong test suite (`test_tiktok_workflow.py`), các fixture/test mock (`MockAdapter`, `CameraSurface`, `StubbornCameraSurface`) thường chỉ implement các primitive tối thiểu:
- `dump_ui()`
- `tap(x, y)`
- `back()`

Nếu gọi trực tiếp `adapter._tap_if_found(...)`, unit test sẽ lập tức raise `AttributeError: '<Mock>' object has no attribute '_tap_if_found'`.

### Quy tắc an toàn:
1. Luôn dùng `getattr(adapter, "_tap_if_found", None)` hoặc `try...except AttributeError`.
2. Kiểm tra `callable(tap_fn)` trước khi gọi.
3. Không thực hiện blind fallback tap (như tọa độ cứng `tap(315, 1820)`) nếu không có bằng chứng UI thực sự cần switch hoặc nếu adapter là test mock.

## Pitfall: Nhận diện sai chế độ Camera vs TẠO (Template)
Dưới đáy màn hình camera TikTok, thanh điều hướng luôn hiển thị đồng thời các tab:
`ẢNH`, `CAMERA`, `TẠO` (hoặc `LIVE`).

### Cảnh báo điều kiện nhầm lẫn:
Nếu viết điều kiện:
```python
elif any(m in xml_text for m in ('text="TẠO"', 'text="Mẫu"')) and any(m in xml_text for m in ('text="CAMERA"', 'text="Máy ảnh"')):
    needs_camera_switch = True
```
Điều kiện này sẽ luôn `True` trên mọi màn hình camera chuẩn của TikTok (và mọi test mock chứa `<hierarchy><node text="CAMERA" /><node text="TẠO" /></hierarchy>`). Hậu quả:
- State machine tưởng nhầm màn hình camera đang ở tab khác, cố switch tab hoặc tap toạ độ fallback.
- Ghi thêm các lệnh tap không mong muốn vào danh sách hành động của adapter, làm vỡ các assertion số lần tap (`assert adapter.taps == [...]`) và làm nhảy mock iterator trong unit test.

### Cách phân biệt chính xác:
- Chỉ chuyển tab khi thực sự ở chế độ LIVE (`Phát LIVE`, `Trung tâm LIVE`).
- Hoặc khi tab `TẠO`/`Mẫu` có thuộc tính `selected="true"` và không có upload thumbnail / camera shutter.
- Hoặc sau khi kiểm tra các upload entry (`view_bg2`, `upload_hot_area`) đều vắng mặt.

## Dynamic Screen Size Scaling cho Coordinate Fallback
Khi buộc phải fallback sang toạ độ (ví dụ tap tab `CAMERA` ở đáy màn hình khi XML mất text selector), tuyệt đối không hardcode pixel cố định `tap(315, 1820)`:
- Lấy kích thước thực qua `adapter.get_screen_size()` (fallback 1080x1920 nếu không có).
- Tính toạ độ theo tỷ lệ chuẩn: `tap(int(width * 0.292), int(height * 0.948))`.
- Chỉ thực hiện fallback này khi trên thiết bị thật (`hasattr(adapter, "serial")`) và XML thực sự có dấu hiệu tab camera cần switch.

## Hashtag Verification trong Caption Composer (50% Threshold)
TikTok composer thường hiển thị hashtag dưới dạng token chip/pill hoặc cắt ngắn (ellipsis) khi caption dài:
- Kiểm tra chính xác chuỗi caption chuẩn hoá (`normalized_caption in normalized_visible`).
- Nếu caption có hashtag, yêu cầu match tối thiểu 50% số hashtag (`matched_tags >= max(1, (len(hashtags) + 1) // 2)`) thay vì bắt buộc 100% hoặc chỉ cần 1 tag ngẫu nhiên.

## Explicit Failure State Tracking (`last_failed_state`)
Khi workflow gặp lỗi và chuyển sang state `FAILED`:
- Lưu `self.last_failed_state = self.current_state` trước khi set `self.current_state = fail_state`.
- Tại runner (`run_post.py`), khi `machine.current_state == WorkflowState.FAILED`, lấy state thực tế gây lỗi từ `last_failed_state` thay vì ghi nhận generic `"FAILED"`, giúp báo cáo và dashboard phân loại chính xác nguyên nhân.

## Linter/Review: Explicit Short-Circuit Fallback Chains
Với các chuỗi cascading UI selectors dùng toán tử `or`:
```python
# Intentional short-circuit fallback chain
tapped = (
    adapter._tap_if_found(xml, text="...")
    or adapter._tap_if_found(xml, text_contains="...")
)
```
Luôn thêm comment `# Intentional short-circuit fallback chain` để linter và code review nhận biết đây là cascading fallback có chủ đích, tránh bị gắn cờ code complexity.
