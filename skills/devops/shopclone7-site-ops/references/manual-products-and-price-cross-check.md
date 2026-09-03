# Manual products ("up tay"), price age, and external price-list cross-check

Session-derived reference (2026-08-15): user brought a China reseller's Telegram price list (越南哥供货群) and asked whether doravo prices match, and whether a 0.17$ TikTok product price was new or old, plus its cost.

## Distinguish API vs manual products (products table)

- API product: `supplier_id > 0` AND `api_id` non-NULL. `cost` = source price (e.g. taikhoan295 TikTok rows: cost = price = 1700/3500).
- Manual upload ("up tay"): `supplier_id = 0` AND `api_id IS NULL`, typically `cost = 0`. Price is operator-set at creation; there is NO cost basis in DB — "giá gốc" must come from the purchase source, not the DB.
- Quick probe:

```sql
SELECT id, name, price, cost, supplier_id, api_id, status, create_gettime, update_gettime FROM products WHERE ...;
```

## "Is this price new or old?" heuristic

- `products.create_gettime` and `products.update_gettime` are DATETIME columns.
- If `update_gettime = create_gettime`, price has never been edited since creation — the displayed price is as old as the product row.
- This install: id 38 (TikTok US Like New 4600đ) and id 40 (TikTok Random Live 4600đ) created 07-07 / 09-07-2026 with update == create → 0.17$ price was set at upload time, NOT recent.
- Supplier sync cron may touch `update_gettime` on API rows; manual rows are never rewritten by cron.

## Currency display rates (currencies table)

- Table `currencies`: id 3 = VND rate=1 (default_currency=1), id 4 = USD rate=26500 (display=1).
- So 1 USD = 26,500 VND on the shop; 0.17$ ≈ 4,505đ (shop display rounds to 4,600đ).
- `settings` gateway rates (crypto_rate 25000, paypal_rate 23000, perfectmoney_rate 23000, ...) are PAYMENT-GATEWAY rates, NOT shop display currency — never use them for product price conversion.

## Cross-checking an external price list against doravo

Pattern used when user brings a price list (Telegram/other shop) and asks "giá web tao có khớp không":

1. Dump full catalog once: `SELECT id, supplier_id, status, api_id, LEFT(name,70), price, cost FROM products ORDER BY id` — one query covers everything; no need to guess product names.
2. Map by product CLASS, not by name string. Similar names can be different classes:
   - "FB real no 2FA 2$" (real accounts) vs "FB Clone No 2FA 2400đ" (clones) — NOT comparable.
   - "Twitter 2025 search top 0.8$" matches both "X search top 2025" (23850đ) and "X 2025 Search TOP LA" (20800đ) — same class, two SKUs; report both.
3. Report: match found / not found; price difference as %; flag class mismatches explicitly instead of treating them as price errors.
4. Never conclude "missing" from repo grep — the catalog lives in MariaDB on the VPS (see main SKILL).

## DB credential access (verified working pattern)

- Do NOT `set -a; . /root/.shopclone7_db_credentials` then `mysql` with `$DB_PASSWORD` — fails with `ERROR 1045 (28000): Access denied ... using password: NO` (file not safely shell-sourceable).
- Working pattern (also in main SKILL):

```sh
export MYSQL_PWD="$(awk -F= '/^DB_PASSWORD=/{print $2}' /root/.shopclone7_db_credentials)"
DB_HOST="$(awk -F= '/^DB_HOST=/{print $2}' /root/.shopclone7_db_credentials)"
DB_USER="$(awk -F= '/^DB_USER=/{print $2}' /root/.shopclone7_db_credentials)"
DB_NAME="$(awk -F= '/^DB_NAME=/{print $2}' /root/.shopclone7_db_credentials)"
mysql -h"$DB_HOST" -u"$DB_USER" "$DB_NAME" -e "..."
```

## Current manual product inventory (as of 2026-08-19)

Query:
```sql
SELECT p.id, p.code, p.name, p.price, p.status, 
       (SELECT COUNT(*) FROM product_stock ps WHERE ps.product_code = p.code) AS stock_count,
       p.sold
FROM products p
WHERE p.supplier_id = 0 OR p.supplier_id IS NULL OR p.api_id IS NULL OR p.api_id = ''
ORDER BY p.id ASC;
```

Full 6 manual products on shop:
- **ID 38:** `Tài Khoản TikTok US Like New` (cat 12: TikTok US), Price: 4.600đ ($0.17), Stock: 0, Sold: 490.
- **ID 39:** `Instagram New Reg - Has Avatar & Post` (cat 14), Price: 8.000đ ($0.30), Stock: 0, Sold: 1640.
- **ID 40:** `TikTok Random Live` (cat 15), Price: 4.600đ ($0.17), Stock: 487, Sold: 13.
- **ID 57:** `Instagram · Random Username · Phone Registered · Live · Verified Phone or Email · 2FA On · Aged 1–30 Days · 2FA On` (cat 6), Price: 3.710đ ($0.14), Stock: 1.441, Sold: 13413.
- **ID 60:** `X search top chất lượng cao 2025` (cat 20: X - Search TOP), Price: 23.850đ ($0.90), Stock: 0, Sold: 0.
- **ID 61:** `Gmail Log ALL có Mail khôi phục` (cat 22), Price: 11.925đ ($0.45), Stock: 0, Sold: 506.

Note on out-of-stock products: `product_hide_outstock=1` is active, so out-of-stock manual products (ID 38, 39, 60, 61) are automatically hidden from frontend category grids until stock is added.

