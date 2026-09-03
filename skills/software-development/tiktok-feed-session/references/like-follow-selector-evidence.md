# Like/Follow Selector Evidence (SM-G930F, TikTok ~2026-07-27)

## Nút Like thực tế

```xml
<node index="0" text="" resource-id="com.ss.android.ugc.trill:id/fan"
  class="android.widget.ImageView" package="com.ss.android.ugc.trill"
  content-desc="Thích" checkable="false" checked="false"
  clickable="false" enabled="true" focusable="false"
  bounds="[934,983][1069,1111]" />
```

- `content-desc="Thích"` ✅ — khớp `LIKE_BUTTON_CONTENT_DESC`
- `resource-id="com.ss.android.ugc.trill:id/fan"` ❌ — KHÔNG rỗng, không khớp `resource_id=""`
- `clickable="false"` — lưu ý: không clickable trong accessibility tree, nhưng tap theo tọa độ vẫn hoạt động
- Center: `[1001, 1047]`

## Nút Follow thực tế

```xml
content-desc="Follow Deltaforce short"
```

- `content-desc` luôn có định dạng `"Follow <tên_người_dùng>"`, không bao giờ chỉ là `"Follow"`
- Nếu đã follow rồi: text hiển thị `"Following"` hoặc `"Đang follow"` (trên chính nút follow đó, element clickable)

## False positive: text "Đã follow" trên TOP TAB

Top navigation tab "Đã follow" (Following tab) có:
```xml
<node ... class="android.widget.FrameLayout" content-desc="Đã follow" clickable="true" ...>
  <node text="Đã follow" ... />
</node>
```

Nếu dùng `find_by_fields(root, resource_id=None, text="Đã follow")` → match nhầm top tab này → `already_following` trả về True → CHẶN mọi lần follow.

**Fix:** Khi check `already_following` cho tiếng Việt, phải yêu cầu `element.clickable` VÀ match text/desc của nút follow, không phải text của tab. Dùng pattern:
```python
if (desc.startswith("Following") or desc == "Đang follow" or txt == "Đang follow" or txt == "Following") and element.clickable:
    already_following = element
    break
```

## Hàm find_by_fields — cơ chế exact match

```python
def find_by_fields(root, *, text=None, content_desc=None, resource_id=None):
    for element in iter_elements(root):
        if text is not None and element.text != text:
            continue
        if content_desc is not None and element.content_desc != content_desc:
            continue
        if resource_id is not None and element.resource_id != resource_id:
            continue
        return element
    return None
```

Khi gọi `find_by_fields(root, resource_id="", content_desc="Thích")`:
- `resource_id is not None` → True (vì `""` không phải None)
- `element.resource_id != ""` → True (vì `"com.ss.android.ugc.trill:id/fan" != ""`)
- → continue → BỎ QUA element

**Quy tắc:** Truyền `None` cho field muốn bỏ qua. Truyền chuỗi rỗng `""` nghĩa là "chỉ match element có field đó rỗng".
