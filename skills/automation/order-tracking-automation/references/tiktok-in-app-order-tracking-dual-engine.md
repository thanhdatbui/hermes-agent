# TikTok In-App Order Tracking & Dual-Engine OCR/XML Extraction

## Background & Problem
When TikTok Shop orders are placed across phone farm accounts:
1. **Mail Dispatch Blind Spot:** TikTok Shop frequently omits shipping confirmation emails or dispatches them with significant latency. Relying solely on mailbox sync will leave orders stuck at "Đã đặt hàng" even after parcels have shipped.
2. **Device UI Complexity:** The in-app order details screen may render order details using mixed native views and WebViews/Canvases. An XML dump alone may miss tracking numbers or carrier names if they are embedded within non-text nodes or graphic banners.
3. **Farm Stability Invariant:** On Android 7 / Galaxy S7 devices, running raw `uiautomator dump` in adb shell triggers process kill (Exit 137). Calling ADB taps or blind gestures without device locks causes collisions with scheduled feed/rest cycles.

## Dual-Engine Architecture (XML Hierarchy + WinRT Native OCR)

To achieve 100% extraction reliability without human intervention, use a dual-engine parser:

```text
[Device Screen / App State]
         │
         ├── Step 1: Capture Screen Image & Dump Hierarchy XML (via atx-agent port 7912)
         │
         ▼
[Engine 1: XML Parser]
   ├── Extract all `text` and `content-desc` attributes from hierarchy nodes
   └── Run regex matches for Carrier (SPX, J&T, Ninja Van...) & Tracking Code (SPXVN..., JNT...)
         │
         ├── Found Code & Carrier? ──► [DONE: Update JSON/Excel]
         │
         ▼ Missing tracking or carrier
[Engine 2: Native WinRT OCR Fallback]
   ├── Pass captured screenshot to Windows Native OCR (`Windows.Media.Ocr.OcrEngine` via PowerShell/Python)
   ├── Extract bounding boxes and full text lines
   └── Run regex matches across recognized OCR lines
         │
         ▼
[Canonical State Synchronization]
   ├── Update `orders.json` and sync with workbook `QuanLyDonHang_TikTokShop.xlsx`
   └── Hand off tracking code to carrier tracking loop (`track_order.py`)
```

## Key Invariants & Pitfalls

1. **Hierarchy Extraction on S7:**
   - Always query `atx-agent` JSONRPC on port 7912 (`http://<device_ip>:7912/jsonrpc/0` method `dumpWindowHierarchy`, params `[False]`).
   - Never call `adb shell uiautomator dump` on farm devices.
2. **WinRT OCR PowerShell Template:**
   - Invoke Windows Runtime APIs using `[Windows.Media.Ocr.OcrEngine]` with fallback from `vi-VN` to `en-US` and user profile languages.
   - Use `AwaitTask` helper with `[System.WindowsRuntimeSystemExtensions]::AsTask` for asynchronous WinRT tasks.
3. **Tracking Code & Carrier Regex:**
   - Normalized ASCII matching (strip diacritics) for carrier recognition (`shopee xpress|spx`, `j&t|jnt`, `ninja ?van`, `viettel post`).
   - Match tracking labels (`mã vận đơn`, `mã vận chuyển`, `mã theo dõi`, `tracking number`) followed by alphanumeric tokens of length 8–30.
   - Prefix carrier inference (e.g. `SPXVN...` implies SPX, `JNT...` implies J&T Express).
4. **Device Lock Isolation:**
   - Always wrap device access in `operator_device_lock` or `python D:/Taadaa/tools/with_device_lock.py --machine <N>`.
   - If physical connection drops (`Present: False`), classify as hardware disconnect and do not fail silently or attempt blind adb commands.
