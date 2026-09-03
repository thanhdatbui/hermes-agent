# API_31 (clonefbig) — pricing, visibility, and order verification

Session-derived reference for the SHOPCLONE7 live-site operator skill. Do not put API keys, DB passwords, cron keys, or account contents in this file.

## Supplier identity and schema

- Live supplier state is in MariaDB table `suppliers`, not `product_api`.
- Identify the source using the tuple `id + type + domain + status`; this installation uses `id=1`, `type=API_31`, `domain=https://clonefbig.com`, `status=1`.
- `suppliers` has no `name` column. Avoid admin pages that render the saved API key.
- Product API linkage is `products.supplier_id > 0` plus `products.api_id`; manually uploaded products have `supplier_id=0` and normally `api_id=NULL`.

## API_31 price semantics (verified against `cron/suppliers/api31.php`)

For source price `api_price`:

```text
markup = api_price * suppliers.discount / 100
if update_price == ON:
    products.price = api_price + markup  # roundMoney may round it
if update_price == OFF:
    existing products.price is preserved
products.cost = api_price
```

- API_31's connector does **not** multiply by `suppliers.rate`; `rate` is stored but not used by this connector.
- `suppliers.discount` is supplier-level markup, not a per-product override.
- `products.discount` is a separate storefront sale discount and is applied at display/checkout; do not confuse it with supplier markup.
- With `update_price=ON`, the next supplier sync overwrites existing per-product `products.price` using the formula above. With `OFF`, a manually set `products.price` survives normal API_31 syncs.
- The current code has no per-product `price_override` flag. “Set a separate price and keep auto-sync ON” requires a code change; do not promise that behavior from the existing admin/API connection settings.

## Verify source-vs-shop price without exposing secrets

Run the probe on the VPS, not from a local machine that may be filtered:

1. Read DB credentials only server-side and set `MYSQL_PWD`; never print them.
2. Query safe product fields: `id,api_id,name,price,cost,api_stock,api_time_update`.
3. Read the supplier API key into a shell variable only; call the source endpoint (for API_31, `/api/products.php?api_key=...`) with curl; parse the JSON and print only the matching product's `id,name,price,amount`.
   - **Response shape (verified 2026-08-15):** `{"status":"success","categories":[{"id","parent_id","name","products":[{"id","name","price","amount","description","flag","min","max"}]}]}` — KHÔNG phải mảng `data` phẳng. Phải lặp `categories[].products[]`; `amount` = stock nguồn (0 = hết hàng, sp vẫn còn trên nguồn), `price` = giá nguồn (= `products.cost`). Đếm/so khớp sai nếu đọc nhầm `data`.
4. Compare `source price == products.cost`; compare `products.price/source price` for the effective multiplier.
5. Report the source timestamp/stock as a live snapshot; do not treat an older screenshot as current price or stock.

## Visibility and category mapping

- A product can have `status=1`, `hide_in_shop=0`, and `pending=0` yet still be absent from the category grid when `category_id=0`.
- Products belong in a **child category**, not directly in the platform parent category. The grid query filters by the selected category ID.
- Verify the target child has `categories.status=1` and a valid parent. If no exact child exists (for example a No-2FA Instagram product), do not silently place it in a misleading 2FA category; propose/create a matching child as a separate scoped change.
- Category/homepage HTML may be only a shell. Verify the actual grid through `ajaxs/client/load_products.php` or by a direct product slug; search results can show products that category pages do not.

## Determine what customers bought

To distinguish API inventory from manually uploaded inventory, join orders to products:

```sql
SELECT po.id, po.create_gettime, po.product_id, po.amount,
       p.supplier_id, p.api_id, p.name
FROM product_order po
JOIN products p ON p.id = po.product_id
WHERE po.create_gettime >= '<cutoff>'
ORDER BY po.create_gettime, po.id;
```

- `p.supplier_id=0` → manually uploaded stock.
- `p.supplier_id>0` and `p.api_id` present → supplier/API product.
- To answer “did they buy the newly enabled products?”, compare `product_id` against the exact newly enabled ID set and use the actual DB timestamp of the enable backup/operation. Do not infer from product names or from the latest order alone.

## Worker/live-write verification

A worker's “completed” report is not proof. After any live flag or price operation, independently SSH and verify:

- supplier identity and final flag;
- target product price/cost/status;
- backup path exists and has the expected row count;
- unrelated suppliers/rows are unchanged.

If a concurrent supplier cron changes `api_stock` or `api_time_update` while verifying, report it as concurrent sync drift rather than attributing it to the requested SQL update.
