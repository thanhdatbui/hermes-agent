# OmniRoute Proxy Fallback & Combo Starvation Postmortem

## Bối cảnh & Bài học thực tế (Session 2026-09-28)
Khi một hạ tầng proxy bị sự cố (ví dụ dải Mobi `test.taadaa.click` mất điện), các tài khoản Antigravity Pro được gán vào dải này tưởng như chết nhưng thực tế OmniRoute vẫn đẩy được traffic và trả về HTTP 200. Ngược lại, có tài khoản còn 100% quota nhưng không hề nhận được request nào.

---

## 1. Cơ chế Fallback Proxy ngầm trong OmniRoute (`settings.ts`)

Khi tài khoản được cấu hình proxy tĩnh (`proxy_assignments` với `scope = 'account'`), OmniRoute không dừng lại ngay khi proxy đó chết (dù `.env` có `PROXY_FAIL_OPEN=false`):

```typescript
// src/lib/db/settings.ts -> Step 3
const registryAccount = await resolveProxyForScopeFromRegistry("account", connectionId);
if (registryAccount?.proxy) {
  const isUnreachable = !accountHealthUrl || !(await isProxyReachable(accountHealthUrl));
  if (isUnreachable) {
    // KHI PROXY CỦA TÀI KHOẢN CHẾT (TCP check timeout < 2s):
    const providerFallback = await resolveProviderPoolFallbackProxy(connectionProvider, connectionId);
    if (providerFallback) {
      return providerFallback; // Tự động tráo sang proxy khác đang sống trong provider pool!
    }
  }
}
```

### Thuật toán tráo Proxy:
* Hàm `resolveProviderPoolFallbackProxy` lấy danh sách các proxy đang sống trong `proxy_registry` thuộc provider đó (ví dụ dải MikroTik `mirotik1.taadaa.click:10001..10035`).
* Dùng hàm băm tất định (deterministic hash):
  ```typescript
  const index = hashConnectionId(connectionId) % reachable.length;
  return reachable[index];
  ```
* **Tính chất**: Cùng một `connectionId` sẽ luôn map cố định vào một port sống duy nhất (không nhảy random giữa các request), nhưng đã bị đổi sang IP của pool dự phòng (MikroTik).

---

## 2. Bẫy Starvation của Combo `round-robin`

### Triệu chứng:
* Một số acc trong combo (như `benghowell`, `alicelmorales`, `vuthao`) bị cày liên tục hàng ngàn request, quota hao hụt.
* Một số acc khác (như `ninhvan`) nằm ở vị trí sâu (vị trí 14/18), quota giữ nguyên 100% không một vết xước, trong khi hệ thống liên tục báo lỗi rate-limit hoặc fallback sang provider ngoài (OpenCode).

### Nguyên nhân cốt lõi:
1. Combo cấu hình `strategy: "round-robin"` là **xoay vòng mù quáng theo chỉ số index danh sách**. Nó không đo đếm quota còn lại hay số request đã xử lý.
2. Khi nhiều acc ở đầu danh sách gặp sự cố proxy chết $\to$ mỗi request phải chờ TCP health check timeout (1-2s) $\to$ request bị dồn ứ $\to$ dính semaphore timeout hoặc hết budget `maxGlobalAttempts` $\to$ Combo văng lỗi 503/429 và Hermes trượt xuống provider fallback (OpenCode) trước khi con trỏ xoay kịp tới các acc ở đuôi danh sách.

---

## 3. Cách khắc phục dứt điểm

1. **Đổi chiến lược Combo sang `least-used` (hoặc `headroom`):**
   ```bash
   # Cập nhật combo qua API PUT /api/combos/:id
   # Body: { ...combo, strategy: "least-used" }
   ```
   * Thuật toán `least-used` đọc metrics `byTarget[executionKey]` và tự động xếp các tài khoản ít dùng nhất (hoặc còn 100% quota) lên vị trí đầu tiên để dispatch.
   * Ngăn chặn triệt để tình trạng tài khoản ở đuôi danh sách bị "bỏ đói" (starvation).

2. **Đưa tài khoản ưu tiên lên đầu danh sách (Manual Re-order):**
   * Nếu vẫn giữ `round-robin`, cần đưa các account khỏe mạnh/còn đầy quota lên index `0` trong mảng `models` của combo.
