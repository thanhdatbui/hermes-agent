# In-App Switcher, OCR Kerning & Carrier Prefix Hardening

## 1. Head-of-Line Blocking in App Sync (`max_app_syncs = 1`)
- **Trap:** When restricting app inspection to 1 order per cron tick to save device battery/bus timeout, iterating sequentially through `orders.json` causes the first failing or busy machine to starve all subsequent orders indefinitely.
- **Resolution:** Non-blocking app sync iteration. If an order returns `DEFERRED_DEVICE_BUSY`, `APP_SYNC_ERROR`, or `SKIPPED_NO_MACHINE`, do not count it against `max_app_syncs`. Continue evaluating subsequent pending orders in the batch so a single stuck machine never halts the farm tracking queue.

## 2. OCR Text Mismatch & Kerning Invariants on Farm Devices
- **Handle Kerning & Digit Confusion:**
  - Android fonts often kern usernames so that WinRT OCR inserts internal whitespace (e.g. `@khnh.vyyyy6` -> `@khn h.vyyyy6`).
  - OCR frequently confuses digit zero `0` with letter `o`/`O` (e.g. `thanh.h.dng00` -> `thanh.h.dngOO`).
  - **Normalization Rule:** In `_handle_key(text)`, strip all whitespace, strip `@`, lowercase, and map `0` to `o` before any equality check:
    ```python
    def _handle_key(text: str) -> str:
        return _fold(text).replace(" ", "").replace("0", "o").strip().lstrip("@").strip()
    ```
- **Diacritics & Spelling Noise in Switcher Headers:**
  - "Chuyển đổi tài khoản" is recognized as "Chuyén ddi tåi khoån" or "Chuydn ddi täi khoån".
  - **Resolution:** Check general anchor keywords (`"tai khoan"`, `"chuyen"`, `"switch"`, `"add account"`) constrained to `y < 400` rather than demanding exact string equality.
- **Active Account Bottom-Sheet Trap:**
  - In TikTok Android, tapping an account item that is *already active* does not close the switcher sheet; it stays open and loops until navigation timeout.
  - **Resolution:** After tapping the target account (or detecting that the active account matches), always send `KEYCODE_BACK` (`input keyevent 4`) to explicitly dismiss the bottom sheet and reveal the profile.

## 3. Shop/Mall Home Page vs Order List Marker Ambiguity
- Shopping Mall home tabs contain filter chips like "Tất cả" (All categories/flash sales). Including "Tất cả" in `ORDER_LIST_MARKERS` tricks the navigator into believing it has already reached the order list.
- **Resolution:** Exclude generic shopping chips ("Tất cả", "Tat ca") from `ORDER_LIST_MARKERS`. When on the Shop tab (`header is None`), detect the header icon `"Đơn hàng"` (`y < 500`) to navigate into the true "Đơn hàng của tôi" timeline.

## 4. Carrier Code Prefix Expansion
- GHN (Giao Hàng Nhanh) tracking codes generated from TikTok Shop begin with prefix `VNGH` (e.g. `VNGH80572930814`), followed by numeric sequences.
- Regex rules for carrier code extraction must include `vngh` alongside `spxvn` and `jnt`:
  ```python
  CODE_PREFIX_CARRIERS = (("spxvn", "SPX"), ("jnt", "J&T Express"), ("ghn", "GHN"), ("vngh", "GHN"))
  TRACKING_PREFIX = re.compile(r"\b((?:spxvn|jnt|vngh)[a-z0-9]{6,25})\b")
  ```

## 5. Silent Watchdog Alerting Invariant
- Under Hermes `no_agent: true` cron execution, an empty stdout indicates a silent tick (no Telegram notification).
- Whenever carrier web tracking updates an order status (especially milestone transitions such as `Đang giao hàng (Shipper đang đi phát)` or `Đã giao hàng thành công`), the engine MUST write a structured alert to stdout so the message is delivered immediately to the Telegram chat.
