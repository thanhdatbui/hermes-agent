# Order Tracking In-App Navigation, OCR Normalization & ATX-Agent Fallback

## 1. Head-of-Line Blocking Trap in App-Sync Loops
When managing multiple pending orders in `NEED_APP_SYNC` with `max_app_syncs = 1`:
- **The Bug:** A naive loop `for order in orders: sync_app_order(order); break` always evaluates the first order in `orders.json`. If that device encounters a popup guard rejection, delay, or lock contention, the loop breaks immediately.
- **The Consequence:** Every single background cron tick wastes its single execution slot on the same stalled device, completely starving all subsequent orders in the queue (e.g., orders placed 2 days ago never get inspected).
- **The Invariant:** On `DEFERRED_DEVICE_BUSY`, `SKIPPED_NO_MACHINE`, or `APP_SYNC_ERROR`, the scheduler must `continue` to inspect subsequent pending orders until either a successful sync occurs or the list is exhausted.

## 2. TikTok App Navigation & OCR Kerning Pitfalls
- **Vietnamese Diacritic Variations on Bottom Sheets:**
  - OCR often renders `Chuyển đổi tài khoản` as `Chuyén ddi tåi khoån` or `Chuydn ddi täi khoån`.
  - Checking strict string equality (`"chuyen doi tai khoan" in text`) fails silently. Match broad tokens in header boxes (`y < 400`): `("tai khoan", "chuyen", "switch", "add account")`.
- **Handle Normalization (`0` vs `O` and Kerning Whitespace):**
  - OCR font kerning frequently inserts spaces into usernames (e.g. `@khn h.vyyyy6` instead of `@khnh.vyyyy6`).
  - Digits like `00` in handles (e.g. `@thanh.h.dng00`) are often parsed as capital `OO`.
  - Strip all whitespace and normalize `0` -> `o` across both candidate boxes and wanted handles before matching.
- **Active Account Switcher Sheet Dismissal:**
  - In TikTok Android, tapping on the text of an *already active* account in the switcher sheet does not dismiss the bottom sheet.
  - After sending tap on the switcher handle point, immediately issue `input keyevent 4` (KEYCODE_BACK) to dismiss the sheet and reveal the underlying Profile view.
- **Shop Mall "Tất cả" Filter False Positive:**
  - On the TikTok Shop Mall/Cửa hàng home tab, shopping categories contain a filter button labeled "Tất cả" (All).
  - Never include bare `"Tất cả"` or `"Tat ca"` in `ORDER_LIST_MARKERS`, as it fools the navigator into believing it has already reached the order list.
- **Header Shortcut on Shop Mall Tab:**
  - When navigation lands on the Shop/Mall tab instead of the Profile tab, look for the header shortcut `Đơn hàng` / `Ddn häng` at `y < 500` (typically `(286, 335)`) and tap it to enter My Orders.

## 3. Carrier Code Prefix Auto-Inference
- **Multi-Carrier Support:**
  - `8[4-9]\d{10}` (12 digits) -> `J&T Express`
  - `VNGH[A-Z0-9]+` -> `GHN` (Giao Hàng Nhanh)
  - `SPXVN[A-Z0-9]+` -> `SPX Express`
- When extracting tracking codes, auto-infer the carrier if unset or set to `"Chờ chuyển phát"`. Updating both `tracking_code` and `carrier` immediately transitions the order from `NEED_APP_SYNC` to `ACTIVE_WEB_TRACKING`, retiring the farm device from all future inspection cycles.

## 4. ATX-Agent (Port 7912) as Primary Fallback (Zero Shell UiAutomator Dump)
- **Hard Farm Invariant:** Calling shell `uiautomator dump` or importing `uiautomator2` is strictly forbidden across the farm due to kernel OOM kills (`EXIT 137`) on Samsung S7 devices.
- **Canonical ATX-Agent Fallback:**
  - Primary layer remains WinRT OCR on device screenshots (< 0.2s).
  - When WinRT OCR fails to capture tracking numbers due to layout obstruction or low contrast, query ATX-Agent via `automation_core.persistent_ui.capture_atx_session_ui(adb)` on port 7912.
  - This retrieves the structured UI XML hierarchy over the existing daemon without spawning shell uiautomator processes or conflicting with active stubs.
