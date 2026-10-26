# User Sudo Override & The Investigate Read-Only Deadlock Triangle

## 1. Context & Problem Statement
When designing and enforcing pre-tool interception rules and mechanical gates, overly strict, isolated fail-closed checks can create an unrecoverable "Deadlock Triangle" (Tam giác quỷ liệt cơ học):
1. **Coordinator Layer**: Capped by session budget (e.g. T1 limit of 10 files / 500 lines) -> blocked with Coordinator Write Denied and forced to dispatch.
2. **Worker Layer**: Worker subagent dispatched via delegate_task is blocked with Read-Only Worker because it was not granted a Scope Lock.
3. **Terminal Layer**: Blocked from executing python inline file writes (python -c write blocked) or shell redirections.
4. **User Override Ignored**: Even when the user explicitly types BYPASS_ALL_GUARDS_CONFIRMED or "tao cho phép", runtime rules running in isolated processes cannot see the Telegram user message unless explicitly bridged via an Operator Grant.

---

## 2. Root Cause Analysis: The Investigate Trap & Regex Traps
### A. The INVESTIGATE Trap
In dispatch contract enforcement:
- Any task containing keywords like `budget`, `investigate`, `chỉ đọc`, `khảo sát` is classified as INVESTIGATE.
- Investigate tasks are assigned empty target files and stripped of write permissions (Read-Only Worker).
- **Rule**: When delegating file creation or mutation to a worker, NEVER include `budget: <= N calls` or words implying investigation in the context. Use strictly:
  ```text
  TASK_KIND: CREATE
  FILE: <absolute_path>
  FILE_CONTENT:
  ...
  ```
  or for edits:
  ```text
  TASK_KIND: EDIT
  FILE: <absolute_path>
  OLD_STRING: ...
  NEW_STRING: ...
  FOCUSED_TEST: ...
  ```

### B. Regex False Positives on Code Signatures
- Gate contracts search for target files using regexes such as:
  `re.search(r'\b(?:FILE|File|file|Target file|target_file):\s*([^\r\n]+)')`
- If raw Python code containing function signatures like `def verify(target_file: str, diff_lines: int = 0):` is included in the context, the parser detects `target_file:` and treats `str, diff_lines: int = 0` as a declared file path!
- This triggers MULTI_FILE_VIOLATION (e.g. "Phát hiện 3 files trong 1 task").
- **Rule**: Avoid raw code containing `target_file:` or unescaped colons that match file label patterns in dispatch contexts. Store code in intermediate reference files or rename parameters (e.g., `target_path: str`).

---

## 3. Architecture of User Master Override (Sudo của User)
To prevent agent paralysis when emergency fixes are commanded by the user:

### A. Authorized Keywords
User triggers: `"tao cho phép"`, `"tao cho phep"`, `"bypass"`, `"sửa gấp"`, `"sua gap"`, `"làm luôn"`, `"lam luon"`, `"force"`, `"tao duyệt"`, `"tao duyet"`, `"BYPASS_ALL_GUARDS_CONFIRMED"`.

### B. Single-Use Signed Grant Lifecycle
1. **Grant Generation (user_sudo.py)**:
   - Generates an HMAC-SHA256 signature binding session_id, nonce, target_files, and expires_at (TTL = 300s).
   - Writes grant metadata to `D:/Taadaa/runtime/sudo_grant.json`.
2. **Consumption & Verification**:
   - Runtime checks verify HMAC signature, check expiration, confirm target file matches, and mark used = True (single-use nonce burned immediately).
   - Logs audit record to `D:/Taadaa/runtime/audit_logs/sudo_audit.jsonl`.
3. **O(1) Hard Ceilings & User Supreme Sovereignty (Direction B)**:
   - Maximum 1-2 files, diff <= 30 lines total.
   - Mandatory focused test execution < 30s immediately following modification; immediate auto-rollback if test fails.
   - **User Sovereignty over Rules**: Under valid User Sudo grant (HMAC-SHA256, user trigger keywords, single-use nonce), `hooks/` and `guard_*.py` ARE AUTHORIZED for emergency surgery and auto-rewire fixes. The system must NEVER lock out the Root Owner (Hierarchy Inversion Anti-pattern).
   - Truly forbidden zones that CANNOT be bypassed even via Sudo: `.env`, `credentials`, `secret`, `accounts.db`.
4. **Kill-Switch**: Setting `TAADAA_SUDO=0` immediately disables all sudo bypasses system-wide.

---

## 4. Health Evaluation Discipline: No Idle-Window Bias
- **Invariant**: Assessing gate compliance, error rates, or rule stability MUST be calculated from all-time audit logs or normalized per active chat interaction turn.
- **Strict Prohibition**: NEVER claim "0 errors" or "stable as Closeout Gate" based on an idle window (e.g. nighttime or 4 hours of silence when no one was issuing commands). Idle hours reflect absence of stimulus, not system reliability.

---

## 5. Canonical Worker CLI Execution Ladder for File Creation & Hotfixes
When Coordinator has exhausted the T1 session write budget (10 files / 500 lines) and `delegate_task` is mechanically blocked by dispatch gates:
- **Canonical Execution**: Use `python D:/Taadaa/tools/ag_cli.py fix --workdir <repo> --file <target> "<prompt>" --timeout 180`.
- **Foreground Timeout Whitelist Advantage**: `ag_cli.py`, `dispatch_worker.py`, `sol_worker.py`, `claude_worker.py`, `sol_repair.py`, `closeout_gate.py`, and `pytest` are registered in `LONG_RUNNING_ALLOWLIST` inside `guard_broad_grep.py`. This permits up to 360s in foreground terminal calls (vs standard 60s hard ceiling), preventing false `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` aborts.
- **Worker Autonomy**: Running `ag_cli.py fix` utilizes the local multi-profile Antigravity pool (e.g. `acc_02` on `gemini-3.8-flash-medium`) to write/modify target code cleanly on disk, returning verified exit codes without Coordinator cowboy surgery or Read-Only Worker scope lock deadlock.

---

## 6. Reviewer Security Invariants for Sudo Authorization Modules
When designing or auditing authorization/sudo bypass modules (e.g. `user_sudo.py`), the Closeout Gate Sol Auditor strictly enforces 5 security invariants (score failure if any is violated):
1. **Dynamic Secret Key Generation (No Hardcoded Fallback)**:
   - CẤM TUYỆT ĐỐI hardcode secret mặc định trong source code (`SECRET_KEY = os.environ.get(..., 'default_string')` là lỗ hổng nghiêm trọng vì kẻ tấn công có thể giả mạo chữ ký HMAC khi env var chưa set).
   - **Chuẩn hóa**: Nếu `TAADAA_SUDO_SECRET` không có trong env, tự động đọc từ file cục bộ `D:/Taadaa/runtime/.sudo_secret`. Nếu file chưa tồn tại, tự sinh `secrets.token_hex(32)` và ghi xuống file với quyền hạn chế.
2. **Strict Caller Session Binding**:
   - `verify_and_consume_grant(session_id, ...)` BẮT BUỘC đối chiếu `grant.get('session_id') == session_id`.
   - Chặn đứng trường hợp grant cấp cho session A bị session B lén tiêu thụ.
3. **Exact Canonical Path Matching**:
   - CẤM so khớp hậu tố bằng `.endswith()` hoặc `in` chuỗi (cho phép `/tmp/evil/worker.py` giả mạo `worker.py`).
   - BẮT BUỘC so sánh chính xác canonical path: `Path(target_path).resolve() == Path(tf).resolve()`.
4. **Strict Diff Ceiling Type & Range Validation**:
   - Bắt buộc kiểm tra `isinstance(diff_lines, int) and 0 <= diff_lines <= 30`.
   - Chặn đứng giá trị âm (`diff_lines = -1`) hoặc kiểu dữ liệu lạ bypass kiểm tra trần diff.
5. **Fail-Visible Audit Logging**:
   - CẤM nuốt lỗi audit bằng `except: pass`. Nếu ghi audit JSONL thất bại, bắt buộc xuất cảnh báo ra `sys.stderr` để bảo toàn khả năng truy vết (observability).

---

## 7. Closeout Remediation Escalation & Anti-Rogue Claude Invariant
Trong pha Closeout Remediation khi Gate REJECTED:
- **First-Responder Monopoly**: `sol_repair.py` chạy trước tiên để sinh patch O(1).
- **Fallback Worker Trigger**: Khi `sol_repair.py` timeout hoặc trả về `valid=False`:
  - Thử Antigravity CLI Worker: `python D:/Taadaa/tools/ag_cli.py fix --workdir <repo> --file <target> "<prompt>" --timeout 180`.
- **CẤM TUYỆT ĐỐI TỰ Ý BẬT CLAUDE WORKER (ANTI-ROGUE CLAUDE INVARIANT)**:
  - Claude CLI / Claude Worker (`claude_worker.py`) là **100% On-Demand**.
  - **CẤM** Coordinator tự ý truyền cờ `--on-demand` khi User chỉ ra lệnh chung như "làm đi", "sửa đi", "tiếp tục". Các lệnh đó chỉ cho phép sử dụng Sol và Agy!
  - Cờ `--on-demand` CHỈ được phép truyền khi tin nhắn của User có chứa đích danh từ khóa `"claude"`.
  - Nếu Sol và Agy đều timeout hoặc cooldown: Coordinator BẮT BUỘC dừng lại, báo cáo trung thực biên bản lỗi kèm log audit, KHÔNG ĐƯỢC TỰ Ý "nhảy cóc" gọi Claude Worker để che giấu thất bại của Tier 1 & Tier 2.

---

## 8. Nguyên Nhân Gốc Rễ Sol Repair / Sol Worker Thất Bại & Cách Khắc Phục
Khi gọi `sol_repair.py` hoặc `sol_worker.py` bị timeout hoặc lỗi HTTP 400:
1. **Model Incompatibility trên OmniRoute `:20129`**:
   - `sol_repair.py` có allowlist cứng `ALLOWED_REPAIR_MODELS = {'gpt-web-sol', 'sol-web', 'gpt-5.6-sol-high', 'plan-review-hard'}`.
   - Trên `:20129`: model `sol-web` và `plan-review-hard` bị HTTP 400 (chưa gán provider); `gpt-5.6-sol-high` bị chặn OAuth token Codex.
   - Model `gpt-web-sol` là pool browser chạy headless: khi prompt chứa toàn bộ diff + 13 findings lớn, browser session bị nghẽn (latency > 60-120s) dẫn tới `timed out`.
   - **Giải pháp**: Model `review` trên `:20129` phản hồi cực nhanh (HTTP 200, 3-5s). Cần bổ sung `"review"` vào `ALLOWED_REPAIR_MODELS` trong `sol_repair.py` để Sol Repair xử lý tức thì, tránh timeout.
2. **Streaming Timeout trên Sol Worker**:
   - `sol_worker.py` dùng ReAct streaming. Nếu proxy/browser mất quá 15s để sinh token đầu tiên, turn sẽ báo `Timeout exceeded during model streaming`. Cần duy trì timeout turn >= 180s cho Sol Worker.

---

## 9. Triệt Tiêu Nghịch Lý Điều Phối: "Làm Chặt Thì Liệt, Làm Lỏng Thì Láo Lếu"
Hệ thống AI Coordinator thường rơi vào hai thái cực cực đoan:
1. **Làm Chặt Quá Mức $\to$ Bại Liệt / Khóc Lóc**:
   - Khi gặp Gate DENY, Agent dừng lại xin lỗi, mở ticket chờ User hoặc tuyên bố BLOCKED.
   - **Khắc phục**: Mọi Gate DENY bắt buộc phải kèm **Auto-Rewire** hoặc **Action Mandate O(1)** (lệnh copy-paste chạy được ngay trong cùng turn) hoặc **Queue Pivot**.
2. **Thả Lỏng Quá Mức $\to$ Cao Bồi / Rogue / Láo Lếu**:
   - Khi User nói "làm đi", Agent tự tiện sửa code trong session chính (Cowboy Coordinator), vượt trần 30 dòng, hoặc tự ý lách guard truyền cờ `--on-demand` sang Claude.
   - **Khắc phục**: Rào chắn cơ học không dựa vào "suy đoán ý định" của LLM. Mọi quyền override hoặc on-demand bắt buộc phải có chữ ký/token xác thực cơ học gắn với tin nhắn của User.

---

## 10. Watchdog Compliance Fidelity & Pytest Pollution Elimination
- **Test Artifact Exclusion**: Pre-tool and gate compliance watchdogs MUST filter out test traces (`is_test_log_line`: ignore lines containing `pytest`, `target.py`, `tmp_path`). Mock runs in unit tests previously accounted for 75%+ of reported gate failures (e.g. 27 fake QUOTA, 18 fake TIMEOUT, 9 fake NEEDS_INPUT).
- **Timezone Normalization (Local Naive vs UTC)**: Audit logs written using `datetime.now().isoformat()` without timezone (`LOCAL_NAIVE_LOGS`: `dispatch_audit.jsonl`, `console_block_audit.jsonl`) must be converted from host local timezone (UTC+7) to UTC before filtering by the 6h cutoff window. Treating local naive as UTC shifts the window by 7h, falsely pulling in past afternoon errors.
- **Credit Self-Healing (`rewired_hits`)**: Auto-clamped and auto-rewired actions are recorded as `REWIRED` (0-turn overhead) rather than failures (`FAIL`), preserving high-fidelity telemetry for real blocks.
- **Sol Worker Execution Floor**: Set `SOL_AGY_TIMEOUT_FLOOR = 480s` and `--max-turns = 12` (up from 8) to ensure Sol multi-patch workflows finish reliably without false timeouts.

---

## 11. Cron Safety Tokenizer Null-Byte Exception Trap (`ValueError: embedded null character in path`)
- **Vấn đề kỹ thuật**: Trong module an toàn cron của Hermes (`site-packages/cron/` dòng 259–262), hàm `_read_referenced_script(path)` dùng `os.open(path, flags)` để kiểm tra nhanh shell script được gọi từ lệnh terminal:
  ```python
  try:
      descriptor = os.open(path, flags)
  except OSError:
      return None, False
  ```
- **Bẫy sập (Unhandled ValueError)**: Khi lệnh terminal chứa chuỗi Python nhiều dòng, base64 hoặc quote phức tạp, bộ tokenizer có thể trích xuất các token chứa byte null `\0` hoặc ký tự đường dẫn không hợp lệ. Trên Windows, `os.open` ném lỗi `ValueError: open: embedded null character in path`. Vì `ValueError` không kế thừa từ `OSError`, lỗi này không bị bắt, làm văng exception ra ngoài và đánh sập tiến trình terminal của Coordinator!
- **Chuẩn hóa (Fail-Open cho binary/invalid tokens)**:
  BẮT BUỘC bọc `except (OSError, ValueError):` để khi gặp token dị dạng hoặc null byte, hàm trả về `(None, False)` an toàn và cho phép lệnh terminal tiếp tục thực thi bình thường.

---

## 12. Ephemeral Path Exclusion in Coordinator Write Ledger (Chống Ngộ Độc Ngân Sách T1)
- **Vấn đề kỹ thuật**: Trong plugin kiểm soát Coordinator (`coordinator_write_gate`), trần `COORD_T1_MAX_FILES = 10` tính gộp mọi file ghi/sửa trong phiên làm việc.
- **Bẫy tê liệt (T1 Poisoning)**: Khi Coordinator tạo các script phụ tạm thời (ví dụ: `tmp_make_avatar.py`, `tmp_detect.py`, hoặc ghi file trong `D:/Taadaa/tmp/`), những file tạm này nhanh chóng lấp đầy hạn ngạch 10 files. Khi đạt 10 files, hook kích hoạt `COORDINATOR WRITE DENIED` vĩnh viễn cho phần còn lại của session, khóa chặt cả `write_file` và `patch` ngay cả khi User đã ra lệnh trực tiếp ("làm đi", "Còn lại xử lý đi").
- **Chuẩn hóa**:
  1. **Tách bạch Ephemeral Paths**: Mọi đường dẫn thuộc thư mục tạm (`/tmp/`, `\tmp\`, `tmp_*.py`, `temp_*.py`, `reports/`) BẮT BUỘC được miễn trừ khỏi danh sách `t1_files` và `t1_lines`. Chỉ các file mã nguồn chính thức (core codebase/repo) mới tính vào hạn ngạch T1.
  2. **Tích hợp Bridge User Sudo**: `coordinator_write_gate` phải chủ động đọc và xác thực `D:/Taadaa/runtime/sudo_grant.json` để mở quyền ghi khẩn cấp ngay khi có grant hợp lệ từ User, không để cơ chế tự khóa trói chân hệ thống.

