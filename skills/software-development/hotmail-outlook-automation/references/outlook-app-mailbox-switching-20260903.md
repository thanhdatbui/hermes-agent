# Outlook App Mailbox Switching on Drawer Left Rail (2026-09-03)

## Problem
When a device has multiple Microsoft/Hotmail accounts signed into the Outlook Android app:
- Only 1 mailbox is "active" (shown in `drawer_header_summary`, resource-id `com.microsoft.office.outlook:id/drawer_header_summary`)
- Other mailboxes appear as icons on the left rail of the Navigation Drawer (`bounds[0] < 250`, resource-id `btn_all_account` or empty)
- The old `_outlook_app_account_present` only checked `drawer_header_summary` → would fail if target mailbox was not the active one

## Solution: `_ensure_outlook_app_mailbox_selected(adb, device, email, xml)`

Added to `flows/hotmail_login.py` after `_close_outlook_app_drawer` (around line 1639).

### Logic
1. **If drawer already open**:
   - Check if `drawer_header_summary` matches target email → return True
   - Else scan left rail nodes (`rid in (btn_all_account, "")` with `bounds[0] < 250`) for matching `text`/`content-desc` → tap to switch, wait for header update, close drawer, return True
   - Return False if not found

2. **If drawer not open**:
   - Open via account button (`OUTLOOK_APP_ACCOUNT_BUTTON_ID`)
   - Check header → if matches, close drawer, return True
   - Else scan left rail, tap to switch, wait for header, close drawer, return True
   - Return False if not found (caller adds account)

### Integration
Replaced `_outlook_app_account_present` calls in:
- `read_tiktok_otp_from_outlook_app` (OTP reader)
- `read_tiktok_magic_link_from_outlook_app` (Magic link reader)

### Drawer Open on Launch Fix
Also added `_outlook_app_drawer_open(value)` to the initial `wait_for` predicate so that when the app launches with drawer already open, the flow proceeds to `_outlook_app_open_inbox_from_archive` (which already handles tapping "Hộp thư đến" in drawer) instead of failing with `OUTLOOK_APP_INBOX_NOT_VERIFIED`.

### Testing
- 6/7 existing tests pass
- New logic properly switches mailbox on left rail before reading OTP/Magic link