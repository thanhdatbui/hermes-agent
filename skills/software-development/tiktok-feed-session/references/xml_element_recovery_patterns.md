# XML Element Detection & Tap Recovery Patterns

## Nguyên tắc Dynamic Element Center
Tuyệt đối KHÔNG hardcode tọa độ bấm (`input tap X Y`) trong auto-recovery và flow navigation khi đã có UI XML dump hoặc UI inspection.

### 1. Hàm `parse_xml` trong `automation_core.ui`
`parse_xml(xml_text: str)` nhận chuỗi XML (`str`), **không nhận file path**:
- Nếu nguồn là file (`xml_path`):
  ```python
  xml_content = Path(str(xml_path)).read_text(encoding="utf-8")
  root = parse_xml(xml_content)
  ```
- Nếu nguồn từ identity dict:
  ```python
  xml_text = latest_identity.get("xml_text")
  if not xml_text and (latest_identity.get("xml_path") or latest_identity.get("artifact_path")):
      p = latest_identity.get("xml_path") or Path(str(latest_identity.get("artifact_path", ""))) / "ui.xml"
      if Path(p).is_file():
          xml_text = Path(p).read_text(encoding="utf-8")
  if xml_text:
      root = parse_xml(xml_text)
  ```

### 2. Tìm Element & Tap Center
Sử dụng `find_element` hoặc `find_by_fields`:
```python
elem = find_element(root, {"resource_id": "com.ss.android.ugc.trill:id/dcj"}) or find_element(root, {"text": "Thử lại"})
# hoặc find_by_fields:
# elem = find_by_fields(root, resource_id="com.ss.android.ugc.trill:id/dcj") or find_by_fields(root, text="Thử lại")

if elem and elem.center:
    ctx.adb.shell(["input", "tap", str(elem.center[0]), str(elem.center[1])], timeout=ctx.timeout("adb_seconds", 5))
```
`elem.center` trả về tuple `(center_x, center_y)` được tính từ thuộc tính `bounds` của element, đảm bảo bấm chính xác mọi độ phân giải máy thay vì tọa độ cố định.
