# J&T Tracking Mobile 422 Trap & Order SQLite SSOT Governance

## 1. J&T Express Web Tracking Mobile 422 Trap & Link Anchor Pattern

When tracking J&T Express orders via `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}`:

- **The Mobile 422 Trap:**
  - J&T server renders the complete shipping timeline directly into the HTML response under `<input type="checkbox" id="chck-{billcode}">` when `cellphone` is passed.
  - However, on mobile viewports, the browser viewport lands at the top search form.
  - If the user or agent clicks the red "Tra cứu vận đơn" button again, J&T's client JavaScript fires a redundant AJAX POST to `/api/web/v1/tracking` without the necessary session CSRF token, throwing a red error banner: **"Tra cứu thất bại (422)"**.
- **Canonical Solution:**
  - Append the HTML element anchor `#chck-{billcode}` to the URL:
    `https://jtexpress.vn/vi/tracking?type=track&billcode={code}&cellphone={phone_last4}#chck-{code}`
  - Instruct the user to **scroll down** instead of tapping "Tra cứu vận đơn".
  - Deliver clean raw URLs in Telegram chats rather than complex markdown links that might break rendering.

---

## 2. Orders SQLite SSOT Migration & Anti-Copy-Paste Governance

### The Failure Mode of Per-Order Scripts (`save_order_*.py`)
- Creating standalone scripts (`save_order_20261029_004.py`, `save_order_20261029_008.py`) by duplicating older scripts causes severe copy-paste errors (e.g. copying recipient "Mai Mai" from `DH-20261028-003` into `DH-20261029-004` which actually belonged to "Thanh Hà Dương").
- Downstream watchdogs reading `orders.json` or Excel will spam Telegram with false customer names across all milestones until delivery.

### SQLite Master Ledger Integration (`farm_master.db`)
Orders are centrally governed in SQLite SSOT (`D:/Taadaa/data/farm_master.db` table `orders`):
- **Schema:**
  `order_id`, `order_date`, `customer_name`, `customer_phone`, `masked_phone`, `shipping_address`, `machine_id`, `slot_row`, `device_serial`, `tiktok_handle`, `tiktok_email`, `shop_name`, `product_name`, `product_variation`, `quantity`, `price`, `total_amount`, `cod_amount`, `status`, `carrier`, `tracking_code`, `tracking_url`, `tiktok_order_code`, `current_event`, `delivery_estimate`, `image_path`, `note`, `archived`, `archived_at`, `raw_json`, `updated_at`.
- **DAL Functions (`farm_db.py`):**
  - `get_all_orders(include_archived=True)`
  - `get_order(order_id)`
  - `upsert_order(order_dict)`: updates SQLite and auto-syncs `orders.json` for backward compatibility.

### Standardized CLI Entrypoint (`manage_orders.py`)
Never create one-off `save_order_*.py` scripts. Use `D:/Taadaa/tools/manage_orders.py`:
```bash
python D:/Taadaa/tools/manage_orders.py --add \
  --machine 14 --slot 1 \
  --name "Tên Khách" --phone "0905..." --address "..." \
  --product "Tên sản phẩm" --cod 50000
```
- **Auto-Resolution:** Passing `--machine` and `--slot` automatically pulls `device_serial`, `tiktok_handle`, and `email` directly from `farm_db`, preventing identity mismatches.
- **Excel as Read-Only Export:** `QuanLyDonHang_TikTokShop.xlsx` is purely generated via `--export-excel` as a view artifact; Excel is never treated as the mutable database source of truth.
