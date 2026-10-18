# LLM Cronjob Gateway Queue Saturation & Prevention

## 1. Hiện Tượng & Triệu Chứng (Symptoms)
- **Tắc nghẽn hàng đợi diện rộng:** Toàn bộ các session, topic hoặc người dùng nhắn tin qua Telegram bot đều không nhận được phản hồi trong thời gian dài (30 phút – 2 tiếng).
- **Phản hồi bùng nổ hàng loạt (Queue Burst):** Khi nút thắt được tháo gỡ, hàng loạt session bỗng nhiên nhận câu trả lời cùng lúc dồn dập.
- **Bẫy chẩn đoán nhầm:** Rất dễ bị ngộ nhận là do đứt mạng, lỗi Telegram webhook/polling, hoặc do tiến trình Gateway bị restart.

## 2. Gốc Rễ Kỹ Thuật trong Hermes Runtime (Root Cause)
Hermes hỗ trợ 2 chế độ chạy Cronjob thông qua tool `cronjob`:
1. **`no_agent: True` (Script-only Watchdog - Chuẩn Farm):**
   - Scheduler chỉ gọi subprocess chạy script thô (`python script.py`) trong 1–3 giây.
   - Stdout được gửi nguyên văn hoặc im lặng nếu stdout rỗng (watchdog pattern).
   - **0 token LLM**, không sinh session agent, không chiếm hàng đợi.
2. **`no_agent: False` (LLM-driven Agentic Cron - NGUY CƠ NGHẼN):**
   - **Mặc định của tool `cronjob` là `no_agent: False`** nếu Agent hoặc người dùng không truyền rõ `no_agent: True`.
   - Scheduler khởi tạo một **Full AI Agent Session độc lập** (nạp system prompt đầy đủ, context, toolset).
   - Agent đọc prompt, chạy script, đọc stdout. Nếu script gặp lỗi hoặc output dài, Agent sẽ tự động suy luận, đọc thêm file, gọi tool, thử lại... liên tục trong **50 – 90 turns/messages**.
   - Nếu cronjob này được lập lịch chạy dày đặc (ví dụ `*/15 * * * *` - 15 phút một lần), mỗi tick sẽ spawn một agentic session nuốt trọn kết nối LLM provider (concurrency/rate limit), đẩy toàn bộ tin nhắn Telegram của người dùng vào hàng đợi chờ (`Queue Saturation`).

## 3. Quy Trình Chẩn Đoán Tức Thời O(1) (Triage Playbook)
Khi phát hiện bot Telegram im lặng bất thường:
1. **Kiểm tra uptime Gateway:**
   - Đọc `%LOCALAPPDATA%\hermes\gateway-starts.log` và PID của Gateway (`tasklist | grep python`).
   - Nếu PID sống liên tục và thời điểm start không thay đổi, Gateway **không hề bị restart** mà đang bị nghẽn queue.
2. **Quét tìm Cronjob vi phạm trong `jobs.json`:**
   ```bash
   python D:/Taadaa/tools/reconcile_cronjobs.py
   ```
   Lệnh dry-run sẽ liệt kê ngay các job có `no_agent is not True` hoặc thiếu cờ.
3. **Đối soát Session Transcripts:**
   - Tìm các session có tiền tố `cron_<job_id>_*` trong SQLite/session store.
   - Nếu thấy số turns > 10 và kéo dài hàng chục phút, đây chính là thủ phạm chiếm dụng LLM.

## 4. Kiến Trúc Phòng Vệ Chiều Sâu (Defense-in-Depth)

### Tầng 1: PreToolUse Hook Enforcement (`D:/Taadaa/tools/guard_cronjob_safety.py`)
Hàm `check_cron_policy(ti, cwd)` kiểm tra nghiêm ngặt trước khi tool `cronjob` kịp thực thi:
- **Với `action == 'create'`:**
  * Ép kiểu bool chặt chẽ: `ti.get("no_agent") is True`. Từ chối tuyệt đối `False`, `None`, số `1`, chuỗi `"true"`, `"True"`.
  * Trường `script` bắt buộc là chuỗi không rỗng.
  * Chống Path Traversal: Cấm tuyệt đối `..` trong đường dẫn script.
  * Kiểm tra tính tồn tại thực tế của file script (trong `%LOCALAPPDATA%\hermes\scripts\`, `cwd`, hoặc `D:/Taadaa/**`).
  * Từ chối sẽ trả về lỗi rõ ràng: `[CRON_AGENT_POLICY_BLOCKED]`.
- **Với `action == 'update'`:**
  * Cấm cập nhật `no_agent` thành `False`.
  * Cấm xóa rỗng `script` (ngăn việc lách luật biến script job thành prompt job).
  * Cho phép update schedule và metadata an toàn.
- **Với các action cứu hộ (`list`, `pause`, `resume`, `remove`):** Luôn cho phép để Operator xử lý sự cố.

### Tầng 2: Reconciler Tự Động Cách Ly (`D:/Taadaa/tools/reconcile_cronjobs.py`)
- Mặc định chạy `--dry-run` để audit.
- Chạy với cờ `--apply` khi phát hiện sự cố:
  * Tự động sao lưu `jobs.json.bak`.
  * Thực hiện ghi nguyên tử (Atomic write qua file `.tmp` và `os.replace` có `os.fsync`).
  * Chuyển các job vi phạm sang `enabled=False`, `state='paused'`, `paused_reason='AUTO_QUARANTINE: Cronjob missing no_agent=True'`.
  * Ghi audit log vào `D:/Taadaa/runtime/audit_logs/cron_reconcile_audit.jsonl`.

### Tầng 3: Quy Chuẩn Bất Biến (Invariant Rule)
- 100% cronjob tự động trong farm bắt buộc là `no_agent: True`.
- Cấm tuyệt đối Agent tự động tạo hoặc sửa cronjob gọi LLM Agent (`no_agent: False`) với tần suất dưới 6 tiếng.
