# TikTok Benign Popup Unlabeled Close Button Detection

## Problem & Context

TikTok popups (such as "Add Phone" / "Thêm số điện thoại", "Quick Security", "Update", etc.) on Samsung Galaxy devices often render the top-right dismissal button without text or accessibility description (`NAF="true"`, `content-desc=""`, `text=""`).

When benign popup detectors only inspect `element.content_desc` or `element.text` matching explicit string labels (e.g. `_ADD_PHONE_CLOSE_LABELS` like `Đóng`, `Close`, `Bỏ qua`), the close button is completely missed. This prevents dismissing benign blocking overlays during automation.

## Canonical Pattern (`_close_candidate` in `benign_popup.py`)

To reliably detect both labeled and unlabeled dismissal controls while preventing false positives:

1. **Spatial Boundaries (1080x1920 Galaxy standard):**
   - Ensure `element.center` and `element.bounds` exist.
   - Enforce header / top-right boundary: `left >= 800` and `top <= 350`.
2. **Exclude Positive Action Buttons:**
   - Filter out explicit action buttons like `tiếp tục`, `continue`.
3. **Dual Candidate Pools (Labeled Priority with Unlabeled Fallback):**
   - Labeled candidates: `(element.content_desc or element.text).strip().casefold() in close_terms`.
   - Unlabeled candidates: `not label` AND (`clickable == "true"` or `"button" in class.lower()` or `"image" in class.lower()`).
   - Prioritize labeled matches over unlabeled fallbacks: `pool = candidates or unlabeled_candidates`.
4. **Deterministic Tie-Breaking:**
   - Sort candidates by `(item.bounds[1], -item.bounds[0])` to pick the topmost, rightmost candidate.

## Reference XML Sample

```xml
<hierarchy>
  <node NAF="true" index="1" text="" resource-id="" class="android.widget.Button" package="com.ss.android.ugc.trill" content-desc="" clickable="true" bounds="[936,84][1056,216]" />
  <node text="Thêm số điện thoại" />
  <node text="+84" />
  <node text="Số điện thoại" />
  <node text="Tiếp tục" />
</hierarchy>
```
Expected output:
- `close_bounds = (936, 84, 1056, 216)`
- `close_center = (996, 150)`
- `markers` contains `"close_x"`
