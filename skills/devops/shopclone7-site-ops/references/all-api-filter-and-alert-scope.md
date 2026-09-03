# All-API filter and alert scope

## Meaning of “all sản phẩm qua API”

For Doravo/SHOPCLONE7, “all API products” means every product row with `products.supplier_id > 0` (normally also a non-empty `api_id`), not only the supplier mentioned in the previous message.

Always enumerate live suppliers first:

```sql
SELECT id, type, domain, status FROM suppliers ORDER BY id;
SELECT supplier_id, COUNT(*) AS total, SUM(status=1) AS active,
       SUM(status=0) AS hidden
FROM products
GROUP BY supplier_id
ORDER BY supplier_id;
```

Report the total and breakdown by supplier/domain. Keep `supplier_id=0` separate as manually uploaded inventory.

## Admin filter implementation

The legacy admin products page may support only:

- `supplier_id=none` → `supplier_id=0` (manual products)
- numeric `supplier_id` → one supplier only

For a reusable all-API link, add a minimal branch in the page's existing filter:

```php
if ($supplier_id === 'api') {
    $where .= ' AND `supplier_id` > 0 ';
} else {
    $supplier_id_value = $supplier_id === 'none' ? 0 : $supplier_id;
    $where .= ' AND `supplier_id` = "'.$supplier_id_value.'" ';
}
```

Add a dropdown option with `value="api"`, preserve the existing `none` and numeric supplier options, and make no database mutation. Verify the live page implementation before sending the link.

Canonical authenticated URL after this filter exists:

```text
https://doravo.net/?module=admin&action=products&supplier_id=api&limit=100
```

Unauthenticated HTTP 200 followed by a redirect to `/client/login` is expected; it is not proof that the filter rendered. Verify the code marker and live DB counts separately. The URL requires admin login.

## Source-price alert scope

A watcher keyed as `source_price_alert_state_clonefbig` and querying `supplier_id=1` covers only `clonefbig.com`/API_31. It does not cover `taikhoan295.com`, `xscr.us`, or any supplier referred to by an informal label such as `fbclonefb` unless the live `suppliers` identity proves they are the same record.

Before claiming the bot reports price changes:

- verify the function marker and cron hook on the live release;
- verify the dedicated state row is valid JSON and its product count matches the watcher scope;
- distinguish baseline creation from an observed Telegram delivery;
- if no real source transition occurred, report installation/baseline only.
