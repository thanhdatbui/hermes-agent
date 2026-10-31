# In-App Tracking Extraction & Switcher Disambiguation Protocol

## 1. Profile Username vs Switcher Bottom Sheet Ambiguity
When automating navigation to "Đơn hàng của bạn" (My Orders) on TikTok Android:
- **Symptom:** On the Profile tab (`SplashActivity`), the active account handle (e.g. `@tooanh2604`) is rendered immediately under the user avatar.
- **Trap:** A naive switcher check checking `if _find_handle_center(boxes, wanted_handle)` evaluates to `True` on the profile screen itself. The script assumes the account switcher bottom sheet is open, taps on the handle coordinates, and enters an infinite loop tapping the profile's own username text instead of clicking "Đơn hàng của bạn".
- **Resolution:**
  1. Enforce explicit switcher sheet markers (`Chuyển đổi tài khoản`, `Thêm tài khoản`, `Switch account`, `Add account`) before interpreting handle coordinates as a switcher item.
  2. If the current header handle matches the target account (`_handle_key(header) == wanted`), immediately tap `ORDER_ENTRY_LABELS` ("Đơn hàng của bạn" / "Cửa hàng").

## 2. J&T Express Numeric Billcode Extraction
- On the TikTok Shop "Theo dõi kiện hàng" (Tracking Details) timeline screen, J&T Express billcodes are frequently displayed as raw 12-digit integers (`8626...`) without any prefix label (`Mã vận đơn:` or `JNT`).
- Generic regexes matching `(?:mã vận đơn|tracking code):\s*(\w+)` fail completely.
- **Detection Pattern:** When carrier is identified as `J&T Express` or when standard labeled patterns yield no candidates, scan explicitly for `\b(8[4-9]\d{10})\b`.

## 3. Double Device-Lock Deadlock Trap
- When an execution wrapper (`with_device_lock.py --machine <N>`) runs an automation script whose internal functions (`_adb_run`, `_adb_screencap`) also invoke `operator_device_lock(serial=...)`, the child process will deadlock against the parent process holding the lock file.
- **Resolution:** Either remove the outer wrapper when the inner script handles device locking atomically, or ensure re-entrant lock compatibility.

## 4. Terminal Retirement Protocol
- When an order reaches a terminal delivery event (`Đã giao hàng thành công`, `Đã ký nhận`, `Đã hủy`):
  1. Mark `"archived": true`, `"archived_at": "<ISO_TIMESTAMP>"` in canonical JSON.
  2. Update Excel column `Lưu Trữ` to `ĐÃ LƯU TRỮ`.
  3. The order lifecycle engine classifies the order as `TERMINAL` and permanently bypasses all ADB, phone inspection, and carrier web polling for that order.

## 5. Switcher OCR Noise & Already-Active Bottom Sheet Dismissal Trap
- **OCR Kerning Space Trap:** WinRT OCR frequently injects spaces into handle names due to font kerning (e.g. `@khnh.vyyyy6` -> `@khn h.vyyyy6`). TikTok handles never contain spaces. All handle normalization functions (`_handle_key`) must strip all spaces before string comparison (`.replace(" ", "")`).
- **OCR Diacritic Variation:** Vietnamese diacritics on bottom sheet headers frequently deform under OCR (e.g. `Chuyển đổi tài khoản` -> `Chuyén ddi tåi khoån`). Substring checks must match fuzzy variations like `chuyen ddi` or `chuyen doi` rather than full exact phrases.
- **Already-Active Switcher Hang:** In TikTok Android, tapping an account item on the switcher bottom sheet that is *already active* does not dismiss the sheet. The navigation loop must issue `keyevent 4` (KEYCODE_BACK) after selection to ensure the sheet collapses and reveals the profile shortcuts ("Đơn hàng của bạn" / "Cửa hàng").

## 6. False-Positive Order List Markers on Mall Landing Pages
- Generic filter words like `"Tất cả"` or `"Tat ca"` appear everywhere on TikTok Shop Mall / Flash Sale pages. Including them in `ORDER_LIST_MARKERS` tricks the navigator into believing it has already reached the user's order history, halting navigation prematurely on the shopping homepage.
- Reserve `ORDER_LIST_MARKERS` strictly for unambiguous order-history screens (`"Đơn hàng của tôi"`, `"Chi tiết đơn hàng"`, `"Tìm kiếm đơn hàng của bạn"`, `"Đã đặt hàng"`, `"Hủy đơn hàng"`). Mall pages exposing a `"Đơn hàng"` shortcut button must be tapped to reach the real order list.

