# Profile Switcher Network Error Retry Pattern

## Context
When switching TikTok accounts via the bottom sheet switcher, the app may show a network error overlay "Đã xảy ra lỗi / Thử lại sau" with a "Thử lại" button (resource-id `com.ss.android.ugc.trill:id/dcj`) if the network settle is slow or cache is stale. The runner was checking username immediately after tap, causing `profile username still mismatched after switch` false positives.

## Root Cause
1. Tap account in switcher sheet (`selected_account_by_exact_switcher = True`)
2. TikTok navigates to profile but network hasn't settled
3. Overlay appears: "Đã xảy ra lỗi" + "Thử lại" button (`id/dcj`)
4. Profile XML still shows old username (cached)
5. Runner checks `verify_selected_account` → fails → `manual-needed`

## Fix Pattern (in `verify_and_switch_profile`)
After tapping exact switcher account and initial verify fails:

```python
if not verified and selected_account_by_exact_switcher:
    # Parse actual XML to find "Thử lại" button (dcj) by resource-id or text
    xml_path = latest_identity.get("xml_path")
    if not xml_path and latest_identity.get("artifact_path"):
        from pathlib import Path
        xml_path = Path(latest_identity["artifact_path"]) / "ui.xml"
    tapped_retry = False
    if xml_path and os.path.exists(xml_path):
        try:
            xml_text = Path(xml_path).read_text(encoding="utf-8")
            root = parse_xml(xml_text)
            elem = find_element(root, {"resource_id": "com.ss.android.ugc.trill:id/dcj"}) \
                   or find_element(root, {"text": "Thử lại"})
            if elem and elem.center:
                cx, cy = elem.center
                ctx.adb.shell(["input", "tap", str(cx), str(cy)], timeout=ctx.timeout("adb_seconds", 5))
                tapped_retry = True
                logger.info("Tapped 'Thử lại' button at (%s, %s)", cx, cy)
        except Exception as exc:
            logger.warning("Gặp lỗi khi parse/tap Thử lại: %s", exc)
    if not tapped_retry:
        # Fallback: check text in recaptured_xml and tap hardcoded center if found
        recaptured_xml_lower = (recaptured_xml or "").lower()
        if "com.ss.android.ugc.trill:id/dcj" in (recaptured_xml or "") or "thử lại" in recaptured_xml_lower or "đã xảy ra lỗi" in recaptured_xml_lower:
            try:
                ctx.adb.shell(["input", "tap", "540", "1436"], timeout=ctx.timeout("adb_seconds", 5))
                tapped_retry = True
            except Exception as exc:
                logger.warning("Gặp lỗi khi bấm Thử lại (fallback): %s", exc)
        if tapped_retry:
            time.sleep(3.0)
        else:
            time.sleep(2.0)
    else:
        time.sleep(3.0)

    latest_identity = _read_profile_identity_with_add_phone_guard(...)
    # Re-evaluate verified with fresh identity
```

## Key Points
- **Use actual XML parsing** (`xml_path` from `latest_identity["artifact_path"]/ui.xml`) instead of string search in `recaptured_xml` (which is a stringified object, not raw XML)
- **Tap element center** (`elem.center`) instead of hardcoded coordinates (540, 1436)
- **Fallback to hardcoded** only if XML parsing fails
- **Sleep 3s after tap** for network settle before re-reading identity
- **Re-read identity** with `_read_profile_identity_with_add_phone_guard` before final verification

## Verification
- Unit test: `python_runner/tests/test_profile_switcher_retry.py` (3 passed)
- Canary test: M33 Row 3 RecoveryTestSwipes 2

## Commit
`1623c41` — `fix(switcher): add retry and tap dcj on error screen after profile switch`

## Related Patterns
- `benign_popup_registry.py::_dismiss_network_error_retry` — similar detection for network error overlay during swipe recovery
- `coordinate-fallback-after-ladder.md` — coordinate fallback as last resort after full recovery ladder
- `samsung-s7-ui-timeout-propagation.md` — S7 UI timeout handling

## Artifacts from Canary Run (2026-09-11)
- Baseline XML with dcj button: `.ai-runs/20260911-184753/machines/machine_33/.../baseline/attempt_1/ui.xml`
- Switcher verify XML with dcj button: `runtime/kibe/live/2026-09-11/row-3-120042/20260911-120048/machines/machine_33/.../profile_preflight_verify_3_identity_guard/attempt_1/ui.xml`
- Element center: (540, 1200) in baseline, (540, 1436) in verify — varies by screen state