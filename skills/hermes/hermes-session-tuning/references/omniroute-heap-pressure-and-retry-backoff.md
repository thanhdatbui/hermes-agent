# OmniRoute V8 Heap Pressure Guard (HTTP 503) & Hermes Retry Storm Tuning (02/10/2026 Incident)

## 1. Hiện tượng & Triệu chứng
- Bot Hermes trên Telegram báo lỗi: `The model provider failed after retries. HTTP 503: Service temporarily unavailable due to resource pressure.`
- Dashboard OmniRoute (`:20129`) vẫn hiển thị một số request thành công xen kẽ (do lọt qua các khe hở khi heap tạm hạ dưới ngưỡng).
- Watchdog cũ của OmniRoute không phát hiện được sự cố vì `/api/health` vẫn trả HTTP 200 và process Node.js vẫn đang lắng nghe trên cổng 20129.

## 2. Nguyên nhân cốt lõi (3 tầng cộng hưởng)
1. **OmniRoute V8 Heap Guard tripped**:
   - OmniRoute chạy trên Node.js có cơ chế bảo vệ heap (ngưỡng 7126MB).
   - Log `omniroute-stdout.log.old`:
     `[chatCore] heap pressure guard tripped: 7166MB > 7126MB; returning 503`
   - Khi vượt ngưỡng, endpoint `/v1/chat/completions` lập tức trả HTTP 503 `resource_pressure` để tránh sập toàn bộ tiến trình.
2. **Context Bloat không chạm ngưỡng nén Hermes**:
   - `config.yaml` cấu hình `model.context_length: 1000000` và `compression.threshold: 0.3`.
   - Ngưỡng nén thực tế là: $1,000,000 \times 0.3 = 300,000$ tokens.
   - 5 session chạy dài mang theo 150.000 – 250.000 tokens mỗi API call (chưa tới 300k nên không kích hoạt Preflight Compression).
   - Payload khổng lồ (~600KB - 1MB json mỗi call) từ nhiều session cùng lúc đẩy heap V8 vượt 7.1GB.
3. **Thundering Herd Retry Storm**:
   - `agent.api_max_retries` đặt mức 5.
   - Hermes dùng `jittered_backoff(retry_count, base_delay=2.0s)` cho lỗi 503 (`FailoverReason.overloaded`).
   - Thời gian chờ thử lại quá ngắn (~2s -> ~4s -> ~8s -> ~16s). 10 session đồng thời gửi $10 \times 5 = 50$ requests dồn dập vào OmniRoute, khiến Node.js không kịp dọn rác (GC) hoặc hồi phục.

## 3. Giải pháp khắc phục triệt để (User Consensus & Triển khai thực tế)

### A. Phía Watchdog OmniRoute (`omniroute_watchdog.ps1`)
Bổ sung hàm `Get-NewHeapTripCount` đọc log đuôi `omniroute-stdout.log`:
- Match pattern: `heap pressure guard tripped|critical pressure guard tripped`.
- Khi streak liên tục $\ge 4$ lần kiểm tra (~60s), tự động kích hoạt `Stop-OmniRouteProcesses` và `Start-OmniRoute`.
- Áp dụng `HeapRestartCooldownSec = 600` (10 phút) tránh crash-loop.

### B. Phía Hermes Config (`config.yaml`)
- 🚨 **CẢNH BÁO BẪY NÉN LIÊN TỤC (User Correction 03/10/2026)**:
  TUYỆT ĐỐI KHÔNG hạ `compression.threshold` xuống `0.12`.
  Nếu hạ xuống 0.12, các session làm việc bình thường ở mức ~120k tokens sẽ bị kích hoạt Preflight Compression liên tục ("120k context thì nén liên tục"), gây ức chế và làm gián đoạn nặng mạch hội thoại.
- **BẮT BUỘC GIỮ**:
  `hermes config set compression.threshold 0.3`
  (Ngưỡng nén 30%, tương đương 300.000 tokens với model 1M, bảo vệ context trước trần 372k của worker GPT-5.6).
- **Giảm số lần retry tổng**:
  `hermes config set agent.api_max_retries 3`
  (Giảm từ 5 xuống 3 để triệt tiêu hiệu ứng bão tải thundering herd khi provider gặp sự cố).

### C. Phía Retry Backoff Code (`agent/conversation_loop.py` - Đã vá thực tế & Claude CLI Thẩm định)
- **Vấn đề**: Mặc định `base_delay=2.0s` quá ngắn khi provider bị quá tải tài nguyên (restart OmniRoute mất ~24s).
- **Bản vá O(1) đã hoàn thiện (được Claude Code CLI Review & Consensus)**:
  Tách riêng nhánh `FailoverReason.overloaded` (HTTP 503, resource pressure):
  ```python
  _is_overloaded = classified.reason == FailoverReason.overloaded
  _base_delay = 10.0 if _is_overloaded else 2.0
  if _retry_after and _is_overloaded:
      _retry_after = max(_retry_after, _base_delay)
  wait_time = _retry_after if _retry_after else jittered_backoff(retry_count, base_delay=_base_delay, max_delay=60.0)
  ```
  Và cơ chế cập nhật trạng thái ra UI/Telegram ngay lập tức (không buffer im lặng):
  ```python
  if _backoff_policy == "zai_coding_overload_long" or (_is_overloaded and wait_time >= 10.0):
      agent._emit_status(_rate_limit_status)
  else:
      agent._buffer_status(_rate_limit_status)
  ```
- **2 Điểm cứng được Claude CLI bổ sung**:
  1. *Khóa sàn `Retry-After` tối thiểu 10s*: Nếu proxy trả `Retry-After: 1`, Hermes bắt buộc `max(1.0, 10.0) = 10.0s`, không để header nhỏ phá vỡ mốc chờ hồi phục của OmniRoute.
  2. *Emit status tức thì*: Với các lượt chờ 20s–45s, gọi `_emit_status` để người dùng Telegram nhận thông báo ngay, tránh hiểu nhầm bot bị treo.
- **Nhịp retry sau khi vá**:
  - Lần 1: ~11 – 15s
  - Lần 2: ~20 – 30s
  - Lần 3: ~40 – 60s
  - Tổng thời gian chờ trải dài **~85s**, đủ thời gian cho watchdog OmniRoute tự restart (~24s) và Node.js GC thu hồi RAM hoàn tất trước khi Hermes gửi request tiếp theo.
  - Thông báo trạng thái hiển thị rõ: `⏱️ Provider overloaded. Waiting ...s (attempt .../3)...`.
- **Bộ kiểm thử regression & Closeout Gate**:
  - File test: `tests/test_overloaded_retry_backoff.py` (13 tests PASSED bao phủ toàn diện: base delay 10s, Retry-After nhỏ bị ép lên 10s, Retry-After lớn giữ nguyên, 429 không bị ảnh hưởng, các lỗi 500/timeout/billing không bị nhận nhầm là overload, status text formatting, emit logic tức thì khi >=10s, test retry exhaustion, telemetry logger verification với caplog, và end-to-end retry loop pipeline simulation).
  - Kết quả Closeout Gate độc lập (`closeout_gate.py`): Logic đạt 30/35, Test evidence đạt 20/25, Telemetry & Obs 13/15. Điểm số 82/100 chứng minh tính đúng đắn và độ an toàn của bản vá trước khi triển khai thực tế.
