# TikTok Account Switcher: Resource-ID Suffixes & Prepare Guard Pattern

## Context
In `automation-core/src/automation_core/tiktok/account_switcher.py`, `open_switcher()` handles opening the TikTok account switcher sheet from the profile screen.

## 1. Resource-ID Suffix Expansion
Different versions of the TikTok client (and different farm devices) obfuscate or assign varying resource-ids to the username / account-switcher anchor button in the top profile header.

Known suffixes registered in `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`:
- Standard / classic: `rv5`, `ryo`, `s0g`, `s3f`, `rz5`, `rn8`, `p48`, `pcq`, `pmi`, `pke`, `pmf`
- Modern expanded: `qzs`, `r0k`, `r1a`, `r2b`, `s1g`, `pmg`, `pnk`, `pnl`
- Observed on Samsung Galaxy S7 (Machine 40, TikTok update):
  - Node: `com.ss.android.ugc.trill:id/pq2`
  - Bounds: `[366, 72][720, 228]`
  - Suffix: `pq2`

When encountering a new device or build where the profile header is visible but `find_switcher_anchor()` fails to resolve it:
1. Inspect the UI XML dump from the device.
2. Check the `resource-id` of the username text node at the header top.
3. Extract the suffix after `:id/` and append it to `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`.
4. Update unit tests in `tests/test_account_switcher_preconfirmed.py` (`test_find_switcher_anchor_accepts_new_tiktok_ui_suffixes`).

## 2. Pitfall: The Prepare Guard Infinite Continue Loop
In `open_switcher()`, if the anchor node is not detected initially, the adapter may invoke `prepare_switcher_anchor()` (e.g. performing a small nudge/swipe on the profile to reveal headers).

### Bad Pattern (Bug)
```python
if anchor is None:
    prepare = getattr(adapter, "prepare_switcher_anchor", None)
    if callable(prepare):
        if prepare() is not False:
            continue
```
If `prepare()` returns `True` (indicating swipe succeeded), but the anchor remains undetectable in the UI XML on every retry, `prepare()` executes on **every attempt** (attempt 0, 1, ...).
The loop `continue`s every time and exhausts all attempts, **never reaching the fallback tap** (coordinate fallback / viewport-ratio tap) located further down.

### Correct Pattern (Bounded to Attempt 0)
```python
if anchor is None and attempt == 0:
    prepare = getattr(adapter, "prepare_switcher_anchor", None)
    if callable(prepare):
        if prepare() is not False:
            continue
```
- **Attempt 0**: If anchor is missing, execute `prepare()` once to nudge UI and refresh.
- **Attempt 1+**: If anchor is still `None`, do NOT re-swipe. Fall through to the coordinate / viewport ratio tap (`center-x=sw//2, center-y=sh*(150/1920)`).
