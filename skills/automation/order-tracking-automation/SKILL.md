---
name: order-tracking-automation
description: "Use for orders, mail codes, carrier scans, or dashboards."
version: 1.0.0
license: Proprietary
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [orders, tiktok-shop, outlook, hotmail, tracking, carrier-api, dashboard, cron]
    related_skills: [hotmail-outlook-automation, evidence-first-delivery, taadaa-farm-ops-rules]
---
# Order Tracking Automation

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
> - `references/parallel-workers-milestone-alerts-and-bundle-product-traps.md`: Cấm cuốn chiếu mà bắt buộc chạy song song ThreadPoolExecutor (max 15 workers) kèm file lock, 3 mốc cảnh báo Telegram bắt buộc (mã mới, về Đà Nẵng, shipper đi phát), khử bẫy silent init, bẫy quà tặng kèm ("Thư cảm ơn"), modal popup dismiss và bộ lọc xóa khoảng trắng OCR kerning.
> - `references/jt-express-link-traps-and-ingestion-integrity.md`: Bẫy link tra cứu web J&T (văng lỗi đỏ 422 khi bấm nút thừa trên mobile, giải pháp thêm neo #chck-{code}), định dạng raw URL Telegram chống gãy link và kỷ luật đối soát customer.name chống copy-paste nhầm tên từ template cũ.
> - `references/jt-express-carrier-tracking-and-pickup-watchdog.md`: Tra cứu J&T Express web, anchor #chck-{code} chống bẫy 422 trên mobile, raw URL Telegram không bọc markdown dày, và quy chuẩn giải thích SĐT shipper bị che (+847****3464).
> - `references/parallel-workers-and-atx-jsonrpc-fallback.md`: Kiến trúc đa luồng song song Phase 1 (ThreadPoolExecutor max 15 workers kèm threading.Lock), cấm shell uiautomator dump mà dùng ATX-Agent JSON-RPC port 7912 làm fallback, phân tách Two-Phase Cadence (Phase 2 realtime 30m vs Phase 1 S7 cooldown 6h), bẫy silent init và bộ lọc OCR kerning.
> - `references/order-lifecycle-parallel-sync-cadence-and-in-app-traps.md`: Kiến trúc Two-Speed Cadence (Phase 2 realtime 30m Zero-ADB vs Phase 1 S7 cooldown 6h), cấm tuần tự cuốn chiếu mà bắt buộc chạy song song ThreadPoolExecutor (max 15 workers) kèm file lock, bẫy silent watchdog no_agent thiếu print alert, và bộ 5 bẫy điều hướng app/OCR (kerning space, 0/o, switcher dismissal, feed vs profile y-bounds, atx-agent fallback).
