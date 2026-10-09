# ChatGPT Web Pool P2C 502 Loop Pathology & Resolution

Ghi lại giải phẫu kiến trúc khi vận hành pool tài khoản ChatGPT Web (16+ accounts) trong OmniRoute, nguyên nhân gây vòng lặp 502 liên tục bị đè ra gọi lại, và giải pháp từ Sol Architect.

---

## 1. Triệu chứng (Symptoms)
- Pool 16 accounts ChatGPT Web (cùng model string `chatgpt-web/gpt-5.6-sol-high`) chạy qua các proxy di động khác nhau.
- Khi một account (ví dụ `voh` - port 5105) gặp lỗi mạng / proxy (HTTP 502 Bad Gateway):
  + Request hiện tại failover sang account khác và được cứu thành công (`200 OK healed`).
  + Tuy nhiên ở các request tiếp theo, hệ thống **tiếp tục bốc đúng account lỗi đó làm first-try**, gây chậm trễ 60-90s và dồn lỗi liên tục vào 1 node.

---

## 2. Nguyên nhân kiến trúc cốt lõi (Root Cause)

### A. Granularity Abstraction Mismatch (Chấm điểm sai tầng)
- Trong `open-sse/services/combo/targetSorters.ts` (hàm `getP2CTargetScore`):
  ```typescript
  const modelMetric = metrics?.byModel?.[target.modelStr] || null;
  const successRate = Number(modelMetric?.successRate);
  const avgLatency = Number(modelMetric?.avgLatencyMs);
  ```
- **Lỗi:** Hàm P2C chỉ đọc metric theo `modelStr` (`chatgpt-web/gpt-5.6-sol-high`). Vì cả 16 accounts dùng chung model string, tất cả nhận chung 1 điểm số, bất kể account nào vừa bị 502.
- Khi 2 target bằng điểm nhau, P2C fallback chọn target đầu tiên trong danh sách candidate, khiến account lỗi giữ nguyên vị trí ưu tiên.

### B. Transient Error Classification & Reset On Heal
- Mã lỗi `502` được phân loại là transient (tạm thời), chỉ bị đưa vào `per-request exhaustion set`. Nó **không kích hoạt Connection Cooldown** trong SQLite/Memory.
- Khi lượt gọi sau được node khác cứu thành công (`healed`), bộ đếm lỗi liên tiếp (`failureTracker.ts`) reset về 0. Account lỗi không bao giờ tích lũy đủ 3 failure liên tiếp để bị ngắt mạch.

### C. Session Stickiness & Prompt Cache Affinity
- Mặc định OmniRoute băm SHA-256 nội dung tin nhắn để ghim session vào cùng một connection nhằm giữ Prompt Cache. Nếu không tắt, các turn tiếp theo luôn ưu tiên bốc lại node cũ.

---

## 3. Giải pháp khắc phục

### A. Cấu hình Combo (Không sửa code engine)
Áp dụng cấu hình bắt buộc cho combo ChatGPT Web pool:
```json
{
  "strategy": "p2c",
  "config": {
    "failoverBeforeRetry": true,
    "disableSessionStickiness": true,
    "disablePromptCacheAffinity": true,
    "stickyRoundRobinLimit": 0,
    "maxRetries": 0,
    "maxGlobalAttempts": 8,
    "targetTimeoutMs": 120000,
    "retryDelayMs": 500
  }
}
```
- `failoverBeforeRetry: true`: Khi dính 502, lập tức nhảy sang account khác, cấm retry trên cùng account lỗi.
- `disableSessionStickiness: true`: Hủy bỏ việc ghim cứng request vào 1 account.
- `maxRetries: 0`: Không thử lại trên node vừa rớt mạng.

### B. Vá mã nguồn OmniRoute (Sửa tận gốc)
1. **`open-sse/services/combo/targetSorters.ts` (`getP2CTargetScore`):**
   - Đổi đọc metric từ `metrics?.byModel?.[target.modelStr]` sang `metrics?.byTarget?.[target.executionKey]`.
   - Khi đó, account vừa dính 502 sẽ có `byTarget.successRate` giảm lập tức, P2C tự động phạt điểm và hạ ưu tiên.
2. **`open-sse/services/combo/targetExhaustion.ts`:**
   - Khi nhận status `502` trên provider `chatgpt-web`, kích hoạt **Connection Cooldown 30s - 60s** cho `target.connectionId` đó để cách ly tạm thời khỏi candidate pool.
