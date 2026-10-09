# Cạm Bẫy Tab TẠO (Template Hub) Nhầm Là Camera & Ưu Tiên Thumbnail Trái (Case M39)

## 1. Hiện tượng & Triệu chứng (Case Máy 39 - `tachau1704`)
- **Mã lỗi:** `[MANUAL_REVIEW] [VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED] Picker was not verified after the bounded create-entry recovery`
- **Triệu chứng UI:**
  - Máy 39 nhấn nút `+` trên Home Feed nhưng không bao giờ vào được Gallery Picker.
  - Sau nhiều lượt recovery, máy rơi về Home Feed và kết thúc bằng `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.
  - Phiên xử lý bị lặp kéo dài nhiều chu kỳ nếu không phân tích đúng ảnh hiện trường.

---

## 2. Nguyên nhân cốt lõi (Root Cause)

### 2.1. Nhầm lẫn tai hại giữa tab "TẠO" và Camera Viewfinder
- Khi ấn `+`, thanh chuyển chế độ (bottom mode bar) của TikTok hiển thị:
  `CAMERA` (x ~ 217..414) | `TẠO` (x ~ 494..585) | `LIVE` (x ~ 668..761) tại y ~ 1805..1839 (độ phân giải 1080x1920).
- Logic cũ trong codebase:
  ```python
  # Switch from LIVE tab to ĐĂNG/TẠO if in LIVE mode
  if any(m in xml_text for m in ('text="Phát LIVE"', 'text="Trung tâm LIVE"', 'text="LIVE"', 'text="Live"')) and any(m in xml_text for m in ('text="ĐĂNG"', 'text="TẠO"')):
      if not adapter._tap_if_found(xml_text, text="ĐĂNG"):
          adapter._tap_if_found(xml_text, text="TẠO")
  ```
  Code chủ động tap vào `"TẠO"` khi thấy LIVE, hoặc TikTok mở mặc định vào tab `"TẠO"`.
- **Bản chất tab "TẠO":**
  Tab "TẠO" trên TikTok hiện tại chính là **CapCut Templates Hub** (chứa các danh mục: "Video mới", "Mẫu", "Đề xuất", "Bài hát lan truyền", "Xu hướng" và các video card mẫu).
  Tại màn hình này **KHÔNG CÓ nút chụp (shutter)** và **KHÔNG CÓ nút Tải lên / Album thumbnail**.

### 2.2. Vòng lặp Dismissal Loop khi chạy Visual Fallback
- Khi ở tab "TẠO", do XML không có nút upload rõ ràng, robot kích hoạt `_tap_visual_camera_upload_entry`.
- Visual fallback quét các góc màn hình và tap vào tọa độ ứng viên (ví dụ góc phải `R` hoặc góc trái `L`).
- Cú tap trúng vào 1 video card template CapCut $\rightarrow$ Mở màn hình xem trước mẫu CapCut.
- Logic phát hiện `_is_capcut_template_surface` kích hoạt và gọi `_dismiss_capcut_template_surface`, bấm Back/Close.
- Khi dismiss template, TikTok thoát thẳng ra **Home Feed (`Trang chủ`)** thay vì ở lại camera.
- Robot rơi vào recovery: bấm `+` $\rightarrow$ lại vào tab "TẠO" $\rightarrow$ lại tap trúng template $\rightarrow$ lại dismiss về feed $\rightarrow$ timeout fail-closed `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED`.

---

## 3. Giải pháp chuẩn hóa (Standard Fix)

### 3.1. Helper `_ensure_camera_viewfinder_mode`
Bắt buộc chuyển sang tab `CAMERA` / `Máy ảnh` / `ĐĂNG` khi phát hiện đang ở `LIVE` hoặc `TẠO` / Template Hub:
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
        width, height = 1080, 1920
        if hasattr(adapter, "get_screen_size") and callable(adapter.get_screen_size):
            try:
                size = adapter.get_screen_size()
                if size and len(size) == 2 and size[0] > 0 and size[1] > 0:
                    width, height = size[0], size[1]
            except Exception:
                pass
        adapter.tap(int(width * 0.292), int(height * 0.948))
        switched = True

    if switched:
        time.sleep(2)
        try:
            xml_text = adapter.dump_ui()
        except Exception:
            pass
    return xml_text
```

### 3.2. Ưu tiên Thumbnail Trái (`L`/`BL`) trong Visual Upload
Trên hầu hết build Samsung, thumbnail thư viện nằm bên trái (`L` hoặc `BL`), còn bên phải (`R`) thường là shortcut Mẫu CapCut hoặc hiệu ứng. Luôn xếp ứng viên trái lên trước ứng viên phải:
```python
left_targets = []
if non_dark_l >= 0.20:
    left_targets.append(("L", (int(width * 0.145), int(height * 0.82)), non_dark_l))
if non_dark_bl >= 0.20:
    left_targets.append(("BL", (int(width * 0.11), int(height * 0.95)), non_dark_bl))
left_targets.sort(key=lambda item: item[2], reverse=True)

right_targets = []
if non_dark_r >= 0.20:
    right_targets.append(("R", (int(width * 0.875), int(height * 0.83)), non_dark_r))

ordered_candidates = left_targets + right_targets
```

### 3.3. An toàn cho Test Mock
- Không gọi trực tiếp `adapter._tap_if_found(...)` mà dùng `getattr(adapter, "_tap_if_found", None)` để tránh `AttributeError` khi test suite dùng `MockAdapter`.
- Fallback tọa độ màn hình chỉ áp dụng khi `hasattr(adapter, "serial")` (máy thật), không áp dụng trên test mock.
