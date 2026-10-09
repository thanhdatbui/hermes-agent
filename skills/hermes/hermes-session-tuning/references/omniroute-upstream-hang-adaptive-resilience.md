# OmniRoute Upstream Hang & Adaptive Resilience Architecture

## Bối cảnh sự cố (2026-09-24 Incident)
- **Hiện tượng**: User nhắn tin trên Telegram thấy bot im bặt 4 phút (13:51 đến 13:55). Bảng điều khiển OmniRoute (:20129) rơi vào khoảng lặng trống trơn 0 request.
- **Dữ liệu thực tế bóc tách từ SQLite (`storage.sqlite` bảng `call_logs`)**:
  - Từ 13:48:38 đến 13:51:16: Có 7 request liên tiếp vào provider `antigravity` (Google Gemini Pro/Flash) bị ngâm đúng trần timeout client **~90.00s** (89.9s – 90.5s) rồi trả về `[499] Request aborted`.
  - Các accounts bị timeout: `jinrakal@gmail.com`, `phungthibichngoc...`, `minhan2745...`, `dangmai3101...`, `toloan1209...`, `duongkien1202...`, `bobbyxruizz...`.
  - Đến 14:03 – 14:06, OmniRoute tiếp tục phân phối request mới vào chính các account này (`jinrakal`, `duongkien...`), dẫn đến thêm 4 lần timeout 90s tiếp theo.
  - Cùng lúc (13:45 – 13:50), có 7 subagents chạy song song dồn **252 requests** vào OmniRoute trong 5 phút.
  - Máy chủ: Ổ C: trống 127 GB, `Avg. Disk Queue Length` = 0.014 (không nghẽn I/O hệ điều hành).

---

## Biên bản Tranh biện Kiến trúc: Claude CLI vs GPT-5.6 Sol High

### 1. Bản chất sự cố: "Failure Amplification" & Bẫy Deadlock HTTP 499
- Không phải do thiếu CPU/RAM, không phải nghẽn đĩa hay sập Telegram Bot API.
- **Tử huyệt lệch trần Timeout giữa Client & Router**:
  1. *Hermes Client side (`run_agent.py:1269–1301`)*: Có trần stale timeout ngầm định `90.0s` (`_resolved_api_call_stale_timeout_base`). Quá 90s không có byte nào trả về, httpx/OpenAI client tự động cancel socket.
  2. *OmniRoute Router side (`comboConfig.ts` & `storage.sqlite`)*: `ag-gemini-pool-3` cấu hình `targetTimeoutMs: 90000` (90s), còn `omni-worker` không set `targetTimeoutMs` (rơi về `DEFAULT_COMBO_TARGET_TIMEOUT_MS = 120_000` hoặc `FETCH_TIMEOUT_MS = 600_000`).
  3. *Hậu quả Deadlock (`open-sse/services/combo.ts:2066 & 3570`)*:
     Khi socket upstream Google bị treo, vì timeout của OmniRoute (90s–120s) lớn hơn hoặc bằng Hermes (90s), **Hermes luôn abort trước đúng vào giây thứ 90.0**.
     Khi nhận tín hiệu abort từ client, OmniRoute ghi nhận HTTP 499 và chạy code:
     `if (result.status === 499) { log.info("COMBO", "Client disconnected (499) during ... — stopping combo loop"); }`
     $\rightarrow$ OmniRoute **DỪNG TOÀN BỘ VÒNG LẶP COMBO NGAY LẬP TỨC**, tuyệt đối không chuyển sang Tier 2 (Gemini Free), Tier 3 (Claude) hay Tier 4 (Luna).
     $\rightarrow$ OmniRoute coi 499 là "người dùng tự ngắt kết nối", nên **KHÔNG tính lỗi và KHÔNG áp dụng cooldown cho account bị treo**. Request kế tiếp từ subagent lại tiếp tục được chia vào chính account chết đó $\rightarrow$ ngâm tiếp 90s $\rightarrow$ tạo thành chuỗi treo domino 4 phút.
- **Giải pháp Cốt lõi: Tạo "Headroom Gap" giữa Router & Client**:
  - Hạ `targetTimeoutMs` trên toàn bộ combo (`omni-worker`, `ag-gemini-pool-3`...) xuống **45s** (`45000ms`).
  - Nâng `HERMES_API_CALL_STALE_TIMEOUT=120` (120s) trên Hermes `.env`.
  - Nhờ khoảng chênh lệch 45s vs 120s: OmniRoute `targetTimeoutRunner` sẽ timeout trước ở giây 45, sinh mã 504 `combo_target_timeout`, kích hoạt `checkFallbackError` nhảy tầng ngay sang Tier 2/3/4; trong khi đó Hermes ở giây 45 vẫn đang kiên nhẫn đợi và nhận được kết quả fallback ở giây 50 mà không bao giờ bị abort 499!

### 2. Phản biện của Claude CLI về Đề xuất "Flat Timeout 30s"
- **Rủi ro False-Kill**: Cắt flat timeout 30s là **nguy hiểm** cho workload của agent phone farm với prompt lớn (~150k tokens):
  - Network transit: 1–2s.
  - Prefill time: 150,000 tokens / 8,000 tok/s ≈ 18–20s.
  - Peak load queuing: 10–15s.
  - TTFB (Time to First Byte) hợp lệ trong giờ cao điểm có thể lên tới 30–40s.
- Nếu đặt flat timeout 30s, router sẽ giết nhầm các request 150k token hợp lệ đang prefill bình thường.
- **Giải pháp chuẩn hoá: Timeout 3 tầng theo vòng đời request**:
  - `connect_timeout = 5s`: Bắt lỗi đứt cáp / treo handshake TCP.
  - `first_byte_timeout (TTFB) = 45s`: Bắt trúng hiện tượng Google Antigravity treo ngâm socket không nhả byte đầu tiên mà không giết nhầm request 150k token.
  - `inter_chunk_timeout = 15s`: Bắt hiện tượng stream đang truyền thì đột ngột đứng hình (stall).

### 3. Phản biện về Circuit Breaker: Phân loại tín hiệu & Gradient Routing
- **Phân loại tín hiệu lỗi**:
  - `499 (Client timeout/abort)`: Tín hiệu về latency/congestion, không phải server chết hoàn toàn. Phạt giảm điểm uy tín nhẹ.
  - `503/504 / Connection Reset`: Tín hiệu sập server thật sự, phạt nặng gấp đôi.
- **Adaptive Weight Gradient Routing** (thay vì cắt nhị phân ON/OFF):
  - Trạng thái bình thường: `weight = 1.0`
  - Dính 1 lần timeout: `weight = 0.7` (giảm tải, ít ưu tiên hơn)
  - Dính 2 lần timeout: `weight = 0.3` (chỉ gọi khi thiếu account)
  - Dính 3 lần timeout: `weight = 0.0` (Mở Circuit Breaker — Cách ly)
- **Half-Open Recovery với Exponential Backoff**:
  - Thời gian cách ly ban đầu: 10 phút.
  - Hết 10 phút: cho 1 request probe thử nghiệm. Nếu thành công, phục hồi dần (0.3 $\rightarrow$ 0.7 $\rightarrow$ 1.0). Nếu thất bại, nhân đôi thời gian phạt (20 phút $\rightarrow$ 40 phút).

### 4. Router-Level Saturation Guard (Blast Radius Containment)
- Ngăn ngừa tình trạng 1 provider (như Google Antigravity) làm sập toàn bộ các luồng khác:
  $$\text{Nếu } \text{Slot\_Usage(Provider)} > 90\% \quad \text{và kéo dài } > 30\text{s}$$
  $\rightarrow$ **Đóng cổng nhận request mới vào Provider đó**, tự động chuyển toàn bộ traffic sang **Tier 3 (Claude Sonnet) / Tier 4 (Codex Luna)** trong combo `omni-worker` ngay lập tức, không chờ từng account đơn lẻ timeout xong mới failover.

### 5. Bulkhead Isolation & Preemption
- Phân chia dung lượng worker cố định:
  - **65% Slots**: Dành riêng cho Interactive (Hermes Coordinator, tin nhắn User chat trực tiếp).
  - **30% Slots**: Dành cho Background (Subagents chạy test, batch jobs, sync).
  - **5% Slots**: Dành riêng cho Health Probe / Watchdog.
- **Interactive Preemption**: Khi hàng đợi quá tải, request từ User/Coordinator có quyền ưu tiên ngắt hoặc hoãn request từ Background Subagents.

---

## Kế hoạch hành động thống nhất (Unified Plan)

| Phase | Nhiệm vụ | Mức độ | Mục tiêu |
|---|---|---|---|
| **Phase 1** | **Timeout 3 tầng** (`connect: 5s`, `TTFB: 45s`, `inter_chunk: 15s`) | **P0** | Triệt tiêu vĩnh viễn việc ngâm socket 90s, an toàn với prompt 150k token |
| **Phase 2** | **Adaptive Circuit Breaker & Weight Gradient** | **P0** | Không bơm request vào account đang lỗi; phục hồi qua Half-Open probe |
| **Phase 3** | **Router-Level Saturation Guard** | **P0** | Tránh bão request từ 1 provider làm tê liệt cả hệ thống |
| **Phase 4** | **Bulkhead Isolation & Preemption** | **P1** | Đảm bảo chat của User không bao giờ bị nghẽn bởi dàn subagent ngầm |
| **Phase 5** | **Observability Upgrade** | **P1** | Giám sát TTFB p50/p95/p99, stream stall duration, slot occupancy heatmap |
| **Phase 6** | **Chaos Validation** | **P2** | Kiểm thử mô phỏng Google timeout 90s và tải 200 concurrent requests |

---

## Biên bản Nghiệm thu Triển khai P0 (Claude CLI Review - VERDICT: APPROVED)

Sau khi triển khai thực tế trên `C:/Users/Kibe/OmniRoute` và `C:/Users/Kibe/AppData/Local/hermes`:

### 1. Bảng giá trị đối soát thực địa:
- `DEFAULT_STREAM_READINESS_TIMEOUT_MS`: `45_000` ms (`runtimeTimeouts.ts`) và `40_000` ms (`OmniRoute/.env`).
- `DEFAULT_FETCH_CONNECT_TIMEOUT_MS`: `5_000` ms (`runtimeTimeouts.ts` & `.env`).
- `ACCOUNT_SEMAPHORE_TIMEOUT_MS`: `45_000` ms (`accountSemaphore.ts` & `.env`).
- `HERMES_API_CALL_STALE_TIMEOUT`: `120` s (`AppData/Local/hermes/.env`).
- `targetTimeoutMs`: `45000` ms cho cả 5 combos (`ag-gemini-pool-3`, `omni-worker`, `ag-gemini-free-pool`, `codex-luna-pool`, `codex-terra-pool` trong `storage.sqlite`).

### 2. Tinh chỉnh Đệm An toàn 5s Chống Race Condition (Claude CLI Recommendation):
- Đặt `STREAM_READINESS_TIMEOUT_MS = 40_000` (40s) và `targetTimeoutMs = 45_000` (45s).
- **Lợi ích**: Khi Google upstream bị treo, bộ đếm `STREAM_READINESS` ngắt kết nối trước ở giây thứ 40, sinh mã lỗi upstream rõ ràng (`ANTIGRAVITY_PRE_RESPONSE_TIMEOUT`) trước khi bộ đếm combo 45s kích hoạt, giúp tầng combo chuyển đổi fallback sạch sẽ và không tranh chấp tài nguyên.
- Đã khai báo tường minh `ACCOUNT_SEMAPHORE_TIMEOUT_MS=45000` vào file `.env` của OmniRoute để cấu hình ổn định lâu dài.
