# J&T Express Tracking & Autonomous Delivery Watchdog Protocol

## 1. J&T Express Web Tracking Reverse-Engineering & Privacy Gate

Unlike legacy APIs that return 404 (`/api/tracker`), J&T Express Vietnam (`jtexpress.vn`) employs a web-based tracking flow with anti-scraping and recipient privacy protection:

- **Tracking URL:**
  `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}`
- **The Privacy Gate (`cellphone`):**
  If `cellphone` is omitted or empty, J&T opens an interactive modal requiring the recipient's last 4 phone digits (`#cellphone`, 4 digits). Without this parameter, the HTTP response HTML omits the shipment history section entirely.
- **Passing the Recipient's Last 4 Digits:**
  Extract the last 4 digits from the canonical order recipient phone (e.g., `0905.382.174` -> `2174`) and supply it directly as a GET query parameter `&cellphone=2174`.
- **Parsing the Event Timeline:**
  The validated HTML contains `<input type="checkbox" id="chck-{billcode}">` wrapping the timeline. Each event block contains:
  * Event time: `HH:MM:SS` and `YYYY-MM-DD`
  * Action & Location description:
    - Sort Center arrival: `Hàng đã được chuyển đến【TTKT ĐÀ NẴNG】`
    - Transit between hubs: `Bưu cục【TTKT HÀ NỘI】đang chuyển hàng đến【TTKT ĐÀ NẴNG】`
    - Pickup scan: `Nhân viên【...】của bưu cục【...】đã nhận hàng. SĐT nhân viên...`
    - Out for delivery: `Nhân viên【...】của bưu cục【...】đang giao hàng. SĐT shipper...`

---

## 2. Hub Topology & Pickup Timing (Sort Center SOC vs Local Hub)

When an operator requests **self-pickup at carrier station (tự lấy tại bưu cục, không để shipper đi giao)**:

1. **Regional Sort Center / SOC (`TTKT` - Trung tâm Khai thác):**
   - Example: `TTKT ĐÀ NẴNG` (located in Liên Chiểu).
   - **Do NOT advise pickup here:** This is an automated high-volume inter-provincial sorting hub. It is closed to public walk-ins and does not dispatch parcels to retail customers.
2. **Local Delivery Hub (`Bưu cục phát` / Station):**
   - Parcels move from the SOC on early morning feeder trucks (typically 04:30 - 06:30) to the district delivery post office (e.g. Bưu cục Thanh Khê / Tam Thuận).
   - **Actionable Golden Window:** 07:30 - 08:30 morning of the delivery day, immediately after the local hub scans "Đã đến bưu cục" and before couriers load their bikes for the morning round.

---

## 3. Autonomous Watchdog Pattern ("Sao Không Canh Cho Tao?")

Do not tell the operator to manually refresh a carrier tracking link or call hotlines themselves when the agent has execution tools. Implement a silent autonomous watchdog:

1. **State Persistence (`data/jt_delivery_state.json`):**
   Store `last_known_time` and `last_known_desc`.
2. **Silent On No Change (Classic Unix Watchdog):**
   On each cron tick (e.g. every 10–15 minutes), probe the carrier URL. If the latest event matches the saved state, exit silently with zero output.
3. **Escalated Alert on Milestone Scan:**
   When a change is detected:
   - Check for keywords: `bưu cục`, `đến bưu cục`, `đang giao`, `shipper`, `phát hàng`.
   - Output a high-priority alert (`🚨 BÁO ĐỘNG KHẨN CẤP`) with recipient name, phone, COD cash amount, latest hub name, and the direct tracking URL.
   - Update canonical `orders.json` status to `Đã đến bưu cục phát` or `Đang giao hàng (Shipper đang đi phát)`.
