# TikTok In-App Order Tracking & Dual-Engine OCR/XML Extraction

## Background & Problem
When TikTok Shop orders are placed across phone farm accounts:
1. **Mail Dispatch Blind Spot:** TikTok Shop frequently omits shipping confirmation emails or dispatches them with significant latency. Relying solely on mailbox sync will leave orders stuck at "Đã đặt hàng" even after parcels have shipped.
2. **Device UI Complexity:** The in-app order details screen may render order details using mixed native views and WebViews/Canvases. An XML dump alone may miss tracking numbers or carrier names if they are embedded within non-text nodes or graphic banners.
3. **Farm Stability Invariant:** On Android 7 / Galaxy S7 devices, running raw `uiautomator dump` in adb shell triggers process kill (Exit 137). Calling ADB taps or blind gestures without device locks causes collisions with scheduled feed/rest cycles.

## Dual-Engine Architecture (WinRT Native OCR PRIMARY, XML Hierarchy Fallback)

To achieve 100% extraction reliability without human intervention, use a dual-engine parser with **WinRT OCR as the PRIMARY engine (User Invariant)**:

```text
[Device Screen / App State]
         │
         ├── Step 1: Capture Screen Image & Dump Hierarchy XML (via atx-agent port 7912 / adb)
         │
         ▼
[Engine 1: Native WinRT OCR (PRIMARY)]
   ├── Pass captured screenshot to Windows Native OCR (`Windows.Media.Ocr.OcrEngine` via PowerShell/Python with `vi-VN`)
   ├── Extract text lines directly from rendered pixels (handles Canvas, Flutter, and embedded WebViews)
   └── Run regex matches across recognized OCR lines for Carrier & Tracking Code
         │
         ├── Found Code & Carrier? ──► [DONE: Update JSON/Excel & Hand off to Carrier API]
         │
         ▼ Missing tracking or carrier
[Engine 2: XML Hierarchy Parser (FALLBACK)]
   ├── Query hierarchy nodes via `atx-agent` HTTP JSONRPC on port 7912
   ├── Extract all `text` and `content-desc` attributes from hierarchy nodes
   └── Run regex matches for Carrier (SPX, J&T, Ninja Van...) & Tracking Code (SPXVN..., JNT...)
         │
         ▼
[Canonical State Synchronization]
   ├── Update `orders.json` and sync with workbook `QuanLyDonHang_TikTokShop.xlsx`
   └── Hand off tracking code to carrier tracking loop (`track_order.py`)
```

## Key Invariants & Pitfalls

1. **WinRT OCR MUST BE PRIMARY (User Invariant):**
   - In-app order detail screens render via customized WebView / Flutter canvases where accessibility nodes frequently have empty text.
   - Screen capture combined with `Windows.Media.Ocr.OcrEngine` directly reads visible text on screen, capturing carrier names (`Shopee Xpress / SPX`, `J&T Express`, `Ninja Van`, `Viettel Post`, `Giao Hàng Tiết Kiệm`) and tracking codes (`SPXVN...`, `JNT...`, `8-30` alphanumerics).
2. **Hierarchy Extraction on S7 (Fallback Only):**
   - Only call hierarchy extraction when OCR lacks fields or is inconclusive.
   - Query `atx-agent` JSONRPC on port 7912 (`http://<device_ip>:7912/jsonrpc/0` method `dumpWindowHierarchy`, params `[False]`).
   - Never call `adb shell uiautomator dump` on farm devices (triggers exit 137).
3. **Tracking Code & Carrier Regex:**
   - Normalized ASCII matching (strip diacritics) for carrier recognition (`shopee xpress|spx`, `j&t|jnt`, `ninja ?van`, `viettel post`).
   - Match tracking labels (`mã vận đơn`, `mã vận chuyển`, `mã theo dõi`, `tracking number`) followed by alphanumeric tokens of length 8–30.
   - Prefix carrier inference (e.g. `SPXVN...` implies SPX, `JNT...` implies J&T Express).
4. **Device Lock Isolation:**
   - Always wrap device access in `operator_device_lock` or `python D:/Taadaa/tools/with_device_lock.py --machine <N>`.
5. **Hardware Triage: Physical Disconnect vs Soft ADB Transport Hang:**
   - When a device disappears from `adb devices`, inspect `Get-PnpDevice | Where-Object { $_.InstanceId -like "*<SERIAL>*" }`.
   - `Present: True` but absent from `adb devices`: USB hardware connection and endpoint are intact; soft ADB split or unresponsive `adbd`. Recover via `adb -s <serial> reconnect` or killing rogue port 5038 listeners.
   - `Present: False` AND simultaneous Wi-Fi drop: Complete device shutdown, dead battery, or physical cable pull. Host reboot cannot revive unpowered hardware.
   - `Present: False` with Wi-Fi alive: Controller EHCI/Hub port hang; host PC reboot or bus reset will restore enumeration.
