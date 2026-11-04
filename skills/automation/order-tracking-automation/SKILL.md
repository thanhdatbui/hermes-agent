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
> - `references/zero-code-order-ingestion-via-json-patch-and-manage-orders.md`: Quy trình nạp nhanh đơn hàng từ màn hình farm (Qiudao/TotalControl) không đụng file .py (chống dính COORDINATOR GUARD code edit/terminal write), chuẩn tọa độ crop (548, 162, 828, 667), đối soát WinRT OCR, patch JSON và xuất Excel tự động qua manage_orders.py.
> - `references/phase2-web-tracking-parallel-executor-and-zero-sequential.md`: Xóa bỏ hoàn toàn tàn dư tuần tự trong Phase 2 (chuyển sang ThreadPoolExecutor song song 100% cho Web API bưu cục), cô lập lỗi per-order và bảo vệ an toàn ghi đồng thời vào SQLite SSOT.
> - `references/farm-waybill-ocr-triage-and-ingestion-gaps.md`: Triage đối soát tem vận đơn thực tế (OCR waybill) khi gói hàng vật lý đã về nhưng không có tên/mã trong SQLite SSOT (`farm_master.db`), bẫy ngắt dòng `Ri\nn gci` (Rin gọi [SĐT]) và đối sách trả lời phân định rạch ròi giữa "chưa nạp vào DB" vs "DB lưu ngu".
> - `references/order-phase1-idle-windows-and-lock-reentrancy.md`: Khóa cứng 4 khung giờ máy rảnh chuẩn (04:30, 10:30, 16:30, 22:30) triệt tiêu bẫy trôi lệch giờ do dynamic cooldown, khắc phục lỗi deadlock tự khóa re-entrancy khi gọi ADB/screencap dưới device lock, và 3 checkpoint điều hướng TikTok Feed -> Profile -> Order List.
> - `references/order-archived-state-blindness-and-sqlite-ssot-enforcement.md`: Khắc phục lỗi desync "cứ lòi ra Excel", bẫy mù trạng thái archived khiến đơn đã giao xong bị lặp lại trong Phase 1 (bắt buộc kiểm tra order.get('archived') trước khi xét status), cưỡng chế SQLite SSOT (`farm_master.db` table `orders` qua `farm_db.upsert_order`), khôi phục metadata ô `None` qua `manage_orders.py --sync-excel`, và kỷ luật Coordinator Terminal Guard (chặn tuyệt đối ghi đè qua `python -c`).
> - `references/phase1-switcher-canonical-reuse-and-body-pattern-gate.md`: Khắc phục lỗi tự chế Account Switcher trong Phase 1 (bịt lỗ hổng gate body_patterns, cấm so khớp chuỗi thô sơ, bắt buộc import canonical matches_switcher_identity từ automation-core).
> - `references/sqlite-master-ledger-db-browser-and-1905-dashboard-access.md`: Hướng dẫn truy cập và xem SQLite SSOT (`farm_master.db`) ưu tiên qua Web Dashboard `:1905` hoặc File Explorer + DB Browser for SQLite trực quan dạng lưới (Excel-like). Kỷ luật cấm spam lệnh SQL terminal bắt user nhớ, cấm tự ý spawn GUI desktop gây bẫy pipe leak treo terminal 60 phút, và bản đồ vị trí các file SQLite toàn hệ thống (`D:\Taadaa\data\farm_master.db`, `tiktok_tracker.db`, `C:\Users\Kibe\.omniroute\storage.sqlite`, `D:\Taadaa\GPM auto\`).
> - `references/jt-mobile-422-trap

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
