# OmniRoute Proxy Fallback & Provider Pool Resolution

## Overview
Khi cấu hình proxy theo các cấp độ trong OmniRoute (`account` -> `provider` -> `combo` -> `global`):
- Connection thường được gán cứng một proxy cấp account (`proxy_assignments` với `scope='account'`).
- Nếu proxy này gặp sự cố (mạng chết, timeout, port đóng), trước đây `resolveProxyForConnection` trả về ngay proxy chết đó, dẫn tới tầng egress bị Fast-Fail ngắt kết nối (`HTTP 502 / 503 ALL_TARGETS_SKIPPED`), bỏ qua hoàn toàn các proxy còn sống trong pool provider.

## Cơ chế Fallback 3 Lớp (Account -> Provider Pool -> Direct)
1. **Lớp 1 (Account Proxy)**:
   - Resolver lấy proxy gán cho connection qua `resolveProxyForScopeFromRegistry('account', connectionId)`.
   - Thực hiện probe nhanh qua `isProxyReachable(proxyUrl)`.
   - Nếu proxy sống, sử dụng proxy này.
2. **Lớp 2 (Provider Pool Fallback)**:
   - Nếu proxy cấp account bị unreachable, resolver tự động gọi `getAliveProxyPoolForScope('provider', connectionProvider)`.
   - Duyệt qua danh sách các proxy có `status='active'` trong provider pool và chọn candidate đầu tiên vượt qua probe `isProxyReachable`.
   - Ghi log cảnh báo: `[ProxyFallback] Account proxy unreachable; using provider pool for <provider>`.
3. **Lớp 3 (Direct Fallback - PROXY_FAIL_OPEN)**:
   - Nếu toàn bộ proxy trong provider pool cũng đều unreachable, kết quả phân giải trả về `direct` hoặc ở tầng egress (`proxyFetch.ts`), cờ `PROXY_FAIL_OPEN=true` sẽ cho phép request gửi trực tiếp qua Direct IP thay vì làm gián đoạn traffic.

## Cache Invalidation & Dynamic Failover
- `resolveProxyForConnection` có bộ nhớ đệm `proxyResolutionCache`.
- Khi đọc cache, nếu proxy cached là cấp `account`/`key`/`apiKey` nhưng hiện tại bị probe là unreachable, cache entry sẽ tự động bị bỏ qua và fallback sang provider pool, bảo đảm phản ứng ngay khi proxy đột ngột chết giữa phiên.
