---
name: gpm-account-pool-automation
description: "GPMLogin v3 + Playwright/CDP account-pool operations: proxy-safe Gmail lifecycle, nurture, OAuth, and ChatGPT direct registration."
version: 1.2.1
---

# GPMLogin Local API & Account Pool Automation

## 1. Nguyên Tắc Cốt Lõi
- **API Cổng 19995:** Thao tác tạo, mở, đóng profile qua GPMLogin Local API `http://127.0.0.1:19995`.
- **Proxy 1-1:** Mỗi profile gán 1 proxy riêng biệt; cấm dùng chung IP trực tiếp.
- **Tự động đóng profile stale:** Profile chạy xong hoặc kẹt > 1h bắt buộc phải được watchdog đóng dọn giải phóng RAM/CPU.

## 2. Quy Chuẩn Vận Hành
- **Đăng ký ChatGPT:** 100% Direct Email + OTP (cấm Google SSO).
- **Nuôi Gmail:** Lướt Web/YouTube tự động so le, giãn cách cooldown an toàn.
- **Bóc Cookie/Token qua CDP:** Kết nối qua Playwright CDP để trích xuất cookie tự động, không yêu cầu thao tác tay.

## 3. Tài Liệu Tham Khảo (References)
- Chi tiết API và các case watchdog: xem danh mục tài liệu trong thư mục `references/` của skill.
