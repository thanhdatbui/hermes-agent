# Protected Priority Target & Quota Exhaustion Semantics in OmniRoute combo.ts

## 1. Cơ chế `protectedPriorityTarget` trong `open-sse/services/combo.ts`

Trong OmniRoute, khi một target trong combo có:
- `strategy === "priority"`
- `fallbackOnlyOnQuotaExhaustion === true`

Nó được đánh dấu là `protectedPriorityTarget`.

### Luồng xử lý mã nguồn (Source Evidence - 2026-09-11):

```typescript
// Định nghĩa protected target
const protectedPriorityTarget =
  strategy === "priority" && target.fallbackOnlyOnQuotaExhaustion === true;

const stopProtectedPriorityTarget = (message: string) => {
  observeFailure(false, target.executionKey);
  return protectedPriorityTarget
    ? { ok: false, response: errorResponse(503, message) }
    : null;
};
```

1. **Pre-dispatch checks (Circuit Breaker, Quality Validation, v.v.):**
   - Nếu Circuit Breaker mở hoặc kiểm tra chất lượng không đạt, `stopProtectedPriorityTarget()` trả về `{ ok: false, response: errorResponse(503, ...) }`.
2. **Post-dispatch execution:**
   - Khi target gặp lỗi non-quota (lỗi mạng, HTTP 500/502, timeout, hoặc transient error không thuộc quota):
   ```typescript
   if (
     protectedPriorityTarget &&
     (!protectedTargetTrust?.observedFailure ||
       !protectedTargetTrust.allObservedFailuresQuota)
   ) {
     ...
     return { ok: false, response: result };
   }
   ```
3. **Vòng lặp combo chính (`handleComboChat`):**
   ```typescript
   const res = await executeTarget(i);
   if (res && !anySuccess) {
     if (res.ok) {
       anySuccess = true;
       globalResolve!(res.response!);
       ...
     } else if (res.response) {
       // Fatal error, abort combo
       anySuccess = true;
       globalResolve!(res.response);
     }
   }
   ```

## 2. Bẫy Fatal Abort (Fatal Error vs Failover)

- Khi `executeTarget` trả về `{ ok: false, response: ... }`, vòng lặp xem đây là **Fatal error** và lập tức gọi `globalResolve(res.response)` để **hủy toàn bộ combo** và trả ngay mã lỗi (ví dụ 503) về client.
- **Hệ quả chết người trên nested combo (như `omni-worker`):**
  - Nếu gắn `fallbackOnlyOnQuotaExhaustion: true` lên Tier 1 (`ag-gemini-pool-3`), chỉ cần pool Gemini gặp 1 lỗi non-quota (như Circuit Breaker tạm thời, lỗi proxy, v.v.), OmniRoute sẽ ngắt toàn bộ combo `omni-worker` và trả 503 ngay lập tức.
  - Các tier dự phòng bên dưới như Tier 2 (`ag-claude`) hay Tier 3 (`omni-free`) **hoàn toàn bị bỏ qua, không bao giờ được kích hoạt**.

## 3. Quy chuẩn cấu hình an toàn

1. **TUYỆT ĐỐI KHÔNG GẮN `fallbackOnlyOnQuotaExhaustion: true`** lên Tier 1 ref trong worker combo đa tầng (`omni-worker`).
2. **Cơ chế failover an toàn thay thế:**
   - Sử dụng cơ chế tự nhiên: target trả về `null` khi lỗi để combo loop duyệt tiếp sang target / tier kế tiếp.
   - Kết hợp `reset-aware` cho pool con (`ag-gemini-pool-3`) để tự động sắp xếp ưu tiên các tài khoản dựa trên thời gian reset quota.
   - Điều chỉnh `comboCooldownWait` budget trong `resilienceSettings` (ví dụ `maxWaitMs = 5000`, `maxAttempts = 1`) để tránh chờ xoay quá lâu khi toàn bộ pool Gemini đều đang cooldown, nhanh chóng failover sang Claude/Free.
