# Tab Navigation Friends/Following Popup Fallback Architecture

## Context & Problem
During TikTok feed automation (`feed_swipe_smoke.py` / `_feed_session_flow`), the runner periodically switches from `for-you` to `friends` or `following` tabs (e.g. `switch_friends_<N>` or `switch_following_<N>`).
On Samsung farm devices running TikTok v47.0.3 / v46.6.3:
- Entering the `friends` tab frequently triggers contact sync permission dialogs (`contacts_settings_permission_dialog`) or contact follow suggestion sheets (`contact_follow_suggestion`).
- Even after dismissers (allowlist dismiss, blind probe, or BACK action) handle the popup, the subsequent observation / confirm step may still detect `manual-needed:popup` or land on empty friends suggestions.
- When two consecutive checks return `manual-needed`, `ManualReasonGuard` records consecutive failure and trips.
- If unhandled, this prematurely aborts the feed session (`stop_reason: unexpected popup/dialog marker detected` or `manual review required`), leaving the device with 0 or few completed swipes and triggering watchdog farm alerts ("Lỗi App TikTok/Script").

## Architecture: Graceful For-You Tab Fallback

Inside `_feed_session_flow` at the tab navigation confirm checkpoint:
```python
if manual_guard.record(_safety_from_row(ctx, confirm)):
    if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and (
        confirm.get("detected") in {"manual-needed:network", "manual-needed:empty", "manual-needed:retry", "manual-needed:popup"}
        or _has_friends_feed_content(confirm)
    ):
        ctx.logger.log(
            device_id=ctx.device_id,
            account=ctx.account,
            step=f"{artifact_prefix}/switch_{next_feed_type}_{swipe_count}_empty_feed_fallback_for_you",
            action="fallback_feed_tab",
            result="warning",
            extra={
                "failed_target": next_feed_type,
                "fallback_target": FEED_TYPE_FOR_YOU,
                "reason": "empty_following_or_network_or_popup_fallback_to_for_you",
                "detected": confirm.get("detected"),
                "safety_status": confirm.get("safety_status"),
            },
        )
        # Graceful fallback: Tap back to For You feed and continue session quota
        tap_navigation_target(
            ctx,
            _top_tab_target(FEED_TYPE_FOR_YOU),
            current_top_tab=next_feed_type,
            artifact_prefix=artifact_prefix,
            log_prefix=artifact_prefix,
        )
        current_feed_type = FEED_TYPE_FOR_YOU
        next_feed_type = FEED_TYPE_FOR_YOU
        confirm["status"] = ExitStatus.DEGRADED.value
        confirm["safety_status"] = "ok"
        videos_until_tab_decision = random.randint(5, 10)
    else:
        results.append(confirm)
        _store_partial_result(ctx, results, max_swipes, **result_kwargs)
        return finalize_feed_session_cleanup(ctx, ...)
```

## Critical Invariants & Pitfalls

1. **Guard Ordering Invariant:**
   - NEVER bypass `manual_guard.record(...)` by putting fallback conditions before the guard.
   - The guard ensures transient popups are given dismiss opportunities first, and prevents infinite bouncing/looping across tabs.
2. **Detection Set Invariant:**
   - The fallback condition MUST include `"manual-needed:popup"` alongside `"manual-needed:network"`, `"manual-needed:empty"`, `"manual-needed:retry"`, and `_has_friends_feed_content(confirm)`.
3. **Telemetry Observability:**
   - Always log `failed_target`, `fallback_target`, `reason`, `detected`, and `safety_status` in `extra` for auditability in `log.jsonl`.
4. **Session Quota Preservation:**
   - Setting `confirm["status"] = ExitStatus.DEGRADED.value` and resetting `videos_until_tab_decision = random.randint(5, 10)` allows the device to stay on the main For You feed and complete its requested swipe quota (e.g. 17-22 swipes) instead of failing the run.
