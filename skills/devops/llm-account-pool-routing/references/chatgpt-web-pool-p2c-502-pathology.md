# ChatGPT Web Pool P2C Granularity Pathology & 502 Failover Runbook

## 1. Bản chất sự cố P2C Loop trên Pool ChatGPT Web (Cùng Model String)
Khi một pool gồm nhiều tài khoản ChatGPT Web (ví dụ 16 accounts) chạy qua các proxy di động khác nhau nhưng đều cấu hình cùng một model string (`chatgpt-web/gpt-5.6-sol-high`):

### Triệu chứng:
- Một tài khoản (ví dụ `voha03082002@gmail.com`) dính lỗi `HTTP 502 Bad Gateway` hoặc `403 Forbidden`.
- Request được failover sang tài khoản thứ 2 và thành công (`200 OK healed`).
- Nhưng ở các request tiếp theo, hệ thống **tiếp tục đè đúng tài khoản lỗi đó ra gọi đầu tiên (first-try)**, gây chậm trễ 10-70s cho mỗi request.

### Root Cause trong Engine OmniRoute (`open-sse/services/combo/targetSorters.ts`):
1. **Health Abstraction Granularity Mismatch**:
   - Hàm `getP2CTargetScore(target, metrics)` đọc metrics theo `metrics?.byModel?.[target.modelStr]`, KHÔNG đọc theo `metrics?.byTarget?.[target.executionKey]`.
   - Vì cả 16 accounts đều chung model `chatgpt-web/gpt-5.6-sol-high`, cả 16 accounts nhận chung 1 điểm số giống hệt nhau.
   - Khi tie-break, P2C chọn phần tử đầu tiên trong danh sách (Index 0).
2. **Transient Error không được ghi Cooldown**:
   - Mã lỗi `502` được phân loại là transient (lỗi mạng/gateway tạm thời) chứ không phải `401/429` (permanent/exhausted).
   - Engine chỉ loại account đó trong phạm vi nội bộ của đúng request đó (`per-request exhaustion set`). Request kết thúc, account vẫn ở trạng thái `active` 100%, không bị cooldown.
3. **Session Stickiness & Prompt Cache Affinity**:
   - Băm SHA-256 prompt ghim cứng session vào connection đầu tiên nếu không tắt cờ stickiness.

## 2. Giải pháp cấu hình tối ưu tức thì (Không cần sửa Engine code)
Chuyển Strategy của combo sang `round-robin` với bộ cờ bắt buộc:
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
- `disableSessionStickiness: true` + `stickyRoundRobinLimit: 0`: Ép con trỏ xoay vòng đều qua 16 accounts, không bao giờ ghim một account qua nhiều requests.
- `failoverBeforeRetry: true` + `maxRetries: 0`: Khi gặp lỗi mạng/502, lập tức nhảy sang account kế tiếp trong pool (0ms delay), cấm thử lại trên cùng account lỗi.

## 3. Phân biệt Lỗi Proxy vs Lỗi Cookie Cloudflare trên ChatGPT Web
- **Proxy Port (ví dụ 5105) vẫn sống**: Kiểm tra socket IP vẫn trả về bình thường qua proxy.
- **Thủ phạm thực sự là Cookie**: Cloudflare challenge chặn cookie `__Secure-next-auth.session-token` / `cf_clearance`.
- **Triệu chứng Probe**: POST `/api/providers/<id>/test` trả về:
  `{"code": "network_error", "message": "Cloudflare blocked the validator..."}`.
- **Xử lý**:
  1. Tạm thời set `isActive: false` trên connection để loại khỏi candidate pool.
  2. Mở Profile GPM tương ứng, vào `chatgpt.com` để giải lại Cloudflare challenge / login lại.
  3. Cập nhật cookie mới vào OmniRoute và bật lại `isActive: true`.
