# OCR Kerning, Switcher Dismissal & Lifecycle Queue Starvation Safeguards

## 1. Head-of-Line Blocking in Multi-Order App Sync
When multiple orders are placed simultaneously (e.g. batch voucher orders across machines 2–13), all pending orders enter `NEED_APP_SYNC`.
- **The Starvation Trap:** If `run_lifecycle_once` iterates sequentially through orders with `max_app_syncs = 1` and breaks immediately upon attempting the first order, any single stuck device (e.g. device 2 encountering a modal dialog or navigation delay) consumes the sole sync slot of each cron tick. All subsequent orders (devices 3–13) are starved indefinitely and never inspected.
- **Remediation Pattern:** Implement non-blocking continuation. If a device returns `DEFERRED_DEVICE_BUSY`, `SKIPPED_NO_MACHINE`, or `APP_SYNC_ERROR`, the loop must `continue` to inspect subsequent pending orders until an actual successful sync occurs or all candidates have been safely evaluated:
  ```python
  for o in orders:
      if classify_order_phase(o) != "NEED_APP_SYNC":
          continue
      res = sync_app_order(o, dry_run=dry_run)
      if res.get("status") in ("SKIPPED_NO_MACHINE", "DEFERRED_DEVICE_BUSY", "APP_SYNC_ERROR"):
          continue
      app_syncs += 1
      if app_syncs >= max_app_syncs:
          break
  ```

## 2. Carrier Auto-Inference & Zero-ADB Promotion
- **The Stale Carrier Trap:** When an app sync extracts a tracking code, if the database record retains `carrier: "Chờ chuyển phát"` or `None`, naive phase classifiers fail to promote the order to `ACTIVE_WEB_TRACKING`, keeping it in Phase 1 and unnecessarily touching the phone on future ticks.
- **Deterministic Prefix Mapping:**
  - `8[4-9]\d{10}` (12 digits) -> `J&T Express`
  - `VNGH[A-Za-z0-9]+` -> `GHN` (Giao Hàng Nhanh)
  - `SPXVN[A-Za-z0-9]+` -> `SPX`
- When `tracking_code` is present, `classify_order_phase` must auto-infer the carrier if unset, promoting the order immediately to Phase 2 (Zero ADB Web Polling, <1s execution).

## 3. TikTok UI Navigation & OCR Robustness
- **Kerning Space Injection:** OCR frequently splits handles with internal spaces (e.g. `@khnh.vyyyy6` parsed as `@khn h.vyyyy6`). Because TikTok handles cannot contain whitespace, normalizers must strip all spaces:
  ```python
  def _handle_key(text: str) -> str:
      return _fold(text).replace(" ", "").replace("0", "o").strip().lstrip("@").strip()
  ```
- **Zero vs. Capital O Ambiguity:** In low-res screencaps (e.g. `@thanh.h.dng00` parsed as `thanh.h.dngOO`), normalize digit `0` to character `o` before comparison.
- **Active Switcher Bottom Sheet Trap:** In TikTok's "Chuyển đổi tài khoản" sheet, tapping on an account that is *already active* does not dismiss the bottom sheet. Automation must issue an explicit `KEYCODE_BACK` (`input keyevent 4`) after selecting or verifying the handle to reveal the underlying Profile tab.
- **Shop Tab vs Order List Ambiguity:** "Tất cả" appears on the TikTok Shop/Mall tab as a category filter and must NOT be treated as an order list marker. On the Shop tab, tap the dedicated "Đơn hàng" header icon (`shop_don_hang[1] < 500`) to navigate into "Đơn hàng của tôi".

## 4. Daytime Schedule Alignment
- Couriers (J&T, GHN, SPX) primarily update parcel dispatch and out-for-delivery events between 06:00 and 21:00.
- Cron watchdogs operating under `no_agent: true` should use daytime half-hour cadences (`*/30 6-21 * * *`). Because Phase 2 Web API tracking consumes zero tokens and runs in <1s without ADB locking, high daytime frequency provides real-time courier alerts with zero device wear.
