# Multi-Carrier (GHN, J&T, SPX, Ninja Van) Routing & Order Lifecycle Specification

## Overview

TikTok Shop Vietnam dispatches orders through multiple logistics carriers: **J&T Express, Giao Hàng Nhanh (GHN), SPX Express, and Ninja Van**. An order tracking system must not hardcode carrier logic to a single provider. This document details the in-app discovery rules, carrier-specific web/API endpoints, privacy verification parameters, and lifecycle handoff rules.

---

## 1. In-App Discovery & Carrier Recognition

When inspecting order cards or tracking details via WinRT OCR:

| Carrier | Text Keywords in OCR | Billcode Format / Prefix |
| :--- | :--- | :--- |
| **J&T Express** | `J&T Express`, `j&t`, `jnt`, `vận chuyển tiêu chuẩn` | 12-digit numeric: `\b(8[4-9]\d{10})\b` (often lacks label prefix) or `JNT...` |
| **Giao Hàng Nhanh (GHN)** | `Giao Hàng Nhanh`, `GHN`, `ghn express` | Alphanumeric 8-15 chars: `LGY...`, `G...`, or prefix `GHN...` |
| **SPX Express** | `Shopee Xpress`, `SPX Express`, `SPX` | Prefix: `SPXVN...` followed by 8-15 alphanumeric characters |
| **Ninja Van** | `Ninja Van`, `ninjavan` | Prefix: `NLVN...`, `NIVN...`, or 10-15 alphanumeric characters |
| **Viettel Post** | `Viettel Post`, `viettelpost` | Alphanumeric / numeric 10-14 digits |

---

## 2. Carrier Tracking API & Web Endpoints (Zero-ADB Mode)

Once a tracking code is extracted from the farm device, the device is immediately released (`Zero ADB / Zero Phone Access`). Subsequent tracking is handled entirely via carrier web endpoints:

### A. J&T Express
* **Direct Web URL:**
  `https://jtexpress.vn/vi/tracking?type=track&billcode={billcode}&cellphone={phone_last4}`
* **Verification Gate:** Requires recipient's last 4 phone digits (`cellphone`). Without this, the web server prompts an interactive modal and hides the tracking timeline.
* **HTML Scraping Pattern:** Locate `id="chck-{billcode}"` and extract timestamps `HH:MM:SS` paired with `YYYY-MM-DD`.

### B. Giao Hàng Nhanh (GHN)
* **Direct Web URL:**
  `https://donhang.ghn.vn/?order_code={order_code}`
* **Public Tracking API Endpoint:**
  `POST https://fe-online-gateway.ghn.vn/order-tracking/public-api/client/tracking/tracking-order-detail`
* **Headers:**
  ```http
  Content-Type: application/json
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
  Origin: https://donhang.ghn.vn
  Referer: https://donhang.ghn.vn/
  ```
* **Payload:**
  ```json
  {
    "order_code": "<GHN_BILLCODE>",
    "phone_verify": "<PHONE_LAST4_OR_FULL>"
  }
  ```
* **Response Parsing:**
  Read `data.tracking_logs` containing `{action_at, status_name, warehouse_name}`.

### C. SPX Express
* **Public Tracking API:**
  `GET https://spx.vn/api/v2/fleet_order/tracking/search?sls_tracking_number={code}`
* **Direct Web URL:**
  `https://spx.vn/track?{code}`

### D. Ninja Van
* **Public Tracking API:**
  `GET https://api.ninjavan.co/vn/dash/1.0/public/orders/id/{code}`

---

## 3. Unified Event Mapping & Milestone Classification

Regardless of carrier, all events normalize into standard operational milestones:

1. **`Đang trung chuyển` (In Transit / Inter-Hub):**
   * J&T: `Bưu cục【...】đang chuyển hàng đến【...】`
   * GHN: `Đang luân chuyển`, `Rời kho phân loại`
   * SPX: `Đơn hàng đang được vận chuyển đến kho...`
2. **`Đã đến bưu cục phát` (Destination Hub Arrival):**
   * Keywords: `Đến bưu cục`, `Nhập kho`, `Thanh Khê`, `Tam Thuận` (excluding `đang chuyển`).
   * Action: Alert user for golden window self-pickup (07:15 - 08:00 AM).
3. **`Đang giao hàng (Shipper đang đi phát)` (Out for Delivery):**
   * Keywords: `Shipper`, `nhân viên giao`, `đang đi phát`, `phát hàng`.
   * Action: Sound host alarm, push urgent Telegram notification with recipient phone and COD amount.
4. **`Đã giao hàng thành công (Đã ký nhận)` (Terminal Complete):**
   * Keywords: `Ký nhận`, `giao hàng thành công`, `người ký nhận`.
   * Action: Immediately set `archived: true` in JSON, mark `ĐÃ LƯU TRỮ` in Excel, and retire from all tracking loops permanently.
