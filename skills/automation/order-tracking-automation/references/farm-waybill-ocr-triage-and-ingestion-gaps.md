# Farm Waybill OCR Triage & Ingestion Gap Analysis

## 1. Context & Problem Statement
When operators receive physical packages and send shipping label images (waybills) to ask:
*"Đơn này phải của tao không?"* / *"Sao trong kho đơn không có tên X?"*

There is often a discrepancy between:
- **Physical parcel presence**: Real package arrived with a printed waybill.
- **SQLite SSOT (`farm_master.db` -> table `orders`)**: The order ID / recipient name is missing from the database.

Operators will immediately suspect system bugs, data corruption, or "DB lưu ngu" (bad DB logic). The coordinator must follow a rigorous, evidence-backed triage pattern to clarify the root cause without guessing or deflecting.

---

## 2. Waybill OCR Feature Extraction & Anti-Clustering Fingerprints

When parsing a physical TikTok Shop / J&T / GHN / SPX waybill image:

1. **Extract 6 Core Waybill Entities:**
   - **Tracking Number (Mã vận đơn)**: Linear barcode / 12-digit number (e.g. `862606031586`).
   - **TikTok Order ID**: Printed at bottom footer (e.g. `586900142427571430`).
   - **Order Timestamp**: Printed at bottom right (e.g. `2024-11-01 09:20` / `2026-11-01 09:20`).
   - **Recipient Display Name**: Top left box (e.g. `Hài Hồng` / `Hải Hồng`).
   - **Masked Phone**: e.g. `(+84)90*****72`.
   - **Delivery Address & Routing String**: e.g. `24 Đường Đinh Tiên Hoàng ,Ri n gci 0792379705 Phường Hải Châu, Đà Nẵng`.

2. **The "Rin gọi [Phone]" Secret Keyword Fingerprint:**
   - On TikTok Shop voucher farming, recipient names and phone numbers are randomly generated to defeat platform clustering algorithms (anti-sybil / anti-clustering).
   - **The Ground Truth Anchor:** Operators embed their real contact number in the freeform address text:
     - Pattern: `Rin gọi 0792379705` or `Rin ship 0935554653`.
     - **OCR Line-Wrap Pitfall:** Thermal label printers often wrap long address lines mid-word:
       `24 Đường Đinh Tiên Hoàng ,Ri`
       `n gci 0792379705`
       WinRT OCR reads `Ri\nn gci 0792379705` (Vietnamese "gọi" read as "gci").
     - **Triage Action:** Recognize `Ri... gci <phone>` as the operator's canonical phone number anchor.

---

## 3. DB Absence Triage: "Do Quên Nhắn Hay DB Lưu Ngu?"

When the recipient name / order ID does NOT exist in `farm_master.db` table `orders`:

### Root Cause Decision Tree:
1. **Did the order ever enter the ingestion pipeline?**
   - Check chat session history / session DB via `session_search` for the order ID or recipient name.
   - Check `orders` table in `farm_master.db` (`SELECT * FROM orders WHERE ...`).
2. **If NO trace in chat history and NO trace in `orders` table:**
   - **Conclusion:** The order was placed directly on a farm device by the operator or a local script, but was **never ingested** into the management database (neither via chat `--add` nor via automated app sync scan).
   - **Explanation to Operator:** State clearly and calmly:
     - The order is 100% genuine farm order (proven by the secret phone anchor `0792379705` and street address).
     - The absence in DB is because it was placed but not yet forwarded/ingested into the tracking registry (not a silent DB drop or corruption).
     - Offer immediate ingestion into `farm_master.db` with the next available ID (e.g. `DH-YYYYMMDD-XXX`).

3. **If trace exists in chat history but NOT in DB:**
   - **Bug / Failure:** A previous session promised ingestion but failed silently or was interrupted before committing to SQLite.
   - Acknowledge the failure with evidence and immediately run `python D:/Taadaa/tools/manage_orders.py --add ...`.
