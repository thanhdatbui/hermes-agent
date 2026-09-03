# Stat Column Isolation & Content-Desc Handle Verification in Mode 2

## 1. Stat Column Alignment Isolation for Zero-Following Detection

TikTok profile headers display statistics (Following, Followers, Likes) in adjacent vertical columns. Each stat cell typically contains:
- A count TextView (e.g., `"10"`, `"0"`, `"1.2K"`)
- A label TextView (e.g., `"Đang follow"`, `"Follower"`, `"Thích"`)

### The Adjacent-Column Misclassification Pitfall
If proximity matching between the `"0"` count and the `"Đang follow"` label uses a broad bounding box (e.g., `dx <= 360, dy <= 140`), an account with `10 Following / 0 Followers` will match the `"0"` from the adjacent Followers column with the `"Đang follow"` label! This results in:
- False-positive `zero_following` classification.
- Erroneously skipping a valid anchor with 10 following accounts.

### Strict Alignment Solution
Calculate node horizontal centers: `cx = bounds[0] + bounds[2] / 2.0`.
Require:
1. **Horizontal center alignment**: `abs(label_cx - count_cx) <= 70px` (guarantees same column).
2. **Vertical proximity**: `abs(label_y - count_y) <= 100px` (guarantees same stat cell).
3. **Stat resource-ID evidence**: Count node resource-id must match known stat counter IDs (`_STAT_COUNTER_IDS`).

---

## 2. Profile Handle in `content_desc` (TikTok 46.x)

Certain TikTok 46.x builds place the profile handle inside `content_desc` (e.g., `content-desc="@username"`) while leaving `text=""` on the button/view.

### Strict Verification Rules
- When extracting and matching `@handle` in the profile header band (`y < 650`):
  ```python
  values = [node.get("text") or "", node.get("content_desc") or ""]
  is_match = any(
      v.strip().startswith("@") and _normalize_handle(v) == target_normalized
      for v in values
  )
  ```
- **Fail-Closed Gate**: Exactly one matching header handle node must exist, and its normalized bounds `(left, top, right, bottom)` must match `username_element.bounds` from `automation_core` (or fail closed if `username_element` is missing).

---

## 3. Relation Surface Header Compact Counts

Relation surface tab headers (`android:id/text1`) display follower/following counts that may be:
- Plain integers: `"Đang follow 15"`
- Grouped integers: `"Following 1,234"`
- Compact/abbreviated numbers: `"Following 1.2K"`, `"Follower 10.5M"`

`_FOLLOWER_HEADER_RE` must match:
```python
r"^(follower|followers|người theo dõi|đã follow|đang follow|đang theo dõi|following|bạn bè|được đề xuất)(?:\s+([\d.,]+[kmbt]?))?$"
```
This ensures modern relation tabs are recognized as populated lists without triggering false `invalid` surface classifications and timeouts.
