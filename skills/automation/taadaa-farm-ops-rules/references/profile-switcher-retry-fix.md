# Profile Switcher Retry Fix (TikTok "Đã xảy ra lỗi / Thử lại sau")

**Date:** 2026-09-11
**Context:** Batch alert on 80 machines, 10 machines failed with `script-blocker:profile username still mismatched after switch`
**Root Cause:** After tapping account switcher, TikTok shows transient error overlay "Đã xảy ra lỗi / Thử lại sau" (resource-id `com.ss.android.ugc.trill:id/dcj`, text "Thử lại"). Profile doesn't load new account's username → immediate verify fails.

## Fix Applied (feed_swipe_smoke.py: verify_and_switch_profile)

```python
if not verified and selected_account_by_exact_switcher:
    recaptured_xml_lower = (recaptured_xml or "").lower()
    if "com.ss.android.ugc.trill:id/dcj" in (recaptured_xml or "") \
       or "thử lại" in recaptured_xml_lower \
       or "đã xảy ra lỗi" in recaptured_xml_lower:
        try:
            ctx.adb.shell(["input", "tap", "540", "1436"], timeout=ctx.timeout("adb_seconds", 5))
        except Exception as exc:
            logger.warning("Gặp lỗi khi bấm Thử lại: %s", exc)
        time.sleep(3.0)
    else:
        time.sleep(2.0)
    # Re-read identity via _read_profile_identity_with_add_phone_guard + re-verify
    # username/display_name vs expected_norm or matches_switcher_identity
```

## Key Patterns
- **Detection:** Check XML for `com.ss.android.ugc.trill:id/dcj` or Vietnamese text "thử lại" / "đã xảy ra lỗi"
- **Action:** Tap retry button at ~540,1436 (1080x1920) + 3s settle
- **Fallback:** If no error overlay, still sleep 2s for normal transition lag
- **Re-verify:** Full identity re-read + username/display_name match logic

## Unit Test
`python_runner/tests/test_profile_switcher_retry.py` — 3 tests covering:
1. Error XML triggers retry branch
2. "Thử lại" text triggers retry branch
3. Normal XML does NOT trigger retry

## Commit
`1623c41` — `fix(switcher): add retry and tap dcj on error screen after profile switch`
