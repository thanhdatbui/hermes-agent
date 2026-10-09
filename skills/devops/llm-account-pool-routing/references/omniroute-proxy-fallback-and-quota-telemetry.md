# OmniRoute Proxy Fallback & Account Quota Telemetry Runbook

## 1. Cơ chế Proxy Fallback trong OmniRoute (`resolveProviderPoolFallbackProxy`)
Khi proxy được gán tĩnh theo account (`proxy_assignments`, scope `account`) bị chết (TCP unreachable / timeout / cúp điện):
- OmniRoute **không** rơi tự do ra mạng Direct (fail-closed giữ vững khi `PROXY_FAIL_OPEN=false`).
- OmniRoute tìm pool proxy sống của provider (`getAliveProxyPoolForScope('provider', provider)`).
- **Thuật toán gán Deterministic (Cố định, không ngẫu nhiên):**
  ```typescript
  const index = hashConnectionId(connectionId) % reachable.length;
  return reachable[index];
  ```
  `connectionId` là UUID cố định của account. Hàm băm `hashConnectionId` là pure function không có `Math.random()`. Do đó, nếu pool proxy fallback giữ nguyên danh sách port sống, mỗi account sẽ **luôn luôn ăn đúng 1 port fallback duy nhất**, tuyệt đối không bị xoay ngẫu nhiên đổi IP giữa các request.
- **Hệ quả thực tế:**
  1. Khi dải Mobi mất điện, các acc gán Mobi KHÔNG bị fail-closed ngay lập tức nếu provider pool còn dải proxy khác đang sống (như MikroTik `10001..10035`).
  2. Mỗi acc sẽ được map ĐỊNH DANH (deterministic) vào đúng 1 port MikroTik duy nhất dựa trên connection UUID, không bị tráo đổi random giữa các request.
  3. Traffic vẫn thông mạng và trả HTTP 200 bình thường dù domain/IP proxy gốc đang cúp điện.

## 2. Phân biệt Quota Card trên Dashboard UI vs Traffic Thực tế
- **Dashboard Card Quota UI:**
  Chỉ hiển thị các model nặng đo đếm quota cố định (ví dụ: `Claude Opus 4 6 Thinking`, `Claude Sonnet 4 6`, `Gemini 3.1 Pro High`).
  -> Nếu hệ thống đang gọi `gemini-3.8-flash-tiered`, các thanh quota trên UI của account vẫn sẽ báo **100% left** (nguyên vẹn). Cấm tuyệt đối nhìn thanh UI để kết luận account không nhận traffic.
- **Kiểm tra Traffic Thực tế (Source of Truth):**
  - Endpoint `/api/usage/history`: kiểm tra trường `byAccount` -> tìm `rawModel`, `requests`, `promptTokens`, `completionTokens`, và đặc biệt là `lastUsed`.
  - Endpoint `/api/providers`: kiểm tra `lastTested`, `updatedAt`, `tokenExpiresAt`, `testStatus`.

## 3. Chẩn đoán khi Account Pro ngưng nhận Request / Quota Full
Khi một account Pro không có request mới hoặc quota card báo full:
- **Bước 1: Check Token Expiration & Validation:**
  Kiểm tra `tokenExpiresAt` so với giờ hiện tại. Nếu token vẫn được refresh trong vòng 1h qua và `testStatus: active`, tài khoản **KHÔNG** bị Google checkpoint/validation. (Nếu bị checkpoint, Google sẽ từ chối refresh token ngay lập tức với lỗi `invalid_grant` / 401).
- **Bước 2: Check Round-robin Index & Proxy Health:**
  - Trong combo có 18+ accounts, sau khi một acc hoàn thành batch request của nó, con trỏ round-robin sẽ xoay sang các acc còn lại trước khi quay lại acc đó.
  - OmniRoute thực hiện TCP check qua `isProxyReachable(proxyUrl)`. Nếu proxy gán tĩnh của account bị chết (timeout 2s), account đó có thể bị round-robin bỏ qua hoặc trễ nhịp so với các account có proxy phản hồi tức thì.
- **Bước 3: Không dùng clarify hỏi ý kiến khi đang điều tra kỹ thuật:**
  Khi user yêu cầu điều tra account đang chạy qua đâu, phải query code, DB và socket TCP để trả lời dứt khoát kết quả thực tế, cấm phán đoán mò hoặc dùng clarify để hỏi ngược lại user khi chưa đưa ra số liệu.

## 4. OpenCode Bridge Cục Bộ (`opencode_bridge.py :20130`)
- **Nguyên nhân sập khi fallback:** Hermes client đặt timeout kết nối ngắn (15s). Nếu adapter chạy đơn luồng (single-thread) hoặc chờ CLI xử lý xong mới trả HTTP header, Hermes sẽ ngắt kết nối với lỗi `Connection error (ConnectTimeout)`.
- **Kỷ luật kiến trúc bắt buộc:**
  1. **`ThreadingHTTPServer`**: Xử lý đa luồng đồng thời cho nhiều tiến trình agent/cronjob song song.
  2. **Immediate SSE Flush (0.01s)**: Ngay khi nhận request `/v1/chat/completions` dạng stream, gửi ngay HTTP 200 và SSE chunk rỗng khởi tạo (`delta: {"role": "assistant"}`) để giữ kết nối với Hermes, sau đó mới stream dữ liệu từ CLI wrapper (`oc_farm.py`).
  3. **Lọc Model Free**: Chỉ expose đúng các model 100% Free (`muse-spark-1.3`, `nemotron-3-ultra`, `mimo-v2.6-flash`...) qua `/v1/models`, tránh làm context của Agent bị ô nhiễm bởi hàng trăm model trả phí.
