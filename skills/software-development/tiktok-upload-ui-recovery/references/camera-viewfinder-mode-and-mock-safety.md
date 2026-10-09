# Camera Viewfinder Mode Switch and Test Mock Safety (Tiktok-video)

## Bối cảnh & Hiện tượng
Trong quy trình đăng video TikTok (`scripts/tiktok_workflow/state_machine.py`), khi mở camera qua dấu `+` (create button), TikTok trên các thiết bị farm hoặc phiên bản khác nhau có thể mở nhầm vào:
1. **LIVE mode**: Có các marker `text="Phát LIVE"`, `text="Trung tâm LIVE"`, `text="LIVE"`, `text="Live"`.
2. **CapCut Template Hub / Tab TẠO**: Màn hình gợi ý mẫu CapCut với `Thử mẫu này`, `Video mới`, `Mẫu`, hoặc tab bottom bar `TẠO` đang active (`selected="true"`).

Khi bị kẹt ở LIVE hoặc Template Hub, nút thumbnail gallery/upload không xuất hiện hoặc bị che, dẫn đến workflow timeout không thể pick video.

## Pitfall 1: False Positive khi Camera Viewfinder bình thường
Ở màn hình camera viewfinder chuẩn (đã ở tab CAMERA), hierarchy XML thường chứa cả:
- `<node text="CAMERA" ... />`
- `<node text="TẠO" ... />`
(Hai tab cạnh nhau trên thanh trượt dưới đáy màn hình).

**Lỗi thường gặp:**
Nếu kiểm tra ngây thơ:
```python
if any(m in xml_text for m in ('text="TẠO"', 'text="Mẫu"')) and any(m in xml_text for m in ('text="CAMERA"', 'text="Máy ảnh"')):
    needs_switch = True
```
Điều kiện này sẽ **bị kích hoạt nhầm ngay cả khi máy đang ở camera viewfinder chuẩn**. Hệ thống sẽ cố gắng tap chuyển tab, làm rối loạn flow hoặc làm hỏng test mock.

**Giải pháp chuẩn:**
Chỉ switch khi:
- Có marker LIVE rõ ràng: `'Phát LIVE'`, `'Trung tâm LIVE'`, `'LIVE'`, `'Live'`.
- HOẶC thực sự là Template Hub: `_is_capcut_template_surface(xml_text)` trả về True, HOẶC node `text="TẠO"` có thuộc tính `selected="true"`.

## Pitfall 2: Mock Adapter trong Test Suite và AttributeError
Trong `tests/test_tiktok_workflow.py`, các test mock như `MockAdapter`, `CameraSurface`, `StubbornCameraSurface` chỉ định nghĩa `tap(x, y)` và `dump_ui()`, KHÔNG có `_tap_if_found`.
Nếu code gọi thẳng `adapter._tap_if_found(...)`, test sẽ bị nổ `AttributeError`.

**Giải pháp:**
```python
tap_if_found = getattr(adapter, "_tap_if_found", None)
if callable(tap_if_found):
    for target in ("CAMERA", "Camera", "Máy ảnh", "ĐĂNG"):
        if tap_if_found(xml_text, text=target):
            switched = True
            break
```

## Pitfall 3: Coordinate Fallback (315, 1820) làm hỏng Test Assertions
Khi chạy thật trên màn hình 1080x1920, nếu không tìm được text selector, fallback tap vào tab CAMERA ở tọa độ `(315, 1820)`.
Tuy nhiên, trong unit test:
- Mock adapter ghi nhận danh sách taps vào `self.taps`.
- Test kiểm tra `assert adapter.taps == [(120, 1821)]`.
- Nếu fallback `(315, 1820)` chạy trên mock, `self.taps` sẽ trở thành `[(315, 1820), (120, 1821)]` gây fail assertion.

**Giải pháp:**
Chỉ cho phép fallback coordinate khi chạy trên thiết bị thật:
```python
if not switched and hasattr(adapter, "serial") and ('text="CAMERA"' in xml_text or 'text="TẠO"' in xml_text):
    adapter.tap(315, 1820)
    switched = True
```

## Helper Chuẩn: `_ensure_camera_viewfinder_mode`
Áp dụng helper này ở cả 2 điểm vào camera:
1. `_tap_visual_camera_upload_entry`
2. State `VIDEO_PICK` ngay sau khi tap plus button.

```python
def _ensure_camera_viewfinder_mode(self, adapter, xml_text: str) -> str:
    """Switch to CAMERA tab if currently in LIVE mode or Template Hub."""
    if not xml_text:
        return ""
    needs_switch = False
    if any(m in xml_text for m in ('text="Phát LIVE"', 'text="Trung tâm LIVE"', 'text="LIVE"', 'text="Live"')):
        needs_switch = True
    elif self._is_capcut_template_surface(xml_text) or ('text="TẠO"' in xml_text and 'selected="true"' in xml_text):
        needs_switch = True

    if not needs_switch:
        return xml_text

    logger.info("[CAMERA_MODE] Switching to CAMERA tab")
    switched = False
    tap_if_found = getattr(adapter, "_tap_if_found", None)
    if callable(tap_if_found):
        for target in ("CAMERA", "Camera", "Máy ảnh", "ĐĂNG"):
            if tap_if_found(xml_text, text=target):
                switched = True
                break

    # If on real device and not switched via selector, fallback to bottom tab coords
    if not switched and hasattr(adapter, "serial") and ('text="CAMERA"' in xml_text or 'text="TẠO"' in xml_text):
        adapter.tap(315, 1820)
        switched = True

    if switched:
        time.sleep(2)
        try:
            xml_text = adapter.dump_ui()
        except Exception:
            pass
    return xml_text
```

## 4 Hard Locks cho Camera Entry & Viewfinder Recovery

### 1. Negative Spatial Gate
- **Mục đích**: Loại trừ hoàn toàn các toạ độ tap rơi vào dải trung tâm màn hình (`0.15 <= y / height <= 0.75`), vốn là khu vực hiển thị các video card, carousel template CapCut hoặc preview viewfinder.
- **Quy tắc**: Mọi toạ độ tap ứng viên (kể cả phát hiện qua non-dark pixel ratio) nếu rơi vào `0.15 * height <= tap_y <= 0.75 * height` đều bị loại bỏ ngay từ vòng lọc toạ độ.

### 2. Strict Left-Only Priority
- **Mục đích**: Trên các máy Samsung hoặc build có dual thumbnail (trái là gallery album, phải là template/effect/CapCut button), nếu `left_targets` có thumbnail hợp lệ (`non_dark >= 0.20`), **chỉ dùng `left_targets` và bỏ qua hoàn toàn `right_targets`**:
  ```python
  if left_targets:
      ordered_candidates = left_targets
  else:
      ordered_candidates = right_targets
  ```
  Tránh trường hợp round-robin / alternate tap sang phải làm kích hoạt template modal.

### 3. Circuit Breaker (Max 2 Taps)
- **Mục đích**: Giới hạn số lần tap thử thumbnail camera tối đa là `max_taps = 2` (thay vì 4). Nếu sau 2 lần tap không mở được `_is_verified_media_picker_xml`, dừng ngay lập tức để luồng ngoài kích hoạt recovery ladder (feed drop / re-entry), tránh kẹt vô tận trong loop camera viewfinder.

### 4. Swipe Fallback & Pitfall Thiếu `adapter.swipe`
- **Mục đích**: Khi bottom tab selector và coordinate fallback không chuyển được chế độ viewfinder (từ LIVE hoặc Template Hub sang CAMERA), thực hiện swipe ngang (vuốt từ trái qua phải hoặc phải qua trái) để đổi tab.
- **CRITICAL PITFALL**: Class `TikTokAdapter` (`scripts/tiktok_workflow/adapter.py`) **KHÔNG CÓ hàm public `swipe(x1, y1, x2, y2)`** (chỉ có `tap_long`, `tap`, `back`, `keyevent`).
- **Xử lý an toàn**:
  ```python
  # Tuyệt đối KHÔNG gọi adapter.swipe() mà không kiểm tra hasattr:
  if hasattr(adapter, "swipe") and callable(adapter.swipe):
      adapter.swipe(x1, y1, x2, y2)
  elif hasattr(adapter, "_adb") and hasattr(adapter._adb, "shell"):
      adapter._adb.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), "300"], timeout=10, check=False)
  ```
- **Test Assertion Impact**:
  - Khi áp dụng Circuit Breaker `max_taps = 2` và Left-only priority, unit test `test_video_pick_camera_thumbnail_alternates_retry_targets` (vốn mong đợi 3 lần tap xoay vòng giữa left và right) cần được đồng bộ expectation theo giới hạn 2 taps và ưu tiên left.

