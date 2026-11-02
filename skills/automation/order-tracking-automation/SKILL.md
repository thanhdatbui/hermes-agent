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
> - `references/order-phase1-idle-windows-and-lock-reentrancy.md`: Khóa cứng 4 khung giờ máy rảnh chuẩn (04:30, 10:30, 16:30, 22:30) triệt tiêu bẫy trôi lệch giờ do dynamic cooldown, khắc phục lỗi deadlock tự khóa re-entrancy khi gọi ADB/screencap dưới device lock, và 3 checkpoint điều hướng TikTok Feed -> Profile -> Order List.
> - `references/order-archived-state-blindness-and-sqlite-ssot-enforcement.md`: Khắc phục lỗi desync "cứ lòi ra Excel", bẫy mù trạng thái archived khiến đơn đã giao xong bị lặp lại trong Phase 1 (bắt buộc kiểm tra order.get('archived') trước khi xét status), cưỡng chế SQLite SSOT (`farm_master.db` table `orders` qua `farm_db.upsert_order`), khôi phục metadata ô `None` qua `manage_orders.py --sync-excel`, và kỷ luật Coordinator Terminal Guard (chặn tuyệt đối ghi đè qua `python -c`).
> - `references/phase1-switcher-canonical-reuse-and-body-pattern-gate.md`: Khắc phục lỗi tự chế Account Switcher trong Phase 1 (bịt lỗ hổng gate body_patterns, cấm so khớp chuỗi thô sơ, bắt buộc import canonical matches_switcher_identity từ automation-core).
> - `references/jt-mobile-422-trap-and-orders-sqlite-ssot.md`: Bẫy link mobile J&T lỗi 422 khi bấm lại tra cứu trên form pre-rendered, gắn anchor `#chck-{billcode}`, và kiến trúc chuyển đổi toàn diện đơn hàng sang SQLite SSOT (`farm_master.db` table `orders`) qua `manage_orders.py` chấm dứt bẫy copy-paste nhầm tên khách hàng.
> - `references/tiktok-shop-feed-landing-trap-and-navigation-recovery.md`: Xử lý bẫy mở app TikTok rơi vào Feed video/Live khiến OCR lệch font (Hö sd, Cdfa hång), timeout 38s chụp nhầm màn hình feed dẫn đến NO_TRACKING_ON_SCREEN giả tạo, giải pháp fallback tọa độ cứng góc dưới phải (y > 0.97) và header shortcut tab Shop.
> - `references/parallel-workers-milestone-alerts-and-bundle-product-traps.md`: Cấm cuốn chiếu mà bắt buộc chạy song song ThreadPoolExecutor (max 15 workers) kèm file lock, 3 mốc cảnh báo Telegram bắt buộc (mã mới, về Đà Nẵng, shipper đi phát), khử bẫy silent init, bẫy quà tặng kèm ("Thư cảm ơn"), modal popup dismiss và bộ lọc xóa khoảng trắng OCR kerning.
> - `references/jt-express-link-traps-and-ingestion-integrity.md`: Bẫy link tra cứu web J&T (văng lỗi đỏ 422 khi bấm nút thừa trên mobile, giải pháp thêm neo #chck-{code}), định dạng raw URL Telegram chống gãy link và kỷ luật đối soát customer.name chống copy-paste nhầm tên từ template cũ.
> - `references/jt-express-carrier-tracking-and-pickup-watchdog.md`: Tra cứu J&T Express web, anchor #chck-{code} chống bẫy 422 trên mobile, raw URL Telegram không bọc markdown dày, và quy chuẩn giải thích SĐT shipper bị che (+847****3464).
> - `references/parallel-workers-and-atx-jsonrpc-fallback.md`: Kiến trúc đa luồng song song Phase 1 (ThreadPoolExecutor max 15 workers kèm threading.Lock), cấm shell uiautomator dump mà dùng ATX-Agent JSON-RPC port 7912 làm fallback, phân tách Two-Phase Cadence (Phase 2 realtime 30m vs Phase 1 S7 cooldown 6h), bẫy silent init và bộ lọc OCR kerning.
> - `references/order-lifecycle-parallel-sync-cadence-and-in-app-traps.md`: Kiến trúc Two-Speed Cadence (Phase 2 realtime 30m Zero-ADB vs Phase 1 S7 cooldown 6h), cấm tuần tự cuốn chiếu mà bắt buộc chạy song song ThreadPoolExecutor (max 15 workers) kèm file lock, bẫy silent watchdog no_agent thiếu print alert, và bộ 5 bẫy điều hướng app/OCR (k

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
