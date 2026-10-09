# OmniRoute Model Lockout & Free-Pool Cascade OOM Prevention

## 1. Bối cảnh & Hiện tượng sự cố (Incident Diagnosis)
- **Hiện tượng**: OmniRoute cổng `:20129` crash Node.js (V8 Heap OOM exit code `0xC0000409` hoặc event loop nghẽn) khi nhận chùm request context lớn từ bot Hermes (400 - 700+ messages / 268k tokens).
- **Trình tự suy sụp liên hoàn (Domino Crash Chain)**:
  1. Hermes gửi liên tiếp payload nặng (474 msgs, 482 msgs, 694 msgs).
  2. Một vài tài khoản Pro gặp lỗi mạng/proxy thoáng qua (`[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5113` -> HTTP 503).
  3. Cấu hình `modelLockout.baseCooldownMs` bị đặt quá cao ở mức **600.000ms (10 phút)** thay vì **120.000ms (2 phút)** chuẩn.
  4. Lỗi 503 kích hoạt Model Lockout 10 phút trên các tài khoản Pro. Dàn 20 tài khoản Pro nhanh chóng bị cạn slot khả dụng (`refusing sibling selection`).
  5. Combo `omni-worker` failover cascade xuống Tier tiếp theo: `ag-gemini-free-pool` (gồm 79 tài khoản Free).
  6. Router duyệt qua 79 accounts. Với mỗi candidate, router clone request context khổng lồ (268k tokens) trong RAM. Nhân lên qua nhiều concurrent requests và 79 candidate targets, bộ nhớ V8 Heap bị đội lên đột biến. Đây là giả thuyết OOM cần được xác nhận bằng crash dump/V8 fatal log hoặc process-exit evidence trước khi báo cáo là nguyên nhân chắc chắn.

---

## 2. Quy Tắc & Cấu Hình Chuẩn (Standards & Mitigation)

### A. Chuẩn hóa `modelLockout` (Chống giam acc oan)
- `baseCooldownMs`: **120.000ms (120s / 2 phút)**.
- `maxCooldownMs`: **600.000ms (10 phút)**.
- `maxBackoffSteps`: **5** (thay vì 10).
- `errorCodes`: `[403, 404, 429, 502, 503, 504]`.
- **Cơ chế cập nhật**:
  1. Patch runtime qua `PATCH /api/settings`:
     ```json
     {
       "modelLockout": {
         "enabled": true,
         "errorCodes": [403, 404, 429, 502, 503, 504],
         "baseCooldownMs": 120000,
         "maxCooldownMs": 600000,
         "maxBackoffSteps": 5,
         "useExponentialBackoff": true
       }
     }
     ```
  2. Đồng bộ vào SQLite `storage.sqlite` (bảng `key_value`, namespace `settings`, key `modelLockout`).
  3. Lưu backup vào `AI-Tools/tools/omniroute/settings_backup.json`.

### B. Kỷ luật Cascade Protection (Chống tràn payload nặng sang Free Pool)
- Dàn Free Pool (79 accounts) chỉ phù hợp cho request nhẹ (< 50k tokens / < 100 messages) với strategy `p2c` hoặc `least-used`.
- Request context nặng (> 100k tokens / bot messages lớn) tuyệt đối không được cascade tràn qua toàn bộ 79 accounts Free khi Tier Pro bị lockout. Cần có cơ chế fail-fast hoặc circuit-break ngắn để tránh OOM do multi-target payload cloning.

### C. Quản lý Proxy Health cho Dàn Pro
- Các tài khoản Pro có proxy riêng (như `test.taadaa.click:5113`, `5115`, `5135`): nếu proxy rớt kết nối, OmniRoute trả 503 và kích hoạt lockout connection.
- Cần đảm bảo proxy preflight hoặc watchdog phát hiện proxy chết để chuyển sang fallback pool proxy thay vì để tài khoản bị modelLockout liên tục.

### D. Nguy Cơ Subagent Loopback Deadlock Khi Combo Router Nghẽn
- **Hiện tượng**: Worker subagent được dispatch để sửa lỗi cấu hình OmniRoute qua HTTP PATCH `:20129/api/settings` liên tục bị `status=timeout` sau 180s (dù lệnh gọi curl/PATCH rất nhỏ).
- **Cơ chế**:
  - Khi OmniRoute đang bị ngâm chùm request nặng trong Free Pool, combo router bị nghẽn Event Loop và phát cảnh báo:
    `[COMBO] Combo loop safety timeout (600000ms) reached without a terminal response — force-terminating`.
  - Nếu model của subagent (ví dụ `ag-gemini-pool-3` hoặc worker model) lại được định tuyến ngược vào chính cổng `:20129` của OmniRoute, các turn LLM của worker sẽ bị ngâm chờ hàng đợi của router và cạn timeout 180s của harness delegation.
- **Kỷ luật xử lý**:
  1. *Cấm chạy script kiểm tra diện rộng trong Worker*: Tuyệt đối không giao cho worker các script nặng duyệt qua toàn bộ 333 connections/combos (như `check_omniroute_status.py`), vì độ trễ fetch + parse JSON sẽ nuốt sạch budget 180s.
  2. *Thực hiện Direct DB Injection trước*: Khi router bị nghẽn loopback, ưu tiên cập nhật trực tiếp vào file SQLite `~/.omniroute/storage.sqlite` (offline write) thay vì chỉ trông cậy vào HTTP PATCH qua cổng đang nghẽn.
  3. *Tách biệt Model Worker*: Worker cần được cấu hình qua upstream trực tiếp hoặc model lane độc lập (Codex/Claude Code CLI) để tránh vòng lặp tự phong tỏa (self-blocking deadlock).
