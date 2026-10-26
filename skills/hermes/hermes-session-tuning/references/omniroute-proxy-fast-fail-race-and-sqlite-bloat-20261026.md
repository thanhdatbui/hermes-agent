# Bẫy Proxy Fast-Fail 2s So Găng Hủy Request Oan & SQLite 1.06M Rows Deadlock (26/10/2026)

## 1. Hiện Tượng & Nghịch Lý Tại Hiện Trường
- **Nghịch lý:** Người dùng và hệ thống kiểm tra trực tiếp dải proxy di động (`test.taadaa.click:5101..5136`) thấy kết nối TCP cực nhanh (36ms – 62ms), curl IP Viettel/Mobi xoay sạch sẽ 100%, proxy không hề hỏng.
- **Thế nhưng trên OmniRoute (:20129):**
  - Cổng 20129 liên tục văng lỗi:
    `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:51xx`
  - Combo `omni-worker` lập tức gạt bỏ toàn bộ account Antigravity và trả về lỗi 503 hàng loạt:
    `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (hơn 130 lần trong ngày 26/10).
  - Tiến trình OmniRoute bị đơ cứng định kỳ (Event loop starvation), khiến Watchdog kích hoạt deadlock ceiling 12/12 force-restart liên tục.

---

## 2. Nguyên Nhân Gốc Rễ Đã Xác Minh (Mã Nguồn OmniRoute)

### A. Bẫy So Găng Promise.race Của Proxy Fast-Fail (`proxyFetch.ts:681`)
Trong `C:\Users\Kibe\OmniRoute\open-sse\utils\proxyFetch.ts`:
```typescript
const requestPromise = Promise.resolve().then(() => fn());
if (!unreachableProbe) return requestPromise;

const winner = await Promise.race([
  unreachableProbe.then((reachable) => ({ kind: "probe" as const, reachable })),
  requestPromise.then((value) => ({ kind: "request" as const, value })),
]);

if (winner.kind === "probe" && !winner.reachable) {
  requestPromise.catch(() => {});
  const err = new Error(`[Proxy Fast-Fail] Proxy unreachable: ${proxyLabel}`);
  err.code = "PROXY_UNREACHABLE";
  err.statusCode = 503;
  throw err;
}
```
1. **Lệch pha thời gian khổng lồ:**
   - Khi request gửi context lớn (100k – 405k tokens) sang Google Antigravity, thời gian chờ sinh stream kéo dài từ **15s đến 45s**.
   - Cùng lúc, luồng thăm dò nền `unreachableProbe` được kích hoạt với cấu hình mặc định trong `src/lib/proxyHealth.ts`:
     `const FAST_FAIL_TIMEOUT_MS = parseInt(process.env.PROXY_FAST_FAIL_TIMEOUT_MS ?? "2000", 10);`
2. **Cơ chế tự sát (Self-Cancellation):**
   - Mạng Viettel trong ngày chập chờn kỉ lục (>120 lần failover sang FPT Direct trong `gateway.log`), gây vấp gói tin ngắn 1–2 giây.
   - Thăm dò TCP kiểm tra cổng proxy bị trễ quá 2.0s $\rightarrow$ `unreachableProbe` kết luận `reachable: false`.
   - Do request LLM phải mất 15s–45s mới hoàn tất, luồng probe 2s **luôn luôn về đích trước (thắng `Promise.race`)**!
   - Kết quả: OmniRoute **chủ động hủy bỏ (abort oan)** request LLM đang chạy hoàn toàn bình thường trên proxy đó (`requestPromise.catch(() => {})`).

### B. Hiệu Ứng Domino Quét Sạch Pool 28 Account Antigravity
- Toàn bộ 28 account Antigravity đang active trong pool `ag-gemini-pool-3` đều dùng chung dải proxy `test.taadaa.click:51xx`.
- Khi proxy 5103 bị đánh giá nhầm là dead, OmniRoute nhảy sang account kế tiếp (dùng 5114, 5115, 5121...). Từng account đều bị luồng probe 2s bóp chết.
- Chỉ trong vòng 5 giây, toàn bộ 28 account bị loại sạch $\rightarrow$ `recordedAttempts === 0` $\rightarrow$ Router văng lỗi `503 all targets were skipped by pre-dispatch filters`.

### C. SQLite Bloat 1.15 GB & Deadlock Main Event Loop
- Các stream bị abort liên tục tạo ra hàng loạt ngoại lệ `ECONNRESET: read ECONNRESET` trong thư viện mạng `undici`.
- Kiểm tra `C:\Users\Kibe\.omniroute\storage.sqlite` phát hiện:
  - Bảng `conversation_turn_nodes`: **1.061.667 dòng (hơn 1 triệu records)** từ ngày 18/10.
  - Bảng `quota_snapshots`: **418.150 dòng**.
  - Dung lượng file DB đạt **1.15 GB**.
- Khi một lượng lớn request bị abort và router cố gắng ghi log/cleanup đồng bộ vào SQLite 1.15GB, Main Event Loop đơn luồng của Node.js bị **khóa cứng hoàn toàn (I/O wait lock)**.
- Endpoint `/api/health` không thể xử lý ping $\rightarrow$ Watchdog đếm đủ 12 chu kỳ fail (6 phút) và kích hoạt force-kill Node.js.

---

## 3. Biện Pháp Khắc Phục Triệt Để & Chuẩn Hóa

### 1. Nâng Timeout Probe & Cơ Chế Fail-Open Cho Proxy
Trong file cấu hình môi trường của OmniRoute (`server.env` hoặc process launcher):
- **Nâng trần kiểm tra TCP:** `PROXY_FAST_FAIL_TIMEOUT_MS=5000` (5 giây thay vì 2 giây để tránh false-fail khi mạng vấp gói).
- **Kích hoạt Fail-Open:** `PROXY_FAIL_OPEN=true` để khi probe nghi ngờ proxy lỗi, router chuyển sang direct egress thay vì tự tay giết request của người dùng.

### 2. Dọn Dẹp Cơ Sở Dữ Liệu SQLite Định Kỳ (Prune Script)
- Hai bảng `conversation_turn_nodes` và `quota_snapshots` chỉ phục vụ vẽ đồ thị và tracking lịch sử turn, không ảnh hưởng đến token/credentials.
- Chạy dọn dẹp các bản ghi cũ hơn 3 ngày:
  ```sql
  DELETE FROM conversation_turn_nodes WHERE last_seen_at < datetime('now', '-3 days');
  DELETE FROM quota_snapshots WHERE created_at < datetime('now', '-3 days');
  PRAGMA wal_checkpoint(TRUNCATE);
  ```
  Giảm dung lượng DB từ 1.15GB về dưới 300MB, loại bỏ hoàn toàn hiện tượng I/O lock event loop.

### 3. Đồng Bộ Với Protection Regression Gate
- Giữ nguyên cấu hình Hermes đã chuẩn hóa: `api_max_retries: 4`, `api_retry_delay: 6.0s` để Hermes có đủ 90s kiên nhẫn vượt qua bất kỳ đợt restart nào của OmniRoute mà không làm đứt turn Telegram.
