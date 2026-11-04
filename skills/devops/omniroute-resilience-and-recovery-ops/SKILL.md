---
name: omniroute-resilience-and-recovery-ops
description: Quy chuẩn vận hành, phòng chống bẫy build trắng trang Dashboard, kỷ luật failover vs pruning tài khoản, và giao thức phục hồi khẩn cấp OmniRoute (:20129).
version: 1.0.0
tags: [omniroute, proxy, failover, session-stickiness, nextjs, recovery, watchdog]
---
# OmniRoute Resilience and Recovery Ops

## 1. Cấm Chữa Cháy Ngọn (Pruning Accounts vs Adaptive Failover)
- **Hành vi sai lầm**: Khi một tài khoản trong combo (`gpt-web-sol`, `gemini-web`, `ag-gemini-pool-3`) gặp lỗi `502 Bad Gateway`, `Proxy 500` hoặc Cloudflare, Coordinator vội vàng xóa tài khoản đó ra khỏi mảng `models` của combo trong SQLite.
- **Tác hại nghiêm trọng**:
  1. Hầu hết lỗi 502/Proxy 500 chỉ là do cổng proxy 4G xoay IP hoặc mạng chập chờn tạm thời. Xóa account làm mất nick vĩnh viễn, khiến Healer Watchdog (`chatgpt-web-pool-healer-watchdog`) không thể probe và tự động hồi sinh nick.
  2. Không giải quyết được gốc rễ: Tài khoản khác trong pool gặp lỗi proxy tương tự sẽ tiếp tục bị đè ra gọi và gây crash tiếp.
- **Quy chuẩn bắt buộc (Cứu Gốc)**:
  * **Giữ nguyên 100% tài khoản trong combo**: Để Healer Watchdog tự động probe và phục hồi trạng thái `test_status='active'`.
  * **Cấu hình Failover tức thì trên Combo**: Đặt `failoverBeforeRetry: true`, `failoverBeforeRetryExplicit: true`, `stickyRoundRobinLimit: 1` và `maxRetries: 0`.
  * **Cơ chế Unpin trong Core**: Đảm bảo `TERMINAL_STICKY_STATUSES` trong `sessionStickiness.ts` bao gồm cả `"unavailable"` và `"error"`. Khi account chớm lỗi, router tự động nhả ghim session và failover tức thì sang nick tiếp theo mà không đâm đầu vào nick chết.
  * **Loại trừ Proxy Error khỏi Retry In-Place**: Không đưa lỗi proxy/network 502 vào `shouldRetrySameAccountTransport` trong `sameAccountTransportRetry.ts`.

## 2. Bẫy Build Trắng Trang Dashboard OmniRoute (:20129)
- **Thủ phạm**: Chạy `npm run build:backend` hoặc cờ `OMNIROUTE_BUILD_BACKEND_ONLY=1`.
- **Cơ chế phá hoại**: Script `backendOnlyPages.mjs` sẽ stub toàn bộ 126 trang của Next.js App Router thành `null`, làm trắng xóa Dashboard `http://127.0.0.1:20129/dashboard`.
- **Kỷ luật bất di bất dịch**:
  * CẤM TUYỆT ĐỐI chạy `npm run build:backend`.
  * Nếu cần build, BẮT BUỘC chạy Full Build: `node scripts/build/build-next-isolated.mjs` (không có cờ backend-only).
  * Ưu tiên số 1: Can thiệp cấu hình động qua database SQLite (`storage.sqlite`), không cần build, không cần restart, ăn ngay 100% và an toàn tuyệt đối.

## 3. Kỷ Luật Runbook Trước Khi Can Thiệp
- Trước khi thực hiện bất kỳ thao tác build, kill process hay restart OmniRoute, BẮT BUỘC phải ghi lại chi tiết hiện trường, mã code thay đổi và kịch bản cứu hộ vào file markdown trên đĩa (ví dụ `D:/Taadaa/docs/OMNIROUTE_RECOVERY_RUNBOOK.md`) để Operator có thể gọi Claude CLI hoặc Agy CLI cứu hệ thống trong O(1).

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
