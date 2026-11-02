# In-App TikTok Shop: Switcher to Order Detail Navigation Chain

## 1. The Multi-Step In-App Navigation Chain
On Samsung S7 phone farm devices, navigating from TikTok's default state to the full tracking detail of an order requires traversing a strict 5-stage screen hierarchy:

```
[1. Feed / Home] 
       │ (Tap Bottom Right "Hồ sơ" / "Hö sd" @ y ≈ 1880)
       ▼
[2. Profile Screen]
       │ (If current handle != target handle: tap header name @ (300, 320), select from switcher sheet)
       │ (Tap "Đơn hàng của bạn" / "Ddn häng cÖa ban" @ y ≈ 850)
       ▼
[3. Order Hub / Mall Center]
       │ (Tap "Xem tất cả >" / "Xem tät cå >" @ (920, 260) OR specific status card @ y ≈ 580)
       ▼
[4. Order List Screen ("Tất cả đơn hàng")]
       │ (Tap target order item card or tracking summary line @ y ≈ 700-900)
       ▼
[5. Tracking Details Screen ("Theo dõi kiện hàng")]
       └─> Exposes Carrier Name (J&T Express / GHN / SPX), 12-digit Billcode (e.g. 862662878224), and Timestamps.
```

---

## 2. Stage-by-Stage UI Coordinates & OCR Traps (Samsung S7 1080x1920)

### Stage 1: Feed Landing to Profile
- **Default State:** TikTok launches into the video feed with bottom navigation bar: `Trang chi | Cdfa hång | + | Hép thi-f | Hö sd`.
- **Target:** "Hồ sơ" tab is located at bottom right: `(x=972, y=1881)` (`x > 0.9 * width, y > 1700`).
- **OCR Kerning:** WinRT OCR consistently reads "Hồ sơ" as `Hö sd`, `Ho sd`, or `H6 sd`.

### Stage 2: Profile Account Verification & Order Entry
- **Handle Mismatch:** If the profile header does not match the order's `tiktok_handle`:
  - Tap account name/dropdown at `(x=300, y=320)`.
  - On bottom sheet ("Chuyển đổi tài khoản" / `Chuyén döi tåi khoån`), locate the target handle and tap.
  - After tapping, if bottom sheet does not dismiss, send `KEYCODE_BACK` (keyevent 4).
  - Tapping an account often redirects back to Feed; immediately re-tap `Hö sd` at `(972, 1881)`.
- **Order Entry Button:**
  - Located at middle of profile screen: `Ddn häng cÖa ban` / `Đơn hàng của bạn`.
  - Target point: `(x=300, y=850)` (`y` bounds: 800 - 900).

### Stage 3: Order Hub to Order List (The "Xem tất cả >" Trap)
- **The Trap:** Stage 3 is an intermediate shopping/voucher hub, NOT the list of orders. Naive OCR looking for tracking numbers here will find none and falsely conclude `NO_TRACKING_ON_SCREEN`.
- **Navigation:**
  - Tap **"Xem tất cả >"** (`Xem tät cå >`) at top right: `(x=920, y=260)` (`x > 800, 240 < y < 300`).
  - Alternatively, tap the specific status icon (e.g. `Đã giao đơn hàng` at `(x=360, y=580)`).

### Stage 4: Order List to Tracking Details
- **Order Card Selection:**
  - List displays orders with shop name, thumbnail, product title, and status line (e.g. `1 thång 11 Dä giao - Kien häng cÖa ban dä dd4c giao`).
  - Tap either the product title row or status line `(x=400, y=700-900)`.

### Stage 5: Tracking Details Extraction
- **Screen Verification:** Header reads "Theo dõi kiện hàng" (`Theo döi ki#n häng`).
- **Data Extracted via WinRT OCR:**
  - Carrier: `J&T Express`, `GHN`, `SPX`.
  - Billcode: J&T 12 digits (regex `8[4-9]\d{10}`), e.g. `862662878224`.
  - Delivery Status: `Đã giao` (`Dä giao`), `Đang trên đường giao`, `Đang trung chuyển`.
  - Time & Recipient: e.g. `Nov 1 11:47 AM: Đã giao - Kiện hàng của bạn đã được giao. Người nhận: Customer`.

---

## 3. Post-Extraction Protocol
1. Once billcode is extracted, update SQLite SSOT (`farm_master.db` table `orders`) and Excel.
2. If status is delivered/received, mark `archived = 1` (`TERMINAL`).
3. Press `KEYCODE_HOME` (keyevent 3) to return phone to launcher and let screen turn off cleanly.
