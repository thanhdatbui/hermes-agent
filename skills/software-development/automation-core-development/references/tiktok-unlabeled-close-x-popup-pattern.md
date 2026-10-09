# Unlabeled Close Button Fallback in TikTok Popups (Quick Security Pattern)

## Problem Context
On certain TikTok modal dialogs (such as the quick security check "Hãy cùng kiểm tra bảo mật nhanh nhé" seen on Samsung farm devices), the close `X` button does not carry text (`text=""`) or accessibility description (`content-desc=""`). 

Previously, detectors strictly relying on `_find_exact_label_element(elements, ("Đóng",))` failed to locate the dismiss target, causing benign popups to block automation or fail benign dismissal.

## Detection Pattern & Invariants
When an explicit label ("Đóng", "Close", etc.) is absent, inspect candidate UI elements under the matched popup screen with geometric and attribute constraints:

1. **Popup Title / Context Precondition**:
   - Ensure primary context markers (e.g. `quick_security_title`) are strictly matched first before looking for unlabeled buttons. Never attempt blanket unlabeled button matching without strong popup markers.

2. **Unlabeled Top-Right Modal Close Button Invariants**:
   - `el.attrib.get("clickable", "").lower() == "true"` (or `android.widget.Button` / `android.widget.ImageView`).
   - `not (el.text or "").strip() and not (el.content_desc or "").strip()` (truly unlabeled).
   - Bounds validation:
     - Top-right horizontal positioning: `el.bounds[0] >= 800` (on standard 1080x1920 or 720x1280 displays).
     - Compact square/icon bounds: `50 <= width <= 200` and `50 <= height <= 200`.
   - Marker assignment: emit a distinct marker like `"close_x_unlabeled"` to keep diagnostics auditable.

## Unit Test Fixture Pattern
Always verify unlabeled dismiss buttons with a minimal synthesized hierarchy:
```xml
<hierarchy>
  <node class="android.widget.TextView" text="Hãy cùng kiểm tra bảo mật nhanh nhé" bounds="[96,1298][984,1464]" />
  <node class="android.widget.Button" text="" content-desc="" clickable="true" bounds="[936,866][1056,998]" />
  <node class="android.widget.Button" text="Tiếp tục" clickable="true" bounds="[48,1717][1032,1872]" />
</hierarchy>
```
Verify:
- `match.popup_type == "quick_security"`
- `match.action == "dismiss_close_x"`
- `match.close_element.bounds == (936, 866, 1056, 998)`
