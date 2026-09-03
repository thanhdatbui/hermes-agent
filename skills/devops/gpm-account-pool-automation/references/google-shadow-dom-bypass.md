# Google Shadow DOM Overlay & Direct URL Bypass Technique

## Problem
Google's `myaccount.google.com/signinoptions/twosv` page (and potentially other security settings pages) renders a **shadow DOM overlay** (classes `.uW2Fw-Sx9Kwc`, `.uW2Fw-IE5DDf`, `.uW2Fw-T0kwCb`) that intercepts all pointer events. Even when Playwright locators resolve to the correct element (e.g., "Authenticator" option), the click fails with:
```
Locator.click: Timeout 30000ms exceeded.
... subtree intercepts pointer events
```

This happens because the overlay `div` (jscontroller="dGzwdb") sits on top of the visible UI and captures all clicks, even though the target element appears visible and enabled.

## Root Cause
Google uses a custom shadow DOM component for modals/backdrops that doesn't properly handle click-through for automated browsers. The overlay persists even after the dialog appears to be dismissed.

## Solution: Direct Deep-Link URLs
Instead of navigating to the parent page and clicking through, use **direct deep-link URLs** that bypass the overlay entirely:

| Target Page | Overlay-Blocked URL | **Direct URL (Bypasses Overlay)** |
|-------------|---------------------|-----------------------------------|
| Authenticator Setup | `https://myaccount.google.com/signinoptions/twosv` → click "Authenticator" | `https://myaccount.google.com/two-step-verification/authenticator` |
| 2-Step Verification Main | `https://myaccount.google.com/security` → "2-Step Verification" | `https://myaccount.google.com/signinoptions/twosv` |
| Passkeys | `https://myaccount.google.com/security` → "Passkeys" | `https://myaccount.google.com/signinoptions/passkeys` |
| Security Code | `https://myaccount.google.com/security` → "Security Code" | `https://myaccount.google.com/signinoptions/security-codes` |

## Usage Pattern
```python
# BAD: Hits shadow DOM overlay
page.goto("https://myaccount.google.com/signinoptions/twosv")
page.locator('div:has-text("Authenticator")').click()  # TIMEOUT

# GOOD: Direct URL bypasses overlay entirely
page.goto("https://myaccount.google.com/two-step-verification/authenticator", 
          wait_until="domcontentloaded", timeout=45000)
# Now page is directly on Authenticator setup, no overlay
```

## Additional Workarounds (if direct URL not available)
1. **`click(force=True)`** - Bypasses Playwright's visibility/stability checks
2. **Remove overlay via JS evaluation** before clicking:
   ```python
   page.evaluate('''() => {
       document.querySelectorAll('.uW2Fw-Sx9Kwc, .uW2Fw-IE5DDf, .uW2Fw-T0kwCb, div[role="dialog"]')
           .forEach(el => el.remove());
   }''')
   ```
3. **Wait for specific elements** with `wait_for(state="visible", timeout=15000)` instead of fixed sleeps

## Verified Success (2026-09-03)
- Authenticator direct URL works 100% for 2FA activation flow
- All clicks on direct URL page work without `force=True` (no overlay)
- "Không thể quét mã?" button appears after QR loads, clickable with `force=True`

## Applicability
This pattern likely applies to other Google account security pages that use similar shadow DOM overlay architecture. Always test direct deep-link URLs first before attempting click-through navigation on `myaccount.google.com` security settings.