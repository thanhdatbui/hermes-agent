# TikTok Shop CTA Popup Detection (2026-08-07)

## Popup: "Mua ngay" / "Đóng"

TikTok Shop overlay with two buttons:
- **"Mua ngay"** (buy CTA) — clicks through to purchase flow
- **"Đóng"** (close) — safe dismiss

Both are `clickable="true"` `android.widget.Button` elements in TikTok's package context
(`com.ss.android.ugc.trill`).

## Resource ID variants observed

| Variant | Buy ID | Close ID |
|---|---|---|
| Standard | `com.ss.android.ugc.trill:id/h5_` | `com.ss.android.ugc.trill:id/h5f` |
| HN | `com.ss.android.ugc.trill:id/hn6` | `com.ss.android.ugc.trill:id/hnb` |
| HCK | `com.ss.android.ugc.trill:id/hck` | `com.ss.android.ugc.trill:id/hcq` |

Resource IDs vary across TikTok builds — don't match on them. Match on `text == "Mua ngay"`
and `text == "Đóng"` only.

## Implementation (`core/benign_popup.py`)

```python
TIKTOK_PACKAGE = "com.ss.android.ugc.trill"

def detect_tiktok_shop_cta_popup(root):
    elements = list(iter_elements(root))
    buy_button = None
    close_button = None
    for element in elements:
        if element.attrib.get("clickable") != "true":
            continue
        if "button" not in element.attrib.get("class", "").casefold():
            continue
        pkg = element.attrib.get("package", "")
        rid = element.attrib.get("resource-id", "")
        if TIKTOK_PACKAGE not in pkg and TIKTOK_PACKAGE not in rid:
            continue
        text = (element.text or "").strip()
        if text == "Mua ngay":
            buy_button = element
        elif text == "\u0110\u00f3ng":
            close_button = element
    if buy_button is None or close_button is None:
        return None
    return BenignPopupMatch(
        "shop_cta",
        ["shop_cta_buy", "shop_cta_close"],
        close_button,  # Đóng = safe action
    )
```

Key decisions:
- **close_element = "Đóng"**, not "Mua ngay" — tapping "Mua ngay" opens purchase flow; "Đóng" is the safe dismiss
- **Package scoping** — both `package` and `resource-id` attrs must contain `TIKTOK_PACKAGE`. Prevents
  false positives from other apps with matching Vietnamese button text.
- **Both buttons required** — won't match if only one button is present

## Dispatcher integration

Follows the same pattern as `detect_add_phone_popup`:

```python
def detect_tiktok_popup_action(root, **kwargs):
    match = detect_add_phone_popup(root)
    if match is not None:
        return _impl._action_match(match)
    match = detect_tiktok_shop_cta_popup(root)
    if match is not None:
        return _impl._action_match(match)
    return _impl.detect_tiktok_popup_action(root, **kwargs)
```

Shop CTA checked AFTER add-phone, BEFORE core fallback. `_action_match` converts
`BenignPopupMatch` → `TikTokPopupActionMatch` with action `dismiss_close_x`.

## Tests

`TestTikTokShopCTAPopup` in `tests/test_benign_popup.py`:
- `test_detect_shop_cta_standard` — standard resource-id variant
- `test_detect_shop_cta_hn_variant` — HN variant
- `test_detect_shop_cta_hck_variant` — HCK variant
- `test_no_match_without_close` — only "Mua ngay" → None
- `test_no_match_without_buy` — only "Đóng" → None
- `test_no_match_outside_tiktok` — correct text but different package → None

All tests assert `close_element.text == "Đóng"` (not "Mua ngay").
