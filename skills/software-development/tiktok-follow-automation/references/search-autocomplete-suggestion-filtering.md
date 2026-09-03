# Case UI-43: Search Autocomplete Suggestion Filtering & Mandatory Submit Before Profile Open

**Date:** 2026-09-03
**Machine:** 74 (`muyduyen4589` searching `lu.huyn926`)
**Error:** `hồ sơ identity mismatch: expected @lu.huyn926 got `

## Root Cause

When typing UID into Search input, TikTok 46.x shows an autocomplete dropdown (suggestions) with resource-ids:
- `id/tvl_unified_sug`
- `id/tvl_sug`
- `id/tvl_his`
- `id/tvl_recent_search`
- `id/tv_search_sug_word`
- `id/zsc`
- `id/candidate_layout`

These suggestion nodes:
- Have `text` matching the typed UID (or close variants)
- Are NOT clickable (`clickable=false`)
- Are rendered inside the keyboard overlay area
- Are NOT search result cards — they are predictive text candidates

`_exact_search_result_from_xml` previously:
1. Included these suggestion suffixes in `account_card_suffixes`
2. Fell through to `len(identities) == 1` branch without exclusion

This caused the function to return a suggestion node as if it were an exact search result. `_nav_search` then:
- Skipped the "Tìm kiếm" submit button tap
- Did not fire KEYCODE_ENTER fallback
- Tapped the suggestion node (no navigation effect)
- Concluded `opened=True` while screen was still on Search input with keyboard open

Profile identity check then read empty username → identity mismatch alert.

## Fix Applied

### 1. Filter in `_exact_search_result_from_xml`

```python
excluded_suffixes = (
    "id/bdu", "id/desc", "id/cover", "id/video_cover", "id/iv_cover",
    "id/tvl_unified_sug", "id/tvl_sug", "id/tvl_his", "id/tvl_recent_search",
    "id/tv_search_sug_word", "id/zsc", "id/candidate_layout",
)

identities = [
    (index, n) for index, n in enumerate(nodes)
    if n.get("bounds")
    and n.get("class") != "android.widget.EditText"
    and not n.get("editable")
    and is_tiktok_package(n.get("package"))
    and not any((n.get("resource_id") or "").rstrip("/").endswith(sfx) for sfx in excluded_suffixes)
    and _normalize_search_value(n.get("text") or "") == target
]
```

### 2. Fallback uses `initial_xml` (no re-dump)

In `_nav_search`, the KEYCODE_ENTER fallback now validates against `initial_xml` (already captured) instead of re-dumping UI:

```python
nodes = parse_nodes(initial_xml)  # not adapter.dump_ui()
```

### 3. Test Coverage Added

- `test_exact_search_result_rejects_autocomplete_suggestions_in_dropdown`
- `test_nav_search_submits_search_when_autocomplete_dropdown_present`

Both pass in full suite (499/499).

## Prevention Rules

1. **Never include suggestion/dropdown resource-ids in positive match sets** — they are semantic negatives.
2. **Always submit search explicitly** (button tap or ENTER) before waiting for results — suggestions are not results.
3. **Use exclusion list at identity extraction time** — filter before classification, not after.

## Related Files

- `follow_runner/flows/mode1_search_follow.py` — `_exact_search_result_from_xml`, `_nav_search`
- `follow_runner/tests/test_mode1_search_follow.py` — regression tests
- `docs/farm-automation-cases.md` — Case UI-43 documentation
- `docs/uiautomator.md` — Case UI-43 documentation