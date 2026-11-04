---
name: omniroute-resilience-and-recovery-ops
description: Quy chuẩn vận hành, phòng chống bẫy build trắng trang Dashboard, kỷ luật failover vs pruning tài khoản, và giao thức phục hồi khẩn cấp OmniRoute (:20129).
version: 1.0.0
tags: [omniroute, proxy, failover, session-stickiness, nextjs, recovery, watchdog]
---
# OmniRoute Resilience and Recovery Ops

## 1. Cấm Chữa Cháy Ngọn (Pruning Accounts vs Adaptive Failover)
- **Hành vi sai lầm**: Khi một tài khoản trong combo (`gpt-web-sol`, `gemini-web`, `ag-gemini-pool-3`) gặp lỗi `502 Bad Gateway`, `Proxy 500` hoặc Cloudflare, Coordinator vội vàng xóa tài khoản đó ra khỏi mảng `models` của combo hoặc vội vàng tắt vĩnh viễn (`is_active=0` mù quáng) làm mất tài nguyên sử dụng của User.
- **Tác hại nghiêm trọng**:
  1. Hầu hết lỗi 502/Proxy 500 chỉ là do cổng proxy 4G xoay IP hoặc mạng chập chờn tạm thời. Xóa account hoặc tắt nhầm làm mất nick vĩnh viễn, khiến Healer Watchdog (`chatgpt-web-pool-healer-watchdog`) không thể probe và tự động hồi sinh nick.
  2. Bị User phản ứng gắt vì làm mất acc ("Tắt cái mả cha mày tắt r bố mày mất luôn acc k sử dụng à").
- **Quy chuẩn bắt buộc (Cứu Gốc)**:
  * **Giữ nguyên 100% tài khoản trong combo**: Để Healer Watchdog tự động probe và phục hồi trạng thái `test_status='active'`.
  * **Không tắt (`is_active=0`) bừa bãi khi chưa rõ nguyên nhân**: Tuyệt đối không tùy tiện tắt account khi lỗi chỉ là transient hoặc do context request quá nặng làm timeout. Account dính 429 tạm thời thì để cơ chế rate_limited_until/backoff của OmniRoute tự xử lý hoặc probe hồi phục theo chu kỳ reset quota của Google.
  * **Cấu hình Failover tức thì trên Combo**: Đặt `failoverBeforeRetry: true`, `failoverBeforeRetryExplicit: true`, `stickyRoundRobinLimit: 1` và `maxRetries: 0`.
  * **Cơ chế Unpin trong Core**: Đảm bảo `TERMINAL_STICKY_STATUSES` trong `sessionStickiness.ts` bao gồm cả `"unavailable"` và `"error"`. Khi account chớm lỗi, router tự động nhả ghim session và failover tức thì sang nick tiếp theo mà không đâm đầu vào nick chết.
  * **Loại trừ Proxy Error khỏi Retry In-Place**: Không đưa lỗi proxy/network 502 vào `shouldRetrySameAccountTransport` trong `sameAccountTransportRetry.ts`.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
