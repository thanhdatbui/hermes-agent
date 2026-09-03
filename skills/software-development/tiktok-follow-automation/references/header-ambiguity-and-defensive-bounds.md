# Header Ambiguity Resolution & Defensive Bounds Handling

This reference documents the canonical patterns and pitfalls discovered for profile header identity validation, UI bounds parsing, safe result payloads, and zero silent failures logging in `tiktok-follow`.

## 1. Defensive Bounds Validation & Safe Geometry Calculations

### Pitfall
UI XML dump from ATX/uiautomator can occasionally emit malformed, scalar, dict, NaN, infinite, or overflowing values for `bounds` (e.g. `[100, "nan"]`, `[100, 10**10000]`, `{"x": 100}`, `"not_a_list"`). Direct conversion or calculation throws unhandled `TypeError`, `ValueError`, `IndexError`, or `OverflowError`, crashing runner logic unexpectedly.

### Solution
Use a centralized bounds validator with strict component-wise validation before calculating any geometrical values (`center_x`, `center_y`, `top_y`, `bottom_y`, `left_x`):

```python
def _valid_bounds(node: dict) -> tuple[float, float, float, float] | None:
    """Extract and validate (x, y, w, h) bounds.

    Bounds list must have exactly 4 elements. Each component must be finite,
    non-negative (>= 0.0), <= 10000.0, and end coordinates (x+w, y+h) must not exceed 10000.0.
    """
    if not isinstance(node, dict):
        return None
    try:
        b = node.get("bounds")
        if not isinstance(b, (list, tuple)) or len(b) != 4:
            return None
        x, y, w, h = float(b[0]), float(b[1]), float(b[2]), float(b[3])
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(w) and math.isfinite(h)):
            return None
        if x < 0.0 or y < 0.0 or w < 0.0 or h < 0.0:
            return None
        if x > 10000.0 or y > 10000.0 or (x + w) > 10000.0 or (y + h) > 10000.0:
            return None
        return (x, y, w, h)
    except (TypeError, IndexError, KeyError, ValueError, OverflowError):
        return None
```

## 2. Header @-Handle Ambiguity vs Duplicate Representations

### Pitfall
1. **Ambiguous distinct handles**: An imposter or secondary account might place a mention `@partner` or bio link in the top header (`y < 650`). If code accepts any `@` node, it may follow the wrong user.
2. **Duplicate representations of the SAME handle**: Accessibility trees in modern TikTok 46.x frequently render both a `text="@target"` TextView and an enclosing layout with `content-desc="@target"`, or split node representations for the same user. Rejecting whenever `len(header_nodes) > 1` causes false rejections of valid profiles.

### Solution
Extract all header nodes matching strict handle regex (`^@[a-zA-Z0-9_.]+$`), normalize them, and verify that the set of distinct handles contains exactly 1 unique identity matching `target_uid`:

```python
_HANDLE_FIELD_RE = re.compile(r"^@[a-zA-Z0-9_.]+$")

def _find_header_handle_node(nodes: list[dict], target_uid: str) -> tuple[dict | None, str]:
    target_normalized = _normalize_handle(target_uid)
    header_at_nodes: list[tuple[dict, str]] = []

    for n in nodes:
        if not isinstance(n, dict):
            continue
        top_y = _node_top_y(n)
        if top_y is None or top_y >= 650:
            continue
        t = (n.get("text") or "").strip()
        cd = (n.get("content_desc") or "").strip()
        t_is_at = bool(_HANDLE_FIELD_RE.fullmatch(t))
        cd_is_at = bool(_HANDLE_FIELD_RE.fullmatch(cd))
        if not (t_is_at or cd_is_at):
            continue

        if t_is_at and cd_is_at:
            if _normalize_handle(t) != _normalize_handle(cd):
                return None, "conflict_node"
            handle = _normalize_handle(t)
        elif t_is_at:
            handle = _normalize_handle(t)
        else:
            handle = _normalize_handle(cd)

        header_at_nodes.append((n, handle))

    if not header_at_nodes:
        return None, "missing_header_handle"

    distinct_handles = {h for _, h in header_at_nodes}
    if len(distinct_handles) > 1:
        return None, f"ambiguous_duplicate_header_handle: {distinct_handles}"

    node, node_handle = header_at_nodes[0]
    if node_handle != target_normalized:
        return None, f"identity mismatch: expected @{target_uid} got @{node_handle}"

    return node, "ok"
```

## 3. Safe Payload Extraction for List Fields & Contract Invariants

### Pitfall
1. Calling `list(get("followed") or [])` on an unexpected bare string (e.g. `"alice"`) splits it into individual characters `['a', 'l', 'i', 'c', 'e']`, while passing an int causes `TypeError`.
2. Silently converting invalid types to `[]` and keeping `status="OK"` creates silent contract corruption where technical bugs are reported as clean successes.
3. Using `isinstance(val, (list, tuple))` allows subclasses that override `__iter__` or `__len__` to hang or crash the runner.
4. If a payload has malformed collections but also has `follow_failed=True`, failing to clear `follow_failed` causes downstream alerting to mistake a technical contract corruption for a business cooldown.

### Solution
Use `_safe_string_list` with exact type check, iteration item cap, element length cap, and exception logging with traceback. If any collection field is invalid, aggregate all errors, set `status="CONTRACT_ERROR"`, `failed=True`, and clear `follow_failed=False`:

```python
def _safe_string_list(val: Any, field_name: str, max_items: int = 1000, max_item_len: int = 256) -> tuple[list[str], str | None]:
    """Validate and convert list/tuple to list of bounded strings.

    Returns:
        (converted_list, None) on success.
        ([], error_message) if val is not an exact list/tuple, exceeds length,
        or an element cannot be safely converted to a bounded string.
    """
    if val is None:
        return [], None
    if type(val) not in (list, tuple):
        return [], f"field {field_name} must be exact list or tuple, got {type(val).__name__}"
    try:
        res = []
        count = 0
        for x in val:
            count += 1
            if count > max_items:
                return [], f"field {field_name} exceeds max length {max_items}"
            s = str(x)
            if len(s) > max_item_len:
                return [], f"field {field_name} element exceeds max length {max_item_len}"
            res.append(s)
        return res, None
    except Exception as exc:
        logger.exception("_safe_string_list error on field %s: %s", field_name, exc)
        return [], f"field {field_name} iteration/stringification error: {type(exc).__name__}: {exc}"
```

In `_result_payload()`:
```python
    errs: list[str] = []
    followed, err_followed = _safe_string_list(get("followed"), "followed")
    if err_followed:
        errs.append(err_followed)
    skipped, err_skipped = _safe_string_list(get("skipped"), "skipped")
    if err_skipped:
        errs.append(err_skipped)
    failed_ids, err_failed_ids = _safe_string_list(get("failed_ids"), "failed_ids")
    if err_failed_ids:
        errs.append(err_failed_ids)

    if errs:
        combined_err = "; ".join(errs)
        logger.error("_result_payload contract violation on machine %s: %s", machine, combined_err)
        status = "CONTRACT_ERROR"
        failed = True
        follow_failed_flag = False
        reason = f"CONTRACT_ERROR: {combined_err}{(' (' + reason + ')') if reason else ''}"
    elif status == "OK" and follow_failed_flag:
        status = "CONTRACT_ERROR"
        failed = True
        follow_failed_flag = False
        reason = f"CONTRACT_ERROR: status=OK nhưng follow_failed=True{(' (' + reason + ')') if reason else ''}"
```

## 4. Zero Silent Failures & Traceback Logging

Always use `logger.exception(...)` when catching unexpected runtime exceptions in I/O wrappers (`dump_ui`, `close_all_recent_apps`, `profile_identity_from_xml`, recovery tap helpers). Include forensic context such as `uid`, `dump_len`, and `is_reload=True/False`. Never catch bare exceptions silently or convert them to simple `logger.warning("%s", exc)` without traceback context when diagnosing farm failures.

## 5. Consecutive Dump Verification for Zero-Following Detection

### Pitfall
Detecting `zero_following` immediately on the first UI dump during post-tap transition can falsely trigger on stale dumps or intermediate screens where headers haven't finished rendering.

### Solution
In polling loops (e.g. `_open_following_tab`), require at least 2 consecutive positive evaluations of `_is_zero_following_screen_or_profile` before setting `engine._last_anchor_follow_outcome = "zero_following"` and breaking the loop.
