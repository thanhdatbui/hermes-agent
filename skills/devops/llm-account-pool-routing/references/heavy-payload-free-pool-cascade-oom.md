# Heavy Payload Spillover into Large Free Pool & Cooldown Lockout Cascade (OmniRoute)

## 1. Bối Cảnh Sự Cố Thực Tế (04/10/2026)
Hệ thống OmniRoute cổng `:20129` bị crash liên tiếp (V8 Heap Out-Of-Memory / Event Loop freeze) làm gián đoạn toàn bộ request từ bot Telegram Hermes:
- **Tải đầu vào cực nặng**: Bot Hermes tích lũy context lớn và gửi liên tiếp các request nặng: 372 msgs, 474 msgs, 482 msgs, và đỉnh điểm là **694 msgs** (~268.000 - 274.000 tokens).
- **Hiện tượng sập**: Node.js crash thoát mã lỗi `0xC0000409` (tràn V8 heap) hoặc nghẽn Event Loop khiến watchdog không nhận được phản hồi `/api/health` trong thời gian dài.

---

## 2. Giải Phẫu Bệnh Học & Chuỗi Domino (Pathology Anatomy)

### A. Bẫy Cooldown Lockout Quá Dài (600s vs 120s) Kết Hợp Proxy Flake
1. **Nguyên nhân kích hoạt**: Một số port proxy gán riêng cho account (`test.taadaa.click:5113`, `5115`, `5135`) chập chờn mạng, trả về `[Proxy Fast-Fail] Proxy unreachable (HTTP 503)`.
2. **Bẫy cấu hình**:
   - Trong `settings.json`, tham số `modelLockout.baseCooldownMs` bị đặt ở mức **600.000ms (10 phút)** thay vì mức chuẩn **120.000ms (2 phút)**.
   - Khi dính lỗi 503, OmniRoute khóa model trên connection đó suốt 10 phút:
     ```text
     Model-only lockout for antigravity:gemini-3.8-flash-tiered — 503 server_error (connection stays active)
     ```
3. **Hiệu ứng Hard-Bound Pinning**:
   - Mọi target trong `ag-gemini-pool-3` (20 Pro accounts) có chỉ định `connectionId` đều kích hoạt `hardConnectionBinding = true`.
   - Router tuân thủ nghiêm ngặt quy tắc chống Sibling Hijacking:
     ```text
     antigravity | hard-bound connection <id> unavailable; refusing sibling selection
     ```
   - Khi nhiều proxy chập chờn cùng lúc + concurrency cap (5/5 slots) đầy, toàn bộ 20 tài khoản Pro bị khóa sạch trong vài phút. Tier 1 hoàn toàn cạn kiệt target hợp lệ.

### B. Mega-Payload Cascade vào Free Pool Khổng Lồ (79 accounts) gây V8 Heap OOM
1. **Cơ chế tràn tải (Cascade)**:
   - Khi Tier 1 Pro failover, router trượt xuống Tier 2: `ag-gemini-free-pool` (79 targets, strategy: `least-used`).
2. **Cơ chế ngốn RAM O(N) theo số target**:
   - Với request nhỏ (10-20 msgs), router duyệt qua hàng chục target không gây áp lực RAM đáng kể.
   - Nhưng với request khổng lồ (400-700 msgs, ~270k tokens), mỗi lần combo engine duyệt và chuẩn bị payload cho target tiếp theo, cấu trúc request/context được clone và xử lý trong RAM của Node.js.
   - Khi có 3-4 request nặng đồng thời duyệt tuần tự qua **79 accounts Free** (trong đó nhiều account cũng dính rate limit/proxy fail), bộ nhớ V8 heap bị thổi phồng đột biến vượt trần 8GB/16GB, dẫn tới crash OOM hoặc nghẽn Event Loop toàn bộ server.

---

## 3. Quy Tắc Khắc Phục Kiến Trúc Chuẩn (Architectural Safeguards)

### Quy Tắc 1: Khóa Trần Cooldown Lockout Ở Mức 120s
- Tuyệt đối không để `modelLockout.baseCooldownMs` vượt quá **120.000ms (2 phút)** cho các cụm router có proxy động:
  ```json
  "modelLockout": {
    "enabled": true,
    "baseCooldownMs": 120000,
    "maxCooldownMs": 300000,
    "maxBackoffSteps": 5,
    "useExponentialBackoff": true
  }
  ```
- **Lợi ích**: Khi proxy hoặc upstream chập chờn thoáng qua (glitch 5-10s), tài khoản Pro sẽ hồi phục sau 2 phút thay vì bị giam cầm 10 phút làm cạn kiệt cả dàn Pro.

### Quy Tắc 2: Giới Hạn Số Lần Thử Global (`maxGlobalAttempts`) Trên Cụm Pool Lớn
- Đối với các combo có số lượng target lớn (50-100 accounts như Free pool), **bắt buộc** cấu hình giới hạn số lần thử:
  ```json
  "config": {
    "maxGlobalAttempts": 8,
    "queueTimeoutMs": 1000,
    "failoverBeforeRetry": true
  }
  ```
- Không bao giờ cho phép router duyệt tuần tự qua toàn bộ 79 accounts khi hệ thống đang chịu tải nặng. Nếu 8 accounts liên tiếp thất bại, router phải trả về 503/failover ngay lập tức để bảo vệ tiến trình Node.js.

### Quy Tắc 3: Context Size Guard Cho Free Pool
- Request mang context siêu lớn (> 100k tokens hoặc > 200 messages) không được phép cascade xuống Free Tier pool. Free Tier chỉ phù hợp với các tác vụ nhỏ đến trung bình. Request lớn phải dừng lại ở Tier Pro hoặc chuyển sang model trả phí/direct API.

### Quy Tắc 4: Giám Sát Sức Khỏe Proxy Độc Lập
- Các cổng proxy của cụm `test.taadaa.click` (ports 5113, 5115, 5135...) phải được watchdog kiểm tra định kỳ ngoài-band (out-of-band health check).
- Tránh để lỗi proxy cục bộ biến thành sự cố sập toàn bộ router trung tâm.
