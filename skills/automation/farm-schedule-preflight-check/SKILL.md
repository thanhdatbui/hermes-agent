---
name: farm-schedule-preflight-check
description: Kiểm tra máy rảnh an toàn trước khi chạy các batch reg / login / upload — tránh xung đột với lịch Cron nuôi acc (TikTok feed/follow).
---
# Farm Schedule Preflight Check

References:
- Chi tiết toàn bộ quy trình và phân tích chuyên sâu: xem các tài liệu trong thư mục `references/` của skill.

Dùng trước khi khởi chạy bất kỳ batch tác vụ nào (Reg TikTok, Hotmail, Add Mail, Upload video, Reconcile...) để tìm danh sách máy rảnh, không đụng vào lịch nuôi acc tự động.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
