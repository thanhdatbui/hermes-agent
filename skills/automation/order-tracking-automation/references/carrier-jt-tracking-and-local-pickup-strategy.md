# J&T Express Vietnam Tracking & Local Hub Pickup Strategy

## 1. J&T Express Vietnam Tracking Endpoint & Phone Verification

J&T Express Vietnam deprecated legacy tracking endpoints (`/api/tracker` returns 404). Furthermore, querying `jtexpress.vn/vi/tracking?type=track&billcode={code}` opens an anti-scraping / privacy modal requesting the last 4 digits of the recipient's phone number (`cellphone`).

### Working Direct URL
Pass the 4 digits directly in query parameters to bypass the modal and receive full HTML tracking timeline:
```text
https://jtexpress.vn/vi/tracking?type=track&billcode={BILLCODE}&cellphone={PHONE_LAST_4}
```

### HTML Parsing Pattern
Locate the container `id="chck-{BILLCODE}"`:
- Timestamps appear as separate tokens: `HH:MM:SS` followed by `YYYY-MM-DD`.
- Event descriptions contain location brackets: `Hàng đã được chuyển đến【TTKT ĐÀ NẴNG】`, `Bưu cục【...】đang chuyển hàng đến【...】`.
- Courier assignment: `Nhân viên【Tên】của bưu cục【...】đang giao hàng. SĐT shipper【...】`.

---

## 2. Operator / Proxy Receiver Pitfalls (Anti-App Recommendation)

When managing orders placed via farm accounts, burner accounts, or on behalf of third parties:
- **NEVER advise downloading the carrier mobile app** (e.g. "Tải app J&T và đăng nhập bằng số điện thoại người nhận"):
  * Farm accounts / proxy orders use burner phone numbers or customer numbers whose physical SIM is not in the operator's personal phone.
  * Carrier apps require SMS OTP for login; telling the user to log into the app is impossible and creates severe frustration.
- **Dedicated Watchdog instead of App:**
  Use a headless Python watchdog querying the carrier tracking URL directly with the last 4 phone digits, persisting state to a local JSON file (`last_known_time`, `last_known_desc`), and remaining completely silent unless a new event fires.

---

## 3. Local Pickup Protocol (Chặn Shipper & Tự Ra Bưu Cục Lấy Hàng)

### SOC (Trung tâm phân loại / khai thác) vs Bưu cục phát
- **SOC / TTKT (Trung tâm khai thác tự động):** Do NOT attempt pickup at SOC (e.g. TTKT Liên Chiểu). It is an automated transit facility handling cross-provincial freight; retail customer pickup is strictly refused.
- **Bưu cục phát (Local Delivery Hub):** Freight moves from SOC to the local delivery hub via linehaul trucks between 04:00 - 06:30 AM.

### The Golden Window to Call (07:15 - 08:00 AM)
- **Too early (the night before):** The local hub has not received the physical cargo manifest; staff cannot flag or hold the item.
- **Too late (after 08:30 AM):** Couriers (shippers) have already sorted parcels into delivery bags, loaded them onto motorcycles, and departed for daily routes.
- **Golden window (07:15 - 08:00 AM):** Parcels have just been unloaded and inbound-scanned at the hub. Call the hub or carrier hotline immediately with the bill code and recipient name to request holding at counter:
  *"Khách tự đến bưu cục lấy và thanh toán COD, vui lòng giữ lại tại quầy, không xuất cho bưu tá đi phát."*

### The Order Note Fallacy ("Ghi chú nhận tại bưu cục")
- **Order notes on TikTok Shop are for merchants, not logistics:** Merchants print automated thermal labels where notes are either truncated or absent.
- **Automated courier sorting:** Logistics routing algorithms map the structured address string directly to a delivery route. Couriers are evaluated on delivery completion rates and will attempt delivery to the street address regardless of merchant notes.
- **Guaranteed Counter Pickup Method for Future Orders:**
  In the shipping address field, format explicitly:
  `Tên: [Tên người nhận] | SĐT: [SĐT nhận OTP/gọi]`
  `Địa chỉ: (Khách nhận tại quầy) - Bưu cục [Hãng VC] [Tên bưu cục], [Địa chỉ bưu cục], [Quận/Huyện], [Tỉnh/TP]`

---

## 4. Telegram Notification Flood Mitigation

Farm operators often have dozens of Telegram groups with continuous alert traffic. General Telegram notifications get muted or drowned out.
To ensure high-priority order arrival alerts are never missed:
1. **Direct DM Only:** Route cron alert strictly to `deliver: origin` (the user DM), never to farm alert groups.
2. **Pinned Chat & Distinct Ringtone:** Guide user to customize notification sound for the bot DM and pin the conversation.
3. **Local PC Sound Alarm / TTS:** For 24/7 host machines, configure the watchdog script to trigger Windows native sound / TTS when the local hub arrival event is detected.
