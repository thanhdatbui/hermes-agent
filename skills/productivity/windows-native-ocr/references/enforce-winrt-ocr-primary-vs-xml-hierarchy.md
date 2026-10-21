# Kiến Trúc Bắt Buộc WinRT OCR Primary vs XML Fallback trên Phone Farm

## Bối Cảnh Thực Tế & Lỗ Hổng Tư Duy
Khi tự động hóa các tác vụ đọc thông tin trên Android Phone Farm (Samsung Galaxy S7 Android 7/8, ~80 máy trên Host Windows 10) như đơn hàng TikTok Shop, mã vận đơn (tracking code), thông báo đơn vị vận chuyển, trạng thái tài khoản:
- Các lập trình viên và Agent AI (Hermes, Claude Worker, Codex) thường có "quán tính lập trình" nhảy vào cào cây Accessibility XML (`uiautomator dump` hoặc `atx-agent` port 7912 `dumpWindowHierarchy`).
- **Thực tế thất bại:**
  1. Giao diện đơn hàng (TikTok Shop / Shopee) bản chất là WebView / Lynx / Canvas. Accessibility Service của Android không đọc được text bên trong các container này, trả về node rỗng `text=""` hoặc rỗng toàn bộ cây XML.
  2. Phần cứng Samsung Galaxy S7 (Exynos 8890) rất yếu. Lệnh dump XML gây áp lực CPU lớn, dễ bị Android kernel kill (Exit 137) hoặc delay >10s làm đứt luồng automation.
  3. Trong khi đó, Host PC chạy Windows 10 đã có sẵn **WinRT OCR (`Windows.Media.Ocr`)**, xử lý trên CPU/GPU máy tính cực nhanh (<0.3s), trích xuất 100% tiếng Việt có dấu chuẩn xác từ ảnh chụp màn hình (`screencap`), giải phóng hoàn toàn tải cho điện thoại.

## Quy Tắc Bắt Buộc (INVARIANT UI-OCR-1)
Từ nay về sau, mọi script automation bóc tách dữ liệu UI trên Farm phải tuân thủ nghiêm ngặt:

1. **Thứ tự thực thi cứng (Strict Execution Hierarchy):**
   ```text
   Screencap thiết bị -> Lưu ảnh hiện trường -> WinRT OCR (Primary) -> Kiểm tra kết quả
     ├── Đủ trường dữ liệu -> Commit kết quả & hoàn thành
     └── Thiếu trường / Mờ ảnh -> Fallback sang ATX/XML Hierarchy (hoặc Native Profile Bounds)
   ```
2. **Cấm đoán trực tiếp (Banned Direct XML Dumps):**
   - CẤM các script automation coi XML là nguồn chính để đọc text/trạng thái.
   - CẤM gọi shell `uiautomator dump` (bị Android kill).
3. **Phân vai rõ ràng giữa OCR và XML:**
   - **WinRT OCR:** Đảm nhận toàn bộ việc ĐỌC HIỂU và TRÍCH XUẤT (Text, Mã đơn, Trạng thái, Cảnh báo lỗi, Tên shop, Mã tracking, Phát hiện popup che).
   - **XML Hierarchy:** CHỈ dùng khi cần đọc thuộc tính widget native ngầm (`checked`, `focused`, `scrollable`) hoặc lấy tọa độ `bounds` của các form native trong Cài đặt Android.

## Mẫu Triển Khai Chuẩn (Reference Implementation)

```python
from pathlib import Path
from dataclasses import dataclass
import xml.etree.ElementTree as ET

@dataclass(frozen=True)
class UIInfo:
    tracking_code: str | None
    carrier: str | None
    status: str | None

def parse_ui_data(image_path: Path, xml_hierarchy: str = None) -> UIInfo:
    ocr_info = None
    
    # 1. PRIMARY: WinRT OCR quét ảnh trực tiếp
    if image_path and image_path.exists():
        from winrt_ocr_util import winrt_ocr
        ocr_text = winrt_ocr(str(image_path))
        if ocr_text:
            ocr_info = extract_fields_from_text(ocr_text)
            # Nếu OCR đã bóc đủ các trường trọng yếu, return ngay lập tức
            if ocr_info.tracking_code and ocr_info.carrier:
                return ocr_info

    # 2. FALLBACK: Chỉ đọc XML khi OCR thiếu trường
    xml_info = None
    if xml_hierarchy:
        xml_info = extract_fields_from_xml(xml_hierarchy)

    # 3. Hợp nhất dữ liệu ưu tiên OCR
    return UIInfo(
        tracking_code=(ocr_info.tracking_code if ocr_info else None) or (xml_info.tracking_code if xml_info else None),
        carrier=(ocr_info.carrier if ocr_info else None) or (xml_info.carrier if xml_info else None),
        status=(ocr_info.status if ocr_info else None) or (xml_info.status if xml_info else None)
    )
```
