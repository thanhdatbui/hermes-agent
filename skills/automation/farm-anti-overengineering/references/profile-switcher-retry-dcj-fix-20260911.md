# Profile Switcher Retry Fix for "Đã xảy ra lỗi / Thử lại sau" (11/09/2026)

## Problem
After tapping exact account in TikTok switcher modal, app often shows transient network error overlay:
- Text: "Đã xảy ra lỗi", "Thử lại sau"
- Retry button: `com.ss.android.ugc.trill:id/dcj` or text "Thử lại" at ~540,1436 (1080x1920)
- Profile doesn't load new account data → verification fails with `profile username still mismatched after switch`

## Root Cause
TikTok internal network lag during profile load. The switcher tap succeeds but profile activity takes 2-3s to fetch account data. Immediate verification catches old username.

## Fix: Retry Logic in `verify_and_switch_profile` (feed_swipe_smoke.py:17374+)

```python
if not verified and selected_account_by_exact_switcher:
    recaptured_xml_lower = (recaptured_xml or "").lower()
    if ("com.ss.android.ugc.trill:id/dcj" in (recaptured_xml or "")
        or "thử lại" in recaptured_xml_lower
        or "đã xảy ra lỗi" in recaptured_xml_lower):
        # Tap retry button
        try:
            ctx.adb.shell(["input", "tap", "540", "1436"], timeout=ctx.timeout("adb_seconds", 5))
        except Exception as exc:
            logger.warning("Gặp lỗi khi bấm Thử lại: %s", exc)
        time.sleep(3.0)
    else:
        # No error overlay, just TikTok settle lag
        time.sleep(2.0)

    # Re-read profile identity and re-verify
    latest_identity = _read_profile_identity_with_add_phone_guard(
        ctx, results=results, max_swipes=max_swipes, result_kwargs=result_kwargs,
        guard_step=f"profile_preflight_verify_{attempt}_retry_identity_guard",
        after_step=f"profile_preflight_verify_{attempt}_retry_identity_after_add_phone_dismiss"
    )
    recaptured_xml = str(latest_identity.get("xml_text") or "")
    recaptured_username = _normalize_account(latest_identity.get("username"))
    recaptured_display_name = _normalize_account(latest_identity.get("display_name"))
    username_matches = bool(recaptured_username and (
        recaptured_username == expected_norm
        or matches_switcher_identity(recaptured_username, expected)
    ))
    display_name_matches = bool(recaptured_display_name and (
        recaptured_display_name == expected_norm
        or matches_switcher_identity(recaptured_display_name, expected)
    ))
    verified = bool(
        selected_account_by_exact_switcher
        and latest_identity.get("xml_available") is True
        and recaptured_xml
        and not _is_profile_account_switcher_xml(recaptured_xml)
        and (not recaptured_username or username_matches or display_name_matches)
    )
    selected_account_recaptured_without_handle = verified and not recaptured_username and not display_name_matches
```

## Test
`python_runner/tests/test_profile_switcher_retry.py` — 3 unit tests covering:
1. Error XML with `dcj` ID triggers retry
2. Error XML with "thử lại" text triggers retry
3. Normal XML does not trigger retry

**Result**: 3 passed in 0.22s

## Commit
`1623c41` — `fix(switcher): add retry and tap dcj on error screen after profile switch`

## Files Changed
- `python_runner/flows/feed_swipe_smoke.py` (+47 lines)
- `python_runner/tests/test_profile_switcher_retry.py` (new, 44 lines)