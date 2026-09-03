# Popup Chain Recovery Handler — TikTok Feed Session

Evidence from 2026-08-07, machine_1, signature MANUAL_NEEDED_POPUP (run 20260807-170007).

## Root Cause

Three popups stacked in sequence during feed-session-smoke swipe_3:
1. **shop_cta_overlay** — "Mua ngay" (rid=hvg) + "Đóng" (rid=hvm), TikTok package
2. **sponsored_ad_feedback** — "Bạn có quan tâm đến quảng cáo này không?" + No (rid=tca)
3. **packageinstaller contacts-permission** — "Cho phép TikTok truy cập vào danh bạ của bạn?" + "TỪ CHỐI" (permission_deny_button), package=com.google.android.packageinstaller

Core `dismiss_tiktok_popups` correctly dismissed 1→2 (dismiss_close_button + dismiss_no_button), but the final recapture landed on the packageinstaller dialog which core doesn't own → returned `popup_remains` → MANUAL_NEEDED_POPUP.

Ironically, the exact same packageinstaller dialog was denied successfully earlier in the same run (swipe_1_after, log.jsonl line 81: dismiss_deny_button verified=true).

## Implemented Handlers (2026-08-07, slot-3 recovery, not yet committed)

### 1. `detect_tiktok_shop_cta_popup` — `python_runner/core/benign_popup.py`

Detects shop CTA overlay by finding BOTH "Mua ngay" AND "Đóng" button nodes within com.ss.android.ugc.trill package. close_element = "Đóng" (safe dismiss, never taps "Mua ngay"). Wired into `detect_tiktok_popup_action` before core fallback.

**Variants handled:** `hvg/hvm` (standard), `hvg/hvm` alias `hn6/hnb`, `hck/hcq`.

**Tests (7/7 pass):**
- `test_detect_shop_cta_standard` — SHOP_CTA_XML (`hvg/hvm`)
- `test_detect_shop_cta_hn_variant` — SHOP_CTA_HN_XML (`hn6/hnb`)
- `test_detect_shop_cta_hck_variant` — SHOP_CTA_HCK_XML (`hck/hcq`)
- `test_no_match_without_close` — only "Mua ngay", no "Đóng"
- `test_no_match_without_buy` — only "Đóng", no "Mua ngay"
- `test_no_match_outside_tiktok` — matching buttons but non-TikTok package

### 2. `handle_packageinstaller_after_shared_dismiss` — `python_runner/flows/recovery_handlers.py`

Guarded drain of typed Android packageinstaller dialog left after shared dismiss chain:
- **Guard:** `_is_typed_packageinstaller_after_shared_dismiss` — requires ALL: (a) !dismissed, (b) reason contains "popup_remains" or "remained after allowed", (c) after_attempt detected_screen == PACKAGEINSTALLER_DIALOG_SCREEN, (d) XML contains com.android.packageinstaller markers (permission_deny_button + permission_allow_button + permission_message OR package=com.google.android.packageinstaller)
- **Action:** `dismiss_packageinstaller_dialog(ctx, ..., max_attempts=1)` — taps "TỪ CHỐI"
- **Safety:** login/OTP/2FA/captcha/security/account/credential/unknown popups NEVER match the guard → pass through unchanged

**Tests (22/22 pass):**
- `IsTypedPackageinstallerXmlTests` (7): real contacts XML, shop_cta, for-you, login, None, missing file, empty string
- `IsTypedPackageinstallerAfterSharedDismissTests` (6): packageinstaller after popup_remains, already dismissed, non-popup_remains reason, None after_attempt, non-packageinstaller detected, sensitive XML
- `HandlePackageinstallerAfterSharedDismissTests` (9): drains typed, already dismissed pass-through, not popup_remains pass-through, login never touched, unknown pass-through, dismiss failure keeps manual-needed, null after_attempt, OTP not detected, 2FA pass-through

### 3. Wiring — `python_runner/flows/feed_swipe_smoke.py`

`_maybe_dismiss_allowed_popup_chain_recovery` (L8447-8620), invoked at L9193 inside `drain_known_popups` after `_maybe_dismiss_allowed_popup_after_swipe`. Gated on `feed-session-smoke` mode + `allow_benign_popup_dismiss`.

## Verification

```bash
cd "D:\Taadaa\tiktok-luot nuoi acc\python_runner"
PYTHONPATH=src python -m pytest tests/test_benign_popup.py tests/test_chain_recovery_handlers.py tests/test_recovery_handlers.py -v
# Result: 132 passed, 0 fail, 10 skipped (2026-08-07)
```

## File Inventory (uncommitted)

| File | Lines | Status |
|------|-------|--------|
| `python_runner/core/benign_popup.py` | +46 | `detect_tiktok_shop_cta_popup` + wire |
| `python_runner/flows/recovery_handlers.py` | 153 | NEW — handler + guard + XML validator |
| `python_runner/flows/feed_swipe_smoke.py` | +356 | Import + `_maybe_dismiss_allowed_popup_chain_recovery` wiring |
| `python_runner/tests/test_benign_popup.py` | +54 | `TestTikTokShopCTAPopup` class (6 tests) + existing shop CTA dismiss tests updated |
| `python_runner/tests/test_chain_recovery_handlers.py` | 540 | NEW — 22 tests |
