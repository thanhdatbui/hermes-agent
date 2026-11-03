---
name: tiktok-add-2fa-batch-ops
description: "Use when running batch 2FA on TikTok farm. Chạy batch 2FA repo tiktok-add-bao-mat-f2a, preflight, rotate pass, verify sau chạy."
---
# TikTok Add 2FA Batch Ops (repo tiktok-add-bao-mat-f2a)

References:
- `references/falsy-pass-email-fallthrough-and-workbookerror-trap-20261104.md` — Bẫy falsy fall-through `acc.get("password")` khiến worker mở nhầm file Excel legacy, lệch `rowid` SQLite vs dòng Excel gây hàng loạt lỗi `WorkbookError`.
- `references/multi-node-sqlite-ssot-and-disaster-recovery-discipline-20261103.md` — Kiến trúc Full-Farm Replica SQLite SSOT giữa Kibe và Admin, nguyên tắc Disaster Recovery (DR), Row-Level Upsert chống ghi đè file, và kỷ luật timeout sàn 300s (Gate G15).
- `references/distributed-sqlite-ssot-reconcile-architecture-20261103.md` — Kiến trúc sổ cái phân tán SQLite SSOT giữa Kibe và Admin, nguyên lý failover độc lập, cơ chế Reconcile Pull O(1) qua SSH và kỷ luật giao tiếp trực diện.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.
- `scripts/flush_dpapi_journal_to_workbook.py` — Script tự động flush Secret Key 2FA từ DPAPI journal vào Cột E file Excel `taikhoan_dat_v2_updated .xlsx`, đối chiếu readback và cập nhật state WRITTEN.
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.