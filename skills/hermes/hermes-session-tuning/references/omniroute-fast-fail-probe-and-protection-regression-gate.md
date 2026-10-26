# OmniRoute Proxy Fast-Fail 2s Jitter Trap, SQLite Bloat & Protection Regression Gate (27/10/2026)

## 1. Triệu Chứng Hiện Trường & Ảo Giác "Proxy Chết"
- OmniRoute (`:20129`) liên tục sập, trả lỗi `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` hơn 130 lần trong ngày.
- Telegram của bot văng lỗi hàng loạt trên hơn 10 session: `⚠️ The model provider failed after retries`.
- Kiểm tra thủ công bên ngoài: Toàn bộ 18 cổng proxy mobile `test.taadaa.click:5101..5136` đều online 100%, ping cực thấp (36ms – 62ms), IP xoay sạch.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause - 3 Tầng Cộng Hưởng)

### Tầng 1: Mạng Viettel chập chờn (Flapping >120 lần/ngày)
- Tuyến cáp Viettel chập chờn liên tục từ sáng đến tối, khiến kết nối từ máy chủ tới cụm proxy mobile bị vấp gói tin (micro-jitter) từng đợt ngắn 1–2 giây.

### Tầng 2: Thuật toán "Proxy Fast-Fail" của OmniRoute quá nhạy cảm (Bẫy Probe 2 giây)
- Trong `src/lib/proxyHealth.ts`: `FAST_FAIL_TIMEOUT_MS` mặc định là `2000` (2s).
- Trong `open-sse/utils/proxyFetch.ts`: Cơ chế so găng song song `Promise.race([unreachableProbe, requestPromise])`:
  - Request LLM gửi context lớn (100k–400k tokens) mất 15s–45s để hoàn thành.
  - Luồng probe TCP ngầm chạy song song với timeout 2.0s. Khi mạng Viettel lag trễ 2.1s, probe kết luận proxy chết (`[Proxy Fast-Fail] Proxy unreachable`).
  - **Hậu quả:** OmniRoute tự tay hủy ngang (`requestPromise.catch(() => {})`) request LLM đang xử lý bình thường.
  - Do cả 28 account Antigravity đều dùng chung cụm proxy `51xx`, router lần lượt gạt bỏ sạch toàn bộ account chỉ trong 5s $\rightarrow$ Văng lỗi `503 all targets were skipped`.

### Tầng 3: SQLite phình 1.15 GB (> 1.14 triệu dòng) gây Deadlock Event Loop
- Hàng loạt stream bị hủy đột ngột làm rách socket (`ECONNRESET`), giải phóng bộ nhớ dồn dập.
- Cùng lúc, `storage.sqlite` phình lên 1.15 GB do tích tụ:
  - `conversation_turn_nodes`: 1.066.502 dòng.
  - `quota_snapshots`: 418.577 dòng.
  - `xp_audit_log`: 188.807 dòng.
  - `call_logs` & `proxy_logs`: > 180.000 dòng.
- Thao tác SQLite đồng bộ trên Main Event Loop bị I/O lock 40s–60s $\rightarrow$ `/api/health` không phản hồi $\rightarrow$ Watchdog đếm đủ 12 lần fail (6 phút) và force-kill tiến trình Node.js.
- Khi restart, thiếu độ trễ giải phóng socket `TIME_WAIT` khiến Node.js văng `exit code 1` sau 3s, kéo dài thời gian chết lên 111s.

---

## 3. Phân Định Rõ Ràng: Regression Gate vs Protection Regression Gate

Người dùng đặc biệt lưu ý và chấn chỉnh sự nhầm lẫn giữa hai khái niệm:

1. **Regression Gate (Kiểm thử chức năng hồi quy - Functional Testing):**
   - Chạy test suite `pytest tests/test_*.py` để đảm bảo code logic, hàm, luồng xử lý không bị lỗi so với trước.
   - Thất bại $\rightarrow$ Sửa code hoặc cập nhật test cho đúng spec mới.
2. **Protection Regression Gate (Cổng bảo vệ bất biến cơ học - Mechanical Safety Gate / Vòng Kim Cô):**
   - Giám sát và cưỡng chế các **Luật Bất Biến (Safety Invariants)** được rút ra từ các sự cố nghiêm trọng trong quá khứ.
   - CẤM TUYỆT ĐỐI agent hoặc con người sửa lùi (regress) vào các thông số sống còn vì mục đích tiện lợi nhất thời.
   - Cơ chế: Chốt chặn cơ học (`Deterministic Mechanical Clamp`), vi phạm là đạp phanh ngay lập tức (Exit code != 0, từ chối commit/ghi file).

---

## 4. Bảng Bất Biến Hạ Tầng Được Khóa Cứng Vào `infra_regression_gate.py`

| Mục tiêu | Thông số | Ngưỡng Invariant bắt buộc | Nguy cơ nếu vi phạm (Incident) |
| :--- | :--- | :--- | :--- |
| **Hermes** | `compression.threshold` | `[0.28, 0.35]` (Chuẩn `0.30`) | < 0.28: Nén liên tục từ 14.4k tokens (03/10). > 0.35: Vượt trần 372k của GPT worker. |
| **Hermes** | `agent.api_max_retries` | `[3, 4]` (Chuẩn `4`) | > 4: Gây bão tải Thundering Herd Retry Storm khi dính 503 Heap Pressure (02/10). < 3: Cháy retry trước khi port 20129 kịp mở (26/10). |
| **Hermes** | `agent.api_retry_delay` | `[5.0, 12.0]` (Chuẩn `6.0s`) | < 5.0s: Đốt sạch retry trong 15s trước khi OmniRoute restart xong. |
| **Hermes** | `Total Headroom` | `[70s, 130s]` (Chuẩn `~90s-100s`) | Đảm bảo Hermes kiên nhẫn đợi OmniRoute restart (25-35s) mà không ngắt turn. |
| **Hermes** | `fallback_providers` | Cấm chứa cổng `20129` | Fallback vào chính mình khi sập gây lỗi kép và nhân đôi thời gian treo. |
| **OmniRoute**| `PROXY_FAIL_OPEN` | Bắt buộc `false` | Bật `true` làm rò rỉ IP dân cư nhà Kibe lên upstream, gây ban tài khoản farm. |
| **OmniRoute**| `PROXY_FAST_FAIL_TIMEOUT_MS`| `[4000, 10000]` ms (Chuẩn `5000ms`)| < 4000ms: Probe 2s kill oan request LLM đang chạy bình thường khi mạng jitter (27/10). |
| **OmniRoute**| `$MaxDeadlockFailures` | `[4, 6]` (Chuẩn `4` ~ 120s) | < 4: Bắn nhầm prompt nặng 300k+ tokens đang prefill, khóa Anti-Flapping 15 phút (05/10). |
| **OmniRoute**| Socket TIME_WAIT Delay | `Start-Sleep -Seconds 3` | Thiếu delay gây đụng port khi restart, crash văng `exit code 1` sau 3 giây. |
| **SQLite** | `RETENTION_DAYS` | `<= 3` ngày | Để 7 ngày làm DB tích tụ > 1.2M rows (1.15GB), gây I/O lock và freeze Event Loop. |
| **SQLite** | `CLEANUP_TARGETS` | Đủ 6 bảng nặng | Phải bao trọn: `conversation_turn_nodes`, `agentic_conversations`, `quota_snapshots`, `xp_audit_log`, `proxy_logs`, `call_logs`. |
| **Cron** | `daily-omniroute-db-cleanup`| `every 6h` | Dọn dẹp cuốn chiếu 4 lần/ngày, mỗi lần < 1s, triệt tiêu hoàn toàn nguy cơ phình đĩa. |

---

## 5. Xác Minh Bằng Công Cụ Thực Tế
- Kiểm tra toàn bộ hạ tầng:
  ```bash
  python D:/Taadaa/tools/infra_regression_gate.py --json
  ```
- Chạy unit test kiểm chứng gate:
  ```bash
  pytest D:/Taadaa/tools/tests/test_infra_regression_gate.py
  ```
- Dọn dẹp thủ công và thu nhỏ SQLite:
  ```bash
  python D:/Taadaa/tools/cleanup_omniroute_db.py
  ```
