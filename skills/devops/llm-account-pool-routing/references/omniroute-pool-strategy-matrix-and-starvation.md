# OmniRoute Pool Strategy Matrix & Account Starvation Playbook

## 1. Bản chất sự cố Account Starvation (Tài khoản đầy quota nhưng không được gọi)
- **Triệu chứng**: Dashboard hiển thị tài khoản 100% quota (chưa hao hụt), không có request nào trong log, người dùng nghi ngờ tài khoản bị Google validation/checkpoint/403.
- **Nguyên nhân cốt lõi**:
  1. Combo cấu hình `strategy: "round-robin"` đơn thuần hoặc danh sách account quá dài (18+ accounts).
  2. Các account phía trước trong danh sách gặp sự cố proxy chết/timeout mạng (ví dụ dải proxy di động cúp điện), khiến request bị nghẽn ở các account đầu hoặc trigger fallback sang provider khác trước khi vòng xoay kịp chạm tới account ở cuối danh sách.
  3. Lầm tưởng về số liệu tổng: Kiểm tra `/api/usage/history` thấy account có tổng số request lớn (do tích lũy từ quá khứ), nhưng `lastUsed` thực tế đã dừng từ hàng giờ trước. Bắt buộc phải đối chiếu `lastUsed` gần nhất thay vì chỉ đọc tổng request.
- **Cách xử lý dứt điểm**:
  1. Bốc tài khoản đang rảnh lên TOP 1 của combo qua API `PUT /api/combos/<id>` để ép traffic vào ngay lập tức.
  2. Bắn probe test trực tiếp `POST /v1/chat/completions` vào combo để xác nhận `lastUsed` và `updatedAt` cập nhật thời gian thực.
  3. Chuyển strategy của combo sang `least-used` hoặc `headroom`.

---

## 2. Ma trận chiến thuật tối ưu cho 3 nhóm Pool trong OmniRoute

| Nhóm Pool | Combo tiêu biểu | Strategy tối ưu | Cấu hình Stickiness & Quota | Mục tiêu & Lý do kỹ thuật |
| :--- | :--- | :--- | :--- | :--- |
| **Pool Pro Gemini** | `ag-gemini-pool-3`<br>`ag-gemini-pool-3-37` | **`least-used`** | - `disableSessionStickiness: false`<br>- `disablePromptCacheAffinity: false`<br>- `stickyRoundRobinLimit: 8`<br>- `queueTimeoutMs: 3000`<br>- `failoverBeforeRetry: true` | - Tự động ưu tiên acc còn nhiều quota/ít request nhất lên đầu.<br>- Giữ prompt cache tối đa 8 turns trong cùng một session.<br>- `queueTimeoutMs: 3s` giúp failover tức thì sang acc Pro khác khi proxy bị rớt mạng, triệt tiêu 499 / 429 semaphore timeout. |
| **Pool Free Codex & Claude AG** | `codex-terra`<br>`codex-luna`<br>`ag-opus`<br>`ag-sonnet`<br>`ag-gemini-free-pool` | **`cache-optimized`** | - `disableSessionStickiness: false`<br>- `disablePromptCacheAffinity: false`<br>- `stickyRoundRobinLimit: 6`<br>- `queueTimeoutMs: 2000`<br>- `failoverBeforeRetry: true` | - Tính toán hash prompt context để điều hướng tiếp vào đúng account đang giữ cache.<br>- Tiết kiệm hạn mức free vốn đã eo hẹp.<br>- Xong task 6 turns tự động tản tải sang acc khác. |
| **Pool ChatGPT Web** | `chatgpt-web-pool`<br>`gpt-web-sol`<br>`gpt-web-luna` | **`p2c`** *(Power of 2 Choices)* | - `disableSessionStickiness: true`<br>- `disablePromptCacheAffinity: true`<br>- `stickyRoundRobinLimit: 0`<br>- `queueTimeoutMs: 1000`<br>- `failoverBeforeRetry: true` | - Web session reset quota mỗi vài tiếng; ưu tiên sống sót và tản đều request.<br>- P2C bốc ngẫu nhiên 2 acc, chọn acc có latency thấp nhất và tỷ lệ thành công cao nhất.<br>- Tắt stickiness hoàn toàn để không dí liên tục vào 1 nick gây checkpoint Cloudflare. |

---

## 3. Cơ chế Proxy Fallback khi dải IP tĩnh cúp điện
- Hàm `resolveProviderPoolFallbackProxy()` trong `src/lib/db/settings.ts` dùng thuật toán băm xác định:
  `index = hashConnectionId(connectionId) % reachable.length`
- **Đặc tính**:
  - `connectionId` là UUID cố định của account.
  - Phép băm deterministic đảm bảo mỗi account **luôn map cố định vào đúng 1 port proxy dự phòng** (ví dụ MikroTik) đang sống, tuyệt đối không bị nhảy lung tung giữa các request làm Google nghi ngờ đổi IP.
  - Bộ lọc `reachable` loại bỏ hoàn toàn các proxy chết trước khi chia dư, không bao giờ bốc trúng port chết.
