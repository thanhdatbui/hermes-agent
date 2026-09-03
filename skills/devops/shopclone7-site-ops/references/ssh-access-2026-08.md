# SSH access state — 2026-08-11

## Session context

User (Telegram "Site ban hang clone"): "Kiểm tra các sản phẩm nằm trong site có nối api đến fbclone, thì bật hết lên k ẩn nữa" — unhide all products linked to the fbclone supplier on doravo.net.

## What was found

- Repo `D:\Taadaa\site ban hang clone` (branch main, HANDOFF.md ~367 dòng) — grep "fbclone" toàn repo: **0 hits**. Supplier fbclone chỉ tồn tại ở DB live → không thể làm gì nếu không vào được VPS.
- Site sống: `curl -L https://doravo.net/` → HTTP 200, `<title>Doravo.net</title>`. Ping 152.42.187.200 OK (~56ms).
- `ls -la ~/.ssh/` → chỉ còn:
  - `doravo_deploy` + `doravo_deploy.pub` (ed25519, tạo Thg7 17 08:21)
  - `known_hosts` (có 152.42.187.200 ssh-ed25519 + host cũ 45.76.187.121)
  - Không có `config`, không có `do_web01_vps` (docs HANDOFF/DEPLOY_STAGING_REPORT vẫn ghi key này).

## Diagnostic transcript (tóm tắt)

```text
ssh -i ~/.ssh/doravo_deploy root@152.42.187.200        → Permission denied (publickey,password)
ssh -o BatchMode=yes -i ~/.ssh/doravo_deploy ...       → Permission denied (publickey,password)
ssh -v ...                                             → offering key, server: "Authentications that can continue: publickey,password"
                                                        → read_passphrase: can't open /dev/tty (server hỏi password, KHÔNG phải passphrase key)
grep -c bcrypt ~/.ssh/doravo_deploy                    → 0  (key KHÔNG mã hoá → vấn đề là authorization)
thử root / ubuntu / deploy / admin                     → tất cả Permission denied
known_hosts host key khớp, không HOST_KEY_CHANGED      → VPS còn nguyên, thiếu authorized key
```

## Verdict

`doravo_deploy.pub` chưa được thêm vào `/root/.ssh/authorized_keys` trên VPS. Blocker → user phải tự chạy (có password):

```bash
cat ~/.ssh/doravo_deploy.pub | ssh root@152.42.187.200 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Hoặc user tự bật qua Admin > Sản phẩm > lọc supplier > Cập nhật nhanh > Hiển thị (ON) — precedent session 2026-07-02 clonefbig: 13/13 products status=1, không đụng giá.

## Follow-up khi có SSH (chưa làm)

1. `SELECT id,name,status FROM product_api WHERE name LIKE '%fbclone%';`
2. `SELECT id,name,status,category_id FROM products WHERE supplier_id=<id> AND status=0;` + category check (`status=1`, `parent_id != 0`).
3. Backup rows → `UPDATE products SET status=1 WHERE supplier_id=<id>;`
4. Verify DB + curl frontend category page.

## Lesson ghi lại

Docs ghi key cũ nhưng key trên đĩa đã đổi (doravo_deploy tạo sau docs 2026-07-17) — lần sau SSH tới VPS này: check `ls ~/.ssh/` TRƯỚC, đừng tin tên key trong HANDOFF. Nếu tạo key mới → nhớ user phải add pubkey vào VPS authorized_keys, agent không tự làm được.
