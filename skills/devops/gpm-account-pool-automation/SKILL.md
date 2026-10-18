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
- **Gemini 4 Argon Local CDP Daemon & Web History:** Khi cần gọi model 4 Argon thực thụ (gói Google AI Pro), không dùng HTTP StreamGenerate (chỉ hỗ trợ Gemini 3.1 Pro qua slot 79). Dùng Playwright CDP kết nối ngầm vào GPM profile (offscreen), giữ trang `gemini.google.com/app` chọn 4 Argon và expose API OpenAI-compatible (`:20135`). Tuyệt đối KHÔNG lưu lịch sử chat trên web (dùng Temporary Chat / New Thread) để tránh lẫn ngữ cảnh giữa các task và tránh rủi ro bot abuse.
- **Cạm bẫy AGY CLI LRU Starvation:** 22 profile trong `agy_profiles` là 22 account độc lập (`google_accounts.json`). Khi 1 profile dính timeout (120s) do proxy lag mà không được gán cooldown hay cập nhật `last_used`, thuật toán LRU sẽ lặp lại liên tục trên profile lỗi đó làm tắc cả pool. Phải bắt timeout để cooldown profile tạm thời. Chi tiết xem `references/gemini-web-pro-argon-gpm-cdp-pipeline.md`.

## 3. Tài Liệu Tham Khảo (References)
- Chi tiết API và các case watchdog: xem danh mục tài liệu trong thư mục `references/` của skill.
- Triage cảnh báo telemetry `DONE_WITHOUT_CHATGPT_REG` trong báo cáo 6h: xem [`references/done-without-chatgpt-telemetry-triage.md`](references/done-without-chatgpt-telemetry-triage.md).
