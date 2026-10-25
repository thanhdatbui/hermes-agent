# Veto Gate to Guidance Gate Upgrade & Mechanical Action Mandate

## 1. Bản Chất "Veto Gate Câm" vs "Guidance Gate"
- **Silent Veto Gate (Cổng Phủ Quyết Câm - Kẻ Thù Số 1 Gây Bại Liệt):**
  - Cổng chỉ trả về `{"action": "block", "message": "..."}` hoặc văng exception/exit code mà không có cấu trúc hướng dẫn.
  - Hậu quả: Agent rơi vào "khoảng trống nhận thức" (Cognitive Void), dẫn tới 4 giai đoạn suy thoái:
    1. Đoán mò sửa lung tung (Turns 1-3).
    2. Đi cửa sau / lách cổng (Turns 4-6) — ví dụ: gõ trực tiếp `claude_worker.py` qua terminal để lách `delegate_task`.
    3. Phân trần, than thở, đổ lỗi cho tool (Turns 7-8).
    4. Tuyên bố BLOCKED ảo hoặc đẩy việc cho Operator: *"Anh mở terminal ngoài gõ lệnh hộ em"* (Turns 9-10).
- **Guidance Gate (Cổng Chỉ Dẫn Cơ Học - Rule 1 & Rule 26):**
  - Mọi trường hợp chặn (`block` / `deny`) BẮT BUỘC phải trả về:
    1. `rule_id`: Định danh rõ ràng mã vi phạm.
    2. `guidance`: Bài học kiến trúc giải thích lý do cấm (tại sao cấm, nguyên tắc an toàn).
    3. `required_action`: Cung cấp sẵn `command` (lệnh thoát $O(1)$) hoặc `instruction` (chỉ dẫn hành động cụ thể) để Agent copy-paste chạy ngay ở turn tiếp theo.

## 2. Danh Mục Các Hook Đã Được Chuẩn Hóa 100% (Audit 2026-10-25)

1. **`hooks/guard_broad_grep.py` (Chống quét đĩa diện rộng & clamp timeout 60s/360s):**
   - Tích hợp `GUIDANCE_MAP` và `INSTRUCTION_MAP` cho toàn bộ 10 mã lỗi (`GUARD_DANGEROUS_ROOT`, `GUARD_RECURSIVE_GREP`, `GUARD_RECURSIVE_RG`, `GUARD_PYTHON_WALKER`, `GUARD_POWERSHELL_SCAN`, `GUARD_FIND_SCAN`, `GUARD_FOREGROUND_TIMEOUT_MISSING`, `GUARD_FOREGROUND_TIMEOUT_INVALID`, `GUARD_FOREGROUND_TIMEOUT_EXCEEDED`, `GUARD_SEARCH_FILES_ROOT`).
   - Tự động reconfigure UTF-8 chống sập console Windows cp1252.

2. **`guard_cronjob_safety.py` (Chống console đen & kiểm soát cronjob an toàn):**
   - Hàm `deny()` và `deny_cron_policy()` trả về `_action_mandate()` có `CONSOLE_GUIDANCE`, `CONSOLE_COMMAND` (`pythonw <script>`), `CONSOLE_INSTRUCTION` (`creationflags=subprocess.CREATE_NO_WINDOW`).
   - Guidance riêng biệt theo từng rule: `DEVICE_LOCK_REQUIRED`, `ROLLING_MODE_REQUIRED`, `SCRIPT_EXISTS`, `NO_AGENT_REQUIRED`, v.v.

3. **`claude_worker.py` (Chốt chặn cửa sau Tier 3 Worker):**
   - Khi phát hiện gọi trực tiếp role `worker` không qua gateway: in lỗi, mã thoát 126 và Action Mandate:
     `HƯỚNG DẪN: Tier 1 là Sol Web Worker (100% Free qua :20129). Bắt buộc thi công qua gateway dispatch_worker.py để ưu tiên Sol và Agy trước, cấm đốt quota Claude trực tiếp.`
     `LỆNH THOÁT O(1): python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <target>] "<prompt>"`

4. **`hooks/guard_read_file_size.py` (Chặn đọc file > 10MB):**
   - Trả về `rule_id: GUARD_READ_FILE_SIZE_EXCEEDED`, giải thích tràn context window, cấp lệnh cắt lát `tail -n 200 <path>`.

5. **`hooks/guard_pytest_scope.py` (Chặn pytest quét rộng toàn repo):**
   - Trả về `rule_id: GUARD_PYTEST_SCOPE_BROAD`, giải thích timeout > 900s, cấp lệnh chạy test cụ thể `python -m pytest <file.py> -q`.

6. **`hooks/guard_device_bulkhead.py` (Chặn bấm tay ADB, quản lý device lock & circuit breaker):**
   - Trả về `guidance` và `required_action` cho cả 6 vị trí block (cấm bấm tay ADB, thiếu lock máy, lệnh ADB thiếu `-s`, circuit breaker mở 15m, timeout foreground > 60s).

7. **`hooks/guard_model_drift.py` (Chống tự ý đổi model Reviewer):**
   - Trả về `rule_id: GUARD_MODEL_DRIFT`, giải thích chuẩn reviewer Sol-High, cấp lệnh closeout gate chuẩn.

8. **`hooks/guard_closeout_discipline.py` (Chống panic rollback & né closeout):**
   - Trả về `guidance` và `required_action` cho cả 4 nhánh (panic rollback, push unapproved, clarify handoff, clarify evasion).

## 3. Quy Tắc Triển Khai Cho Mọi Hook Mới (Checklist Bắt Buộc)
- [ ] Không bao giờ in JSON chỉ có `{"action": "block", "message": "..."}`.
- [ ] Bắt buộc có trường `guidance` (văn bản giải thích kiến trúc).
- [ ] Bắt buộc có trường `required_action` gồm `command` (lệnh chạy được) hoặc `instruction` (chỉ dẫn rõ ràng) + `description`.
- [ ] Luôn gọi `sys.stdout.reconfigure(encoding="utf-8")` trong `try/except` trước khi in JSON trên Windows.
- [ ] Có unit test assert sự tồn tại và tính hợp lệ của `guidance` và `required_action`.
