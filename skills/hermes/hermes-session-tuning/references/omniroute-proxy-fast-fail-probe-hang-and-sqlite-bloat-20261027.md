# OmniRoute Proxy Fast-Fail Probe Race & SQLite 1.15GB Event Loop Lock (27/10/2026)

## 1. Triệu Chứng & Phân Tích Hiện Trường
- Cả ngày OmniRoute báo sập liên tục, trả về lỗi:
  `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (xảy ra hơn 130 lần trong ngày).
- Trong khi đó, người dùng kiểm tra proxy bên ngoài thì hoàn toàn bình thường (ping 50ms, curl IP xoay sạch sẽ).
- Đồng thời OmniRoute thỉnh thoảng bị treo cứng 6 phút khiến Watchdog chạm trần 12/12 và force-kill tiến trình.

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause - 3 Tầng Khóa)

### Tầng 1: Mạng Viettel Chập Chờn (Flapping >120 lần/ngày)
- Tuyến mạng Viettel bị packet drop và flap sang FPT Direct liên tục mỗi 2–5 phút.
- Tuyến kết nối từ Kibe PC ra cụm proxy `test.taadaa.click:51xx` đi qua đường truyền này nên bị vấp gói tin ngắn 1–2 giây.

### Tầng 2: Bẫy So Găng Fast-Fail Probe 2s (`Promise.race` trong `proxyFetch.ts`)
- Trong `open-sse/utils/proxyFetch.ts` và `src/lib/proxyHealth.ts`:
  - `FAST_FAIL_TIMEOUT_MS = 2000ms` (2 giây).
  - Khi một request LLM gửi context lớn (100k–400k tokens) sang Google Antigravity (mất 15s–45s), OmniRoute vừa dispatch request vừa chạy ngầm một TCP connect probe 2s.
  - Khi Viettel vấp nhẹ khiến probe TCP trễ mất 2.1s $\rightarrow$ Probe TCP trả về `unreachable`.
  - **Tử huyệt:** `Promise.race` thấy probe 2s giải quyết trước, lập tức **FORCE-KILL REQUEST LLM ĐANG GENERATE DỞ** (`requestPromise.catch(() => {})`).
  - OmniRoute chuyển sang account tiếp theo... nhưng toàn bộ 28 account Antigravity đều nằm trên cụm `test.taadaa.click:51xx`.
  - Kết quả: Cả 28 account bị gạt bỏ sạch sẽ trong 5s $\rightarrow$ Trả về `ALL_TARGETS_SKIPPED (503)`.

### Tầng 3: SQLite Phình To 1.15 GB (> 1.06 Triệu Dòng) Lock Event Loop
- Các stream bị abort giữa chừng làm socket bị vỡ (`read ECONNRESET`), `undici` phải dọn dẹp SSL context dồn dập.
- Cùng lúc, database `storage.sqlite` phình to tới **1.15 GB** với:
  - `conversation_turn_nodes`: **1.061.667 dòng** (> 1 triệu records tích tụ).
  - `quota_snapshots`: **418.150 dòng**.
  - `xp_audit_log`: **188.807 dòng**.
- Thao tác SQLite đồng bộ trên Main Event Loop Node.js bị I/O lock 30s–60s $\rightarrow$ Endpoint `/api/health` không phản hồi $\rightarrow$ Watchdog đếm đủ 12 lần fail liên tiếp (6 phút) và bắn chết tiến trình (force-kill).
- Khi restart, port 20129 còn vướng cờ `TIME_WAIT` của socket Windows $\rightarrow$ Tiến trình mới văng `exit code 1` sau 3 giây.

---

## 3. Bản Vá Kỹ Thuật Đã Áp Dụng & Kiểm Chứng

### A. Nâng Timeout Probe & Khóa An Toàn IP
1. **Nâng trần Probe TCP:** Đặt `PROXY_FAST_FAIL_TIMEOUT_MS=5000` (5s) trong cả `omniroute_watchdog.ps1` và `server.env`. Khi mạng lag 1–2 nhịp, probe 5s kiên nhẫn chờ, không còn kill oan request LLM.
2. **Khóa cứng Farm Safety:** Giữ nguyên `PROXY_FAIL_OPEN=false`. Tuyệt đối cấm bật `true` để không bao giờ bị rơi về IP mạng nhà dân cư Kibe làm ban nick farm.

### B. Prune Sạch 1.14 Triệu Dòng Rác & Nâng Lịch Cron 6h
1. Cập nhật `D:/Taadaa/tools/cleanup_omniroute_db.py`:
   - Giảm retention từ 7 ngày xuống chuẩn **3 ngày** (`RETENTION_DAYS=3`, đồng thuận 01/10).
   - Quét sạch toàn bộ 6 bảng nặng: `conversation_turn_nodes`, `agentic_conversations`, `quota_snapshots`, `xp_audit_log`, `proxy_logs`, `call_logs`.
   - Kết quả: Quét sạch **1.141.000 dòng rác**, đưa số dòng về mức an toàn (<500k), chạy `PRAGMA wal_checkpoint(TRUNCATE)`.
2. Nâng lịch cronjob `daily-omniroute-db-cleanup` (`e61bfd81da93`) từ 1 ngày/lần lên **mỗi 6 giờ (`every 6h`)** để DB luôn được dọn cuốn chiếu, không bao giờ phình quá 400MB.

### C. Khắc Phục Lỗi Restart Sau 3s
- Bổ sung `Start-Sleep -Seconds 3` vào đầu hàm `Start-OmniRoute` trong `omniroute_watchdog.ps1` để Windows dọn sạch socket `TIME_WAIT` trước khi spawn node.exe.

### D. Khóa Cứng Vào Protection Regression Gate
- Tích hợp toàn bộ kiểm định vào `D:/Taadaa/tools/infra_regression_gate.py`:
  - `compression.threshold` trong `[0.28, 0.35]`
  - `agent.api_max_retries` trong `[3, 4]`
  - `agent.api_retry_delay` trong `[5.0, 12.0]`
  - Retry headroom trong `[70s, 130s]`
  - `$MaxDeadlockFailures` trong `[4, 6]`
  - `PROXY_FAIL_OPEN == false`
  - `PROXY_FAST_FAIL_TIMEOUT_MS` trong `[4000, 10000]`
  - `cleanup_omniroute_db.py` retention $\le 3$ ngày
- Đã phủ 12/12 unit test xanh 100% trong `tests/test_infra_regression_gate.py`.
