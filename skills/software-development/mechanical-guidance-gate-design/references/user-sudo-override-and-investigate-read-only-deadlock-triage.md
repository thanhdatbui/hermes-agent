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
3. **O(1) Hard Ceilings**:
   - Maximum 1-2 files, diff <= 30 lines total.
   - Mandatory focused test execution < 30s immediately following modification.
   - Forbidden zones that CANNOT be bypassed even via Sudo: system rule directories, .env, credentials, account databases.
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
