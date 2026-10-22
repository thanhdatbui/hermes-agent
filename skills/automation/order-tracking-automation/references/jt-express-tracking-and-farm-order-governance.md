# J&T Express Web Tracking & Farm Voucher Order Governance

## 1. J&T Express Web Tracking Protocol

### Deprecated API vs Live Web Scraping
- The legacy JSON endpoint `https://jtexpress.vn/api/tracker?billcode={code}` returns HTTP 404.
- Live web tracking requires the GET endpoint:
  ```text
  https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}
  ```
- **Anti-Scraping / Privacy Gate (`cellphone`):** If `cellphone` (4 trailing digits of recipient phone) is omitted, J&T intercepts the request with an interactive modal (`modal-verify`) and hides tracking timeline elements. Passing `cellphone=XXXX` renders the full transit history directly into the HTML response.

### HTML Timeline Extraction Pattern
- Search for the tracking block anchor: `id="chck-{billcode}"`.
- Parse lines matching time regex `^\d{2}:\d{2}:\d{2}$` immediately followed by date regex `^\d{4}-\d{2}-\d{2}$`.
- Extract event descriptions up to the next timestamp, normalizing bracketed facility names (`【...】`).
- Key milestone markers:
  - Transit Hub / SOC Arrival: `Hàng đã được chuyển đến【TTKT ĐÀ NẴNG】` (Sorting center, no retail pickup).
  - Inter-Facility Dispatch (In Transit): `Bưu cục【...】đang chuyển hàng đến【...】` (Đang luân chuyển xe tải giữa các kho/bưu cục, CHƯA đến đích; TUYỆT ĐỐI không coi đây là đã đến bưu cục phát hay kích hoạt báo động).
  - Destination Delivery Hub Arrival: `Hàng đã được chuyển đến【Bưu cục...】` / `Đã đến bưu cục...` (Đã quét barcode nhập kho bưu cục phát, bắt đầu khung giờ vàng liên hệ giữ hàng 07:15 - 08:00).
  - Out for Delivery: `Nhân viên【...】đang giao hàng. SĐT shipper【...】`.

---

## 2. Farm Voucher Order Fulfillment & Courier Governance

### The Cluster-Fraud Evasion Context
- Orders placed via phone farm devices to harvest new-user vouchers deliberately use:
  1. Unique synthetic recipient names.
  2. Virtual or secondary phone numbers (SIM cards are typically not active on the operator's primary handset).
  3. Slight variations in local addresses (different house/alley numbers along a known courier route).
- **Hard Rule (No SMS/App Delegation):** NEVER instruct the operator to download carrier apps or authenticate via carrier SMS OTP. The operator does not hold active SIM cards for synthetic farm accounts and picks up parcels on behalf of the accounts.

### Courier Routing Protocol ("Bao Tuyến / Ký Hiệu Mật")
- Couriers receive per-parcel compensation and prefer bulk drops over searching for scattered pseudo-addresses.
- Establish a consistent convention:
  1. **Secret Code in Order Note:** Include an agreed marker (e.g. `(Giao 47 TCV)` or a specific buyer prefix).
  2. **Direct Courier Agreement:** Brief the primary route courier (e.g. SPX/J&T) to collect all parcels matching the convention, bypass phone dialing, and deliver directly to the consolidation address with cash-on-delivery (COD) paid in a single transaction.
  3. **Local Hub Interception:** If a courier cannot be reached or is unfamiliar, intervene at the local delivery hub during the morning sorting window (07:15 - 08:00) before parcels are loaded onto motorbikes.

### Alert Channel Isolation & Audible Notifications
- High-frequency farm operations flood primary messaging channels (e.g., Farm Alerts, feed logs), causing operators to mute channels.
- To prevent missed pickup windows:
  1. **Dedicated Telegram Group:** Route order watchdogs to a separate, quiet Telegram chat/group (e.g., "Đơn hàng tiktok") with a custom high-priority notification ringtone.
  2. **Desktop Audible Alarm:** On host machines running 24/7, integrate audible alerts when parcels arrive at destination hubs using native Windows APIs:
     ```python
     import winsound
     for _ in range(3):
         winsound.Beep(1200, 300)
         winsound.Beep(1600, 300)
     
     import win32com.client
     speaker = win32com.client.Dispatch("SAPI.SpVoice")
     speaker.Speak("Don hang TikTok da ve buu cuc, di lay ngay!")
     ```
