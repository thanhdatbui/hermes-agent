---
title: Email Subscription Popup at verify_profile (Case UI-FEED-EMAIL-01)
date: 2026-09-02
repos: [tiktok-luot nuoi acc, automation-core]
status: FIXED
---

## Problem
At step `verify_profile` (after swipe 10), TikTok shows an email subscription popup:
- Text: `Nhận thông tin cập nhật qua email của bạn?` (resource-id: `com.ss.android.ugc.trill:id/bw5`)
- Description: `Bạn cũng sẽ nhận được nội dung thịnh hành, bản tin, chương trình khuyến mãi...` (resource-id: `com.ss.android.ugc.trill:id/bw0`)
- Button: `Nhận thông tin cập nhật` at [132,1632][948,1788]
- No close/X button visible in XML

This popup covers the entire screen. Script attempts to navigate to Profile tab → XML dump shows only popup → `navigation target profile not found in XML` error → session stopped with `manual-needed`.

## Root Cause
No rule existed in either `automation-core/src/automation_core/tiktok_popup.py` or `tiktok-luot nuoi acc/python_runner/flows/benign_popup_registry.py` to detect/dismiss this popup.

## Fix Applied
Added to `benign_popup_registry.py` (tiktok-luot nuoi acc):

```python
def _detect_email_subscription_popup(xml_content: str = "", ocr_text: str = "") -> bool:
    """Detect TikTok 'Nhận thông tin cập nhật qua email?' subscription popup."""
    markers = [
        "Nhận thông tin cập nhật qua email",
        "receive email updates",
        "com.ss.android.ugc.trill:id/bw5",
    ]
    combined = (xml_content or "") + " " + (ocr_text or "")
    return any(m in combined for m in markers)


def _dismiss_email_subscription_popup(ctx: Any) -> Any:
    """Dismiss email subscription popup bằng keyevent BACK."""
    from .benign_popup import PopupDismissResult
    before = {"screen": "email_subscription_popup"}
    try:
        if not send_device_back_key(ctx):
            return PopupDismissResult(
                dismissed=False,
                reason="no_action_capability_on_email_subscription_popup",
                before_attempt=before,
                popup_closed=False,
            )
        time.sleep(0.8)
        return PopupDismissResult(
            dismissed=True,
            reason="dismissed_email_subscription_popup_via_back",
            before_attempt=before,
            popup_closed=True,
        )
    except Exception as exc:
        return PopupDismissResult(
            dismissed=False,
            reason=f"failed_dismiss_email_subscription_popup: {exc}",
            before_attempt=before,
            popup_closed=False,
        )

# Registered with priority 74 (after inapp_browser_overlay at 75)
register_popup_handler(RegistryEntry("email_subscription_popup", 74, _detect_email_subscription_popup, _dismiss_email_subscription_popup, True, "manual"))
```

## Verification
- `python_runner/tests/test_benign_popup_registry.py` — PASS
- `python_runner/tests/test_feed_swipe_smoke_popups.py` — PASS
- Commit: `fix(popup): detect and dismiss TikTok email subscription popup at verify_profile step (Case UI-FEED-EMAIL-01)`

## Diagnostic Pattern (CRITICAL)
When investigating machine errors:
- **DO NOT** use `grep -rn` recursively on repos or `.ai-runs` directories (huge, slow)
- **DO** go directly to machine artifact directory:
  ```
  D:\Taadaa\runtime\kibe\live\<date>\row-<X>-<timestamp>\<run-id>\machines\machine_<N>\<run-id>\
  ```
- Read `summary.txt` and `log.jsonl` directly from there
- This is the only reliable way to see the exact UI state at failure time