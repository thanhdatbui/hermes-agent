# J&T Express Web Tracking Link Traps & Order Ingestion Integrity

## 1. J&T Express Web Tracking URL Traps & False HTTP 422 Errors

### A. Naked URL vs Form Submission Trap
- **The Issue:** When sending tracking URLs to Telegram users:
  `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}`
  the J&T server renders the page HTML containing the timeline pre-populated in the DOM (`.tab-content`, `.result-vandon-item`).
- **The Mobile UI Trap:** On mobile screens, viewport loads at the top of the page (showing the input form with pre-filled billcode and the big red "Tra cứu vận đơn" button).
- **The 422 Error:** When a user taps "Tra cứu vận đơn" on mobile after loading the URL with query params, the page's client-side AJAX submits a redundant request without the CSRF/session token or matching state, triggering an inline red error toast:
  `Tra cứu thất bại (422)`.
- **The Solution:**
  1. Add an anchor tag pointing directly to the result accordion:
     `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}#chck-{code}`
  2. Send raw unformatted URLs or markdown links without conflicting markdown brackets that break link parsing in Telegram clients.
  3. Explicitly advise user: The result is already pre-loaded below the fold; do NOT click "Tra cứu vận đơn" again.

---

## 2. Ingestion Template Mutation Pitfall (Customer Name Collision)

### A. The Copy-Paste Seed Bug
- When automating creation of orders using batch template scripts (e.g. `save_order_20261029_004.py` cloned from previous order templates):
  - Do NOT blindly carry over template boilerplate values for `customer.name`, `customer.phone`, or `customer.address`.
  - In this incident, `DH-20261029-004` (TikTok handle `@thanh.h.dng00`) was seeded with customer name "Mai Mai" from `DH-20261028-003`, causing watchdog alerts to announce the wrong recipient name throughout transit until delivery completion proved the signer was "Thanh Hà Dương".
- **Strict Ingestion Rule:**
  - Before writing to `orders.json` or `QuanLyDonHang_TikTokShop.xlsx`, verify that `customer.name` matches the shipping profile of the specific farm device/order confirmation screenshot, NOT an earlier template order.
  - Automatically update `customer.name` if signed receipt event (`Đơn hàng đã ký nhận. Người ký nhận là:【...】`) diverges from the recorded name.
