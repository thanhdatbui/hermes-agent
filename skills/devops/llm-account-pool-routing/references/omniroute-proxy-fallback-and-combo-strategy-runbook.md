# OmniRoute Proxy Fallback & Combo Strategy Operational Runbook

## 1. Cơ Chế Proxy Fallback Thực Tế Của OmniRoute (Cực Kỳ Quan Trọng)

Khi một proxy gán cố định cho account bị chết (ví dụ dải Mobi `test.taadaa.click` cúp điện / timeout):
* **Không phải direct egress bừa bãi:** OmniRoute chạy hàm `resolveProxyForConnection` trong `src/lib/db/settings.ts`.
* **Cơ chế Fallback sang Provider Pool:**
  ```typescript
  const isUnreachable = !accountHealthUrl || !(await isProxyReachable(accountHealthUrl));
  if (isUnreachable) {
    const providerFallback = await resolveProviderPoolFallbackProxy(connectionProvider, connectionId);
    if (providerFallback) return providerFallback;
  }
  ```
* **Deterministic Hashing:** 
  Hàm `resolveProviderPoolFallbackProxy` lọc ra các proxy đang sống trong pool (`reachable`) và dùng hàm băm:
  ```typescript
  const index = hashConnectionId(connectionId) % reachable.length;
  return reachable[index];
  ```
  -> **Mỗi account sẽ map cố định vào đúng 1 port proxy đang sống duy nhất** (ví dụ port MikroTik `10005`, `10014`, `10032`). Không bị xoay IP bừa bãi giữa các request trong cùng phiên, bảo vệ fingerprint Google!

## 2. Bẫy Hiểu Nhầm Về Lỗi & Quota Của Account
* **Lỗi Semaphore 429 (`SEMAPHORE_TIMEOUT` sau 1000ms):** Xảy ra khi có nhiều request đồng thời dồn vào một account vượt quá `maxConcurrent` trong lúc proxy đang kết nối chậm. Hermes thấy 429 sẽ tưởng là rate-limit và kích hoạt fallback ra ngoài (nhảy sang OpenCode).
* **Quota UI 100% không đồng nghĩa acc không chạy:** UI dashboard chỉ hiển thị quota của các model nặng (Opus, Sonnet, Gemini 3.1 Pro). Nếu pool chạy model `gemini-3.8-flash-tiered`, quota UI trên web giữ nguyên 100% trong khi acc đã cày hàng nghìn requests trong `/api/usage/history`.
* **Thứ tự trong Combo Round-Robin:** Nếu account xếp ở cuối danh sách (ví dụ vị trí 14/18) và các account trước bị timeout mạng, request sẽ kẹt hoặc failover trước khi kịp chạm đến account đó, tạo cảm giác account "ngồi chơi không dùng được". Muốn acc chạy ngay: đẩy lên vị trí Top 1 hoặc đổi strategy.

## 3. Ma Trận Chiến Thuật Routing Cho Pool Pro Gemini (Prompt Cache vs Concurrency vs Load Balancing)

| Strategy | Prompt Caching (Stickiness) | Rủi Ro 499 / 429 Semaphore | Cân Bằng Tải Pool Pro | Đánh Giá Vận Hành |
| :--- | :--- | :--- | :--- | :--- |
| `round-robin` | Hỗ trợ session stickiness | Rất cao khi proxy chập chờn | Kém (chạy theo thứ tự mù quáng) | ❌ Dễ gây dồn toa, timeout |
| `priority` | Rất cao | Cực cao (cày nát acc đầu) | Kém | ❌ Nhanh kiệt từng acc |
| `least-used` | Rất tốt khi kết hợp stickiness | Thấp | Rất tốt (acc ít request chạy trước) | 🟢 Tự động đẩy acc rảnh lên trước |
| `p2c` | Kém (chọn ngẫu nhiên 2 acc) | Rất thấp | Tốt | ❌ Phá vỡ prompt cache |
| `headroom` | Tuyệt đối (ưu tiên acc % trống cao) | Thấp nhất | Tối ưu tuyệt đối | 🏆 TỐI ƯU NHẤT CHO POOL PRO |

## 4. Cấu Hình Khuyến Nghị Chuẩn Vận Hành
* **Strategy:** `headroom` (hoặc `least-used` nếu không muốn probe quota upstream).
* **`stickyRoundRobinLimit`:** `20` (giữ session stickiness 20 turns để tối đa hóa Prompt Cache).
* **`queueTimeoutMs`:** `15000` (giảm thời gian chờ hàng đợi từ 30s xuống 15s để failover nhanh, chống lỗi 499 client timeout).
* **`failoverBeforeRetry`:** `true` (khi gặp lỗi thì chuyển ngay sang acc Pro kế tiếp, không retry tại chỗ gây nghẽn socket).
