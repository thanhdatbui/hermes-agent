# OmniRoute Combo Routing Strategies & Pitfalls Reference

## 1. Bản chất các Strategy trong OmniRoute (`open-sse/services/combo/`)

### A. Pool Pro Gemini (Google Antigravity Pro)
- **Vấn đề với `round-robin`:** Xoay vòng mù quáng theo index danh sách cố định (1..N). Khi gặp acc chết proxy / timeout mạng Mobi, cả hàng đợi bị nghẽn làm trượt fallback ra OpenCode trong khi các acc Pro khác (như `ninhvan`, `vuthao`) ngồi rảnh 100% quota.
- **Cạm bẫy với `headroom`:** Lý thuyết `headroom = 1 - max(util_5h, util_7d)` nghe rất hay, nhưng trong code `quotaStrategies.ts`: trước MỖI request nó chạy `mapWithConcurrency(targets, 5, ...)` gọi gần 40 HTTP requests sang Google để query % saturation. Với pool 20 acc qua proxy farm, độ trễ thăm dò vọt lên > 30s gây timeout và HTTP 499 (Client Closed Request) ngay lập tức!
- **Chiến thuật tối ưu nhất: `least-used` + Session Stickiness:**
  - `least-used` đọc metrics từ RAM nội bộ (`metrics.byTarget[executionKey].requests`), zero network overhead.
  - Acc nào nhận ít request nhất / còn nguyên quota sẽ tự động nổi lên đầu hàng đợi.
  - Cấu hình bắt buộc:
    ```json
    {
      "strategy": "least-used",
      "disableSessionStickiness": false,
      "disablePromptCacheAffinity": false,
      "stickyRoundRobinLimit": 8,
      "queueTimeoutMs": 3000,
      "targetTimeoutMs": 30000,
      "failoverBeforeRetry": true,
      "maxRetries": 1
    }
    ```
  - `stickyRoundRobinLimit: 8` giữ nguyên prompt cache trong 8 turns của cùng 1 task, sau 8 turns tự nhả để xoay sang acc rảnh khác.

### B. Pool Free Codex & Claude AG (`codex-terra`, `codex-luna`, `ag-opus`, `ag-sonnet`, `ag-gemini-free-pool`)
- **Vấn đề với `cache-optimized`:** Khi cache hit, code `targetResolution.ts` vô tình set `disableSessionStickiness = true`, dẫn đến hệ thống chỉ dí liên tục vào 1-2 acc có cache cho đến khi cạn quota / rate-limit trong khi các acc free khác rảnh rỗi.
- **Chiến thuật tối ưu:** **`least-used`** kết hợp `stickyRoundRobinLimit: 6` và `queueTimeoutMs: 2000`.
  - Chia đều request giữa các acc free.
  - Vẫn giữ prompt cache cho subagent trong 6 turns.

### C. Pool ChatGPT Web (`chatgpt-web-pool`, `gpt-web-sol`, `gpt-web-luna`)
- **Đặc điểm:** Web session reset request limit mỗi vài tiếng; ưu tiên sống sót, tránh dồn cục request vào 1 nick gây Cloudflare block hoặc checkpoint.
- **Cạm bẫy với `p2c` trên Pool đồng nhất model:**
  - Trong `open-sse/services/combo/targetSorters.ts`, hàm `getP2CTargetScore` đọc metric từ `metrics.byModel[target.modelStr]` thay vì `metrics.byTarget[target.executionKey]`.
  - Hậu quả: Khi 16 accounts cùng phục vụ `chatgpt-web/gpt-5.6-sol-high`, cả 16 acc đều nhận chung một điểm số. Khi điểm bằng nhau, tie-breaker luôn chọn `firstIndex`, làm lệch tải và không hạ điểm acc bị lỗi 502.
- **Chiến thuật tối ưu: `strict-random` (Deck Shuffling):**
  - Cấu hình: `strategy: "strict-random"`, `disableSessionStickiness: true`, `disablePromptCacheAffinity: true`, `stickyRoundRobinLimit: 0`, `queueTimeoutMs: 1000`.
  - OmniRoute dùng `getNextFromDeck` theo `executionKey`, chia bài quay vòng đều 100% qua tất cả các account trong deck, triệt tiêu hoàn toàn nguy cơ đè liên tiếp vào một account đang dính lỗi transient.

## 2. Quy tắc chẩn đoán khi acc không nhận traffic
1. Đừng chỉ nhìn `testStatus: active` hay token refresh thành công: Phải kiểm tra vị trí của acc trong combo (`/api/combos`) và thời gian request gần nhất (`/api/usage/history`).
2. Nếu dải proxy chính bị cúp điện/chết: OmniRoute fallback sang MikroTik theo hash connectionId cố định (`hashConnectionId % pool.length`).
3. Nếu acc bị xếp sâu (ví dụ index 13/20) trong combo `round-robin`, các acc trước bị kẹt timeout proxy sẽ làm request trượt sang fallback ngoài (OpenCode) trước khi kịp chạm đến acc đó.
4. Muốn ép acc vào chạy thử ngay: gọi PUT `/api/combos/<id>` đảo acc lên vị trí index 0 hoặc chuyển strategy sang `least-used`.

## 3. Bệnh lý "Đè acc lỗi 502/403 ra chạy lặp đi lặp lại" (Transient Failover Amnesia)
- **Triệu chứng:** Một account (ví dụ `voha03082002`) liên tục bị văng 502 Bad Gateway / 403 Sentinel, nhưng mọi request mới tiếp theo của client vẫn tiếp tục bốc đúng acc đó ra thử đầu tiên rồi mới failover sang acc khác (`healed 200`).
- **Nguyên nhân gốc rễ trong code OmniRoute (`open-sse/services/combo/`):**
  1. *Lỗi 502 chỉ là Transient Scope:* Trong `combo.ts`, 502 được xếp vào nhóm `isTransient` ([408, 429, 500, 502, 503, 504]). Nó chỉ bị đưa vào `exhaustedConnections` tạm thời của *đúng 1 request hiện tại*. Kết thúc request, DB vẫn giữ `is_active=1` và `test_status='active'`, không hề bị cooldown hay ngắt kết nối trong SQLite.
  2. *Healed 200 xóa sạch vết lỗi:* Khi acc 1 văng 502, hệ thống failover sang acc 2 thành công $\to$ trả về `200 OK (healed)`. Vì tổng thể request thành công, `failureTracker.ts` lập tức reset streak lỗi về 0 (`count = 0`). Circuit breaker không bao giờ tích lũy đủ 3 lần fail để ngắt acc.
  3. *Session Stickiness (Ghim phiên) không nhả trên 502:* `sessionStickiness.ts` ghim connection theo SHA-256 prompt/messages. Nó chỉ nhả ghim khi tài khoản dính cờ terminal (`banned`, `expired`, `rateLimitedUntil > now`). Transient 502 không kích hoạt nhả pin, nên các request cùng session/tool tiếp theo vẫn bị ép đè acc cũ lên Index 0.
  4. *Bẫy thống kê Least-Used:* Điểm usage trong `sortTargetsByUsage` chỉ ghi nhận khi request thành công. Acc văng 502 ngay từ đầu không được cộng request count, nên thuật toán luôn thấy nó "rảnh nhất / ít dùng nhất" (`requests = 0`) và tiếp tục ưu tiên bốc nó lên đầu.
  5. *Bẫy chấm điểm P2C trên Pool đồng nhất model:* `getP2CTargetScore()` trong `targetSorters.ts` đọc `metrics.byModel[target.modelStr]` chứ không đọc theo `executionKey`. Khi 16 acc dùng chung model `gpt-5.6-sol-high`, mọi acc nhận điểm số y hệt nhau $\to$ tie-break luôn chọn `firstIndex`, acc lỗi 502 không hề bị trừ điểm hay né tránh.
- **Biện pháp xử lý dứt điểm:**
  - *Xử lý nóng:* Vào Dashboard `Providers -> ChatGPT Web`, gạt toggle tắt tài khoản lỗi (`is_active = 0`) để loại ngay khỏi danh sách targets.
  - *Cấu hình Combo chuẩn cho Web Pool:* BẮT BUỘC chuyển sang `strategy: "strict-random"`, `disableSessionStickiness: true`, `disablePromptCacheAffinity: true`, `stickyRoundRobinLimit: 0` để chia bài xoay vòng đều qua deck theo `executionKey`, triệt tiêu hoàn toàn thiên lệch bốc lại acc cũ.
  - *Vá code thuật toán (Lâu dài):* Sửa `getP2CTargetScore` trong `targetSorters.ts` chuyển sang đọc `metrics.byTarget?.[target.executionKey]` để P2C hạ điểm đúng từng account cá thể khi dính lỗi thay vì dùng metric chung của cả model.
  - *Xử lý hạ tầng:* Kiểm tra proxy gắn với acc (ví dụ port proxy di động bị đứt socket/mất mạng) và refresh lại session cookie qua GPM CDP.
