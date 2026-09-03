# Bot text & new-product auto-show — recipe (2026-08-13)

Context: user gửi ảnh Telegram kênh "THÔNG BÁO HÀNG TỒN KHO", yêu cầu (1) sản phẩm API mới tự hiện trên site (không ẩn) và (2) sửa ngôn ngữ bot (Tiếng Việt chuẩn có dấu).

## A. Tự hiện sản phẩm mới (code fix)

File: `D:\Taadaa\site ban hang clone\SHOPCLONE7\cron\suppliers\`
- `xscr.php` — 2 chỗ (dòng ~210 child-category, ~383 cấu trúc cũ)
- `shopclone7.php` — 2 chỗ (~205, ~378)
- `shopmail.php` — 2 chỗ (~214, ~387)

Tìm (mỗi file 2 occurrences, dùng replace_all):
```php
$product_status = (isset($supplier['isAutoShow']) && $supplier['isAutoShow'] == 1) ? 1 : 0;
```
Thay bằng:
```php
$product_status = 1; // tự động hiển thị sản phẩm API mới (không ẩn)
```
Chỉ INSERT path bị đổi; UPDATE path giữ nguyên (không ghi đè status sản phẩm cũ).
Ảnh hưởng: chỉ sản phẩm MỚI. Sản phẩm đã ẩn (vd SP ID 77) vẫn ẩn → hiện hết bằng playbook SQL "Bật hết sản phẩm".

## B. Sửa text/ngôn ngữ bot Telegram

File: `D:\Taadaa\site ban hang clone\SHOPCLONE7\libs\stock_alert.php`
4 hàm gọi từ `cron/cron.php`. Chuỗi `sprintf` cần sửa (old → new):

stockAlertCheck (⚠️ CẢNH BÁO TỒN KHO THẤP):
- `"San pham: %s\nDa ban: %s\nTon kho: %s"` → `"Sản phẩm: %s\nĐã bán: %s\nTồn kho: %s"`
- header `"⚠️ <b>CANH BAO TON KHO THAP</b>"` → `"⚠️ <b>CẢNH BÁO TỒN KHO THẤP</b>"`

sourcePriceAlertCheck (🔔 ĐỔI GIÁ NGUỒN CLONEFBIG):
- `"SP ID: %s\nAPI ID: %s\nTen: %s\nGia nguon cu: %s\nGia nguon moi: %s\nGia ban hien tai: %s"` → `"SP ID: %s\nAPI ID: %s\nTên: %s\nGiá nguồn cũ: %s\nGiá nguồn mới: %s\nGiá bán hiện tại: %s"`
- header `"🔔 <b>DOI GIA NGUON CLONEFBIG</b>"` → `"🔔 <b>ĐỔI GIÁ NGUỒN CLONEFBIG</b>"`

newApiProductAlertCheck (🆕 SẢN PHẨM API MỚI):
- `"Supplier: %s (%s)\nSP ID: %s\nAPI ID: %s\nTen: %s\nGia nguon (cost): %s\nGia ban: %s\nTon kho: %s\nTrang thai: %s"` → `"Supplier: %s (%s)\nSP ID: %s\nAPI ID: %s\nTên: %s\nGiá nguồn (cost): %s\nGiá bán: %s\nTồn kho: %s\nTrạng thái: %s"`
- `$visible ? 'Hien thi' : 'An'` → `$visible ? 'Hiển thị' : 'Ẩn'`
- (header `"🆕 <b>SẢN PHẨM API MỚI</b>"` đã có dấu, giữ nguyên)

supplierBalanceAlertCheck (⚠️ SỐ DƯ API THẤP):
- `"Supplier: %s (%s)\nSo du hien tai: ~%s VND\nNguong: %s VND"` → `"Supplier: %s (%s)\nSố dư hiện tại: ~%s VND\nNgưỡng: %s VND"`
- header `"⚠️ <b>SO DU API THAP</b>"` → `"⚠️ <b>SỐ DƯ API THẤP</b>"`

## Verify
- `php -l` không có trên Windows local → skip; edits chỉ thay chuỗi.
- grep không còn chuỗi không dấu: `San pham|Da ban|Ton kho|Trang thai|Hien thi|'An'|Gia nguon|CANH BAO|SO DU|DOI GIA|Gia ban hien tai|So du hien tai|Nguong`.
- grep `product_status = 1` phải có 6 kết quả (3 file × 2).
- Lần cron tiếp theo (5 phút) sinh alert mới với `Trạng thái: Hiển thị` + text có dấu.
- CAVEAT: code deploy có thể lệch repo ở vài chuỗi (header stock-low thấy live CÓ dấu nhưng repo KHÔNG). So chuỗi thực tế user xem trước khi sửa; verify alert thật sau sửa.
