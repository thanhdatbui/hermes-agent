# CapCut Template & Creation Hub UI Recovery (2026-09-04)

## Triệu chứng & Bối cảnh
- **Lỗi:** `upload_subprocess_nonzero` hoặc `VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED` khi đăng video TikTok trên các máy Samsung S7 (vụ máy 61, nick `khahoan01`, video 2).
- **Hiện tượng:** Khi tap nút `+` (Quay/Tạo video) hoặc mở thumbnail upload trong Camera, TikTok không mở trực tiếp Gallery Picker mà bung ra màn hình xem trước Mẫu CapCut/TikTok (Template Preview) hoặc Hub tạo mẫu (Creation Hub):
  - **Màn hình Template Preview:** Chứa tiêu đề template (VD: `beat1 máy bay`), nút CTA lớn `Thử mẫu này` (`id/use_template`), nút quay lại `<` (`id/bq3` ở top-left).
  - **Màn hình Creation Hub / Mẫu:** Chứa các công cụ `Trình chỉnh sửa ảnh`, `AutoCut`, `Phụ đề`, `AI Self`, `Tách nền`, `Video mới` (`id/pnx`), `Mẫu`, và nút đóng `X` (`id/h32` có `content-desc="Đóng"` ở top-left bounds `[18,84][150,216]`).

## Nguyên nhân gốc (Root Cause)
1. Hàm `_is_capcut_template_surface` cũ chỉ kiểm tra một số keyword đơn lẻ trong text của Template Preview, bỏ lọt cấu trúc Creation Hub đa công cụ.
2. `adapter.py` của consumer thiếu hỗ trợ lọc theo `content_desc` trong `_find_ui_element` và `_tap_if_found`, khiến việc tìm nút `content-desc="Đóng"` bị trượt.
3. Khi dismiss màn hình Template Preview bằng nút `<` (`id/bq3`), TikTok rơi vào Creation Hub chứ chưa về ngay Camera/Feed. Nếu vòng lặp chỉ gửi 1 action dismiss mà không có multi-step recovery thì flow vẫn bị kẹt ở Hub.
4. Trong `_wait_for_verified_media_picker_after_recovery`, cờ `camera_entry_attempted` chỉ cho phép tap upload thumbnail đúng 1 lần. Khi thumbnail mở ra template rồi bị dismiss về camera, script không tap lại thumbnail dẫn đến timeout picker.

## Giải pháp chuẩn & Code Pattern

### 1. Nhận diện 2 tầng Template Preview & Creation Hub
```python
@classmethod
def _is_capcut_template_surface(cls, xml_text: str) -> bool:
    if not xml_text or cls._is_verified_media_picker_xml(xml_text):
        return False
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return False

    template_cta_markers = ("thử mẫu này", "thu mau nay", "thử mẫu trong capcut", "use this template", "use template")
    capcut_brand_markers = ("bởi capcut", "capcut của", "capcut", "mẫu capcut", "capcut template")
    hub_tool_markers = ("trình chỉnh sửa ảnh", "chỉnh sửa hình ảnh", "autocut", "phụ đề", "ai self", "tách nền", "video mới", "bản nháp")

    labels, res_ids = [], []
    has_use_template_rid = False
    has_hub_nav = False
    for node in root.iter("node"):
        if node.attrib.get("visible-to-user", "true").casefold() == "false":
            continue
        rid = (node.attrib.get("resource-id", "") or "").casefold()
        if rid:
            res_ids.append(rid)
            if "use_template" in rid:
                has_use_template_rid = True
            if rid.endswith((":id/bq3", ":id/h32", "/bq3", "/h32")):
                has_hub_nav = True
        for attr in ("text", "content-desc"):
            val = " ".join(unicodedata.normalize("NFC", node.attrib.get(attr, "")).casefold().split())
            if val:
                labels.append(val)

    # Tầng 1: Template Preview
    if has_use_template_rid or any(any(m in l for m in template_cta_markers) for l in labels):
        return True
    if any(any(m in l for m in capcut_brand_markers) for l in labels) and any("mẫu" in l or "template" in l for l in labels):
        return True

    # Tầng 2: Creation Hub
    matched_tools = sum(1 for tool in hub_tool_markers if any(tool in l for l in labels))
    has_hub_title = any(l in {"mẫu", "templates", "đề xuất", "bài hát lan truyền", "xu hướng"} for l in labels)
    if matched_tools >= 2 and (has_hub_title or has_hub_nav):
        return True

    return False
```

### 2. Multi-step Dismiss Loop (Preview -> Hub -> Camera/Feed)
- Quét top-left node ($y \le 400$) tìm các ID/desc/text đóng: `:id/bq3`, `:id/h32`, `content-desc="Đóng"`, `quay lại`, `back`, `close`.
- Nếu không có node top-left, gửi semantic `adapter.back()`.
- Lặp tối đa `max_attempts=4` và re-capture UI sau mỗi bước cho đến khi thoát hoàn toàn khỏi màn template/hub.

### 3. Hồi phục luồng mở Media Picker
- Cho phép retry `_tap_visual_camera_upload_entry` tối đa 3 lần trong `_wait_for_verified_media_picker_after_recovery` khi màn hình camera hiện lại sau khi dismiss template.
- Trong `_tap_visual_camera_upload_entry`, tự động dismiss template/hub nếu thumbnail tap kích hoạt nhầm template preview.

### 4. Xử lý Stale Media Fingerprint Reservation
- Khi một lượt chạy bị ngắt quãng hoặc crash giữa chừng, reservation file trong `D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<sha256>.json` giữ trạng thái `reserved`.
- Nếu chạy lại canary ngay trước 30 phút (`stale_after_seconds=1800`), cần dọn file reservation của run cũ hoặc chờ timestamp stale để tránh bị chặn bởi `MEDIA_FINGERPRINT_PENDING`.
