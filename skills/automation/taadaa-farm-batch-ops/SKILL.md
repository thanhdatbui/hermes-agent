---
name: taadaa-farm-batch-ops
description: "Re-run / resume farm batch jobs (TikTok upload, Tik3 render, reg, nuoi acc) using canonical commands."
version: 1.0.0
author: Hermes Agent
tags: [tiktok, farm, batch, render, upload, resume, kibe]
---
# Taadaa Farm Batch Operations

## 1. Nguyên Tắc Cốt Lõi
- **Tái sử dụng công cụ chuẩn:** Tuyệt đối không tự viết lệnh ad-hoc khi đã có script pipeline chính thống.
- **Tiến trình ngầm không mở Console:** Mọi lệnh batch kích hoạt qua cronjob hoặc background bắt buộc phải bọc ẩn cửa sổ theo `guard_cronjob_safety.py`.
- **Thẩm định chạy bù (Catch-Up / Compensatory Run):** Bắt buộc đối soát chu kỳ 4 ngày (Parity 96h) từ base 11/10/2026. CẤM chạy bù đè vào Dead Zone (21:30 - 05:59) hoặc Ca 1 sáng (06:00). Khi máy văng do hạ tầng (USB/Proxy), cấm rerun toàn bộ 80 máy; chỉ chạy selective máy failed khi hạ tầng đã phục hồi và trong khung giờ an toàn. Chi tiết xem [`references/compensatory-feed-run-safety-and-cadence-parity.md`](references/compensatory-feed-run-safety-and-cadence-parity.md).
- **Kiến trúc Xác minh Upload Video (In-Session vs Post-Session Audit):** In-session dùng in-app playback surface / markers; cấm dùng cào web public realtime do cache lag & SlardarWAF. Cào Dashboard chỉ dùng đối soát sau ca 1-2h qua công cụ chuẩn `python D:/Taadaa/tools/audit_upload_dashboard_reconcile.py --date <YYYY-MM-DD> --row <N>`. Chi tiết xem [`references/tiktok-upload-verification-vs-public-dashboard-audit.md`](references/tiktok-upload-verification-vs-public-dashboard-audit.md).
- **Đối soát Lệch Nhịp Snapshot Cadence:** Khi nghi vấn Dashboard hiển thị thiếu video so với upload ledger, bắt buộc đối soát mốc thời gian cào snapshot (`10:00` sáng) vs giờ upload của ca (18:00 tối). CẤM vội kết luận lỗi upload khi snapshot Dashboard chưa đến lượt cập nhật. Chi tiết xem [`references/upload-reconcile-dashboard-cadence-and-ground-truth-20261029.md`](references/upload-reconcile-dashboard-cadence-and-ground-truth-20261029.md).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
