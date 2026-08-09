# Recovery executor: Codex hết quota → Hermes CLI fallback (thiết kế 2026-08-07)

Task: "Implement Hermes CLI fallback cho auto recovery khi Codex hết quota" — sửa ở
automation-core + consumer `tiktok-luot nuoi acc`. Session này mới khảo sát kiến trúc +
dựng baseline (chưa sửa code — bị cắt iteration). Nội dung dưới là bản đồ kiến trúc đã
xác minh + thiết kế fix đã chốt, để session sau làm tiếp không phải khảo sát lại.

## Bản đồ kiến trúc (đã xác minh từ source)

Consumer `python_runner/scheduler/`:

- **`recovery_supervisor.py`**:
  - `PlannerStatus` (l.128): `READY / PROVIDER_UNAVAILABLE / NOT_READY / INVALID` — enum đã có sẵn.
  - `_PROVIDER_UNAVAILABLE_CODES` (l.137): ĐÃ chứa `quota_exhausted`, `quota_exceeded`,
    `quota_unavailable`, `provider_quota_429`, ... → **chỉ cần evidence code đúng là fallback
    gate nhận ngay, không phải thêm code mới**.
  - `_safe_provider_evidence` (l.185): chấp nhận mapping `{code, provider/model/effort/source}`
    với code ∈ danh sách trên; từ chối marker auth/policy/effort/duplicate. Cần ≥1 identifier
    (provider/model/source) hoặc `machine_readable: true`.
  - `PlannerResult.provider_unavailable(reason=, evidence=)` (l.284) + `ready_for_fallback`
    (l.309) = `status == PROVIDER_UNAVAILABLE` + evidence hợp lệ + digest.
  - `build_repair_command` (l.1213) / `build_advisor_command` (l.1250): LUÔN build
    `codex exec --model <m> --config model_reasoning_effort="<e>" --sandbox workspace-write
    --cd <repo> --output-last-message <path> -`; deepseek slot thêm
    `--config model_provider="9router"`. Không có nhánh CLI khác.
  - `DEEPSEEK_EXECUTOR_LADDER` (l.788): slot 1-7, `cmc/deepseek/deepseek-v4-flash|pro`,
    provider `9router`. `planner_preflight(role="executor")` admit luna/max + ladder này.
- **`recovery_runtime.py`**:
  - `_repair_with_codex` (l.2067): code != 0 + không parse được decision → trả
    `PlannerStatus.INVALID("gpt-planner-process-failed")` — **quota output của codex CLI
    KHÔNG được detect → không bao giờ kích fallback. Đây là gap chính.**
  - `_advise_with_codex` (l.2135): tương tự, `invalid("planner-process-failed")`.
  - `_run_capture` (l.809): `subprocess.run(capture_output=True, text=True)` — chỉ có
    (returncode, stdout+stderr merged), không có PTY.
  - `RecoveryRuntime.__init__` (l.883): default `deepseek_executor = _repair_with_codex`,
    `deepseek_planner_executor = _advise_with_codex` → **ladder deepseek fallback vẫn gọi
    `codex exec` → khi OpenAI/Codex provider hết quota, fallback cũng chết. "Fallback" hiện
    có chỉ là fallback MODEL, không phải fallback TOOL.**
  - Kích hoạt fallback (l.1918–1931): repair trả `ready_for_fallback` →
    `_activate_deepseek_executor_mode` (persist `provider_mode=deepseek_executor` +
    `LUNA_PROVIDER_UNAVAILABLE`) → `_run_deepseek_executor_mode` (l.1356) chạy ladder qua
    callback `deepseek_executor`. Persist qua restart (không probe Luna lại).
  - `_run_deepseek_executor_mode` cũng xử lý `ready_for_fallback` từ deepseek executor
    (l.1452) → ghi `DEEPSEEK_EXECUTOR_UNAVAILABLE`.

## Thiết kế fix đã chốt

1. **Detect quota trong `_repair_with_codex`/`_advise_with_codex`**: scan merged output
   (stdout+stderr) cho pattern `429 | usage limit | rate limit | quota | hit your ... limit`
   (case-insensitive) khi code != 0 → trả
   `PlannerResult.provider_unavailable(reason="quota_exhausted", evidence={"code": "quota_exhausted", "provider": "codex", "model": slot.model, "source": "codex-cli-output"})`
   thay vì `invalid("...process-failed")`. `_PROVIDER_UNAVAILABLE_CODES` đã nhận → `ready_for_fallback` True.
2. **Hermes CLI executor path**:
   - Contract đã xác minh qua `hermes --help`: `-z/--oneshot PROMPT` in CHỈ final response
     (dùng được cho scripts/pipes); `-m MODEL` + `--provider PROVIDER` override.
   - Hermes hiện đang chạy model `deepseek-v4-flash` / provider `custom:9router` (khớp
     `cmc/deepseek/deepseek-v4-flash` trong `DEEPSEEK_FALLBACK_MODELS`).
   - Lệnh: `hermes -z "<prompt>" -m deepseek-v4-flash --provider 9router` — KHÔNG có
     `--sandbox`/`--output-schema`/`--output-last-message` (khác codex); đọc kết quả từ stdout.
     Lưu ý: `-z` lấy prompt làm positional arg của flag, không phải stdin — build command
     khác hẳn codex (codex đọc stdin `-`).
   - Thêm `build_hermes_repair_command`/nhánh hermes trong `build_repair_command` theo
     provider/slot; thêm `_repair_with_hermes`/`_advise_with_hermes`; đổi default
     `deepseek_executor`/`deepseek_planner_executor` sang Hermes path (hoặc executor
     abstraction chọn CLI theo slot).
3. **Test offline**: (a) quota pattern → PROVIDER_UNAVAILABLE + evidence hợp lệ →
   `ready_for_fallback`; (b) build command trả `hermes -z` cho deepseek slot; (c) E2E qua
   `ScheduleRecoveryRuntime` + `patch("scheduler.recovery_runtime._run_capture")` trả output
   quota → outcome kích hoạt `DEEPSEEK_FALLBACK` executor Hermes.

## Environment gotcha (quan trọng khi chạy test recovery)

- `recovery_supervisor.py` import `from automation_core.global_recovery import GlobalRecoveryPolicy`
  trong `try/except ImportError: GlobalRecoveryPolicy = None` → wheel core cũ thiếu module
  này cài vẫn OK nhưng **constants tự rơi về hardcode** (`MAX_LIVE_RECOVERY_ATTEMPTS = 7`)
  và test vẫn pass → dễ tin nhầm policy đang chạy.
- Verify module tồn tại trước khi tin test: `python -c "import automation_core.global_recovery"`.
- Fix: `pip install --force-reinstall --no-deps "D:\Taadaa\automation-core\dist\automation_core-<ver>-py3-none-any.whl"`
  — **bắt buộc path Windows native `D:\...`; pip fail `OSError: No such file or directory:
  'D:\d\...'` nếu truyền MSYS path `/d/...`**.
- Baseline đã xác minh sau khi upgrade core 0.4.32→0.4.40 (wheel có `global_recovery.py`):
  consumer `tests/test_recovery_*.py` = 95 passed; core `test_global_recovery.py +
  test_recovery_contract.py + test_mandatory_recovery_contract.py` = 34 passed.
- Chạy pytest bằng venv Hermes (`/c/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python -m pytest`),
  cwd `python_runner/`; `.pytest_cache` Permission denied trên D:\ → thêm `-p no:cacheprovider`.

## Trạng thái worktree (bị cắt giữa chừng)

Branch sạch từ baseline: `feat/hermes-cli-fallback` (automation-core @ 68822dc),
`feat/hermes-cli-fallback-consumer` (consumer @ fb5b682). Worktree `git worktree add` từ
git-bash bị mangle path → đã move thư mục tay sang `D:\Taadaa\worktrees\` nhưng registration
git cũ chưa dọn → `git worktree add -b` báo "branch already exists". Trước khi code:
`git worktree remove <path> --force` + `git worktree prune` + `git branch -D <branch>`, rồi
`git worktree add -b <branch> "D:/Taadaa/worktrees/<name>" HEAD` (path native, forward slash).

## UPDATE 2026-08-07 — ĐÃ implement + LIVE, phát hiện lỗi parse fenced JSON

Fallback đã được implement (session sau) và recovery đang chạy thật với Hermes CLI:
- `recovery_runtime.py` giờ có `_repair_with_hermes` (l.2155) / `_advise_with_hermes` (l.2256),
  default `deepseek_executor`/`deepseek_planner_executor` trỏ sang Hermes path (l.915-916).
- `recovery_supervisor.py` khai báo Hermes exe path (l.91). Ledger ghi `provider_mode=deepseek_executor`,
  `LUNA_PROVIDER_UNAVAILABLE`, `DEEPSEEK_EXECUTOR_RESULT` — 113 lần gọi Hermes CLI.

**BUG LIVE (gốc rễ của "nhiều session Hermes hiện đang xử lý + FINAL_BLOCKED hàng loạt")**:
`_json_object` (recovery_runtime.py:703) chỉ parse (a) toàn string là 1 JSON object, hoặc
(b) JSON nằm gọn trên 1 dòng. Hermes CLI `-z` in kết quả dạng **markdown-fenced multi-line**
JSON:

    ```json
    {
      "decision": "PATCH_READY",
      "action": "...",
      ...
    }
    ```

→ parse ra `None` → caller fallback `{}` → `_write_deepseek_executor_result` ghi
`deepseek-executor-result.json` với toàn field rỗng → `DEEPSEEK_EXECUTOR_NOT_READY`
(reason `structured-patch-decision-required`) → ladder leo slot 1→2→3, mỗi slot 1 `hermes -z`
chạy cả vòng agent (UI hiện nhiều session "đang xử lý" đồng thời) → hết ladder →
`FINAL_BLOCKED` (99 lần trong ledger) dù model trả `PATCH_READY` hợp lệ.

**Triệu chứng / chẩn đoán nhanh** (ko cần đọc code):
- So 2 file trong run dir: `slot-N/repair-output.txt` (chứa JSON `PATCH_READY` đầy đủ)
  vs `slot-N/deepseek-executor-result.json` (rỗng `{"decision":"","action":"",...}`).
- Event counts ledger: `REPAIR_NOT_READY` / `DEEPSEEK_EXECUTOR_NOT_READY` cao,
  `FINAL_BLOCKED` reason `repair-ladder-exhausted-without-approved-patch`.

**Fix ĐÃ IMPLEMENT + TEST GREEN (2026-08-07, session này)**: `_json_object`
(recovery_runtime.py:703) giờ parse theo thứ tự: (1) whole stripped string → (2)
fenced block → (3) last embedded multi-line object trong prose → (4) reversed
single-line scan (fallback cũ giữ nguyên). Kèm unwrap 1 lớp `{"content": "{...}"}`.

### `_json_object` implementation đã chạy green — capture chi tiết

- **Fence regex**: `` ```(?:json)?\s*\n(\{.*?\})\r?\n\s*``` `` (DOTALL, non-greedy tới
  fence đóng; `\r?\n` chịu CRLF; fence không tag ` ``` ` cũng khớp).
- **Balanced-brace scan trong prose**: quét từng `{` bằng scan string-aware (trạng thái
  in_string/escaped) tìm `}` đóng cân bằng → `json.loads(span)`; **lấy object NGOÀI CÙNG
  cuối cùng** — mấu chốt: `{"a": {"b": 1}, "c": 2}` phải trả object ngoài, KHÔNG nhầm
  `{"b": 1}` (lỗi khi chỉ track start/end ngây thơ).
- **Unwrap 1 lớp**: `{"content": "{...json...}"}` → parse `content` (inner là `json.dumps`),
  trả dict trong nếu load được.
- **Test wrap**: inner JSON phải qua `json.dumps` (escaped), đừng để raw quote lồng nhau
  → vỡ outer JSON.
- Tests: `tests/test_recovery_runtime_hermes_parser.py` (12 case) + `test_recovery_runtime_parser.py`
  + `test_recovery_runtime_audit.py` = **19 passed**; ad-hoc `hermes-verify-` script dưới
  Temp = 10/10 PASS. CRLF: verify count (2964 CRLF / 0 LF-only).
- Lệnh chạy: `D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest
  tests/test_recovery_runtime_hermes_parser.py tests/test_recovery_runtime_parser.py
  tests/test_recovery_runtime_audit.py -q`.

## Restart chain để nạp code mới (bài học 2026-08-07)

Patch file KHÔNG đủ — `recovery_runtime` chạy trong memory, process cũ import code cũ.
Sau khi sửa parser, ledger VẪN ghi `structured-patch-decision-required` dù fix đã xong,
vì child PID cũ (khởi động 17:38) chưa reload. Phải restart chain đúng cách:

- **Chain**: task `TikTokScheduleRecovery` → powershell watch
  `scripts/run-schedule-recovery-watch.ps1` (watch-parent) → child
  `-m scheduler.recovery_runtime --watch --lease ... --watch-parent-pid <pid>`.
- **Restart an toàn**: (1) đọc lease `runs/schedule-recovery-watch-lease.json`, xác nhận
  `child_pid` == PID thật (identity match, không kill mù); backup lease trước; (2) stop
  child trước → watch tự thấy `HasExited` → exit; (3) `schtasks /run /tn
  "TikTokScheduleRecovery"` (qua `cmd //c`; bare `schtasks` trong git-bash fail im lặng);
  (4) verify lease MỚI (new lease_id/parent/child, state=running, heartbeat refresh) +
  log `runs/schedule-recovery-task.log` append + không double-run.
- Process check đáng tin: `wmic process where "ProcessId=N" get ProcessId,ParentProcessId,CreationDate,CommandLine`
  — tasklist filter qua MSYS trả trống dù process sống.
- Chi tiết identity-check + fail-closed: `references/orphan-watcher-runtime-verify.md`.

## 2 rule KHÁC NHAU — đừng trả lời nhầm khi user nói "rule đã lưu" (bài học 2026-08-07)

User hỏi "rule đã lưu, sao mày không tự làm?" về rule fix — mình trả lời bằng
COORDINATOR-WRITE GUARD (session read-only, dispatch worker) → user phải nhắc lại 2 lần
"ý tao hỏi là rule khi fix = AI tới đâu thì phải handle script theo". Có HAI rule độc lập:

1. **Coordinator-write guard** (AGENTS.md v8): session không tự patch, dispatch worker.
2. **Recovery/repair contract** (AGENTS.md "mọi fix thủ công bắt buộc handler" + Ui.md
   COMPAT-POST-VERIFY-003): AI (executor) chỉ được đi tới đề xuất **handler + test offline**
   (bounded); **script** (`recovery_runtime`) handle phần còn lại: parse decision → verifier
   → audit → live recapture. Fix thủ công/AI-tự-chạy-live = vi phạm.

Khi user nói "sao mày không làm theo rule" — hỏi/đối chiếu nghĩa: nếu nói về fix, nghĩa là
rule 2 (fix phải thành handler trong source + test, không để AI tự chạy live), KHÔNG phải
rule 1. Trả lời đúng câu hỏi: chỉ ra AI đã hoàn thành bound (PATCH_READY đầy đủ) và script
gãy ở khâu nào (VD parse), thay vì giải thích guard dispatch.

## PITFALL: `hermes -z` recovery session LÀ session thật trong desktop — interactable (2026-08-07)

Câu hỏi lặp lại của user: "recovery có mở session trong Hermes Desktop không? có bắt buộc
giữ desktop bật khi auto recovery chạy?" Trả lời ĐÚNG (xác minh state.db, không đoán):

- Recovery chạy **headless qua CLI** (`hermes -z`), KHÔNG cần GUI — Task Scheduler +
  CLI độc lập, desktop tắt vẫn chạy.
- NHƯNG mỗi `hermes -z` ghi **session record vào CÙNG `state.db` mà desktop đọc**
  (`source='cli'`, cwd = repo consumer, msgs đầy đủ) → session **hiện trong sidebar
  desktop** dưới project, và **nhắn tiếp được như session thường** (không có flag
  oneshot-locked; user nhắn → trả lời bình thường trong context bounded-prompt).
- Vì vậy: **CẤM khẳng định "recovery không gửi session vào desktop" hoặc "session CLI
  không tương tác được"** — đó là session thật trong cùng DB, desktop chỉ là UI render
  danh sách. Đúng = "recovery spawn headless CLI, nhưng session vẫn nằm cùng DB nên
  desktop hiện + nhắn tiếp được; desktop không cần bật cho recovery tự chạy, chỉ cần
  khi muốn xem/nhắn".
- Cách check nhanh ai tạo session: `python -c` đọc `C:\Users\Kibe\AppData\Local\hermes\state.db`
  (bảng `sessions`, cột `source` = cli/desktop/subagent, `cwd`) — chứng cứ trước khi
  trả lời, tránh phán đoán sai như session này.

## Commit + verify độc lập fix parser (bổ sung 2026-08-07)

- Commit: `3e47dfb4b227317fa6f463df5034a72d6e2b6253` `fix(recovery): parse
  fenced/embedded JSON from Hermes CLI output in _json_object` — đúng 2 file
  (`recovery_runtime.py` + `tests/test_recovery_runtime_hermes_parser.py`), không đụng
  file consumer khác đang sửa dở (multi-session shared repo: chỉ `git add` file mình).
- Verify độc lập sau worker tự báo pass: chạy lại `_json_object` trên **artifact fail
  THẬT** `slot-1/repair-output.txt` (parse ra PATCH_READY + handler_id + action, trước
  đây file kết quả rỗng) — test fixture không đủ, phải replay đúng artifact gốc.
- CRLF check: 2964 CRLF / 0 LF-only sau patch.

## UPDATE 2026-08-08 — 2 bug live nữa (schema oneOf + quota regex false-positive) + prompt tiếng Việt

1. **Codex API TỪ CHỐI `oneOf` trong repair schema**: `_repair_with_codex` viết
   `"evidence": {"oneOf": [object, array]}` — Codex `--output-schema` trả
   `ERROR: Invalid schema ... 'oneOf' is not permitted` → mọi lần repair fail
   `structured-patch-decision-required` → 7 máy FINAL_BLOCKED dù advisor Codex chạy tốt.
   **Fix: thay bằng `"evidence": {}`** (giữ trong `required`, chấp nhận mọi dạng) —
   99 test pass. Triệu chứng nhận nhanh: repair-output.txt có `ERROR: ... oneOf' is not permitted`.
2. **Quota regex false-positive**: `_QUOTA_MARKERS` chứa bare `429|403` → match cả số
   bình thường trong data artifact (`"source_row": 403`) mà Codex copy vào output →
   `detect_provider_quota` trả `quota_exhausted` → **kích hoạt nhầm deepseek_executor
   (Hermes fallback)** cho máy không hề hết quota. Fix: `429|403` → chỉ khớp khi có
   HTTP context: `\b(?:HTTP|status|code)[ /:=]*[45][0-9]{2}\b` (test mới
   `test_quota_status_codes_require_http_context`). Bài học: regex số hiếm — phải đòi
   token context, không list số trần.
3. **Recovery worker output phải tiếng Việt** (user yêu cầu đọc được): thêm câu
   "Trả lời bằng tiếng Việt..." vào cả 4 prompt template
   (`_repair_with_codex`/`_repair_with_hermes`/`_advise_with_codex`/`_advise_with_hermes`)
   trong `recovery_runtime.py` — giữ enum máy-đọc (PATCH_READY...), strategy_id, handler_id,
   tên file/test bằng tiếng Anh.
4. **Restart runtime = restart chain**: đã xác nhận lại đúng quy trình (backup lease →
   taskkill child → watch tự exit → `schtasks /run` qua PowerShell `Start-ScheduledTask`
   thay cmd //c nếu cmd bị nuốt → verify lease MỚI (new lease_id/parent/child, state=running)
   + không double-run). Code mới chỉ có hiệu lực sau restart; incident slot đang chạy khi
   restart → `LIVE_ATTEMPT_UNKNOWN_AFTER_CRASH` (fail-closed đúng, không blind-retry).
5. Verification findings: `_json_object` fix 08-07 đã đủ cho fenced/embedded 1 lớp
   (`{"content":...}`) — sau restart, Hermes deepseek-pro trả JSON fenced đầy đủ parse
   được. Khi repair fail dù JSON hợp lệ: so `repair-output.txt` vs
   `deepseek-executor-result.json` (rỗng) = script parse fail, đừng đổ lỗi worker.


