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

## 2. Quy Chuẩn Vận Hành
- **Đăng ký ChatGPT:** 100% Direct Email + OTP (cấm Google SSO).
- **Nuôi Gmail:** Lướt Web/YouTube tự động so le, giãn cách cooldown an toàn.
- **Bóc Cookie/Token qua CDP:** Kết nối qua Playwright CDP để trích xuất cookie tự động, không yêu cầu thao tác tay.
- **Báo cáo định kỳ 6H & Cooldown 24H (`is_profile_in_needs_login_cooldown`):** Báo cáo nuôi 6H bắt buộc đọc danh sách email Group 10 qua SQLite read-only (`mode=ro`). Phân biệt rõ DB lỗi (`None`) vs Group rỗng (`set()`) theo nguyên tắc fail-closed; chặn timestamp tương lai `0 <= (now_ts - last_checked) <= WINDOW_HOURS*3600`; tuyệt đối không dùng nhãn phỏng đoán như "Google Live Ready" hay "100% cookie sống tốt". Profile `NEEDS_LOGIN` được cách ly 24h qua hàm chuẩn hóa `is_profile_in_needs_login_cooldown` trước khi tự động tái thẩm định. Chi tiết xem `references/gpm-6h-report-phantom-dropout-and-fail-closed-observability-20261019.md`.
- **Gemini 4 Argon Local CDP Daemon & Thinking Selector:** Khi gọi model 4 Argon thực thụ (gói Google AI Pro qua `:20135`), để kích hoạt mức tư duy sâu (High Thinking), BẮT BUỘC match mô tả `Cực kỳ kỹ lưỡng` (CẤM match chuỗi con `Cao` vì bốc nhầm `3.1 Pro\nSuy luận nâng cao`), kích hoạt qua `page.evaluate` DOM click vì phần tử bị ẩn trong Angular Material. CẤM bắt nút Stop tĩnh (phantom stop); BẮT BUỘC polling độ dài token ổn định (Token Length Stabilization, 3s-4s zero growth) tránh cắt cụt code 3k-5k chars giữa chừng. Tuyệt đối KHÔNG lưu lịch sử chat trên web (dùng Temporary Chat / New Thread) để tránh lẫn ngữ cảnh giữa các task và tránh rủi ro bot abuse. Chi tiết xem `references/gemini-web-pro-argon-gpm-cdp-pipeline.md`.
- **Kỷ luật Benchmark & Đánh giá Chất lượng Code:** Tuyệt đối CẤM chỉ so sánh thời gian phản hồi (latency) và cú pháp AST (`ast.parse`). Đánh giá model bắt buộc bóc tách 4 tiêu chí chất lượng thực tế: (1) Spec coverage (đủ 100% method theo đề, không bỏ sót Reader/Writer), (2) Khả năng chịu lỗi OS (Windows Sharing Violation `[WinError 32]` / `PermissionError` retry jitter), (3) Tối ưu giải thuật (DCT 2D tách làm 2 lần 1D $O(N^3)$), và (4) Test suite đa luồng thực chiến. Chi tiết xem `references/gemini-web-pro-argon-gpm-cdp-pipeline.md`.
- **Cạm bẫy AGY CLI LRU Starvation:** 22 profile trong `agy_profiles` là 22 account độc lập (`google_accounts.json`). Khi 1 profile dính timeout (120s) do proxy lag mà không được gán cooldown hay cập nhật `last_used`, thuật toán LRU sẽ lặp lại liên tục trên profile lỗi đó làm tắc cả pool. Phải bắt timeout để cooldown profile tạm thời. Chi tiết xem `references/gemini-web-pro-argon-gpm-cdp-pipeline.md`.
- **Kỷ Luật Tách Biệt Pure Google Login và Dừng OAuth Antigravity (Strict Pure Login vs OAuth Decoupling):** Chỉ thị của farm: Dừng toàn bộ cron/luồng OAuth Antigravity trên farm/GPM profiles. Hiện tại CHỈ LOGIN thuần túy Google (`accounts.google.com/signin`) trên profile GPM (nhập pass, giải TOTP, lưu session cookie) rồi chuyển ngay sang nuôi tự nhiên (`cron_gpm_gmail_nurture.py` lướt YouTube, News, Search). CẤM TUYỆT ĐỐI lồng ghép mở `api/oauth/antigravity/authorize` làm proxy/màn chắn đăng nhập hoặc tự ý bấm "Cho phép" nạp OAuth Antigravity trong pha login. Việc vừa xuất hiện trên thiết bị mới (PC GPM) đã lập tức cấp quyền Cloud Developer API sẽ kích hoạt Google Risk Engine gắn cờ `New Device Anomaly + Developer Privilege Escalation` dẫn đến chết nick hàng loạt. Rà soát codebase để loại bỏ các lệnh gọi ngầm `perform_antigravity_oauth` và `run_oauth_s7_pipeline.py` trong các watchdog login/healer. Chi tiết xem `references/gpm-login-pure-google-signin-and-antigravity-decoupling-20261019.md`.

## 3. Tài Liệu Tham Khảo (References)
- Chi tiết API và các case watchdog: xem danh mục tài liệu trong thư mục `references/` của skill.
- Pure Google Sign-in vs OAuth Antigravity Decoupling (2026-10-19): xem [`references/gpm-login-pure-google-signin-and-antigravity-decoupling-20261019.md`](references/gpm-login-pure-google-signin-and-antigravity-decoupling-20261019.md).
- Gmail GPM Re-Login Failure Triage & S7 Co-op Safety (2026-10-19): xem [`references/gmail-gpm-relogin-failure-triage-and-s7-coop-safety-20261019.md`](references/gmail-gpm-relogin-failure-triage-and-s7-coop-safety-20261019.md).
- Triage cảnh báo telemetry `DONE_WITHOUT_CHATGPT_REG` trong báo cáo 6h: xem [`references/done-without-chatgpt-telemetry-triage.md`](references/done-without-chatgpt-telemetry-triage.md).
- GPM 6H Report Phantom Dropout & Fail-Closed Observability Protocol: xem [`references/gpm-6h-report-phantom-dropout-and-fail-closed-observability-20261019.md`](references/gpm-6h-report-phantom-dropout-and-fail-closed-observability-20261019.md).
- Chuẩn hóa báo cáo 6H Group 10 fail-closed và cooldown 24h cho `NEEDS_LOGIN`: xem [`references/gpm-6h-nurture-report-group-filter-and-fail-closed-telemetry.md`](references/gpm-6h-nurture-report-group-filter-and-fail-closed-telemetry.md).
- Chống báo cáo ảo văng cookie và bẫy nghẽn nuôi vĩnh viễn (Selection Choke): xem [`references/gpm-gmail-nurture-6h-report-telemetry-and-choke-prevention.md`](references/gpm-gmail-nurture-6h-report-telemetry-and-choke-prevention.md).
- Khắc phục báo cáo ảo 6H Group 10 và cooldown 24h cho `NEEDS_LOGIN`: xem [`references/gmail-6h-report-group10-filter-and-anti-false-alert.md`](references/gmail-6h-report-group10-filter-and-anti-false-alert.md).
- Chuẩn hóa thuật ngữ và đo lường fail-closed cho báo cáo 6H: xem [`references/gpm-6h-nurture-report-terminology-and-fail-closed-metrics.md`](references/gpm-6h-nurture-report-terminology-and-fail-closed-metrics.md).
