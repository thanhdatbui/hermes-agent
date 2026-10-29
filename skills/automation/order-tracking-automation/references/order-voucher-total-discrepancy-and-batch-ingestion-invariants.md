# Order Total Voucher Discrepancy & Batch Ingestion Invariants

## Context & Problem
During high-volume TikTok Shop voucher farming across multi-device grids:
1. **Initial Order Confirmation vs Actual Payable Total Trap:**
   - In freshly submitted orders (e.g. `Đã đặt hàng` status), the UI frequently displays the product list price or cart subtotal (e.g. `59.000₫`) in the product card.
   - However, after voucher/platform discounts are applied at checkout or when the order transitions to `Chờ chuyển phát` (Awaiting shipment), the actual payable amount `Tổng: 1₫` or `COD 1đ` is rendered at the bottom summary pill.
   - Initial ingestion scripts that pull `item.price` as `item.total` or misread the bottom `Tổng:` pill create corrupted financial accounting records.

2. **User Explicit Correction Authority:**
   - When the user explicitly notes: *"kiểm tra lại đơn hàng ở máy 11 tik 1, tổng có 1đ thôi"*, the user's statement of the payable amount is ground truth.
   - Coordinator must immediately cross-verify against the fresh rendered screenshot (`browser_vision` + WinRT OCR), update `item.total = 1`, `cod_amount = 1`, and update the status to `Chờ chuyển phát` if indicated by the app header.

3. **High-Frequency Ingestion & Coordinator Write Quota Safeguards:**
   - In sessions where the user submits multiple consecutive order screenshots (e.g. Orders 008, 009, 010, 011, 012, 013), writing individual standalone scripts (`save_order_YYYYMMDD_XXX.py`) for each order rapidly depletes Coordinator T1 write budget (`COORDINATOR WRITE DENIED: Hết ngân sách T1 > 500 dòng`).
   - Standalone scripts also create file bloat in `D:/Taadaa/orders/`.
   - **Canonical Pattern:**
     - Maintain and reuse existing batch ingestion runners (e.g. `crop_order_20261029.py` or `manage_orders.py`) or dispatch atomic multi-order batch updates.
     - Never create N single-use script files for N orders in the same session.
