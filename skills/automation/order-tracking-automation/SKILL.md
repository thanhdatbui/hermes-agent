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
> - `references/order-manual-accounting-ledger-and-monthly-summary.md`: Kỷ luật Sổ Đơn Hàng Nhập Tay Độc Lập & Tổng Kết Tháng (Clean Manual Accounting Ledger) — tách biệt hoàn toàn bảng tính lời lỗ với bảng bưu cục Phase 1/2, cấm tự động map đơn farm, khởi tạo bảng sạch sẽ, chuẩn hóa 6 trường (Mã đơn, Mặt hàng, Ngày nhập, Giá nhập, Giá bán, Tiền lời), bộ lọc tổng kết theo Tháng và quy trình triage hạch toán khi User cung cấp doanh thu thực tế.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
