# Kiến Trúc Routing OmniRoute: Cache-Optimized vs P2C (Sol vs Claude Debate)

## 1. Bối Cảnh Sự Cố Thực Tế
- **Hiện tượng:** Các agent chạy task dài dính lỗi `429 Semaphore Timeout` sau 30 giây kẹt tại 1 tài khoản (`lamngocdiep...`), trong khi các tài khoản Pro khác trong pool ngồi chơi. Kèm theo lỗi `413 Payload Too Large` khi fallback sang `chatgpt-web` hoặc `401/403` khi sang `omni-free`.
- **Nguyên nhân cốt lõi:**
  1. `disableSessionStickiness: false` kết hợp với `stickyRoundRobinLimit` cao ghim cứng toàn bộ conversation vào 1 connection duy nhất (`maxConcurrent = 2`).
  2. `queueTimeoutMs: 30000` (mặc định 30s) và `queueDepth > 0` biến hàng đợi semaphore thành "bãi đỗ xe chết", khiến request bị treo 30s rồi nổ 429 timeout thay vì nhảy acc.
  3. Chuỗi fallback `omni-worker` chứa model rác (chatgpt-web payload nhỏ bị 413, omni-free lỗi auth).

---

## 2. Cuộc Tranh Luận Kỹ Thuật: Sol (GPT-5.6) vs Claude Code CLI

### A. Về Vấn Đề Ban/Flag Account: Fill-First vs Round-Robin vs P2C
- **Fill-First (Dùng kiệt 1 acc rồi mới chuyển):**
  - **RỦI RO CAO NHẤT:** Tạo ra "Hot Account" với request velocity bất thường, đốt 100% quota/ngày trong khi các acc khác 0%. Google Anomaly Detection gắn cờ ngay. Khi acc đó chết, 100% tải dội sang acc tiếp theo gây "Cascade Death" sụp đổ dây chuyền cả dàn.
- **Round-Robin Thuần Túy (Xoay cơ học từng lượt):**
  - Quá máy móc ($1 \rightarrow 2 \rightarrow 3 \rightarrow 4...$), tạo fingerprint bot định kỳ.
  - Phá vỡ 100% Prompt Cache (mỗi turn nhảy 1 acc khác nhau khiến model phải nạp lại 50k-100k tokens từ đầu).
- **P2C (Power of Two Choices - Chiến Thắng cho Free Pools):**
  - Bốc ngẫu nhiên 2 acc, chọn acc nhẹ tải hơn.
  - Phân phối ngẫu nhiên không cơ học, tự động né acc đang bận, không tạo hot target.

### B. Về Stickiness & Micro-Queue cho Pool Pro (16 Accs):
- **Claude CLI bắt lỗi Sol:**
  - Sol ban đầu đề xuất `sticky = 200` + `queueDepth = 3, timeout = 5000ms`.
  - Claude phản biện: Mỗi acc chỉ có `maxConcurrent = 2`. Nếu để sticky = 200, khi có burst requests từ nhiều agent, tất cả request đều bị ép vào 1 acc $\rightarrow$ tái hiện lỗi 429!
- **Sol phản pháo tính cực đoan của Claude:**
  - Claude đòi `queueDepth = 0, timeout = 0` (Zero-Queueing) và `sticky = 4`.
  - Sol chỉ ra: AI Agent là stateful workload (`patch -> test -> fix -> explain`). Các request chỉ cách nhau vài trăm ms. Nếu `queueDepth = 0`, chỉ vì acc đang bận 300ms mà đá văng sang acc khác sẽ mất sạch Prompt Cache, tăng latency thêm 2-5s.
  - Sol đề xuất **Micro-Queue**: `queueDepth = 1, queueTimeoutMs = 1000ms`.
- **Chốt Đồng Thuận Tuyệt Đối:**
  - `stickyRoundRobinLimit = 8`: Đủ cho 1 session agent chạy trọn vẹn task mà không gây nghẽn.
  - `queueDepth = 1, queueTimeoutMs = 1000ms`: Cho phép chờ tối đa 1s để giữ cache. Quá 1s là `failoverBeforeRetry = true` lập tức nhảy sang acc Pro khác.

---

## 3. Ma Trận Cấu Hình Chuẩn Cho Toàn Farm

| Cụm Tài Nguyên | Số Lượng Acc | Strategy | Stickiness | QueueDepth & Timeout | Failover |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ag-gemini-pool-3` (Pro)** | 16 Pro | `cache-optimized` | `sticky = 8`, `disableStickiness: false` | `queue = 1`, `timeout = 1000ms` | `failoverBeforeRetry: true` |
| **`ag-gemini-free-pool`** | 88 Free | `p2c` | `sticky = 0`, `disableStickiness: true` | `queue = 0`, `timeout = 1000ms` | `failoverBeforeRetry: true` |
| **`ag-claude` (Sonnet Free)** | 57 Free | `p2c` | `sticky = 0`, `disableStickiness: true` | `queue = 0`, `timeout = 1000ms` | `failoverBeforeRetry: true` |
| **`ag-opus` (Opus Thinking)** | 78 Free | `p2c` | `sticky = 0`, `disableStickiness: true` | `queue = 0`, `timeout = 1000ms` | `failoverBeforeRetry: true` |
| **`chatgpt-web-pool` (Sol Web)**| 16 Free | `p2c` | `sticky = 0`, `disableStickiness: true` | `queue = 0`, `timeout = 1000ms` | `failoverBeforeRetry: true` |
| **`omni-worker` (Combo Tổng)**| 3 Tiers | `priority` | Tier 1 Pro $\rightarrow$ Tier 2 Free $\rightarrow$ Tier 3 Claude | `nestedComboMode: 'execute'` | `failoverBeforeRetry: true` |

---

## 4. Kiểm Thử Nghiệm Thu (Smoke Test)
1. **Stress test đa luồng:** Chạy script 4 worker đồng thời gọi `omni-worker`. Đảm bảo 4/4 request đạt HTTP 200 trong 2-4 giây, không xuất hiện 429 hay 413.
2. **Kiểm tra Telemetry logs (`/api/usage/call-logs`):** Xác nhận các request phân phối đều qua nhiều account khác nhau trong pool, không còn hiện tượng ghim cứng vào 1 email duy nhất.
