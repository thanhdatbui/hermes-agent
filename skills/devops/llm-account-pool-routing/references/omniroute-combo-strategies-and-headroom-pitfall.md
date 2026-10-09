# OmniRoute Combo Routing Strategies & Pitfall Runbook

## 1. Bản chất các Routing Strategies trong OmniRoute

OmniRoute hỗ trợ 17+ routing strategies (`src/shared/constants/routingStrategies.ts`, `open-sse/services/combo/`). Dưới đây là phân tích hành vi và bẫy thực tế:

| Strategy | Cơ chế thực tế | Prompt Caching | Nguy cơ 499 / Semaphore | Khi nào nên dùng |
| :--- | :--- | :--- | :--- | :--- |
| **`least-used`** | Đọc `metrics.byTarget[executionKey].requests` trong RAM, bốc acc ít request nhất lên đầu | Rất tốt khi kèm Session Stickiness | **Cực thấp** (0ms network overhead) | **Chuẩn nhất cho Pool Pro Gemini & Pool Free Codex/Claude AG** |
| **`headroom`** | Gọi `mapWithConcurrency(expandedTargets, 5, ...)` query 5h & weekly saturation qua mạng | Tốt | **CỰC KỲ CAO (Bẫy chết người)** | Tránh dùng khi pool có >10 acc chạy proxy farm, vì 40+ HTTP probe gây timeout >30s $\to$ dính 499 |
| **`p2c`** | Power of 2 Choices: bốc ngẫu nhiên 2 acc, chọn acc latency thấp + success rate cao | Không giữ được cache (nhảy acc) | **Rất thấp** | **Chuẩn nhất cho Pool ChatGPT Web** (tản đều, chống Cloudflare/chết session) |
| **`cache-optimized`** | Tính hash prompt để tìm acc có cache, nhưng có bẫy tắt stickiness | Tốt trên lý thuyết | Trung bình | Dễ làm dồn tải vào 1 acc có cache khiến acc đó cạn quota sớm |
| **`round-robin`** | Xoay vòng cố định theo thứ tự 1 $\to$ N | Khá | Cao khi gặp acc chết | Không nên dùng khi mạng proxy chập chờn |
| **`priority`** | Cày nát acc 1, lỗi mới sang acc 2 | Cực tốt (chỉ 1 acc) | Cực cao | Chỉ dùng cho test probe hoặc failover bậc thang |

---

## 2. Bẫy Headroom vs Least-Used trên Pool Proxy Farm
* **Triệu chứng:** Khi đổi combo sang `strategy = "headroom"`, request từ Hermes/client bị `Err: timed out` sau 30s hoặc `HTTP 499`.
* **Nguyên nhân:** Hàm `orderTargetsByHeadroom()` bắt buộc phải thăm dò quota của từng connection trước khi trả về danh sách target. Với pool 20 acc, proxy farm có độ trễ sẽ biến 1 request chat thành 40 request probe nối tiếp nhau, làm nổ `targetTimeoutMs` (30s).
* **Khắc phục:** Dùng **`least-used`**. Thuật toán này đọc biến đếm request ngay trong memory của OmniRoute, hoàn toàn không tốn request mạng, phản hồi tức thì 0ms.

---

## 3. Cấu hình Vận hành Khuyên dùng (Best Practices)

### A. Pool Pro Gemini (`ag-gemini-pool-3`, `ag-gemini-pool-3-37`)
* `strategy`: `"least-used"`
* `disableSessionStickiness`: `false`
* `stickyRoundRobinLimit`: `12` (ghim 12 turns để ăn trọn prompt cache của 1 task subagent)
* `queueTimeoutMs`: `3000` (chờ hàng đợi tối đa 3s, quá 3s failover sang acc Pro khác ngay, chống nghẽn semaphore)
* `failoverBeforeRetry`: `true`

### B. Pool Free Codex & Claude AG (`codex-terra`, `codex-luna`, `ag-opus`, `ag-sonnet`)
* `strategy`: `"least-used"`
* `disableSessionStickiness`: `false`
* `stickyRoundRobinLimit`: `12`
* `queueTimeoutMs`: `2000`
* `failoverBeforeRetry`: `true`
*(Lưu ý: Không dùng `cache-optimized` vì mã nguồn OmniRoute sẽ set `disableSessionStickiness = true` khi cache affinity áp dụng, làm vỡ logic ghim session của subagent).*

### C. Pool ChatGPT Web (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`)
* `strategy`: `"p2c"`
* `disableSessionStickiness`: `true` (tắt stickiness để request tản đều ra 27 acc web)
* `stickyRoundRobinLimit`: `0`
* `queueTimeoutMs`: `1000`
* `failoverBeforeRetry`: `true`

---

## 4. Bẫy Proxy Cúp điện & Deterministic Hashing
* Khi proxy tĩnh gán cho account bị cúp điện (`isProxyReachable == false`), OmniRoute sẽ gọi `resolveProviderPoolFallbackProxy()`.
* Hàm này dùng `hashConnectionId(connectionId) % reachable.length` để map cố định acc sang một port sống (ví dụ MikroTik).
* Mỗi acc chỉ đi qua đúng 1 port cố định, không nhảy lung tung giữa các request.
* **Cảnh báo Dashboard Quota:** Nếu một acc hiển thị 100% quota trên UI, cần kiểm tra:
  1. UI chỉ đếm 3 model nặng (Opus, Sonnet, Gemini 3.1 Pro High). Nếu traffic chạy `gemini-3.8-flash-tiered`, thanh quota trên UI sẽ không tụt.
  2. Kiểm tra `lastUsed` và `byAccount` trong `/api/usage/history` để biết chính xác acc có nhận request hay không.
