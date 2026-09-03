# Source-API probe & reprice-by-markup recipe (doravo / SHOPCLONE7)

Session-derived reference (2026-08-15): đối chiếu sp API trên doravo với nguồn clonefbig + bật lại sp ẩn và set giá theo markup %. Không chứa secret.

## Khi nào dùng
- User hỏi "sp X có còn bên nguồn không / nguồn đang bán mấy sp / menu thấy 6 sp mà".
- User yêu cầu bật sp ẩn lên + set giá theo % giá gốc (vd "+80%", "x2").

## 1. Probe catalog nguồn (clonefbig) — API shape
- Key: đọc `api_key` từ `suppliers` trên VPS (không in ra).
- Endpoint: `https://clonefbig.com/api/products.php?api_key=$KEY`
- **Response shape:** `{status, msg, categories: [ {id, parent_id, name, icon, products: [ {id, name, price, amount, description, flag, min, max} ] } ]}` — KHÔNG phải mảng `data` (parse sai trả `NoneType`).
- `amount` = stock nguồn. **`amount=0` = sp vẫn tồn tại trên nguồn nhưng hết hàng** — không phải bị xóa; chớ báo "không còn trên nguồn".
- **Menu dropdown nguồn ≠ tổng sp API.** Site clonefbig menu chỉ hiện 6 loại con (Facebook Clone ON 2FA / New No 2FA, Instagram 3 loại, Hotmail Trusted) nhưng API trả 19 sp. Luôn đếm qua API.
- Đối chiếu bằng `api_id`: `products.api_id` (doravo) == `products[].id` (nguồn). API id có thể trùng giữa các category nguồn — map qua tên + giá khi nghi ngờ.

## 2. Đọc trạng thái + giá hiện tại (doravo DB)
```sql
SELECT id, name, price, cost, status, category_id, api_id, api_stock, sold, create_gettime, update_gettime
FROM products WHERE supplier_id=1 ORDER BY status, id;
```
- `status=0` + nguồn `amount>0` → sp đang ẩn nhầm, đáng bật (vd 2026-08-15: id 56 api 16 stock 109.678; id 67 api 3591 stock 40.917).
- `status=0` + nguồn `amount=0` → để ẩn (bật lên = sp rỗng, khách mua lỗi).

## 3. Reprice theo markup % + unhide (scoped, backup trước)
- `price = ROUND(cost * (1 + pct/100), 0)`. VD +80%: `UPDATE products SET status=1, price=ROUND(cost*1.8,0) WHERE id IN (56,67) AND status=0;`
- **Kiểm tra connector trước:** `grep -n "update_price\|price" cron/suppliers/api31.php` — nếu supplier `update_price=OFF` thì giá set tay sống qua sync; nếu `ON` thì sync ghi đè theo `discount` (phải set `suppliers.discount` thay vì price tay).
- **category_id=0 pitfall:** sp bật `status=1` nhưng `category_id=0` KHÔNG hiện trong grid category (chỉ mở được qua link trực tiếp). Grid render qua `ajaxs/client/load_products.php?category_id=<id>` (GET) — verify bằng cách grep `feature-name` + `price` trong HTML trả về. `category_id` phải là child (`parent_id != 0`), không phải parent.
- Luôn backup trước write: dump TSV `id,name,price,cost,discount,status,hide_in_shop,category_id,api_id,api_stock,sold` vào `/var/www/shopclone7/backups/pre-<desc>/<TS>/` kèm MANIFEST.

## 4. Margin thật từ đơn hàng
```sql
SELECT po.product_id, po.amount, po.money, po.cost, po.create_gettime
FROM product_order po WHERE po.product_id IN (...) ORDER BY po.create_gettime;
```
- `po.money` = khách trả, `po.cost` = giá gốc lúc bán. Bằng nhau → bán hòa vốn (vd TikTok UK id 31: money=cost=1500 → 0% margin).
- `products.sold` chỉ là counter, không chứng minh margin.

## 5. Sai lầm đã gặp (2026-08-15)
- Parse API sai shape (`data` thay vì `categories`) → `NoneType has no len`.
- Nested quote ssh+python từ git-bash fail nhiều lần (`unexpected EOF`, `KeyError`, f-string mất quote) → **scp script local lên /tmp rồi chạy** mới sạch.
- Grid cat 6 hiện 2 sp vì có sẵn 1 sp manual (id 57) cùng category — verify từng slug trước khi kết luận "67 hiện lầm".
