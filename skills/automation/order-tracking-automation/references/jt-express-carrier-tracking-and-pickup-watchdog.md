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

---

## 4. Zero-Prompt Telegram Group Discovery via `channel_directory.json`

- **The Problem:** In farm setups, existing Telegram groups receive hundreds of automated farm alerts daily, causing operators to mute Telegram or miss order milestones. Creating a separate group (e.g., "Đơn hàng tiktok") is essential.
- **The Pitfall:** Asking the user to run `/status` or manually copy their new group's Chat ID is an unnecessary round-trip that frustrates the user.
- **Canonical Solution:** Hermes automatically registers all connected chats in `channel_directory.json` located at `$LOCALAPPDATA/hermes/channel_directory.json`.
  1. Inspect `channel_directory.json` (under `platforms.telegram`).
  2. Locate the newly created group by name (e.g., `{'id': '-5316882628', 'name': 'Đơn hàng tiktok', 'type': 'group'}`).
  3. Update the cronjob delivery target directly: `deliver: "telegram:-5316882628"` in $O(1)$ without prompting the user.

---

## 5. Continuous Admin Host Siren & Chat-Driven Stop Gate

To alert operators across physical rooms before couriers dispatch morning routes:

1. **Continuous Looping Siren on Admin (`192.168.110.119`):**
   - When the delivery watchdog detects arrival at the local destination hub or courier assignment, trigger an infinite audio siren on the physical Admin host.
   - Run via `admin_ssh.py` with detached execution:
     `start cmd /c python D:\OneDrive\Taadaa_Sync_Shared\tools\admin_alarm.py D:\OneDrive\Taadaa_Sync_Shared\tools\stop_jt_{billcode}.flag`
   - `admin_alarm.py` loops `winsound.Beep(1200, 250)` and `winsound.Beep(1800, 300)` continuously until the specified flag file exists.
2. **Instant Chat-Driven Stop Mechanism:**
   - The siren must continue until the operator acknowledges it.
   - When the user sends any stop intent ("dừng", "tắt loa", "stop", "đã lấy hàng"), Hermes creates the flag file via SSH:
     `python D:/Taadaa/tools/admin_ssh.py "echo stop > D:\OneDrive\Taadaa_Sync_Shared\tools\stop_jt_{billcode}.flag"`
   - The looping process detects file existence (`os.path.exists`) and exits in $< 1$ second.

---

## 6. Farm Voucher Multi-Account Courier Coordination & Secret Keyword Convention

1. **The Anti-Fraud Clustering Requirement:**
   Bao voucher farming requires each purchase to use distinct, randomized recipient names, dummy phone numbers, and varied street numbers/alleys to bypass platform fraud detection (anti-clustering).
2. **The Courier Failure Mode:**
   Couriers finding invalid street addresses and unreachable dummy phone numbers will mark orders as "Khách không nghe máy" and initiate return-to-sender (RTS), causing lost vouchers and failed orders.
3. **Establishing a Mutual Benefit Courier Agreement:**
   - Couriers earn commissions per delivered parcel and are penalized for returns. A consolidated delivery of multiple parcels with instant cash COD payment is highly desirable for them.
   - **Secret Keyword / Marker Protocol:**
     * Agree on a fixed keyword on the printed waybill (e.g., fixed surname prefix in Recipient Name or note substring in Address).
     * The courier inspects parcels at the local hub floor during morning sort (07:15 - 08:00 AM).
     * Any parcel bearing the secret keyword is automatically bundled and delivered directly to the physical farm headquarters (e.g., 47 Tran Cao Van) for bulk cash settlement, without calling the dummy numbers.
