# TikTok Shop Order Creation and Cross-Reference Audit Protocol

## Context

When the user submits a screenshot (often captured from a multi-phone control software like Total Control or Genymotion/scrcpy grid) showing a successful TikTok Shop order and asks to record/save the order:

1. The order may originate from an automated phone farm device.
2. The user might only provide a recipient name, phone number, and address hint ("địa chỉ trong hình").
3. The phone screen in the image displays critical ground truth: order status, items, variation, unit price, total price, delivery estimate, masked phone number (`(+84)98*****15`), and masked linked email (`t***6@gmail.com`).

---

## Step-by-Step Procedure

### 1. Ingestion and Crop Integrity
* **Do not use the full desktop screenshot as the primary card image**: A 1280x720 or 1920x1080 farm grid screenshot placed directly into an order card forces the user to squint at tiny text.
* **Crop the clean phone screen**: Extract the bounding box of the active phone window (portrait ratio ~ 9:16).
* **Dual Asset Archival**:
  - `order_confirmation`: Clean cropped vertical phone screen (`D:/Taadaa/orders/images/order_YYYYMMDD_XXX.jpg`).
  - `desktop_screenshot`: Full uncropped screen capture (`order_YYYYMMDD_XXX_raw.jpg`).
* **Sync to Cloud Mirror**: Copy the cropped JPEG immediately to OneDrive (`D:/OneDrive/TaadaaData/kibe/orders/images/`).

### 2. OCR and Transliteration Extraction
* Use Windows Native OCR (`Windows.Media.Ocr`) with 3x Lanczos upscaling on difficult crops (e.g. address block, product details).
* Handle English OCR engine transliteration of Vietnamese vowels:
  - `76 DtJdng Trån cao Vån, PhtJdrg Thanh Khé. Då Nång` $\rightarrow$ `76 Đường Trần Cao Vân, Phường Thanh Khê, Đà Nẵng, Việt Nam`.
* Reconcile masked phone number from image (`(+84)98*****15`) with full unmasked phone number explicitly provided by the user (`0986.327.915`).

### 3. Farm Account Identity Cross-Referencing
Never leave the account or farm device as `Unknown` if device indicators exist:
1. **Identify Machine Number**: Read the window title bar in Total Control (e.g. `22 SM-G930F` $\rightarrow$ Machine 22).
2. **Read Masked Email**: Note the prefix and suffix from the order email notification toggle (e.g. `t***6@gmail.com`).
3. **Lookup Farm Workbooks & Focus Verification**:
   - **Tiled Multi-Device Ambiguity Triage (SparkActivity)**: In tiled Total Control grids where window title bars are adjacent or non-standard, verify candidate machines in O(1) via `with_device_lock.py --machine <N> -- adb -s <serial> shell "dumpsys window windows | grep mCurrentFocus"`. If `mCurrentFocus` is `com.bytedance.hybrid.spark.page.SparkActivity`, that machine is the live TikTok Shop order host.
   - `taikhoan_run_safe.xlsx`: Filter rows where `May == 22`. Identify slot/row handles (e.g. Row 128 `ngomai.ly`, Row 129 `tooanh2604`, Row 131 `tangchi10`).
   - `Tik1.xlsx` - `tik4.xlsx`: Check niche and slot status (e.g. `Tik2.xlsx` Row 23 corresponds to Machine 22, Slot 2, `@tooanh2604`).
   - `gmail_clean_v2.xlsx`: Search for email starting with `t` and ending with `6` belonging to Machine 22 (e.g. `tooanh26041996@gmail.com`).
4. **Bind Full Identity**: Record Machine 22, Slot 2, TikTok handle `@tooanh2604`, and linked email `tooanh26041996@gmail.com`.

### 4. Canonical Order Record Creation
Store the order record in JSON with the canonical schema:
```json
{
  "order_id": "DH-YYYYMMDD-XXX",
  "order_date": "YYYY-MM-DD HH:MM",
  "customer": {
    "name": "...",
    "phone": "...",
    "address": "..."
  },
  "farm_device": {
    "machine": 22,
    "slot_row": 2,
    "tiktok_handle": "@tooanh2604",
    "email": "tooanh26041996@gmail.com",
    "masked_email_on_app": "t***6@gmail.com"
  },
  "shop": {
    "name": "...",
    "type": "Shop"
  },
  "item": {
    "product_name": "...",
    "variation": "...",
    "quantity": 1,
    "price": 88000,
    "total": 88000,
    "currency": "VND"
  },
  "status": "Đã đặt hàng",
  "carrier": "Chờ chuyển phát",
  "tracking_code": null,
  "tracking_url": null,
  "cod_amount": 88000,
  "current_event": "...",
  "delivery_estimate": "Chậm nhất 26 tháng 10",
  "image_path": "D:/OneDrive/TaadaaData/kibe/orders/images/order_YYYYMMDD_XXX.jpg",
  "local_image_path": "D:/Taadaa/orders/images/order_YYYYMMDD_XXX.jpg",
  "images": [
    {"role": "order_confirmation", "path": "D:/Taadaa/orders/images/order_YYYYMMDD_XXX.jpg"},
    {"role": "desktop_screenshot", "path": "D:/Taadaa/orders/images/order_YYYYMMDD_XXX_raw.jpg"}
  ],
  "note": "TikTok Shop đơn hàng thật trên máy 22 slot 2 (@tooanh2604)"
}
```

### 5. Multi-Store Synchronization
Synchronize atomically across all targets:
- `D:/Taadaa/data/orders.json`
- `D:/OneDrive/TaadaaData/kibe/orders/orders.json`
- `D:/Taadaa/orders/QuanLyDonHang_TikTokShop.xlsx`
- `D:/OneDrive/TaadaaData/kibe/QuanLyDonHang_TikTokShop.xlsx`

### 6. Eye-Read Verification Invariant
Before presenting evidence or returning `DONE` to the user:
- Navigate to the raw image endpoint `http://localhost:1905/orders/images/<filename>` in browser.
- Call `browser_vision` to confirm:
  * Order status badge is clearly legible.
  * Recipient, phone, address, and product details are uncropped and uncorrupted.
  * Image is not black or distorted.
- Report specific visual evidence findings in the response.
