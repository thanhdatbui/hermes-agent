# Semaphore Timeout vs Pre-Cascade Queue & Strategy Trade-offs (OmniRoute)

## 1. Bản chất phân biệt: Semaphore Timeout vs Upstream 429 vs Pre-Cascade Queue

### A. "429 Semaphore timeout after 30000ms" là lỗi nội bộ, KHÔNG PHẢI account die hay Google ban
- **Dấu hiệu nhận biết trong `call_logs`**:
  - Mã HTTP: `429`
  - Duration: Kéo dài xấp xỉ `30.5s - 34.0s` (chính xác quanh mốc `30000ms`).
  - Error summary: `Semaphore timeout after 30000ms for <provider>:<connectionId>`.
- **Nguyên nhân**:
  - Mỗi connection có `max_concurrent` (mặc định = 2).
  - Khi 2 slot đồng thời của account đang bận, request mới dồn vào bị đẩy vào hàng đợi chờ slot nhả ra.
  - Nếu `queueTimeoutMs` chưa được cấu hình (mặc định `30000ms`), OmniRoute ngâm request đúng 30 giây.
  - Hết 30 giây chưa có slot nhả ra -> OmniRoute tự quăng ra lỗi `SEMAPHORE_TIMEOUT` (mã HTTP 429 nội bộ) trước khi request kịp chạm tới Google/OpenAI.
- **Quy tắc chẩn đoán O(1)**:
  - Thấy lỗi 429 kéo dài ~31s -> KHÔNG KẾT LUẬN account die hay Google bóp quota.
  - Phải kiểm tra log duration và test O(1) qua endpoint local (`http://127.0.0.1:20129/v1/chat/completions`) để xác nhận liveness thực tế.

### B. `queueDepth` (Combo) vs `accountSemaphore` (Connection)
- **`queueDepth` trong `comboConfig.ts`**:
  - Là hàng đợi **pre-cascade** ở cấp độ combo: quyết định số request được giữ lại chờ ở combo member trước khi cascade sang member/tier tiếp theo.
  - `queueDepth: 0` có nghĩa là: nếu member bão hòa thì không xếp hàng trước khi thử, chuyển ngay sang member khác.
- **`accountSemaphore` trong `accountSemaphore.ts`**:
  - Là hàng đợi **bên trong connection** đã được chọn.
  - Ngay cả khi `queueDepth: 0`, nếu request đã được dispatch vào một connection đang bận, connection đó vẫn có semaphore riêng với `queueTimeoutMs`.
  - Do đó, để triệt tiêu việc ngâm 30 giây: phải kết hợp cả `queueTimeoutMs` thấp (ví dụ 1000ms) VÀ cơ chế `tryAcquire` atomic spillover (commit `1c1634f0b`).

---

## 2. Head-of-Line Blocking trong Multi-Tier Router

### Mô hình tắc nghẽn cổ điển:
```text
Request -> omni-worker (priority)
             |
             +-> Tier 1: ag-gemini-pool-3 (16 Pro, round-robin, maxConcurrent=2)
             |     |
             |     +-> 4 acc Pro bận -> ngâm chờ 30 giây (queueTimeoutMs: null = 30s)
             |     +-> Sau 30s mới văng 429 Semaphore Timeout
             |
             +-> Tier 2: ag-gemini-free-pool (70 Free còn quota)
             |     +-> Bị "bắt cóc" 30 giây không được gánh tải!
             |
             +-> Tier 3: Codex Luna High (Chỉ nhảy sang khi Tier 1 & 2 đã timeout)
```

### Cách giải quyết đúng kiến trúc:
1. **Tier 1 (Pro Pool)**: Đặt `queueTimeoutMs: 1000` (hoặc `500-1000ms`), `failoverBeforeRetry: true`. Hễ đầy tải 2/2 slot thì trong vòng <= 1s phải nhả quyền điều khiển để tràn tải (spillover) sang Tier 2 ngay, không được giữ hostage request.
2. **Tier 2 (Free Pool)**: 70 accounts đóng vai trò bể chứa đệm dung lượng lớn (Elastic Overflow Capacity), hấp thụ tải dồn khi Tier 1 đầy.

---

## 3. Đánh đổi chiến lược định tuyến (Strategy Trade-offs): Cache vs Tuổi thọ Acc

| Strategy | Giữ Prompt Cache / Session | Khả năng chia đều tải | Tuổi thọ Acc (Chống Bot/Burn) | Phù hợp cho cụm nào |
| :--- | :---: | :---: | :---: | :--- |
| **`cache-optimized`** | **Tốt nhất (100%)** | Trung bình (cần spillover khi bận) | Tốt khi gán proxy 1-1 | **Bắt buộc cho Pool Pro (16 acc)** |
| **`p2c` (Power of Two Choices)** | **Kém** (mỗi turn có thể nhảy acc khác) | **Tốt nhất** (tự né acc nóng/bận) | **Cao nhất** (dàn đều 70 acc) | **Bắt buộc cho Pool Free (70-97 acc)** |
| **`round-robin`** | Trung bình (phụ thuộc `sticky`) | Tốt (xoay tuần tự) | Tốt hơn fill-first | Thích hợp khi các acc có năng lực ngang nhau |
| **`fill-first`** | Tốt trên 1 acc đầu | Kém (dồn cục) | **Rất nguy hiểm** (dễ tạo Hot Account bị Google cắm cờ) | **CẤM DÙNG TRÊN FARM** |

### Bài học cốt lõi:
- **KHÔNG BAO GIỜ đổi Pro Pool sang P2C toàn phần**:
  - Pro có giá trị cốt lõi là **Prompt Cache Hit và Context Continuity**.
  - Đổi Pro sang P2C với `disablePromptCacheAffinity: true` sẽ phá vỡ toàn bộ bộ nhớ đệm KV/Prompt Cache, làm tăng latency và chi phí xử lý token.
- **Nguyên tắc phân tầng**:
  - **Tier 1 (Pro)**: Giữ `cache-optimized` hoặc `round-robin` có session stickiness + `failoverBeforeRetry: true` + timeout ngắn (1s).
  - **Tier 2 (Free)**: Dùng `p2c` không cần stickiness để tối đa hóa chia tải và kéo dài tuổi thọ acc.

---

## 4. Kỷ luật An toàn Farm: INV-5 Invariant (Chống Probe Trực tiếp từ Host)

- **Sự cố thực tế**: Coordinator tự ý viết script Python chạy ngầm giải mã token từ SQLite rồi bắn request kiểm tra hàng loạt tài khoản lên `daily-cloudcode-pa.googleapis.com` từ IP máy host (Direct connection).
- **Rủi ro**: Làm lộ dấu vết dính chùm cả dàn farm lên máy chủ Google, có nguy cơ dính delayed ban wave hoặc bị revoke quyền OAuth Cloud Code.
- **Kỷ luật bất biến INV-5**:
  - Coordinator **TUYỆT ĐỐI CẤM TỰ Ý** viết script probe, test sức khỏe hay bắn request trực tiếp lên các máy chủ bên ngoài (Google, OpenAI...) từ IP máy host khi chưa có lệnh chỉ định rõ ràng từ User.
  - Mọi chẩn đoán định tuyến/health-check **BẮT BUỘC** gọi qua endpoint local nội bộ OmniRoute (`http://127.0.0.1:20129/v1/chat/completions`).
  - Mọi request ra ngoài từ worker/cronjob phải đảm bảo 100% Zero-Direct Policy (bọc Proxy 1-1 tương ứng).
