# Sự Cố OmniRoute Bị Watchdog Sập Hoài, Bẫy Fast-Fail Probe 2 Giây Kill Oan Request & Tràn SQLite 1.15GB (26-27/10/2026)

## 1. Hiện Tượng & Triệu Chứng Hiện Trường
- Cụm proxy 4G mobile (`test.taadaa.click:51xx`) đo trực tiếp qua TCP và curl hoàn toàn bình thường, độ trễ 36ms–62ms, 18/18 cổng online 100%.
- Tuy nhiên OmniRoute liên tục báo:
  - `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:51xx`
  - `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (xảy ra hơn 130 lần trong ngày).
- Sau đó OmniRoute bị treo Event Loop suốt 6 phút (12 chu kỳ `/api/health` timeout), Watchdog force-kill Node.js (`deadlock ceiling reached`).
- Khi Watchdog restart Node.js, tiến trình bị văng lỗi `exited prematurely with exit code 1 after 3 seconds` (do kẹt cờ `TIME_WAIT` socket trên port 20129). Thời gian gián đoạn kéo dài tới 111 giây, khiến hàng chục session Telegram văng thông báo `The model provider failed after retries`.

---

## 2. Phân Tích 3 Nguyên Nhân Gốc Rễ (Root Cause)

### Nguyên nhân 1: Mạng Viettel Chập Chờn (>120 Lần Flapping Trong Ngày)
- Trong `gateway.log`, ghi nhận hơn 120 lần `Multi-ISP Failover: PRIMARY (Viettel) bị lỗi → chuyển sang FALLBACK (FPT Direct)`.
- Tuyến kết nối từ máy Kibe tới router MikroTik / dải proxy mobile bị vấp gói tin từng nhịp 1–3 giây.

### Nguyên nhân 2: Bẫy So Găng `Promise.race` Trong `proxyFetch.ts` & Probe 2 Giây
- Trong `open-sse/utils/proxyFetch.ts` (dòng 681–711):
  ```typescript
  const winner = await Promise.race([
    unreachableProbe.then((reachable) => ({ kind: "probe" as const, reachable })),
    requestPromise.then((value) => ({ kind: "request" as const, value })),
  ]);
  ```
- `unreachableProbe` gọi `isProxyReachable(resolvedProxyUrl)` với timeout mặc định chỉ vỏn vẹn **2.0 giây (`FAST_FAIL_TIMEOUT_MS = 2000`)**.
- Trong khi đó, request LLM gửi 100k–400k tokens sang Google Antigravity mất **15s–45s**.
- **Hệ quả chết người:** Khi mạng Viettel chập chờn vấp 1 gói tin khiến probe TCP trễ 2.1 giây:
  1. `winner.kind === "probe"` luôn thắng cuộc đua vì request LLM chưa xong.
  2. `winner.reachable` là `false` do quá hạn 2.0s.
  3. OmniRoute **FORCE-KILL REQUEST LLM ĐANG STREAM HỢP LỆ TRÊN PROXY ĐÓ** (`requestPromise.catch(() => {})`).
  4. Ném lỗi 503 `PROXY_UNREACHABLE` và gạt bỏ proxy khỏi pool trong 2s.
  5. Vì cả 28 account Antigravity đều dùng chung dải `test.taadaa.click`, chuỗi skip diễn ra đồng loạt trên cả 28 targets $\rightarrow$ Văng `all targets were skipped by pre-dispatch filters`.

### Nguyên nhân 3: Database SQLite Phình 1.15 GB (> 1.14 Triệu Dòng Stale)
- Hàng chục stream context lớn bị kill ngang xương sinh ra `ECONNRESET` dồn dập trên socket undici.
- Kiểm tra `C:/Users/Kibe/.omniroute/storage.sqlite`:
  - `conversation_turn_nodes`: **1.066.502 dòng** (> 1 triệu dòng).
  - `quota_snapshots`: **418.577 dòng**.
  - `xp_audit_log`: **188.807 dòng**.
  - `call_logs` & `proxy_logs`: gần **180.000 dòng**.
- Dung lượng DB phình lên 1.15 GB. Mỗi khi abort hoặc ghi log, thao tác SQLite đồng bộ trên Main Event Loop gây I/O freeze hàng chục giây $\rightarrow$ Event loop deadlock $\rightarrow$ Watchdog kill.

---

### 3. Phân Biệt Giữa "Regression Gate" vs "Protection Regression Gate"
- **Regression Gate:** Là các bộ test chức năng (`pytest tests/`) của 18 repos nhằm đảm bảo tính đúng đắn của phần mềm.
- **Protection Regression Gate:** Là **chốt chặn cơ học bất biến (Mechanical Invariant Gate)**, quét trực tiếp vào code diff để ngăn cấm tái phát các bài học xương máu (được điều khiển bởi `GuardGate` qua `rules.json` và `infra_regression_gate.py`).

---

### 4. Kỷ Luật Chống Over-Engineering (Anti-Hook Sprawl)
- **CẤM rải file `.git/hooks/pre-push` vào 20 repo:** Farm vận hành qua cron và script local, không dùng `git push`. Rải hook vào `.git` là quan liêu, gây kẹt môi trường khi dev ngoài VS Code.
- **Tập trung hóa O(1):** Mọi điều cấm bất biến được gom về duy nhất 2 chốt chặn trung tâm:
  1. `D:/Taadaa/tools/guardgate/rules.json`: Chứa 8 luật bất biến của Farm (Case 161, Case 162, cấm uiautomator dump, timeout worker >= 300s, cấm skip Hotmail login, cấm scan D:/, cấm gán domain vào Android http_proxy, cấm socks5h).
  2. `D:/Taadaa/tools/infra_regression_gate.py`: Chứa 5 luật bất biến của hạ tầng Hermes & OmniRoute.

---

### 5. Bộ Thông Số Vá Chuẩn Xác (Không Xung Đột)

1. **`omniroute_watchdog.ps1` & `server.env`:**
   - `PROXY_FAST_FAIL_TIMEOUT_MS = 5000` (5s timeout cho probe, tránh false-kill stream).
   - `PROXY_FAIL_OPEN = false` (bắt buộc duy trì false để cấm rò rỉ IP mạng nhà).
   - `$MaxDeadlockFailures = 4` (~120s, vừa đủ an toàn cho prompt nặng 300k+ tokens prefill, vừa không ngâm chết tiến trình).
   - `Start-Sleep -Seconds 3` ở đầu `Start-OmniRoute` (nhả sạch TIME_WAIT socket).
2. **`cleanup_omniroute_db.py`:**
   - `RETENTION_DAYS = 3` (chuẩn 3 ngày theo consensus 01/10/2026).
   - Quét dọn cả 6 bảng nặng: `conversation_turn_nodes`, `agentic_conversations`, `quota_snapshots`, `xp_audit_log`, `proxy_logs`, `call_logs`.
   - Cronjob `daily-omniroute-db-cleanup` đổi lịch thành **`every 6h`** (dọn cuốn chiếu 4 lần/ngày).
3. **Hermes Config (`manage_hermes_config.py`):**
   - `agent.api_max_retries = 4` (chống Thundering Herd Retry Storm 503).
   - `agent.api_retry_delay = 6.0` (tổng thời gian chờ ~90s, bao trọn 25–35s restart của OmniRoute).
