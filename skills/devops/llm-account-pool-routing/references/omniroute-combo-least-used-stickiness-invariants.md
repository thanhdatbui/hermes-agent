# OmniRoute Combo Routing Invariants: Least-Used, Stickiness & Auto-Injection

## 1. Strategy Selection: Least-Used vs Headroom vs Cache-Optimized
- **`headroom` Pitfall (DO NOT USE for large proxy pools):**
  - Trực giác ban đầu thường nghĩ `headroom` (chọn acc có % quota trống nhiều nhất) là tối ưu.
  - Tuy nhiên, trong code `quotaStrategies.ts`, `orderTargetsByHeadroom` phải quét saturation qua `mapWithConcurrency(expandedTargets, 5, ...)`. Với pool 20+ accounts chạy qua proxy farm có độ trễ, mỗi request phải chờ 30-40 cuộc gọi HTTP thăm dò Google qua proxy -> **Latency vọt lên > 30s gây timeout và lỗi 499 (Client Closed Request) tức thì**.
- **`least-used` (LỰA CHỌN TỐI ƯU SỐ 1):**
  - Zero Network Overhead: Đọc trực tiếp từ in-memory `metrics.byTarget[executionKey].requests`. Không tốn 1 request nào ra ngoài.
  - Tự động san tải: Acc nào ít request nhất / còn nguyên 100% quota (như acc mới hoặc acc rảnh) sẽ tự động được ưu tiên lên đầu.
- **`cache-optimized` Caveat:**
  - Trong `targetResolution.ts`, khi `cache-optimized` phát hiện cache hit, nó vô tình set `disableSessionStickiness = true` và chỉ đập vào acc có cache cũ -> Dễ vắt kiệt 1 acc duy nhất trong khi các acc free khác bị bỏ hoang.
  - Giải pháp: Chuyển cả Codex và Claude AG sang `least-used` kết hợp `disableSessionStickiness: false`.

## 2. Session Stickiness Budget: Khớp chuẩn 15 Calls
- Cấu hình `stickyRoundRobinLimit: 15`:
  - Khớp tuyệt đối với ngân sách subagent của Hermes (`Worker budget <= 15 calls`).
  - Toàn bộ vòng đời của 1 subagent (read code -> edit -> run test verify) được ghim chặt trên đúng 1 tài khoản để hưởng trọn 100% Prompt Caching.
  - Khi subagent xong task (hết 15 calls) hoặc mở task mới, `least-used` sẽ tự động nhả và chọn tài khoản rảnh rỗi nhất tiếp theo trong pool.
- Cơ chế tự thoát an toàn:
  - Nếu trong 15 turns mà acc bị lỗi kết nối, dính `429`, hoặc hết quota, `sessionStickiness.ts` tự động phát hiện và hủy binding ngay lập tức (`clearStickyBinding`), failover sang acc sống khác mà không bị kẹt.

## 3. Proxy Fallback: Deterministic Hash
- Khi dải proxy chính bị chết / cúp điện (như dải Mobi), OmniRoute dùng cơ chế băm `hashConnectionId(connectionId) % reachable.length` để gán sang dải proxy dự phòng (như MikroTik).
- Mapping này là cố định và tất định (Deterministic): Cùng 1 account UUID sẽ luôn map ra đúng 1 port duy nhất, không bị nhảy IP lung tung giữa các requests.

## 4. Tự động nạp tài khoản mới vào Combo (Cron OAuth)
- Khi cron nạp OAuth mới (từ GPM Profiles lên OmniRoute), ngoài việc exchange code và lưu vào `api/providers`, **BẮT BUỘC** phải gọi API `PUT /api/combos` để nạp ngay connectionId mới vào các pool tương ứng (`ag-gemini-free-pool`, `ag-gemini-free-pool-37`).
- Tránh tình trạng tài khoản đã nạp thành công vào hệ thống nhưng các combo không biết đến để sử dụng.

## 5. Watchdog Phục hồi tài khoản tắt nhầm (isActive = False)
- Trong quá trình vận hành, một số tài khoản có thể bị OmniRoute chuyển sang `isActive: false` dù `testStatus: active` và OAuth token còn hạn (do network timeout tạm thời khi exchange hoặc sync).
- Định kỳ (mỗi giờ) watchdog kiểm tra database:
  ```sql
  UPDATE provider_connections 
  SET is_active = 1 
  WHERE provider = 'antigravity' 
    AND is_active = 0 
    AND test_status = 'active';
  ```
  Tự động kích hoạt lại các acc này để đưa trở lại vào pool hoạt động.
