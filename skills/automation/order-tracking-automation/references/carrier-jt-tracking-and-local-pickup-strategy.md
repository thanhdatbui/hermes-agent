# J&T Express Vietnam Tracking & Local Hub Pickup Automation Strategy

## 1. J&T Express Tracking Endpoint & Anti-Scraping Bypass

### 1.1 Direct Endpoint via Tracking URL
- **Deprecated / Dead Endpoint:** `https://jtexpress.vn/api/tracker?billcode={code}` returns HTTP 404.
- **Client-Side Privacy Modal:** When navigating to `https://jtexpress.vn/vi/tracking?type=track&billcode={code}`, J&T prompts for the last 4 digits of the recipient's phone number before displaying the timeline.
- **Canonical Bypass Query:** Passing the query parameter `cellphone={phone_last4}` directly in the URL:
  ```http
  GET https://jtexpress.vn/vi/tracking?type=track&billcode={billcode}&cellphone={phone_last4}
  ```
  bypasses the interactive phone-number challenge and renders the tracking timeline directly in the HTML response.

### 1.2 HTML Parsing Selectors
- Locate container: `<section id="chck-{billcode}">` or class `.timeline`.
- Each event row provides:
  - Timestamp: `HH:MM:SS`, `YYYY-MM-DD`
  - Event status & Location: e.g. `Hàng đã được chuyển đến【TTKT ĐÀ NẴNG】`, `Bưu cục【...】đang chuyển hàng đến【...】`.
- Watchdog change detection: Store `last_known_time` and `last_known_desc` in a persistent JSON state file. The cron watchdog must stay completely silent (`no stdout`) when no new events have occurred, and only alert when a new milestone or `Bưu cục phát` arrival is detected.

---

## 2. The "Proxy / Farm Receiver" Operational Invariant

### 2.1 The Carrier App Anti-Pattern
- **Anti-Pattern:** Advising a farm operator or proxy recipient to *"Download the J&T/Shopee/TikTok app and log in with the account phone number"*.
- **Why It Fails:** In farm operations and bulk account management, accounts are registered with virtual, rented, or inactive SIMs that are not physically present in the operator's smartphone. The operator cannot receive SMS OTP to log into carrier apps.
- **Rule:** Never advise downloading carrier mobile apps for proxy pickups. All tracking must be resolved via web endpoints, direct shipper communication, or local bưu cục contacts.

---

## 3. Local Hub (Bưu cục phát) Pickup Strategy

### 3.1 Sorting Center (SOC) vs. Delivery Hub (Bưu cục phát)
- **SOC / TTKT (Trung tâm khai thác / phân loại, e.g., TTKT Liên Chiểu, SOC Củ Chi):**
  - Strictly closed logistics hubs. They DO NOT service retail walk-ins or hold parcels for customer pickup.
  - Calling or visiting an SOC is futile and disrupts warehouse operations.
- **Bưu cục phát (Local Delivery Hub):**
  - The neighborhood station responsible for last-mile delivery to the street address.
  - Parcels arrive here via overnight linehaul transfer trucks between 04:00 AM and 07:00 AM.
  - Retail customers CAN pick up directly at the counter if intercepted before the courier departs.

### 3.2 The Golden Interception Window (07:15 - 08:00 AM)
- **Too Early (Before 07:00 AM):** Parcel is still in transit from SOC or being unloaded from linehaul trucks. Bưu cục staff cannot locate specific bags.
- **Golden Window (07:15 - 08:00 AM):** Inbound scan at Bưu cục phát is completed (`Đã đến bưu cục phát`). Shipper has not yet loaded parcels onto delivery bikes.
  - Action: Call the bưu cục hotline or delivery supervisor immediately with the bill code.
  - Instruction: *"Giữ lại tại quầy bưu cục, khách sẽ tự ra quầy lấy, không phát cho shipper đi giao"*.
- **Too Late (After 08:30 AM):** Shipper has completed outbound loading and is en route. The customer must then chase down the courier on the road or wait for normal delivery.

### 3.3 Addressing Strategy for 100% Guaranteed Hub Pickup
- **TikTok Shop / E-commerce Note Failure:** Putting *"Khách nhận tại bưu cục"* in the order note / seller note is ineffective because shipping labels are generated automatically by API; couriers only read the structured recipient address.
- **Guaranteed Fix for Future Orders:** Put the hub destination directly into the structured Address Line:
  ```text
  Người nhận: [Tên người nhận]
  SĐT: [SĐT nhận SMS/Call]
  Địa chỉ: (Khách nhận tại quầy bưu cục) - Bưu cục J&T [Tên bưu cục], [Số nhà, Tên đường bưu cục], Phường [X], Quận [Y], TP [Z]
  ```
  When the parcel reaches that specific bưu cục, the system recognizes it as counter pickup, preventing shipper dispatch.

---

## 4. Telegram Alert Noise & Notification Governance
- **Problem:** Operators managing large device farms receive hundreds of Telegram alerts daily across multiple group chats (`Nuôi`, `Up`, `Farm Alert`). Critical delivery alerts get drowned out.
- **Solution:**
  - Route delivery/parcel critical alerts to a dedicated priority channel or 1-on-1 DM with pinned notification and custom sound.
  - Alternatively, trigger a local desktop TTS chime or system notification on the operator's PC when the tracking status changes to `Đã đến bưu cục phát`.
