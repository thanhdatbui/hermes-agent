# Admin view-file atomic deploy — session record 2026-08-11

Task: add "Tất cả sản phẩm API" filter to admin products page and deploy live.
File duy nhất: `SHOPCLONE7/views/admin/products.php` (working tree byte-identical với HEAD trước khi sửa; `M` trong git status chỉ là EOL artifact LF/CRLF — chứng minh bằng sha256, không phải content diff).

## Hashes & paths

- Live release (symlink `current`): `/var/www/shopclone7/releases/20260702-163927`
- File live cũ / HEAD: sha256 `e2f5490be7e0e3be7f2e3fcf47bf2cc0a34519348399d5431d66fac7478f65a4`, 53979 bytes, owner/mode `deploy:www-data 644`, thuần LF
- File mới đã deploy: sha256 `7ef1981dcb6e73277c82a1483c63048b4402ee7d4d12048d4df97f4eee2477f7`, 54280 bytes (+6 dòng)
- Backup: `/var/www/shopclone7/backups/pre-admin-api-all-filter/20260811T112014Z/` (products.php + MANIFEST.txt)

## Code thay đổi

Filter block (đầu view, dòng ~60):
```php
if(!empty($_GET['supplier_id'])){
    $supplier_id = check_string($_GET['supplier_id']);
    if($supplier_id == 'api'){
        $where .= ' AND `supplier_id` > 0 ';
    }else{
        $supplier_id_value = $supplier_id == 'none' ? 0 : $supplier_id;
        $where .= ' AND `supplier_id` = "'.$supplier_id_value.'" ';
    }
}
```

Dropdown option (đặt TRƯỚC option `none`, sau placeholder):
```php
<option value="api" <?=$supplier_id == 'api' ? 'selected' : '';?>>
    <?=__('Tất cả sản phẩm API');?></option>
```

## MANIFEST.txt format (đã dùng)

```
BACKUP_MANIFEST
timestamp_utc: 20260811T112014Z
source_path: /var/www/shopclone7/releases/20260702-163927/views/admin/products.php
source_symlink: /var/www/shopclone7/current/views/admin/products.php
sha256: e2f5490b...
owner: deploy
group: www-data
mode: 644
size_bytes: 53979
```

## Trình tự deploy đã chạy (đúng chuẩn)

1. `scp -i ~/.ssh/doravo_deploy <file> root@152.42.187.200:/var/www/shopclone7/current/views/admin/products.php.new` (temp CÙNG thư mục → mv atomic cùng filesystem)
2. Remote: `sha256sum temp` khớp local → `php7.4 -l temp` ("No syntax errors detected")
3. `chown deploy:www-data temp && chmod 644 temp` → `mv -f temp products.php`
4. `php7.4 -l` final sạch; `sha256sum` final == local; grep marker: `supplier_id == 'api'` ×2, label dòng 189, `supplier_id\` > 0` dòng 63
5. Không reload PHP-FPM (view file, không opcache issue)

## Verification results

- HTTP: homepage 200 (`https://doravo.net/`); admin URL `/?module=admin&action=products&supplier_id=api&limit=100` → hop đầu 302, follow → `/client/login` 200 (không 500). **curl trên git-bash Windows trả exit 23 "client returned ERROR on write" với `-o /dev/null` — benign, http_code vẫn đúng.**
- DB read-only: `GROUP BY supplier_id` → 0:6, 1:19, 2:23, 4:11; `supplier_id>0` total = 53; manual = 6.
- Mock probe php7.4 (heredoc /tmp, logic y hệt block): 5 case PASS — `api→' AND \`supplier_id\` > 0 '`, `none→= "0"`, `1→= "1"`, `4→= "4"`, `''→''`.
- Local ad-hoc script (tempfile `hermes-verify-*` prefix, chạy xong xoá): 16/16 PASS (counts, order api<none<foreach, EOL LF-only, braces/parens).
- Git: không stage/commit; HEAD giữ `bbc24ce`; báo "commit not made" vì repo dirty nhiều file khác.

## URL sản phẩm

`https://doravo.net/?module=admin&action=products&supplier_id=api&limit=100` — filter "Tất cả sản phẩm API" (53 sản phẩm = id1 API_31 clonefbig.com 19, id2 SHOPCLONE7 taikhoan295.com 23, id4 XSCR xscr.us 11).
