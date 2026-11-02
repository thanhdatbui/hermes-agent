---
name: shopclone7-site-ops
description: "Operate the SHOPCLONE7 live shop (doravo.net / 'site ban hang clone'): product-supplier-category state changes over SSH, unhide products, safe scoped SQL with backup, atomic admin view-file deploys, SSH access pitfalls"
version: 1.0.0
author: Hermes Agent
tags: [shopclone7, cmsnt, doravo, vps, mariadb, product-ops]
---
# SHOPCLONE7 Live Site Operations

Trigger: user asks about products / suppliers / categories / pricing / visibility on "site ban hang clone", doravo.net, or the SHOPCLONE7 repo — e.g. "bật sản phẩm lên", "kiểm tra sản phẩm nối api X", "ẩn/hiện hết", "sửa giá".

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
