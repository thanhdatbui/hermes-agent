# OmniRoute Incident: Zombie Proxy Trap, Global Cooldown Spillover & Event Loop Starvation

## 1. Triệu Chứng Sự Cố Thực Tế (07/10/2026)
1. Combo `omni-worker` trả HTTP 503 (`ALL_TARGETS_SKIPPED`) hàng loạt dù tài khoản Gemini Pro còn nguyên quota.
2. Server OmniRoute (:20129) bị treo, `/api/health` timeout liên tục, watchdog kill và restart lặp đi lặp lại mỗi vài phút.

---

## 2. Căn Nguyên Bệnh Học Sâu

### A. Bẫy Zombie Proxy (Port TCP Mở nhưng Tunnel Ra Ngoài Chết)
- **Cơ chế:** Hàm kiểm tra độ sống của proxy (`isProxyReachable` trong `src/lib/proxyHealth.ts`) chỉ thực hiện **TCP SYN connect** tới `host:port`.
- **Hậu quả:** Một proxy như `khoalee.duckdns.org:16001` có port TCP mở trên router, nhưng đường truyền Internet từ máy chủ proxy ra Google đã chết. `isProxyReachable` trả về `healthy: true` và đưa nó vào mảng `reachable` của Provider Pool.
- **Tác động:** Khi một account có proxy riêng bị chập chờn > 2s, hàm `resolveProviderPoolFallbackProxy` băm `hashConnectionId(connectionId) % reachable.length`. Mọi account hash trúng con zombie proxy này đều bị ngâm kết nối 30s ➔ 504 Gateway Timeout ➔ Kéo theo chuỗi lỗi 503.
- **Xử lý:**
  ```sql
  -- Xóa sạch mọi assignment trỏ tới proxy chết
  DELETE FROM proxy_assignments WHERE proxy_id = '<DEAD_PROXY_ID>';
  -- Đánh dấu status='dead' để loại trừ vĩnh viễn khỏi PROXY_ALIVE_PREDICATE
  UPDATE proxy_registry SET status = 'dead' WHERE id = '<DEAD_PROXY_ID>';
  ```

### B. Bẫy Global Cooldown Spillover (Vạ Lây Toàn Bộ Provider)
- **Sai lầm:** Khi muốn cách ly tài khoản ChatGPT Web bị rate limit trong 1 giờ (rolling window của OpenAI), cấu hình bị sửa nhầm vào biến toàn cục:
  `resilienceSettings.providerCooldown.minRetryCooldownMs = 3600000 (1 giờ)`.
- **Hậu quả:** Cấu hình này áp dụng **GLOBAL** cho mọi provider. Khi Gemini dính 1 lỗi mạng thoáng qua hoặc timeout do proxy, OmniRoute lập tức phạt cả dàn Gemini Pro ngủ đông **1 đến 3 tiếng**, gây tê liệt toàn bộ hệ thống.
- **Quy tắc chuẩn:**
  - `providerCooldown` toàn cục trong DB phải giữ ở mức **min 30s – max 10 phút** với Exponential Backoff ($30s \rightarrow 60s \rightarrow 480s \rightarrow 600s$).
  - Không cần ép cứng cooldown 1h cho ChatGPT Web vì với **94 accounts chạy Round-Robin**, chu kỳ tự nhiên quay lại 1 nick là $94 \times 30s \approx 47$ phút, tự động tạo khoảng nghỉ an toàn mà không làm nghẽn router.

### C. Nghẽn Event Loop do Fan-Out & Background Loopback
- **Fan-Out quá lớn:** Combo `omni-worker` nhồi tới 265 target (do lồng cả 2 pool free khổng lồ). Mỗi request duyệt qua 265 target đọc SQLite đồng bộ ➔ Event loop bị block hoàn toàn.
- **Tự sát Loopback:** Mỗi lần khởi động, background task tự động kiểm tra credential cho 340 connections bằng cách tự gửi HTTP request vào chính nó qua loopback ➔ Vòng lặp tự làm nghẽn và chết.
- **Xử lý:**
  1. Thu gọn combo `omni-worker` chỉ còn 2 tiers sạch: **Gemini Pro ➔ Sonnet** (giảm 99.2% fan-out).
  2. Bật cờ chặn tự sát loopback trong `server.env`:
     ```env
     APP_LOG_LEVEL=warn
     OMNIROUTE_DISABLE_BACKGROUND_SERVICES=true
     OMNIROUTE_DISABLE_CREDENTIAL_HEALTH_CHECK=true
     ```
  3. Cấu hình watchdog (`omniroute_watchdog.ps1`) chống ngộ sát:
     ```powershell
     $script:HttpClient.Timeout = [System.TimeSpan]::FromSeconds(15)
     $MaxDeadlockFailures = 12        # ~180s hung ceiling
     $CheckIntervalSec = 15
     ```
