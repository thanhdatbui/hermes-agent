# Kiến Trúc Farm Coordinator Guard (State Guard + Action Guard)

Tư vấn kiến trúc bởi: **Claude Opus & Claude Sonnet CLI** (05/09/2026).
Đã kiểm chứng thực tế & đạt **PRODUCTION-READY VERDICT** qua 5 concurrent OS processes stress test trên Windows.

## 1. Bối cảnh & Vấn đề Cốt Lõi
Trong hệ thống Multi-Agent Taadaa Farm (Hermes Coordinator + Worker Subagents):
1. **Lỗi 1 (State-based - Farm Alert `[MÁY N]`):** Khi nhận alert, Coordinator bị "ngứa tay" chạy 5–10 lệnh terminal (ls, grep, đọc log, test import) để điều tra sâu trước khi chịu dispatch subagent.
2. **Lỗi 2 (Action-based - Giao việc chạy Batch/Script dài):** Khi người dùng giao việc thông thường ở trạng thái IDLE ("chạy batch upload Tik2", "chạy batch 12 proxy GPM", "checklive 226 mail"), Coordinator lại tự tiện gõ `terminal` chạy script dài (5–25 phút) trực tiếp tại session chính, gây:
   - **Treo session chính (Session Lock):** Chặn toàn bộ luồng chat, người dùng hỏi han hay can thiệp thì bot bị treo (`Operation interrupted`).
   - **Tràn context (Context Bloat):** Log chạy batch xả hàng vạn ký tự vào context, kích hoạt compaction làm rơi rụng các chỉ thị quan trọng.
- **Nguyên lý Claude Opus & Sonnet:**
  > *"Đừng bao giờ tin LLM tự kỷ luật với một tool đang nằm trong tay nó. Mọi thứ đặt trong context/prompt đều là 'gợi ý' mà LLM có thể tự thương lượng lại với chính mình. Muốn khóa chặt bắt buộc phải dùng cơ chế bên ngoài (External Deterministic Guard) kết hợp giữa State Guard và Action Guard."*

---

## 2. Kiến Trúc Bảo Vệ 2 Trục (Two-Tier Enforcement v2.0)

```
                       Tool Call đến (PreToolUse Hook)
                                     │
  ┌──────────────────────────────────┴──────────────────────────────────┐
  ▼                                                                      ▼
[TRỤC 1: STATE GUARD (Session-Scoped)]                [TRỤC 2: ACTION GUARD]
(Chặn theo pha Alert / Worker per session)            (Chặn long-runner kể cả khi IDLE)
  │                                                                      │
  ├─ Phase ALERT:                                                        ├─ Tầng 1: ALLOWLIST (O(1) ops)
  │  * Investigative Tools (read_file, search_files,                     │  git, psutil, adb devices,
  │    patch, write_file, execute_code) -> HARD BLOCK.                   │  inspect_machine, py_compile -> CHO QUA
  │  * Terminal: Ngân sách inspect = 1 lệnh O(1).                        │
  │    Lệnh 2 trở đi -> HARD BLOCK.                                      ├─ Tầng 2: ESCAPE TOKEN (v2.0 DB Verified)
  │                                                                      │  Subagents (parent_session_id trong state.db)
  ├─ Phase WORKER_RUNNING:                                               │  hoặc TAADAA_WORKER=1 -> CHO QUA 100%
  │  Worker đang chạy -> BLOCK probe.                                    │
  │  (Auto-expire 20p chống deadlock)                                    └─ Tầng 3: DENYLIST (Long-runners & Probes)
  │                                                                         .ps1 (kèm quotes/spaces), run_*batch*,
  ├─ Phase CLOSEOUT:                                                        upload_video, checkmail, reg_*,
  │  Chốt phiên 6 Gate -> MỞ (Expire 2h).                                   python -c (subprocess/loop/exec) ->
  │                                                                         HARD BLOCK, ÉP DELEGATE_TASK!
  └─ Phase IDLE:
     Chuyển tiếp sang Trục 2 kiểm tra.
```

---

## 3. Mô Hình FSM 4 Trạng Thái (State Guard)

File trạng thái: `$HERMES_HOME/farm_coordinator_phase.json` (bảo vệ bằng atomic exclusive `.lock` file kèm stale lock TTL check).

```
IDLE ──Farm Alert [MÁY N]──► ALERT ──(inspect budget = 0)──► BẮT BUỘC DISPATCH
                               │
                         delegate_task()
                               ▼
                        WORKER_RUNNING ──Worker done / Auto-expire (20m)──► IDLE / CLOSEOUT
                               │
               User: "chốt phiên" / "/closeout"
                               ▼
                           CLOSEOUT ──(6 Gate G0-G4 / Auto-expire 2h)──► IDLE
```

1. **`ALERT` (Khi nhận Farm Alert):**
   - Kích hoạt khi `user_message` khớp regex: `\[MÁY\s+\d+\]|\[FARM\s+ALERT|Farm\s+Alert`.
   - Cấp ngân sách cứng: `inspect_budget = 1`.
   - Cho phép duy nhất 1 lệnh terminal khớp `inspect_machine.py <N>` hoặc `adb devices`.
   - Mọi lệnh terminal thứ 2 trở đi bị PreToolUse Hook **chặn cứng (action: block)**.
   - Cửa thoát hợp lệ duy nhất: gọi `delegate_task` để Worker Subagent xử lý trong context riêng.

2. **`WORKER_RUNNING` (Khi Worker đang làm việc & Chống Deadlock):**
   - Kích hoạt tự động khi Coordinator gọi `delegate_task`.
   - Khóa terminal tại session chính (chỉ cho phép lệnh đọc trạng thái git an toàn).
   - **Chống kẹt Deadlock:** Tự động hết hạn (auto-expire) sau 20 phút (hoặc sau 5 phút nếu user gửi prompt mới chuyển việc khác), đưa FSM về lại `IDLE` và ghi đĩa tức thì.

3. **`CLOSEOUT` (Chốt phiên 6 Gate):**
   - Kích hoạt khi `user_message` khớp: `chốt phiên|đóng phiên|chốt session|/closeout`.
   - Mở toàn quyền terminal tại session chính để chạy 6 Gate: G0 Canary $\rightarrow$ G0.5 Docs $\rightarrow$ G1 Plan-Review $\rightarrow$ G2 Commit $\rightarrow$ G3 Rebase $\rightarrow$ G4 Push.
   - **Bảo vệ rò rỉ quyền:** Tự động khóa lại (auto-expire) về `IDLE` sau 2 giờ (`CLOSEOUT_TIMEOUT_SECONDS = 7200`) nếu người dùng không thao tác.

4. **`IDLE` (Trạng thái bình thường):**
   - Hoạt động cho các lệnh thông thường O(1), nhưng bị giám sát bởi Action Guard (Trục 2).
   - **Giải quyết Chicken-and-Egg Session ID:** Luôn ghi nhận/cập nhật `session_id` của Coordinator vào state file ngay cả trong phase IDLE để nhận diện chính xác Subagent thoát hiểm. Mở khóa thủ công qua `/reset_guard`.

---

## 4. Cơ Chế 3 Tầng Lọc Lệnh (Action Guard)

Áp dụng cho mọi lệnh terminal ở session chính (kể cả khi `phase = IDLE`):

### Tầng 1: ALLOWLIST (O(1) Operations — Luôn cho qua)
- Git: `git status`, `git log`, `git diff`, `git add`, `git commit`, `git push`, `git rebase`, ...
- Kiểm tra nhanh: `psutil`, `tasklist`, `Get-Process`, `ls`, `cat`, `head`, `tail`, `wc`, `which`.
- Chẩn đoán O(1): `python D:/Taadaa/tools/inspect_machine.py <N>`, `adb devices`, `python -m py_compile ...`, `python --version`.
- Tư vấn: `claude -p "..."`.

### Tầng 2: ESCAPE TOKEN (Cơ chế thoát hiểm hợp lệ)
- **Subagents:** Khi chạy qua `delegate_task`, subagent sở hữu `session_id` riêng biệt (khác `coordinator_session_id`) $\rightarrow$ Hook tự động bỏ qua, worker chạy script thoải mái.
- **Biến môi trường:** Chỉ chấp nhận `TAADAA_WORKER=1` trong môi trường tiến trình thực tế (`os.environ`). Đã gỡ bỏ việc check chuỗi text trong command để ngăn Coordinator tự gõ chuỗi lách luật.

### Tầng 3: DENYLIST (Long-Runners & Inline Probes — Bị chặn đứng tại session chính)
Khớp các pattern kịch bản chạy dài:
- Powershell runners (Space-tolerant & Quotes-tolerant trên Windows): `run_.*batch.*\.ps1`, `(?:"[^"]*"|\x27[^\x27]*\x27|\S+)\.ps1\b`.
- Video batch: `upload[_-]?video`, `upload_tik`.
- Checklive / Mail: `checkmail`, `reg[_-]?(tiktok|gmail)`.
- Browser / Automation: `playwright`, `gpm.*(auto|proxy|script)`.
- Batch loop: `\bpython\b.*\b(run_batch|batch_|run_all|check_live|untouched_proxies)\b`, `for.*in.*do`, `while.*\$true`.
- Python inline probe: `\bpython\s+-c\b.*(subprocess|playwright|while|for\s+.*in|openpyxl|adb|exec|importlib)\b`.

---

## 5. Bằng Chứng Thực Nghiệm Concurrency Stress Test trên Windows

Để bảo đảm tính nguyên tử (Atomicity) của file lock `os.O_CREAT | os.O_EXCL | os.O_RDWR` trên Windows NTFS mà không cần cài thêm thư viện ngoài (như `portalocker` hay `redis`):
- Đã khởi chạy stress test với 5 tiến trình OS độc lập chạy đồng thời tranh chấp file lock.
- **Kết quả thực tế:**
  ```text
  Execution sequence (5 concurrent OS processes on Windows):
    Worker 0 START at 1788614609.7352188
    Worker 0 END at 1788614609.8362346
    Worker 3 START at 1788614609.8482578
    Worker 3 END at 1788614609.9492452
    Worker 4 START at 1788614609.9632406
    Worker 4 END at 1788614610.0652695
    Worker 2 START at 1788614610.0802429
    Worker 2 END at 1788614610.18126
    Worker 1 START at 1788614610.191243
    Worker 1 END at 1788614610.2931404
  >>> Multi-process Concurrency Stress Test: PASSED WITH ZERO VIOLATIONS! <<<
  ```
- 100% tuân thủ loại trừ tương hỗ (Mutual Exclusion), không double-acquire, không crash `PermissionError`, và tự động phá stale lock khi quá 10s.

---

## 6. File Triển Khai Thực Tế

- **Plugin:** `~/.hermes/plugins/farm-coordinator-guard/`
  - `plugin.yaml`: Khai báo hooks `pre_llm_call`, `pre_tool_call` (version 2.0.0).
  - `__init__.py`: Mã nguồn thực thi 2 trục bảo vệ (State Guard v2.0 session-scoped + Action Guard, khóa cứng toàn bộ investigative tools `read_file`, `search_files`, `patch`, `write_file`, `execute_code` ở Phase ALERT, xác thực worker qua SQLite `state.db`, atomic lock, auto-cleanup session > 2h).
- **Lệnh kích hoạt:** `hermes plugins enable farm-coordinator-guard`
- **Kiểm tra trạng thái:** `hermes plugins list --plain | grep farm-coordinator-guard`

---

## 7. Bài Học Thực Tế Từ Production (05/09/2026): Multi-Session Race Condition & UI Signals

### 1. Dấu hiệu nhận biết trên UI Telegram
- Khi Hermes Gateway chạy, dòng trạng thái live cập nhật dạng:
  `⚙️ Working — <N> min — iteration <X>/<Y>, <tool_name>` (ví dụ: `⚙️ Working — 3 min — iteration 16/200, terminal`).
- **Ý nghĩa:** Đây là counter vòng lặp của **session chính hiện tại**. Nếu nó hiển thị `<tool_name> = terminal`, nghĩa là Coordinator đang tự tay gọi terminal trực tiếp, **chưa dispatch worker subagent** qua `delegate_task`.
- Khi đã `delegate_task`, session chính sẽ dừng ngay (`[SILENT]`), worker chạy ngầm ở session con và không hiển thị counter terminal trên session chính.

### 2. Cạm bẫy Multi-Session State Overwrite (Lỗ hổng Escape Token `!= coord_session`) & Bỏ Sót Investigative Tools
- **Triệu chứng thực tế:** Khi có nhiều máy alert dồn dập trong thời gian ngắn (ví dụ Máy 19 lúc 21:22, Máy 46 lúc 21:23, Máy 74/23/41 lúc 21:24):
  - File `$HERMES_HOME/farm_coordinator_phase.json` ở bản v1 lưu một `session_id` toàn cục duy nhất.
  - Alert của Máy 46 ghi đè `session_id` mới vào file JSON.
  - Logic thoát hiểm kiểm tra:
    ```python
    if coord_session and session_id and session_id != coord_session:
        return None  # Coi là subagent -> Cho qua!
    ```
  - Hậu quả: Session của Máy 19 bị xem là `session_id != coord_session`, hook nhận diện nhầm session chính Máy 19 thành subagent worker và mở toang quyền terminal cho Coordinator tự mò mẫm hơn 20 lệnh terminal!
  - Đồng thời, bản v1 chỉ check `tool_name == "terminal"`, hoàn toàn không chặn `read_file` hay `search_files`, khiến Coordinator lách qua đọc file và tìm kiếm hàng chục lượt gây chạm mốc iteration 16/200 trên UI.

- **Chuẩn khắc phục v2.0 (Đã kiểm chứng & triển khai vào plugin):**
  1. **Tách biệt FSM State theo Session (Session-Scoped State):** State JSON lưu dạng `{"sessions": {<session_id>: {"phase": "ALERT", "inspect_budget": 1, ...}}}` với atomic lock file `.lock` và hàm dọn dẹp session cũ quá 2 giờ (`SESSION_EXPIRY_SECONDS = 7200`). Các phiên chat/máy alert chạy song song không bao giờ đè trạng thái của nhau.
  2. **Nhận diện Subagent chuẩn xác qua SQLite `state.db`:** Không dùng so sánh phủ định `!= coord_session`. Subagent chỉ được miễn trừ khi truy vấn có `parent_session_id IS NOT NULL` từ bảng `sessions` của Hermes `state.db` HOẶC cờ `TAADAA_WORKER=1` trong môi trường tiến trình:
    ```python
    def _is_worker_session(session_id: str) -> bool:
        if not session_id:
            return False
        if os.environ.get("TAADAA_WORKER") == "1":
            return True
        try:
            db_path = Path(os.environ.get("HERMES_HOME", Path.home() / "AppData" / "Local" / "hermes")) / "state.db"
            if db_path.is_file():
                with sqlite3.connect(str(db_path), timeout=2.0) as con:
                    row = con.execute("SELECT parent_session_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
                    if row and row[0]:  # Có parent_session_id -> CHẮC CHẮN là Worker Subagent
                        return True
        except Exception:
            pass
        return False
    ```
  3. **Khóa toàn bộ Investigative Tools ở Phase ALERT:**
    ```python
    INVESTIGATIVE_TOOLS = frozenset({"read_file", "search_files", "patch", "write_file", "execute_code"})
    if phase == "ALERT" and tool_name in INVESTIGATIVE_TOOLS:
        return {
            "action": "block",
            "message": "⛔ [FARM GUARD - PHASE: ALERT] CẤM Coordinator đọc/sửa file ở session chính! Bắt buộc gọi delegate_task!"
        }
    ```
    Coordinator chỉ được chạy duy nhất 1 lệnh inspect O(1) terminal (`inspect_machine.py <N>` hoặc `adb devices`), toàn bộ các lệnh tìm kiếm/đọc file/chạy script khác bị chặn đứng hoàn toàn.

  4. **Kiểm thử nghiệm thu v2.0 (Test Suite 100% PASS):**
    - `Test 1`: Coordinator nhận Farm Alert -> gọi `read_file` -> bị block ngay lập tức.
    - `Test 2`: Coordinator gọi `terminal` (inspect O(1)) -> pass lần 1, tiêu hao ngân sách. Lần 2 -> bị block.
    - `Test 3`: Subagent Worker (có `parent_session_id` trong DB) -> gọi cả `terminal` lẫn `read_file` -> pass 100%.
    - `Test 4`: Multi-session stress -> Session B nhận alert sau KHÔNG BAO GIỜ đè hỏng trạng thái của Session A.
    - `Test 5`: IDLE chặn long-runners; CLOSEOUT mở 6 Gate thành công.
    - `Test 6`: Stale session cleanup tự động dọn session cũ > 2 giờ.

---

## 8. Nâng Cấp v2.1: WorkerToolGate (Anti-Analysis Paralysis Cho Subagents)

### 1. Bối cảnh & Vấn đề Cốt Lõi
Ở bản v2.0, khi một phiên được xác định là Subagent Worker (`_is_worker_session == True`), hook trả về `None` (Escape Token cho qua 100%).
Tuy nhiên, thực tế phát sinh hiện tượng **Analysis Paralysis ở Worker**:
- Khi nhận task, worker có xu hướng lặp lại `read_file` và `search_files` nhiều lượt liên tục (đọc lan man từ hàm này sang hàm khác, đọc phân trang) thay vì áp dụng patch ngay.
- Kết quả: Worker tiêu tốn 15–35 tool calls mà chưa hề chạm vào đĩa để sửa code, dẫn tới chạm trần `max_iterations = 35` hoặc cạn ngân sách phiên.

### 2. Kiến Trúc 3 Trục (Three-Tier Hard Guard v2.1)
Thay vì bypass 100%, Worker được kiểm soát bởi **`WorkerToolGate`**:

```
                              pre_tool_call hook
                                      │
                        _is_worker_session(session_id)?
                                ├── YES ──► [TRỤC 3: WORKER TOOL GATE]
                                │             ├─ READ_BUDGET = 3 (read_file/search_files)
                                │             ├─ WRITE_DEADLINE = 4 (Phải có write_file/patch)
                                │             └─ Test tools (terminal/py_compile/git diff) -> PASS
                                └── NO  ──► [TRỤC 1 & 2: COORDINATOR GUARD]
                                              ├─ Trục 1: State Guard (ALERT/WORKER/CLOSEOUT)
                                              └─ Trục 2: Action Guard (Allowlist/Denylist)
```

### 3. Quy Tắc Hoạt Động & Mã Lệnh
Trạng thái được lưu per-session trong cấu trúc:
```python
worker_state: Dict[str, Dict[str, int]] = {}
# session_id -> {"read_count": 0, "write_count": 0, "call_count": 0}
```

- **Quy tắc 1 (READ_BUDGET = 3):**
  Nếu `tool_name in ("read_file", "search_files")` và `read_count >= 3`:
  Trả về `action: block` với thông báo:
  `⛔ [WORKER TOOL GATE - READ BUDGET EXHAUSTED]: Ngân sách đọc của Worker đã hết (3/3). Bạn BẮT BUỘC phải gọi write_file hoặc patch ngay bây giờ theo patch_intent! CẤM tiếp tục khảo sát lan man.`

- **Quy tắc 2 (WRITE_DEADLINE = 4):**
  Nếu `call_count >= 4` và `write_count == 0` và `tool_name in ("read_file", "search_files")`:
  Trả về `action: block` với thông báo:
  `⛔ [WORKER TOOL GATE - WRITE DEADLINE]: Đã qua 4 tool calls mà chưa có thao tác write_file/patch nào. Mọi công cụ đọc đã bị KHÓA CỨNG. Bạn BẮT BUỘC phải ghi bản vá (write_file/patch) ngay lập tức!`

- **Xử lý Thao tác Ghi & Kiểm Thử:**
  * Khi gọi `write_file` hoặc `patch`: tăng `write_count += 1`, `call_count += 1`, luôn cho phép (`return None`).
  * Các công cụ test/compile (`terminal` chạy py_compile / pytest, `git diff`, etc.) vẫn được phép để worker kiểm thử bản vá sau khi viết code.

---

## 9. Nâng Cấp v2.3: Hard Gate Kiểm Tra Đường Dẫn Tuyệt Đối (Scope Lock Gate Cho `delegate_task`)

### 1. Bối cảnh & Vấn Đề Gốc Rễ (Scope Lock Failure)
- **Hành vi lệch lạc của Coordinator:** Khi dispatch `delegate_task`, Coordinator thường giao việc chung chung hoặc mở ("hãy vào repo Taadaa kiểm tra file monkey", "xem cấu hình trong automation-core").
- **Hệ quả đối với Worker Subagent:**
  - Worker khởi tạo tại thư mục mặc định `C:\Users\Kibe`. Khi không có đường dẫn tuyệt đối, Worker mất 5–10 lượt tool calls lượn qua các ổ đĩa `C:`, `D:`, đọc nhầm repo hoặc chạm mốc giới hạn vòng lặp mà chưa sửa được code.
  - Thậm chí Coordinator bịa ra đường dẫn ảo tưởng không có thật trên đĩa, khiến Worker rơi vào vòng lặp tìm kiếm bế tắc.

### 2. Thiết Kế Hai Tầng Kiểm Soát (Two-Stage Scope Lock Gate)
Tại hook `_on_pre_tool_call` khi phát hiện `tool_name == "delegate_task"`:

1. **Nhận diện Task Sửa Code / Farm:**
   Quét `goal` và `context` (cả trường đơn lẻ lẫn danh sách `tasks=[...]`):
   ```python
   _CODE_WORK_RE = re.compile(r"\b(sửa\s+code|fix\s+code|patch|bug|test|inspect|chạy\s+test|taadaa|farm)\b", re.IGNORECASE)
   _ABS_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/][^\s\'\"<>]+|/(?:[a-zA-Z]|c|d)/[^\s\'\"<>]+)")
   ```

2. **Gate 1: Kiểm Tra Sự Tồn Tại Của Đường Dẫn Tuyệt Đối:**
   - Trích xuất toàn bộ path dạng Windows (`D:\...`, `C:/...`) hoặc MSYS (`/c/...`, `/d/...`) từ `context`.
   - Nếu không có bất kỳ đường dẫn tuyệt đối nào: **Chặn đứng cuộc gọi (HARD BLOCK)**.

3. **Gate 2: Xác Thực File Thật Trên Đĩa (`os.path.exists`):**
   - Kiểm tra ít nhất một đường dẫn tuyệt đối trích xuất được phải tồn tại thật sự trên filesystem.
   - Nếu toàn bộ đường dẫn đều không tồn tại (đường dẫn ảo/bịa): **Chặn đứng cuộc gọi (HARD BLOCK)**.

4. **Thông báo Chặn Chuẩn Hóa:**
   ```text
   ⛔ [FARM GUARD - SCOPE LOCK VIOLATION]: delegate_task bị từ chối!
   Coordinator BẮT BUỘC phải cung cấp đường dẫn tuyệt đối (Absolute Path) đến file cần xử lý và file đó phải tồn tại trên đĩa. CẤM giao việc mở/mò file!
   ```

### 3. Ngoại Lệ Hợp Lệ (Escape Token & Non-Code Tasks)
- Các subagent mang token `_is_worker_session` (có `parent_session_id` hoặc biến môi trường `TAADAA_WORKER=1`) hoàn toàn được miễn trừ.
- Các task không liên quan đến sửa code farm (như benchmark nội bộ, tra cứu docs thuần túy) không bị chặn nhầm.

### 4. Ma Trận Kiểm Thử Nghiệm Thu (Pytest Suite)
- `test_dispatch_no_abs_path`: Dispatch task sửa code farm nhưng không có path tuyệt đối -> **BLOCKED** (`SCOPE LOCK VIOLATION`).
- `test_dispatch_fake_abs_path`: Dispatch kèm path tuyệt đối bịa không tồn tại trên đĩa -> **BLOCKED** (`SCOPE LOCK VIOLATION`).
- `test_dispatch_valid_real_path`: Dispatch kèm path file thật tồn tại trên đĩa và bằng chứng hiện trường -> **PASS** (trạng thái chuyển sang `WORKER_RUNNING`).
- `test_worker_escape_token`: Dispatch khi có cờ `TAADAA_WORKER=1` -> **PASS** (miễn trừ kiểm soát Coordinator).


