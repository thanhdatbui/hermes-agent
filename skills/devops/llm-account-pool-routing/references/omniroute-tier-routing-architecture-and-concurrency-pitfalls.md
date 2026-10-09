# OmniRoute Tier Routing Architecture & Concurrency Pitfalls (2026-09-20)

## 1. Sự Cố Concurrency Semaphore & Bẫy Session Stickiness Vô Hạn

### Hiện tượng
- Dashboard báo lỗi hàng loạt `429 Too Many Requests` (hoặc `0ms - 30000ms`, `TI:0 TO:0`).
- Thực tế tài khoản không bị Google rate-limit hay ban, mà là **nội bộ OmniRoute tự văng 429 sau 30s**:
  `Semaphore timeout after 30000ms for antigravity:<conn_id> (<email>)`
- Chỉ **1 tài khoản duy nhất** hứng trọn hàng chục request đồng thời trong khi hàng chục tài khoản khác trong cùng pool ngồi chơi 0% tải.
- Kéo theo cascade: Request rớt xuống các tầng sau (ví dụ `chatgpt-web`) và nổ tiếp lỗi `413 Payload Too Large` do context quá lớn.

### Nguyên nhân gốc rễ
1. **`disableSessionStickiness: false` (Session Stickiness mặc định):**
   Hàm `applySessionStickiness()` trong `open-sse/services/combo/sessionStickiness.ts` băm hash tin nhắn của conversation và **luôn ép tài khoản đã phục vụ lượt đầu lên vị trí index 0**.
2. **Khiếm khuyết của cơ chế unpin:**
   Code chỉ gỡ sticky khi tài khoản dính lỗi nặng từ Google (`BANNED`, `RATE_LIMITED`, `QUOTA_EXHAUSTED`). Code **hoàn toàn không nhận biết trạng thái kẹt concurrency semaphore nội bộ** (`maxConcurrent=2`).
3. **Bẫy `queueTimeoutMs=30000`:**
   Thời gian chờ hàng đợi mặc định 30s biến semaphore thành bãi đỗ xe chết. Agent gọi burst dồn dập khiến hàng đợi tràn và văng 429 timeout.

---

## 2. Phản Biện Kỹ Thuật: Claude Code CLI vs Sol (GPT-5.6)

### Tranh luận 1: Fill-First vs Round-Robin / P2C
- **Fill-First (vắt kiệt 1 acc rồi mới nhảy):** Tạo ra "Hot Account" với request velocity bất thường, kích hoạt Google Anomaly Detection; khi acc chết sẽ tạo hiệu ứng chết chùm (cascade death) đè chết các acc kế tiếp.
- **Round-Robin thuần túy (nhảy từng nhịp):** Quá máy móc, chia nhỏ request đều như bắp khiến fingerprint giống bot farm, đồng thời phá hủy hoàn toàn Prompt Cache.
- **P2C (Power of Two Choices):** Tối ưu nhất cho pool tài khoản lớn. Mỗi request bốc ngẫu nhiên 2 acc, so sánh tải/latency/lỗi rồi chọn con khỏe hơn. Phân phối ngẫu nhiên tự nhiên, không con nào quá nóng hay quá đói.

### Tranh luận 2: Bẫy `stickyRoundRobinLimit=200` vs Zero-Queueing
- **Sol từng đề xuất `sticky=200`:** Claude CLI phản biện chính xác đây là bug logic nghiêm trọng. Với `maxConcurrent=2`, 16 acc có 32 slots. Nếu sticky=200 thì 200 request đều dồn vào 1 acc, chỉ 2 slot chạy, 30 slot idle $\rightarrow$ tái tạo sự cố 429.
- **Claude từng đề xuất `queueDepth=0, queueTimeoutMs=0`:** Sol phản biện đây là tư duy cực đoan của stateless web traffic. AI Agent có các turn liên tiếp cách nhau vài trăm ms (patch $\rightarrow$ test $\rightarrow$ explain). Nếu cấm chờ 0ms thì chỉ vì acc bận 300ms mà đá văng sang acc khác sẽ mất sạch 100% Prompt Cache, tăng latency thêm 2-5s (tệ hơn là chờ vài trăm ms).
- **Đồng thuận cuối cùng:** Dùng **Micro-Queue (`queueDepth=1`, `queueTimeoutMs=750-1000ms`)** và **`sticky=8`** cho Pro Pool.

---

## 3. Kiến Trúc Phân Tầng Chuẩn (Golden Configuration)

### A. Pool Pro (16 Accs Antigravity - Gemini Pro)
- **Mục tiêu:** Tối ưu hóa Prompt Cache (>32k tokens), giữ context ổn định cho multi-turn agent.
- **Config:**
  - `strategy: 'cache-optimized'`
  - `stickyRoundRobinLimit: 8` (công thức an toàn: $\le 4 \times \text{maxConcurrent}$)
  - `disableSessionStickiness: false`
  - `failoverBeforeRetry: true` (bận hoặc lỗi là nhảy acc khác ngay)
  - `queueDepth: 1` (Micro-queue)
  - `queueTimeoutMs: 1000` (chỉ chờ tối đa 1s, quá 1s failover lập tức)
  - `maxRetries: 1`
  - `maxGlobalAttempts: 5`

### B. Pool Free (87 Accs Antigravity - Gemini Free) & Claude Sonnet Free (57 Accs)
- **Mục tiêu:** Tối đa hóa độ sống (survivability), rải đều tải như đàn ong (swarm), không cần giữ cache.
- **Config:**
  - `strategy: 'p2c'`
  - `stickyRoundRobinLimit: 0`
  - `disableSessionStickiness: true`
  - `failoverBeforeRetry: true`
  - `queueDepth: 0` (Zero queueing)
  - `queueTimeoutMs: 1000`
  - `maxRetries: 1`
  - `maxGlobalAttempts: 8`

### C. Combo Tổng (`omni-worker`)
- **Mục tiêu:** Điều phối tuần tự qua các tầng tài nguyên.
- **Config:**
  - `strategy: 'priority'`
  - `nestedComboMode: 'execute'`
  - Thứ tự các Tier:
    1. **Tier 1:** `ag-gemini-pool-3` (16 Pro - Cache-Optimized Sticky 8)
    2. **Tier 2:** `ag-gemini-free-pool` (87 Free - P2C Swarm)
    3. **Tier 3:** `ag-claude` (57 Free Claude Sonnet - P2C Swarm)
  - *Lưu ý:* Tuyệt đối không nhét `chatgpt-web` hay các model free rác vào giữa chuỗi fallback để tránh lỗi 413 Payload Too Large hoặc 401/403.
