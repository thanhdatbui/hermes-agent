# OmniRoute Incident Runbook: Global Cooldown Trap, Zombie Proxy & Event Loop Choke (07/10/2026)

## Bối cảnh sự cố
Hệ thống OmniRoute (:20129) gặp chuỗi lỗi liên hoàn nghiêm trọng:
1. Combo `omni-worker` trả HTTP 503 liên tục (`ALL_TARGETS_SKIPPED` / `All models failed`).
2. OmniRoute bị "treo" (health check `/api/health` timeout liên tục 4 lần), watchdog buộc phải kill và restart nhiều lần trong buổi sáng.
3. Nguyên nhân ban đầu bị chẩn đoán nhầm thành "DB phình to" hoặc "log flood".

---

## 1. Cạm bẫy Global `providerCooldown` vs Nhu cầu Cooldown từng Provider
- **Nguyên nhân gốc rễ**:
  - Khi vận hành cụm ChatGPT Web (94 acc), do OpenAI Web có chu kỳ rolling rate-limit 1–3 tiếng, operator đã cấu hình `providerCooldown`:
    `minRetryCooldownMs: 3600000` (1 giờ), `maxRetryCooldownMs: 10800000` (3 giờ).
  - **LỖ HỔNG LỚN**: `providerCooldown` trong OmniRoute là biến **GLOBAL** dùng chung cho tất cả các provider (bao gồm Antigravity Google, Claude, OpenRouter, v.v.).
  - Khi một vài cổng proxy của Antigravity gặp sự cố mạng hoặc trả 503, cơ chế cooldown toàn cục bị kích hoạt và áp mức phạt tối thiểu 1 giờ lên **toàn bộ provider `antigravity`** hoặc các account bị gán.
  - Hậu quả: Dù các tài khoản Google Gemini Pro còn nguyên quota tuần, bộ lọc tiền điều phối (pre-dispatch filter) vẫn đánh dấu `Skipping antigravity — provider in global cooldown`, dẫn tới 503 hàng loạt.
- **Giải pháp & Khắc phục**:
  - Đặt `providerCooldown` toàn cục ở mức an toàn: `minRetryCooldownMs: 30000` (30 giây) và `maxRetryCooldownMs: 600000` (10 phút).
  - Không được dùng `providerCooldown` toàn cục để giải quyết rate-limit dài hạn của một provider đơn lẻ (như ChatGPT Web).
  - Cooldown dài cho ChatGPT Web phải được xử lý ở tầng quy tắc lỗi cấp provider (`providerErrorRules` hoặc kiểm tra điều kiện `provider === 'chatgpt-web'`) thay vì bóp nghẹt toàn hệ thống.

---

## 2. Bẫy Zombie Proxy (Port TCP mở nhưng Tunnel chết) & Fallback Pool
- **Cơ chế hoạt động của Fallback Pool**:
  - Khi một account có proxy riêng bị unreachable, hàm `resolveProviderPoolFallbackProxy(provider, connectionId)` sẽ lấy danh sách proxy thuộc `scope='provider'`, kiểm tra các proxy còn sống (`reachable`), sau đó dùng băm `hashConnectionId(connectionId) % reachable.length` để phân bổ đều tải.
- **Điểm mù của `isProxyReachable`**:
  - Hàm `isProxyReachable` trong `src/lib/proxyHealth.ts` chỉ thực hiện kiểm tra `tcpCheckImpl(host, port)` (bắt tay TCP SYN tới IP:Port).
  - Một proxy có cổng TCP mở trên máy chủ nhưng đường truyền upstream ra ngoài Internet/Google bị đứt (ví dụ: `khoalee.duckdns.org:16001`) vẫn được đánh giá là `healthy: true`.
  - Kết quả: Account nào băm trúng vị trí của zombie proxy này đều bị điều hướng vào hố đen tử thần, trả về `504 Gateway Timeout` (ngâm 30s) hoặc `503`, kích hoạt tiếp vòng lặp cooldown giả.
- **Quy trình xử lý Zombie Proxy**:
  1. Xác định proxy chết bằng kiểm tra tunnel HTTP thực tế (`urllib.request.ProxyHandler` hoặc curl qua proxy ra Google).
  2. Xóa toàn bộ liên kết của proxy đó trong bảng `proxy_assignments` (`DELETE FROM proxy_assignments WHERE proxy_id = ?`).
  3. Cập nhật trạng thái proxy trong `proxy_registry`: `UPDATE proxy_registry SET status = 'dead' WHERE id = ?`. Trạng thái này đảm bảo mệnh đề `PROXY_ALIVE_PREDICATE` loại bỏ proxy đó vĩnh viễn khỏi danh sách ứng viên fallback.

---

## 3. Nghẽn Event Loop do Fan-out Quá Tải & Vòng lặp Loopback Khởi động
- **Triệu chứng**:
  - Watchdog ghi nhận `/api/health` timeout liên tiếp, tiến trình Node.js không crash nhưng không phản hồi, watchdog buộc phải kill sau 4 lần thất bại.
- **Hai thủ phạm gây nghẽn Event Loop**:
  1. **Fan-out quá lớn của combo**: Combo `omni-worker` chứa tới 265 target (do lồng cả các pool Gemini free lớn). Khi gặp lỗi, mỗi request duyệt và truy vấn SQLite đồng bộ hàng trăm lần; khi client retry dồn dập, Event Loop bị kẹt hoàn toàn.
  2. **Tác vụ nền tự sát sau khi boot**: Ngay khi khởi động, OmniRoute tự động kích hoạt đồng bộ model catalog và kiểm tra credential health cho hơn 340 connection bằng cách gọi loopback chính nó. Vừa khởi động xong chưa kịp phục vụ thì tài nguyên đã bị chiếm trọn bởi tác vụ nền, gây timeout health check -> Watchdog kill -> Khởi động lại -> Lặp vô tận.
- **Giải pháp dập tắt**:
  - Thu gọn `omni-worker`: Bỏ các pool free cồng kềnh, chỉ giữ lại chuỗi tinh gọn **Gemini Pro -> Sonnet**.
  - Cấu hình trong `server.env`:
    ```ini
    APP_LOG_LEVEL=warn
    OMNIROUTE_DISABLE_BACKGROUND_SERVICES=true
    OMNIROUTE_DISABLE_CREDENTIAL_HEALTH_CHECK=true
    ```
  - Dọn dẹp các bảng phình to trong DB: Định kỳ dọn `quota_snapshots` và `call_logs` để giữ file WAL ở mức thấp (< 50MB).
