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
