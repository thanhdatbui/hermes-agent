# Cronjob LLM-Agent Loop Starvation & Defense-in-Depth Enforcement

## 1. Bản chất sự cố (Failure Mode)
- **Hiện tượng:** Toàn bộ session Telegram của Operator bị treo cứng hơn 1 tiếng (từ 11:00 đến 12:29), không session nào phản hồi, sau đó đến 12:25 đồng loạt xả tin nhắn dồn dập.
- **Nguyên nhân gốc rễ:**
  - Hai cronjob (`cron-auto-feed-chatgpt-pool` và `chatgpt-account-lifecycle-healer`) được tạo với lịch chạy dày đặc (`*/15 * * * *` và `0 */6 * * *`) nhưng **thiếu cờ `no_agent: True`**.
  - Trong Hermes Agent runtime, khi thiếu cờ này (mặc định `no_agent: False`), scheduler coi đây là **LLM-driven job**. Mỗi tick nó tự động spawn một AI Agent session độc lập.
  - Con AI này chạy script Python, đọc stdout, rồi tự động rơi vào vòng lặp agentic reasoning (gọi tool, thử lại, chẩn đoán) kéo dài tới **86 turns / messages** và **55 turns**.
  - Việc một cron session chạy 86 turns chiếm dụng toàn bộ API concurrency và làm nghẽn hàng đợi (message queue) của Hermes Gateway, khiến mọi tin nhắn từ Telegram bị ngâm trong queue suốt 1.5 giờ.

## 2. Kiến trúc Phòng thủ 2 Lớp (Defense-in-Depth)

Được thống nhất và phê duyệt độc lập bởi **Advisor Sol (:20129)**, **Claude Code CLI** và **Coordinator**:

### Lớp 1 — PreToolUse Guard Hook (`D:/Taadaa/tools/guard_cronjob_safety.py`)
- **Vị trí bắt chốt:** Chặn đứng trước khi tool `cronjob` kịp ghi dữ liệu (`check_cron_policy(ti, cwd)`).
- **Quy tắc cho `action == 'create'`:**
  - `no_agent` BẮT BUỘC là `True` kiểu `bool` (`val is True`). Từ chối mọi biến thể ép kiểu: `False`, `None`, số `1`, `0`, chuỗi `"true"`, `"True"`.
  - `script` BẮT BUỘC là chuỗi không rỗng.
  - Chặn đứng Path Traversal: Cấm tuyệt đối `..` trong đường dẫn script (`_has_traversal`).
  - Xác thực tệp tồn tại thực tế trên đĩa (`%LOCALAPPDATA%\hermes\scripts\<script>`, `cwd`, hoặc `D:/Taadaa/**`).
- **Quy tắc cho `action == 'update'`:**
  - Cấm hạ cờ `no_agent` thành `False`.
  - Cấm xóa rỗng `script` (ngăn lách luật biến script-job thành prompt-only job).
  - Cấm `..` trong script update.
  - Cho phép update nếu chỉ đổi `schedule` hoặc metadata an toàn.
- **Các action khác (`list`, `pause`, `resume`, `remove`):** Cho qua 100% để bảo đảm năng lực cứu hộ.
- **Telemetry Event:** Ghi riêng `cron_agent_policy_block` với mã `[CRON_AGENT_POLICY_BLOCKED]` vào audit log.

### Lớp 2 — Storage Reconciler (`D:/Taadaa/tools/reconcile_cronjobs.py`)
- Mặc định chạy `--dry-run` (chỉ liệt kê job vi phạm).
- Khi chạy với cờ `--apply`:
  * Tự động sao lưu `jobs.json.bak`.
  * Ghi nguyên tử (Atomic write qua `.tmp` và `os.replace` có `os.fsync`).
  * Tự động chuyển `enabled: False`, `state: 'paused'`, `paused_reason: 'AUTO_QUARANTINE: Cronjob missing no_agent=True'`.
  * Tuyệt đối không xóa job hay sửa schedule.
  * Ghi audit log vào `D:/Taadaa/runtime/audit_logs/cron_reconcile_audit.jsonl`.

## 3. Bộ kiểm thử hồi quy (Regression Test Matrix)
- File test: `D:/Taadaa/tools/tests/test_guard_cronjob_safety.py` (68/68 tests PASS).
- Ma trận bao phủ:
  * Thiếu `no_agent`, `no_agent=False`, `1`, `0`, `"true"`, `"True"`.
  * Thiếu `script`, `script=""`, script không tồn tại.
  * Path traversal: `../job.py`, `..\job.py`, `..`, `job.py/../../evil.py`.
  * Update schedule an toàn vs update script rỗng / `no_agent=False`.
  * Thao tác `list`, `pause`, `resume`, `remove`.
