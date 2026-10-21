# TikTok Shop In-App Order Tracking & Carrier Handoff

## Context & Reality
TikTok Shop often fails to send dispatch/tracking emails to customer email addresses (especially Hotmail/Outlook via/clones), or sends them with significant delay (sometimes only upon delivery). Relying solely on mailbox polling (`mail_order_sync.py`) can cause the order tracking pipeline to stall at "Đã đặt hàng" without discovering the tracking code.

The primary, real-time ground truth for tracking codes is the **in-app Order Details page** on the farm device where the order was placed.

## End-to-End Pipeline

```text
[Discovery Phase - Dual Path]
  ├── Path A (Passive/Headless): GPM Webmail / Outlook session reader (zero device impact)
  └── Path B (Active/Ground-Truth): TikTok In-App Order Inspector via ADB on farm device
             │
             ▼ Extracts: Carrier (SPX, J&T, Ninja Van) + Tracking Code (SPXVN..., etc.)
[Transit Monitoring Phase]
  └── Carrier API poller (track_order.py) running every 15-30m until destination hub arrival
             │
             ▼
[Canonical State Presentation]
  └── orders.json / Dashboard (/api/orders) / QuanLyDonHang_TikTokShop.xlsx
```

## Protocol for In-App Order Inspection

When mailbox polling yields no tracking code within the dispatch window, invoke the in-app tracker under strict farm safety rules:

1. **Operator Device Lock (Mandatory):**
   Farm devices run automated feeding, nurture, and upload crons. Never issue ADB touch/start commands without acquiring the device lock:
   ```bash
   python D:/Taadaa/tools/with_device_lock.py --machine <M> -- <adb command / script>
   ```

2. **Verify Account Context (Slot / User Binding):**
   Farm phones host multiple accounts (typically 7-8 accounts per phone).
   - Check current focus / UI state.
   - If TikTok is on a different account than the ordering account, use the canonical account switcher flow to switch to the target handle (e.g., Row 4 / `@augustusdant7`).
   - Do NOT attempt to place orders or read orders under the wrong logged-in identity.

3. **Navigate to Order Details & Bypass System Traps:**
   - **Keyguard / Scrim Trap:** Dismiss lockscreen via `wm dismiss-keyguard` and `input keyevent 82`. Do not use blind upward swipes for unlocking if the app might already be running, as that scrolls the view down.
   - **Foreground Focus Check:** Do not rely on `pidof <package>`. Verify `mCurrentFocus` in `dumpsys window windows`. If not focused, bring to front via `am start -n <package>/<splash_activity>`.
   - **Profile Scroll Recovery:** If on profile but the header/shortcuts are scrolled off, swipe down `(540, 400) -> (540, 1600)` to bring "Đơn hàng của bạn" back into view.
   - Go to Profile -> Menu / Order Center -> "Đơn hàng của tôi" (My Orders) or invoke the TikTok Shop order deeplink.
   - Locate the target order ID (e.g., `DH-20261020-001`).
   - Tap tracking banner / product item to open full delivery details.

4. **Visual Evidence & OCR Extraction:**
   - Capture evidence screenshot to `D:/OneDrive/TaadaaData/kibe/orders/images/<order_id>_shipping.jpg` and `D:/Taadaa/orders/images/`.
   - Run WinRT OCR Primary (`automation_core.ui_extract` / `ocr_boxes.ps1`) to extract:
     - Shipping status (e.g., "Đã giao cho đơn vị vận chuyển", "Đang vận chuyển").
     - Carrier name (`Shopee Xpress`, `J&T Express`, `Ninja Van`, `GHTK`, `Viettel Post`).
     - Tracking number (`SPXVN...`, `JNT...`).
   - CẤM TUYỆT ĐỐI dump XML trực tiếp (`uiautomator dump`, `dumpWindowHierarchy`, port 7912) trên màn hình đơn hàng WebView theo Hard Gate `tools/ui_policy_check.py`.

5. **Handoff & Cleanup:**
   - Update canonical records: `orders.json` and `QuanLyDonHang_TikTokShop.xlsx`.
   - Update dashboard card status.
   - Force-stop `com.ss.android.ugc.trill` (or `com.zhiliaoapp.musically`).
   - Release the device lock immediately so the farm phone returns to its scheduled idle/sleep cycle.
   - Hand off monitoring to `track_order.py` (which only queries carrier web APIs and does not touch farm devices).
