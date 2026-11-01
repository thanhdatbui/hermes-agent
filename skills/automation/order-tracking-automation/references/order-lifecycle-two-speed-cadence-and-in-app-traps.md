# Order Lifecycle Two-Speed Cadence & In-App Extraction Traps

## 1. Two-Speed Cadence Decoupling (Phase 1 vs Phase 2)

Combining in-app phone inspection (Phase 1: ADB / ATX / OCR) and carrier Web APIs (Phase 2: Zero ADB Web Tracking) requires decoupled cadence:
- **Phase 2 (Carrier Web API):** Runs high-frequency (every 20–30 minutes, 06:00 to 21:30). Zero ADB, < 2s duration, zero battery impact. Captures real-time shipper dispatch and local delivery events.
- **Phase 1 (In-App S7 Phone Inspection):** Strictly bounded by a persistent cooldown state (5.5h – 6h). Wakes S7 farm phones at most once per 6-hour shift. Prevents battery drain, device overheating, and collision with automated feeding shifts.
- **Auto-Handoff:** The moment a tracking code is extracted, the engine auto-infers the carrier (`8\d{11}` -> J&T Express, `VNGH...` -> GHN, `SPXVN...` -> SPX) and promotes the order to `ACTIVE_WEB_TRACKING`, permanently releasing the farm phone from further inspection.

## 2. Head-of-Line Blocking Elimination
When iterating through `NEED_APP_SYNC` orders with `max_app_syncs = 1`:
- If an order's device is busy (`DEFERRED_DEVICE_BUSY`) or encounters a navigation error (`APP_SYNC_ERROR`), the loop must `continue` to attempt the remaining pending orders rather than `break`.
- A hard `break` on error or deferral starves all subsequent orders indefinitely.

## 3. TikTok In-App Account Switcher & Font Kerning Traps

### A. Active Account Selection on Switcher Sheet
- In TikTok Android, tapping the text of the *currently active* account on the "Chuyển đổi tài khoản" bottom sheet does NOT dismiss the sheet.
- **Resolution:** Send `KEYCODE_BACK` (keyevent 4) after tapping to dismiss the bottom sheet and reveal the profile screen.

### B. OCR Font Kerning & Dialect Variations
- OCR frequently misinterprets Vietnamese diacritics and kerning:
  * "Chuyển đổi tài khoản" -> "Chuyén ddi tåi khoån" or "Chuydn ddi täi khoån". Use flexible substring checks (`"tai khoan"`, `"chuyen"`, `"switch"`).
  * Handles with numbers/dots often have injected spaces or confused glyphs: `@khn h.vyyyy6` for `@khnh.vyyyy6`, `thanh.h.dngOO` for `thanh.h.dng00`.
  * **Rule:** `_handle_key` must normalize by stripping all whitespace and translating `0` <-> `o`.

### C. Shopping Filter vs Order List Marker Trap
- "Tất cả" (All) is standard navigation on TikTok Shop Mall/Flash Sale tabs. Never use "Tất cả" alone as an `ORDER_LIST_MARKER`.
- Require explicit markers (`"Đơn hàng của tôi"`, `"Chi tiết đơn hàng"`, `"Tìm kiếm đơn hàng"`).
- On the Shop/Mall home tab, use the direct "Đơn hàng" header shortcut (`y < 500`) to enter the order list directly.

### D. Feed Tab vs Profile False Positive
- The "Đã follow" (Following) tab at the top of the feed (`y < 200`) easily tricks naive `on_profile` detectors into endless pull-to-refresh swipe loops.
- **Rule:** Profile stats markers (`follower`, `following`, `chinh sua ho so`) must enforce vertical bounding `y > 400`.

## 4. Primary Vision vs ATX-Agent Fallback
- **Hard Farm Invariant:** Shell `uiautomator dump` is strictly banned across the farm due to kernel OOM kills (Exit 137) on Samsung S7.
- **Tier 1 (Primary):** WinRT OCR on raw screencap (< 0.2s, Zero ADB impact).
- **Tier 2 (Fallback):** ATX-Agent JSON-RPC port 7912 (`automation_core.persistent_ui.capture_atx_session_ui`) when WinRT OCR yields ambiguous results or font distortion.
