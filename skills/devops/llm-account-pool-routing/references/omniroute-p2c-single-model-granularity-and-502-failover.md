# OmniRoute P2C Single-Model Granularity Mismatch & 502 Transient Failover Pathology

Tài liệu này ghi lại chi tiết giải phẫu lỗi kiến trúc định tuyến P2C trên pool tài khoản đồng nhất (cùng model string), cơ chế bỏ sót cooldown của lỗi 502 Bad Gateway, và runbook khắc phục tức thì cho OmniRoute (port 20129).

---

## 1. Triệu chứng lâm sàng (Symptoms)
- Pool gồm 16+ tài khoản cùng model (ví dụ `chatgpt-web/gpt-5.6-sol-high` hoặc pool Codex/Gemini đồng nhất) chạy qua các proxy di động khác nhau.
- Một tài khoản bị lỗi mạng/proxy (HTTP 502 Bad Gateway hoặc Cloudflare drop).
- Dù request đó được account phía sau cứu thành công (`200 healed · 2 attempts`), các request TIẾP THEO vẫn liên tục chọn lại đúng tài khoản lỗi đó làm first-try (`502` liên tiếp trên cùng correlationId hoặc tài khoản).
- Người dùng nhận thấy hệ thống chậm và hỏi: *"Cả đống acc sao cứ đè nó ra chạy?"*

---

## 2. Bản chất kỹ thuật & Điểm nghẽn kiến trúc (Root Causes)

### A. Granularity Mismatch trong P2C Target Scoring (`byModel` vs `executionKey`)
- **Vị trí code:** `open-sse/services/combo/targetSorters.ts` (Hàm `getP2CTargetScore`).
- **Cơ chế lỗi:**
  ```typescript
  function getP2CTargetScore(target: ResolvedComboTarget, metrics: ReturnType<typeof getComboMetrics>): number {
    const breakerState = getCircuitBreaker(target.provider)?.getStatus?.()?.state;
    if (breakerState === "OPEN") return -Infinity;
    // LỖI: Đọc theo model chung thay vì theo từng executionKey / connectionId
    const modelMetric = metrics?.byModel?.[target.modelStr] || null;
    const successRate = Number(modelMetric?.successRate);
    const avgLatency = Number(modelMetric?.avgLatencyMs);
    ...
  }
  ```
- **Hệ quả:** Vì tất cả 16 tài khoản đều mang chung `modelStr = "chatgpt-web/gpt-5.6-sol-high"`, toàn bộ 16 targets nhận được **điểm số sức khỏe giống hệt nhau** bất kể tài khoản nào vừa tạch 502.
- Khi P2C bốc ngẫu nhiên 2 target có điểm bằng nhau, tie-break fallback về `firstIndex` (`getP2CTargetScore(second) > getP2CTargetScore(first) ? secondIndex : firstIndex`), khiến mảng giữ nguyên thứ tự ban đầu và tài khoản đầu tiên luôn bị đè ra chạy.

### B. 502 Transient Escape & Healed Masking
- **Phân loại lỗi:** Mã `502 Bad Gateway` (và `504 Gateway Timeout`) được OmniRoute phân loại là `isTransient`.
- `isTransient` chỉ kích hoạt failover trong nội bộ request hiện tại (`per-request exhaustion set`), **KHÔNG ghi cooldown** vào database hoặc persistent memory.
- Khi request được target thứ hai cứu thành công (`200 OK healed`), `recordComboRequest` ghi nhận thành công, reset chuỗi đếm lỗi liên tiếp (`failureTracker.ts`).
- Sang request mới, tài khoản bị lỗi vẫn có trạng thái `isActive = 1` và `testStatus = active` 100%, tiếp tục được xem là candidate hoàn hảo.

---

## 3. Runbook xử lý nóng (Không cần sửa code engine)

### Bước 1: Đổi Combo Strategy sang `round-robin`
Chuyển strategy từ `p2c` sang `round-robin` để con trỏ tịnh tiến liên tục ($1 \to 2 \to \dots \to 16$), đảm bảo phân phối tải đều tuyệt đối và sau khi gặp acc lỗi thì phải đi hết 1 vòng 15 acc khác mới gặp lại.

Cấu hình combo chuẩn (qua API `PUT /api/combos/:id`):
```json
{
  "strategy": "round-robin",
  "config": {
    "disableSessionStickiness": true,
    "disablePromptCacheAffinity": true,
    "stickyRoundRobinLimit": 0,
    "failoverBeforeRetry": true,
    "maxRetries": 0,
    "maxGlobalAttempts": 8,
    "targetTimeoutMs": 60000,
    "retryDelayMs": 500
  }
}
```
* **`disableSessionStickiness: true`**: Triệt tiêu việc băm SHA-256 prompt ghim chết client vào 1 acc cố định.
* **`stickyRoundRobinLimit: 0`**: Bắt buộc mỗi request phải chuyển sang target tiếp theo, không ghim lại.
* **`failoverBeforeRetry: true` + `maxRetries: 0`**: Dính 502 là nhảy ngay lập tức 0ms sang target khác trong pool, không thử lại trên cùng target lỗi.

### Bước 2: Tạm thời cách ly Account lỗi
Khi phát hiện proxy hoặc account của 1 connection cụ thể chập chờn liên tục:
- Gọi API: `PUT /api/providers/:connectionId` với payload `{"isActive": false}`.
- Connection lập tức bị loại khỏi candidate list của tất cả combos mà không cần restart server hay làm gián đoạn pool.

---

## 4. Bản vá kiến trúc tận gốc trong OmniRoute Codebase

Nếu can thiệp vào mã nguồn OmniRoute (`open-sse`):

1. **Vá `open-sse/services/combo/targetSorters.ts`:**
   - Đổi `getP2CTargetScore` đọc từ `metrics?.byTarget?.[target.executionKey]` thay vì `metrics?.byModel?.[target.modelStr]`.
   - Bổ sung penalty điểm số cho `executionKey` vừa có failure trong 60 giây gần nhất.
   - Tie-break khi bằng điểm phải dùng `secureRandomInt` thay vì ưu tiên `firstIndex`.

2. **Vá `open-sse/services/combo/targetExhaustion.ts`:**
   - Khi nhận mã 502/504 từ upstream provider dạng web/proxy (`chatgpt-web`), kích hoạt **Connection Cooldown 30s – 60s** cho chính `connectionId` đó.
   - Ngăn router tái đề cử connection đó làm first-try cho đến khi proxy di động/upstream ổn định trở lại.
