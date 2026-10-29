# In-App Order Sync Cadence, Device Protection and Silent Milestone Trap

## 1. Farm Device Protection & Cadence Discipline in Phase 1 (In-App Sync)

When a TikTok Shop order is newly placed and awaits seller dispatch (`NEED_APP_SYNC`):
* **Do NOT poll phone apps at high frequency (e.g. 15–30 minutes).**
* **User Directive & Operational Reality:** Sellers take hours or days to pack and hand over parcels to couriers. Continuously waking a physical Samsung S7 farm device every 15 minutes causes severe battery drain, high thermal throttling (nóng máy), and touch/device-lock collisions with scheduled feed/video nurturing shifts.
* **Canonical Cadence:** Maintain **6-hour intervals (`0 */6 * * *`)** aligned with farm shift boundaries (00:00, 06:00, 12:00, 18:00).
* **Zero-ADB Boundary Separation:** High-frequency polling (10–15m) is strictly restricted to **Phase 2 (ACTIVE_WEB_TRACKING)** after the tracking code is extracted and all farm devices are 100% disconnected.

---

## 2. The Silent Milestone Delivery Trap (`no_agent: true`)

### Failure Mode
1. At 06:03 AM, the order lifecycle cron ran on schedule, acquired device lock on Machine 40, opened TikTok Shop, captured screenshot `order_20261028_003_app.jpg`, and extracted billcode `862643752194`.
2. It updated `orders.json` correctly.
3. However, `order_lifecycle.py` executed without `--verbose` or `--json`, producing **0 bytes on `stdout`**.
4. In Hermes Cron with `no_agent: true`, empty stdout is designated as "silent tick" (nothing to report). Hermes dropped the tick silently.
5. **The User Experience:** The user saw zero Telegram notifications, checked the chat hours later, and legitimately concluded that the agent failed to run the cron and had been waiting for user intervention.

### Invariant Fix
Whenever a cron watchdog script achieves a milestone state change (extracts a tracking code, detects carrier handoff, transitions phases):
* **It MUST print a concise structured announcement to `stdout`:**
  ```text
  🎉 ĐÃ BÓC ĐƯỢC MÃ VẬN ĐƠN MỚI TỪ TIKTOK APP (MÁY <N>):
  • Đơn hàng: <order_id> (<customer_name>)
  • Đơn vị vận chuyển: <carrier>
  • Mã vận đơn: <billcode>
  • Chuyển sang Phase 2: Theo dõi Web API tự động!
  ```
* Hermes Cron will automatically pick up the non-empty stdout and deliver it verbatim to the target Telegram topic.

---

## 3. Active Magnified Phone Window Detection on Farm Grids

When users send full desktop screenshots from multi-device management software (Total Control, etc.):
1. A dense matrix of device thumbnails (SM-G930F/S/K/W8) sits in the background.
2. The active device being operated is magnified in the center foreground.
3. **Deterministic Crop Algorithm:**
   - Scan horizontal pixels across middle columns (`x = 300 .. 950`) at `y = 360` for light/white page background (`R, G, B > 220`).
   - Find the contiguous white segment corresponding to the phone's WebView (e.g. width ~ 276px).
   - From the column midpoint, scan vertically for light pixels to identify screen top and bottom bounds (`y = [37, 666]`).
   - Crop the exact smartphone aspect ratio (~9:20) and upscale 2x using `Image.Resampling.LANCZOS` for clean rendering on Telegram and web dashboards.
