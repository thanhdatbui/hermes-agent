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
- **Chiến thuật tối ưu: `p2c` (Power of Two Choices):**
  - Cấu hình: `strategy: "p2c"`, `disableSessionStickiness: true`, `stickyRoundRobinLimit: 0`, `queueTimeoutMs: 1000`.
  - Tản đều ngẫu nhiên theo latency và tỷ lệ thành công, không ghim nick web.

## 2. Quy tắc chẩn đoán khi acc không nhận traffic
1. Đừng chỉ nhìn `testStatus: active` hay token refresh thành công: Phải kiểm tra vị trí của acc trong combo (`/api/combos`) và thời gian request gần nhất (`/api/usage/history`).
2. Nếu dải proxy chính bị cúp điện/chết: OmniRoute fallback sang MikroTik theo hash connectionId cố định (`hashConnectionId % pool.length`).
3. Nếu acc bị xếp sâu (ví dụ index 13/20) trong combo `round-robin`, các acc trước bị kẹt timeout proxy sẽ làm request trượt sang fallback ngoài (OpenCode) trước khi kịp chạm đến acc đó.
4. Muốn ép acc vào chạy thử ngay: gọi PUT `/api/combos/<id>` đảo acc lên vị trí index 0 hoặc chuyển strategy sang `least-used`.
