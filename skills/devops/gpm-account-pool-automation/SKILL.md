---
name: gpm-account-pool-automation
description: "GPMLogin v3 + Playwright/CDP account-pool operations: proxy-safe Gmail lifecycle, nurture, OAuth, and ChatGPT direct registration."
version: 1.3.0
---
# GPMLogin Local API & Account Pool Automation

## 1. Nguyên Tắc Cốt Lõi
- **API Cổng 19995:** Thao tác tạo, mở, đóng profile qua GPMLogin Local API `http://127.0.0.1:19995`.
- **Proxy 1-1:** Mỗi profile gán 1 proxy riêng biệt; cấm dùng chung IP trực tiếp.
- **Tự động đóng profile stale:** Profile chạy xong hoặc kẹt > 1h bắt buộc phải được watchdog đóng dọn giải phóng RAM/CPU.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
