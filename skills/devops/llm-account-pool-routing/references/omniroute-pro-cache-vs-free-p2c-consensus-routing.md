# OmniRoute Architecture: Pro Cache-Optimized vs Free P2C Routing Consensus

Tài liệu đúc kết từ cuộc đối chất và phản biện kiến trúc chuyên sâu giữa **Sol (GPT-5.6)** và **Claude Code CLI** trong việc thiết lập hạ tầng OmniRoute (:20129) điều phối 113 tài khoản Antigravity + 16 tài khoản ChatGPT Web cho Phone Farm 160 máy và Multi-Agent.

---

## 1. NGUYÊN NHÂN GỐC RỄ: THẢM HỌA 429 SAU 30S (SEMAPHORE CONGESTION)
- **Cơ chế lỗi:** Khi bật `disableSessionStickiness: false` với `stickyRoundRobinLimit` quá lớn (hoặc vô hạn), OmniRoute ghim chặt tất cả request của một session agent vào đúng 1 connection ID.
- **Điểm nghẽn phần cứng:** Mỗi connection Google Antigravity được bọc Semaphore `maxConcurrent = 2`.
- **Hệ quả:** Khi agent nã burst request hoặc nhiều worker cùng kích hoạt, 1 account (ví dụ `lamngocdiep...`) phải gánh toàn bộ, 18 request xếp hàng chờ trong queue mặc định 30 giây (`queueTimeoutMs = 30000`). Sau 30s nổ hàng loạt lỗi 429 Timeout, trong khi hàng chục tài khoản khác hoàn toàn rảnh rỗi!

---

## 2. TRANH BIỆN KỸ THUẬT: FILL-FIRST VS ROUND-ROBIN VS P2C

### A. Fill-First (Chạy 1 acc cho tới max request rồi mới đổi):
- **Cảm giác sai lầm:** Người dùng thường tưởng dùng 1 acc giống người thật hơn nên ít bị quét.
- **Thực tế rủi ro cực cao:**
  - Tạo ra **"Hot Account"**: 1 account bị nã spike lưu lượng bất thường, đốt 100% quota trong thời gian ngắn $\rightarrow$ Google Anomaly Detection gắn cờ ngay.
  - **Cascade Death (Chết chùm):** Con 1 chết $\rightarrow$ 100% tải dội sang con 2 $\rightarrow$ con 2 sốc tải chết $\rightarrow$ lan truyền làm sụp cả dàn acc trong 1 buổi.
  - **Dormant Reactivation:** Các acc phụ nằm im quá lâu rồi bất ngờ bị nã tải lớn $\rightarrow$ dính cờ tài khoản ngủ bị kích hoạt bất thường.

### B. Round-Robin thuần túy (Mỗi turn nhảy 1 acc):
- Quá máy móc ($1 \rightarrow 2 \rightarrow 3 \rightarrow 4...$), hệ thống ML của provider dễ nhận diện pattern định kỳ của bot farm.
- Phá nát 100% Prompt Cache của LLM vì mỗi turn nhảy sang một tài khoản mới.

### C. P2C (Power of Two Choices) — Chiến thắng áp đảo cho Free:
- Cơ chế: Mỗi request đến, router bốc **ngẫu nhiên 2 acc**, so sánh độ tải hiện tại và chọn acc nhẹ hơn/rảnh hơn.
- Không có chu kỳ máy móc (xóa bỏ bot fingerprint).
- Tự động né các account đang bận hoặc latency cao.
- Phân phối tải gần như đồng đều tự nhiên, bảo vệ tuổi thọ đàn account cao nhất.

---

## 3. ĐỐI CHẤT NẢY LỬA: SOL (GPT-5.6) VS CLAUDE CODE CLI

### 🥊 Điểm bắt lỗi của Claude:
- Claude chỉ ra: Đề xuất `stickyRoundRobinLimit = 200` của Sol là **critical bug**. Với `maxConcurrent = 2`, 200 requests dồn vào 1 acc chắc chắn gây 429.
- Claude đòi: `sticky = 4` và **Zero-Queueing (`queueDepth = 0`, `queueTimeoutMs = 0`)** — bận là đá sang acc khác ngay lập tức, "không bao giờ hy sinh Availability để đổi Cache Hit".

### 🥊 Phản biện của Sol:
- Sol thừa nhận rút bỏ con số 200. Nhưng phản bác tính cực đoan của Claude:
  - AI Agent không phải stateless web traffic. Các request của agent (`patch -> test -> fix`) chỉ cách nhau vài trăm ms.
  - Nếu `queueDepth = 0`, chỉ vì acc đang xử lý dở 300ms mà đá văng sang acc khác sẽ **mất sạch 100% Prompt Cache**, khiến agent phải nạp lại 50k-100k tokens từ đầu, làm tăng latency thêm 2-5s (tệ hơn nhiều so với việc chờ 500-750ms).
  - Sol đề xuất: **Micro-Queue (`queueDepth = 1`, `queueTimeoutMs = 1000ms`)** và **`sticky = 8`**.

### 🤝 Điểm đồng thuận cuối cùng:
Claude CLI hoàn toàn nhất trí với giải pháp Micro-Queue của Sol. Chốt con số vàng cho Pro:
- **`stickyRoundRobinLimit = 8`**: Đủ cho 1 session agent chạy trọn vẹn task ăn Cache sâu, nhưng không đủ lớn để gây nghẽn.
- **`queueDepth = 1`, `queueTimeoutMs = 1000`**: Cho phép chờ tối đa 1s để hấp thụ burst ngắn. Quá 1s là lập tức failover.

---

## 4. BẢNG CẤU HÌNH CHUẨN PRODUCTION CHO TỪNG POOL

| Combo Name | Model chính | Số Acc | Phân loại Acc | Strategy | Sticky | Queue Depth / Timeout | failoverBeforeRetry |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| **`ag-gemini-pool-3`** | `gemini-3.8-flash-tiered` | 16 | **Chỉ Pro** (Tách riêng) | `cache-optimized` | 8 | Depth=1, Timeout=1000ms | **true** |
| **`ag-gemini-free-pool`** | `gemini-3.8-flash-tiered` | 97 | **Chỉ Free** (Tách riêng) | `p2c` | 0 | Depth=0, Timeout=1000ms | **true** |
| **`ag-claude`** | `claude-sonnet-4-6` | 113 | **Gộp chung (Pro + Free)** | `p2c` | 0 | Depth=0, Timeout=1000ms | **true** |
| **`ag-opus`** | `claude-opus-4-6-thinking` | 113 | **Gộp chung (Pro + Free)** | `p2c` | 0 | Depth=0, Timeout=1000ms | **true** |
| **`chatgpt-web-pool`** | `gpt-5.6-sol-high` | 16 | Free Web (GPM) | `p2c` | 0 | Depth=0, Timeout=1000ms | **true** |
| **`omni-worker`** | Combo Tổng | - | Tier 1 Pro $\rightarrow$ Tier 2 Free $\rightarrow$ Tier 3 Claude | `priority` | 1 | Depth=0, Timeout=1000ms | **true** |

### Quy tắc bất biến:
1. **Gemini:** BẮT BUỘC tách riêng 2 combo: 16 Pro (Cache-Optimized) và 97 Free (P2C). Tuyệt đối không gộp chung Gemini vào 1 Flat Combo vì sẽ làm loãng Prompt Cache của dàn Pro.
2. **Claude (Sonnet & Opus):** Gộp chung TOÀN BỘ 113 tài khoản Antigravity (cả Pro lẫn Free) vào chung 1 pool chạy P2C.
3. **Mọi pool Free / Số lượng lớn:** Bắt buộc tuân thủ `p2c + sticky=0 + disableSessionStickiness=true + queueDepth=0 + failoverBeforeRetry=true`.
