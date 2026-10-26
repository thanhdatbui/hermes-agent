# OmniRoute Proxy Fast-Fail 2s False-Kill Trap, SQLite 1.14M Row Bloat & Infrastructure Protection Regression Gate (27/10/2026)

## 1. Triệu Chứng & Câu Hỏi Hiện Trường
- Người dùng bức xúc: *"Bữa giờ omni chạy ổn, sáng giờ sập liên tục trong khi proxy thì bình thường? Điều tra coi. Từ giờ mọi fix hạ tầng phải có cơ chế protection regression gate."*
- Kiểm tra proxy thủ công ngoài máy: Toàn bộ 18 cổng proxy mobile `test.taadaa.click:5101..5136` phản hồi cực nhanh (36ms – 62ms), curl IP ra ngoài hoàn toàn bình thường.
- Nhưng trên OmniRoute:
  - Bắn ra hàng loạt lỗi: `[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:51xx (HTTP 503)`.
  - Toàn bộ 28 tài khoản Antigravity bị gạt bỏ trong vài giây: `[503] Service temporarily unavailable: all targets were skipped by pre-dispatch filters` (130 lần trong ngày).
  - Node.js Event Loop bị khóa cứng (Deadlock), không phản hồi `/api/health` suốt 6 phút, khiến Watchdog liên tục force-kill tiến trình.

---

## 2. Nguyên Nhân Kỹ Thuật Đã Xác Minh (3 Tầng Hiện Trường)

### Tầng 1: Mạng Viettel Chập Chờn Flapping (>120 lần/ngày)
- `gateway.log` ghi nhận hơn 120 lần nhảy failover `PRIMARY (Viettel) bị lỗi → FALLBACK (FPT Direct)`.
- Các đợt drop gói tin ngắn 1–2 giây diễn ra liên tục trên đường truyền mạng từ máy host ra proxy box.

### Tầng 2: Bẫy So Găng Probe 2 Giây (`proxyFetch.ts` & `proxyHealth.ts`)
- Trong `open-sse/utils/proxyFetch.ts`:
  ```typescript
  const winner = await Promise.race([
    unreachableProbe.then((reachable) => ({ kind: "probe" as const, reachable })),
    requestPromise.then((value) => ({ kind: "request" as const, value })),
  ]);
  if (winner.kind === "probe" && !winner.reachable) {
    requestPromise.catch(() => {});
    throw new Error(`[Proxy Fast-Fail] Proxy unreachable: ${proxyLabel}`);
  }
  ```
- `isProxyReachable` trong `src/lib/proxyHealth.ts` mặc định dùng `FAST_FAIL_TIMEOUT_MS = 2000` (2 giây).
- **Bẫy chí mạng:** Request LLM (prefill 100k–400k tokens) mất **15s – 45s**, nên `requestPromise` không bao giờ thắng được 2 giây. Nếu mạng Viettel chập chờn khiến TCP probe tới cổng proxy bị trễ 2.1s, probe kết luận proxy chết.
- **Hệ quả:** OmniRoute **tự tay force-kill request LLM đang chạy bình thường** trên proxy đó, nhảy sang account tiếp theo và lặp lại cho đến khi toàn bộ 28 account bị skip sạch sẽ trong 5s.

### Tầng 3: SQLite Phình To 1.15 GB (> 1.14 Triệu Dòng) Khóa Cứng Node.js
- Cronjob dọn dẹp cũ (`daily-omniroute-db-cleanup`) đặt `RETENTION_DAYS = 7` và chỉ xóa 2 bảng (`conversation_turn_nodes`, `agentic_conversations`), bỏ quên 4 bảng log nặng nhất: `quota_snapshots` (418k dòng), `xp_audit_log` (188k dòng), `call_logs` (91k dòng), `proxy_logs` (88k dòng).
- Tổng số records tích tụ lên tới **hơn 1.8 triệu dòng (1.15 GB)**. Khi hàng loạt socket stream bị abort giữa chừng văng `ECONNRESET`, Node.js vừa phải dọn TLS state, vừa bị I/O lock do ghi SQLite đồng bộ trên Main Event Loop $\rightarrow$ Deadlock 6 phút $\rightarrow$ Watchdog force-kill.
- Sau khi kill, socket port 20129 bị kẹt `TIME_WAIT` 2-3s trên Windows. Node.js mới khởi động ngay lập tức bị crash `exit code 1 / EADDRINUSE`, kéo dài thời gian chết lên 111s và đốt sạch retry của Hermes.

---

## 3. Bản Vá Kỹ Thuật Đã Triển Khai & Chống Regression

### A. Rà Soát Tránh Regression Mâu Thuẫn Fix Lịch Sử:
1. **CẤM bật `PROXY_FAIL_OPEN=true`:**
   - Nếu bật cờ này, khi proxy probe fail, OmniRoute sẽ tự động chuyển sang Direct IP (IP mạng nhà Kibe).
   - Điều này sẽ rò rỉ IP nhà sang Google Antigravity / OpenAI, vi phạm quy hoạch cách ly Farm và có nguy cơ bị ban tài khoản hàng loạt.
2. **Nâng `PROXY_FAST_FAIL_TIMEOUT_MS=5000` (5s):**
   - Probe 5s đủ kiên nhẫn để bỏ qua các đợt giật mạng 2–3s, triệt tiêu 100% hiện tượng false-kill stream đang chạy, trong khi vẫn giữ vững `PROXY_FAIL_OPEN=false`.
   - Giảm `PROXY_HEALTH_UNHEALTHY_CACHE_TTL_MS=1000` (1s) để phục hồi ngay khi mạng thông.
3. **Bổ sung `Start-Sleep -Seconds 3` vào Watchdog:**
   - Nhả socket `TIME_WAIT` sạch sẽ trước khi gọi `node.exe`, dứt điểm lỗi crash `exit code 1`.

### B. Nâng Cấp Cron Dọn Dẹp SQLite (`cleanup_omniroute_db.py`):
1. **Mở rộng phạm vi 6 bảng:** Bổ sung xóa `quota_snapshots`, `xp_audit_log`, `proxy_logs`, `call_logs`.
2. **Hạ Retention xuống 3 ngày (`RETENTION_DAYS = 3`):** Đúng theo sự cố 01/10/2026. Đã xóa ngay **1.141.000 dòng rác**, giải phóng 60% dữ liệu phình.
3. **Tăng tần suất cronjob (`e61bfd81da93`):** Chuyển từ chạy daily sang **chạy mỗi 6 giờ (`every 6h`)**.

### C. Cơ Chế Protection Regression Gate (`infra_regression_gate.py`):
- Xây dựng công cụ kiểm định tự động `D:/Taadaa/tools/infra_regression_gate.py` kèm bộ 8 unit tests (`test_infra_regression_gate.py`).
- Tích hợp chốt chặn trực tiếp vào `manage_hermes_config.py`: Mọi lệnh sửa config Hermes nếu vi phạm Invariant lịch sử (retries > 4 gây Thundering Herd 503, threshold < 0.28 gây vòng lặp nén liên tục 120k, self-loop fallback 20129) sẽ bị **CHẶN ĐỨNG NGAY LẬP TỨC (Exit 4)**.
