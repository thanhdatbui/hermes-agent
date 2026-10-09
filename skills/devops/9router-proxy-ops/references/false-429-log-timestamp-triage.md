# False 429 Triage & Hermes Log Timestamp Quirks

Khi người dùng báo "bị lỗi 429 hàng loạt ở log omniroute / agent":

## 1. Pitfall: Timestamp Milliseconds & Token Counts giả dạng HTTP 429
- Hermes log định dạng timestamp dạng ISO/comma-separated milliseconds: `YYYY-MM-DD HH:MM:SS,mmm` (ví dụ `09:48:26,429`). Khi grep thô `"429"`, chuỗi `,429` xuất hiện hàng loạt từ timestamp của bất kỳ log nào rơi vào millisecond thứ 429.
- Log usage Hermes: `total=144429`, `cache=255429/258495`, `in=42924` cũng chứa substring `429`.
- OmniRoute log có event định kỳ `[RATE-LIMIT] Evicting idle limiter: ... (inactive for 600s+)` — đây là memory cleanup routine cho idle limiter, **không phải lỗi 429 rate limit**.

## 2. Kiểm tra thực sự HTTP 429 trên OmniRoute (:20129)
- **Truy vấn Console buffer trực tiếp**:
  ```bash
  curl -s "http://127.0.0.1:20129/api/logs/console?limit=1000"
  ```
  Lọc theo:
  - `status_code == 429` hoặc `[429]` trong message.
  - `error_code == 'rate_limit_exceeded'` hoặc `'too_many_requests'`.
- **Phân biệt với High Latency do Context Bloat**:
  - Khi nhiều session chạy đồng thời với context lớn (>200k tokens), stream TTFT và latency tăng vọt (100s - 400s).
  - Client hoặc subagent có thể timeout (ví dụ terminal timeout 180s, hoặc gateway timeout), dễ bị hiểu nhầm là upstream rate limit hoặc bị nghẽn do 429.
