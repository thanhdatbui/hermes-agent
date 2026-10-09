# Quy chuẩn Detect Element từ XML & Tap Element Center

## 1. Nguyên tắc
- **Tuyệt đối CẤM hardcode tọa độ pixel** (như `input tap 540 1436`) khi xử lý các nút retry, "Thử lại" (`com.ss.android.ugc.trill:id/dcj`), popup, error dialog hay switcher row.
- Độ phân giải màn hình khác nhau giữa các dòng máy trong farm (80-160 máy gồm nhiều model: A10, A10s, A12, Note, Pixel...) sẽ khiến hardcode tọa độ bấm trượt hoặc bấm nhầm thành phần khác.

## 2. Pattern chuẩn
Khi cần bấm một nút UI xuất hiện trên màn hình (ví dụ nút "Thử lại" khi switch profile gặp lỗi):
1. Lấy `xml_path` từ identity hoặc observation hiện tại:
   ```python
   xml_path = latest_identity.get("xml_path")
   if not xml_path and latest_identity.get("artifact_path"):
       xml_path = Path(latest_identity["artifact_path"]) / "ui.xml"
   ```
2. Parse XML (sử dụng `parse_xml` từ `automation_core.ui` hoặc đọc file / recaptured XML text):
   - Tìm element theo `resource-id` (e.g. `com.ss.android.ugc.trill:id/dcj`) hoặc `text` / `text.lower()` (e.g. "thử lại").
3. Lấy tọa độ tâm (`center` / `(cx, cy)`):
   - Sử dụng `element.center` hoặc `parse_bounds(element.attrib.get("bounds"))`.
4. Thực thi tap qua ADB shell:
   ```python
   ctx.adb.shell(["input", "tap", str(cx), str(cy)], timeout=ctx.timeout("adb_seconds", 5))
   ```
