# Order Lifecycle Parallel Sync Cadence & In-App Traps

## 1. Two-Speed Cadence Architecture (Phase 2 Realtime vs Phase 1 Cooldown)
In hybrid order tracking systems combining in-app device inspection (Phase 1) and carrier web APIs (Phase 2):
- **Phase 2 (Zero-ADB Web API):** Runs at high frequency (every 15–30 minutes, 06:00–21:30). Execution takes < 1.5s, touches no ADB bus, and immediately catches delivery milestones (shipper dispatch, destination hub arrival, delivery completion).
- **Phase 1 (Farm Phone In-App Inspection):** Must NEVER run on the 30-minute cadence. Phone inspection causes battery drain, overheating, and risks collision with scheduled nurture/feed sessions.
- **Rule:** Phase 1 is strictly gated by a persistent state cooldown (`PHASE1_COOLDOWN_SECONDS = 5.5 * 3600`) or locked to designated idle windows (06:30, 11:30, 16:30). If the cooldown is active, the runner logs `Bỏ qua Phase 1` and exits immediately after Phase 2 completes.

## 2. Parallel Workers vs Head-of-Line Blocking Trap
- **The Trap:** Iterating sequentially over pending orders with `max_app_syncs = 1` and an early `break` on error or device lock. If the first order gets stuck in a popup loop or deferred lock, all subsequent orders behind it are starved indefinitely.
- **The Solution:** CẤM tuần tự cuốn chiếu khi có nhiều máy rảnh. Run Phase 1 concurrently across independent devices using `ThreadPoolExecutor(max_workers=min(15, len(pending_orders)))`.
- **Thread Safety:** Wrap all canonical file writes (`orders.json`, `QuanLyDonHang_TikTokShop.xlsx`) in a shared `threading.Lock()` so concurrent worker completions never corrupt or overwrite records.

## 3. Silent Watchdog Siren Invariant (`no_agent: true`)
- In pure script crons (`no_agent: true`), empty stdout means SILENT.
- Updating database or Excel records silently means Telegram receives zero notifications even when a parcel is out for delivery or delivered.
- **Rule:** Whenever an order's status changes (e.g. to `Đang giao hàng`, `Đã giao hàng thành công`) or a carrier tracking event updates, the runner MUST print the formatted alert block to stdout so Hermes delivers it immediately to the destination channel.

## 4. In-App Navigation & OCR Failure Traps
### A. Handle Font Kerning & `0` / `o` Normalization
- TikTok handles never contain spaces. OCR engines frequently introduce accidental spaces (e.g. `@khnh.vyyyy6` -> `@khn h.vyyyy6`) due to font kerning.
- Digits like `0` are frequently OCR'd as uppercase `O` (e.g. `thanh.h.dng00` -> `thanh.h.dngOO`).
- **Rule:** Normalize handles via `_fold(text).replace(" ", "").replace("0", "o").strip().lstrip("@").strip()`.

### B. Account Switcher Active Account Dismissal
- In the TikTok account switcher bottom sheet, tapping on the username of the *already active* account does NOT dismiss the sheet.
- **Rule:** After tapping the target account or if the target is already selected, issue `_adb_run(serial, "shell", "input", "keyevent", "4")` (BACK) to close the bottom sheet and return to Profile.

### C. Feed vs Profile Marker Collision
- On the TikTok video feed, the top category tabs display `Đã follow` at `y < 200`. Naive checks searching for `follower` / `following` / `da follow` without coordinate bounds trigger false-positive profile detection, resulting in infinite swipe-down refresh loops.
- **Rule:** Bound profile stats matching to `box[1] > 400` (below avatar and bio).

### D. Shopping Mall Tab vs Order List Markers
- Generic shopping tabs display `Tất cả` (All) as a product filter. Treating `Tất cả` as an order list marker causes the navigator to halt prematurely on the Mall shopping page.
- **Rule:** Remove `Tất cả` from `ORDER_LIST_MARKERS`. On the Mall/Shop tab, detect the `Đơn hàng` header button (`y < 500`) and tap it to enter the real My Orders center.

### E. ATX-Agent (Port 7912) as Guarded Fallback for WinRT OCR
- While shell `uiautomator dump` (`/system/bin/uiautomator`) is strictly prohibited farm-wide to prevent kernel OOM kill (`EXIT 137`), `atx-agent` on port 7912 via `automation_core.persistent_ui.capture_atx_session_ui` is the authorized fallback when WinRT OCR cannot resolve blurred or obscured text on native screens.
