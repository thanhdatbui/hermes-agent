# Upstream Socket Hang 90s & 3-Layer Timeout Layering (2026-09-24 Incident)

## 1. Bản chất sự cố (Failure Amplification & Blocked Concurrency)
- **Hiện tượng**: Toàn bộ Hermes chat bị đơ ~4 phút, OmniRoute (:20129) không xử lý request nào dù CPU/RAM/Disk I/O của máy chủ hoàn toàn bình thường.
- **Root Cause**:
  1. Google Antigravity upstream bị đơ socket, không nhả byte đầu tiên.
  2. Hermes client có stale timeout mặc định là 90s (`HERMES_API_CALL_STALE_TIMEOUT=90.0s`).
  3. OmniRoute combo timeout cũng để 90s hoặc không cấu hình (fallback 120s).
  4. Đến đúng 90s, Hermes tự hủy socket (`HTTP 499 Request Aborted`) ngay trước khi OmniRoute kịp kích hoạt failover.
  5. 7 subagent chạy song song gửi 252 requests trong 5 phút. Khi nhiều requests bị ngâm 90s, toàn bộ concurrency slots bị chiếm giữ (Blocked Concurrency).
  6. Router không cách ly account lỗi, tiếp tục ném request mới vào các account vừa chết chùm (`jinrakal`, `duongkien`...), tạo vòng lặp nghẽn.

## 2. Mô hình Timeout 3 Tầng (3-Layer Timeout Model - Đồng thuận Claude CLI & Sol High)
CẤM TUYỆT ĐỐI cắt flat timeout 30s vì sẽ giết nhầm các request prompt lớn (150k tokens có thời gian prefill 8k/s mất ~18-20s, giờ cao điểm TTFB lên 30-40s).

Phải bóc tách 3 tầng theo vòng đời request:
1. `connect_timeout = 5s`: Bắt nhanh TCP handshake rớt mạng/đứt cáp.
2. `first_byte_timeout (STREAM_READINESS) = 40s`: Bắt socket upstream ngâm không nhả byte đầu tiên. (Đủ rộng cho 150k token, đủ ngắn để không nghéz concurrency).
3. `combo targetTimeoutMs = 45s`: Ngắt target model và failover sang Tier tiếp theo trong combo.
4. `inter_chunk_timeout = 15s`: Bắt stream đang chạy bị stall giữa chừng.

## 3. Quy tắc Toán học Headroom Buffer (Timeout Math)
Để triệt tiêu vĩnh viễn bẫy `Client 499 Abort`:
$$\text{STREAM\_READINESS (40s)} < \text{Combo targetTimeoutMs (45s)} \ll \text{Client Stale Timeout (120s)}$$

- $t = 0\text{s}$: Request vào OmniRoute.
- $t = 40\text{s}$: Upstream không nhả byte $\rightarrow$ Readiness timeout ngắt socket Google.
- $t = 45\text{s}$: Combo timeout kích hoạt $\rightarrow$ Failover sang Tier kế tiếp (`omni-worker` / `codex pool` / `ag-claude`).
- $t \approx 50-65\text{s}$: Tier tiếp theo trả lời thành công.
- $t = 120\text{s}$: Hermes Stale Timeout còn cách xa 55 giây $\rightarrow$ **0% nguy cơ dính HTTP 499**.

## 4. Vị trí cấu hình chuẩn
- `OmniRoute/.env`:
  ```env
  STREAM_READINESS_TIMEOUT_MS=40000
  FETCH_CONNECT_TIMEOUT_MS=5000
  ACCOUNT_SEMAPHORE_TIMEOUT_MS=45000
  ```
- `hermes/.env` (Hermes Agent Home):
  ```env
  HERMES_API_CALL_STALE_TIMEOUT=120
  ```
- Database `C:\Users\Kibe\.omniroute\storage.sqlite` (bảng `combos`):
  Cập nhật `data.config.targetTimeoutMs = 45000` cho các combos chính:
  `ag-gemini-pool-3`, `omni-worker`, `ag-gemini-free-pool`, `codex-luna-pool`, `codex-terra-pool`.
