# Hướng dẫn mở rộng Benign Popup Registry (`benign_popup_registry.py`)

File: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py`

## 1. Kiến trúc Registry
Registry quản lý các popup lành tính theo độ ưu tiên (priority từ 1 đến 100, số càng lớn càng được check trước):
- `find_matching_handler(xml_content, ocr_text)` lặp qua registry đã sắp xếp theo `-priority`.
- Khi khớp detector, gọi `matching_entry.dismisser(ctx)`.

## 2. Chuẩn hàm Detector & Dismisser

### Detector
- Nhận `xml_content: Any = "", ocr_text: str = ""`
- Chuyển `content = f"{xml_content or ''} {ocr_text or ''}".lower()`
- Kiểm tra các cụm từ nhận diện đặc trưng (phrases tiếng Việt + tiếng Anh) và điều kiện ngữ cảnh.

### Dismisser
- Signature khuyến nghị: `_dismiss_<name>(device: Any, xml_content: Any = None, ocr_text: Any = None) -> Any`
  - Tương thích cả khi registry gọi `dismisser(ctx)` (1 tham số) và khi gọi trực tiếp với 3 tham số.
- Các bước xử lý chuẩn:
  1. Lấy `raw_xml`: dùng `xml_content` nếu có, ngược lại gọi `_safe_capture_hierarchy(device)`.
  2. Phân tích `parse_xml_safely(raw_xml)`.
  3. Quét tìm nút dismiss/từ chối ưu tiên: `Không` / `No` / `✕` / `Đóng` / `Close`.
  4. Nếu tìm thấy tọa độ bounds: tap bằng `_perform_click_target(device, target_pt)`.
  5. Nếu không tìm thấy nút hoặc tap không thành công: fallback swipe up theo kích thước màn hình để bỏ qua ad/popup.
  6. Luôn trả về `PopupDismissResult`:
     ```python
     return PopupDismissResult(
         dismissed=True,
         reason="tapped_..._button", # hoặc "swiped_up_..."
         before_attempt=before,
         popup_closed=True,
         selector={"action": "allowlist_dismiss", "popup_type": "<popup_name>"},
     )
     ```

## 3. Đăng ký Registry
```python
register_popup_handler(
    RegistryEntry(
        "<popup_name>",
        priority,  # Ví dụ: 75
        _detect_<name>,
        _dismiss_<name>,
        True,
        "manual",
    )
)
```

## 4. Lệnh Canary Test B4 sau khi patch
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\Taadaa\tiktok-luot nuoi acc\scripts\run-feed-session.ps1" -Machines <N> -Row 1 -RecoveryTestSwipes 2 -SkipAccountWorkbookSync -Run
```
