# account_switcher.py — Resilient Anchor Patterns

Source: `D:\Taadaa\automation-core\src\automation_core\tiktok\account_switcher.py`  
Tests: `tests/test_account_switcher_preconfirmed.py`

---

## 1. Resource-ID Suffix Expansion

`_SWITCH_ANCHOR_RESOURCE_SUFFIXES` is a `frozenset` of known TikTok obfuscated
resource-ID suffixes that identify the profile-name/switcher-anchor node.

**Pattern for adding new suffixes** (when a device surfaces an unknown suffix
that should work as a switcher anchor):

```python
_SWITCH_ANCHOR_RESOURCE_SUFFIXES = frozenset(
    {
        # Original set
        "rv5", "ryo", "s0g", "s3f", "rz5", "rn8", "p48", "pcq", "pmi", "pke", "pmf",
        # Added 2026-09 (resilient switcher anchor expansion)
        "qzs", "r0k", "r1a", "r2b", "s1g", "pmg", "pnk", "pnl",
        # Semantic names (stable)
        "profile_header_name", "account_name", "profile_header_username", "tv_username",
    }
)
```

**Verification**: add a `@pytest.mark.parametrize` test per suffix:
```python
@pytest.mark.parametrize("suffix", ["qzs", "r0k", ...])
def test_find_switcher_anchor_accepts_new_tiktok_ui_suffixes(suffix):
    xml = f"""<hierarchy>...<node resource-id="com.ss.android.ugc.trill:id/{suffix}" .../>...</hierarchy>"""
    anchor = find_switcher_anchor(xml, None, allow_generic_header=True)
    assert anchor is not None
```

---

## 2. `username_candidates` Strict-Gate + Profile-Menu Fallback

**Problem solved**: `@username` nodes in the body of the profile page (below
the sticky header band) were being picked as the switcher anchor.

**Geometry constants** (relative to 1080×1920):
- `header_y   = height * 250/1920`  → strict band top (~250 px)
- `generic_header_y = height * 320/1920` → extended band (~320 px)

**Correct logic** (two-pass):

```python
# Pass 1 — strict gate: only @-prefixed nodes within header_y
username_candidates = [
    node for node in nodes
    if node.center is not None
    and header_left <= node.center[0] <= header_right
    and node.center[1] <= header_y          # strict — NOT generic_header_y
    and node.text.strip().startswith("@")
]

# Pass 2 — fallback: with profile_menu signal, widen to generic_header_y
# but resolve ONLY the topmost (min center_y) node to avoid ambiguity
if not username_candidates and has_profile_menu:
    extended = [
        node for node in nodes
        if node.center is not None
        and header_left <= node.center[0] <= header_right
        and node.center[1] <= generic_header_y
        and node.text.strip().startswith("@")
    ]
    if extended:
        username_candidates = [min(extended, key=lambda n: n.center[1])]
```

**Key pitfall** — old code used a single-pass `OR` condition:  
`(node.center[1] <= header_y OR (has_profile_menu AND clickable))`.  
This is wrong because `has_profile_menu` alone doesn't make it safe to pick
*any* clickable @username — there may be multiple @username nodes.  
The new two-pass approach ensures at most one candidate is ever produced.

---

## 3. Viewport-Ratio Last-Resort Tap in `open_switcher()`

**Purpose**: after semantic anchor, `switcher_image_point`, and
`coordinate_fallback` all fail to resolve a tap target, use a hard-coded
viewport-ratio coordinate as a last resort instead of immediately raising
`SWITCHER_ANCHOR_AMBIGUOUS`.

**Geometry**: `(sw // 2, int(sh * 150/1920))` — centre-x, ~8% from top.  
On 1080×1920 this is `(540, 150)`, which lands in the profile-name band
for virtually all TikTok UI versions.

```python
screen_size_fn = getattr(adapter, "screen_size", None)
try:
    sw, sh = screen_size_fn() if callable(screen_size_fn) else (1080, 1920)
except Exception:
    sw, sh = 1080, 1920
fallback_x = sw // 2
fallback_y = int(sh * (150 / 1920))
point = (fallback_x, fallback_y)
```

**Consequence for existing tests**: the error code that legacy adapters
(no `coordinate_fallback` hook) see on complete anchor failure changes from
`SWITCHER_ANCHOR_AMBIGUOUS` → `SWITCHER_NOT_CONFIRMED` (because the ratio tap
fires, then the post-tap dump check confirms the switcher didn't open).

**Test pattern** — split original single test into two:
```python
def test_open_switcher_no_fallback_ratio_tap_succeeds():
    # dumps = [no-anchor-xml, switcher-xml] → ratio tap fires, switcher opens → success
    result = open_switcher(adapter, pre_confirmed_xml=NO_ANCHOR_XML, attempts=1)
    assert result == SWITCHER_XML
    tap_x, tap_y = adapter.taps[0]
    assert tap_x == 540
    assert 120 <= tap_y <= 180

def test_open_switcher_no_fallback_ratio_tap_not_confirmed():
    # dump always returns no-anchor-xml → ratio tap fires, still no switcher
    with pytest.raises(AccountSwitcherError) as exc_info:
        open_switcher(adapter, pre_confirmed_xml=NO_ANCHOR_XML, attempts=1, load_attempts=1)
    assert exc_info.value.code == "SWITCHER_NOT_CONFIRMED"
    assert len(adapter.taps) == 1
```

---

## 4. Anchor Fallback Priority Chain (full picture)

In `open_switcher()` after anchor is `None`:

1. `adapter.switcher_image_point()` — image template match
2. `adapter.coordinate_fallback("switcher")` — consumer-supplied hardcoded coords
3. **viewport ratio tap at `(sw//2, sh*150/1920)`** ← new last resort
4. `SWITCHER_ANCHOR_AMBIGUOUS` is now unreachable for adapters that have a
   working `tap()` method; it's only raised if `point` is still `None` after
   step 3, which can't happen unless step 3's geometry calculation itself
   throws unexpectedly.
