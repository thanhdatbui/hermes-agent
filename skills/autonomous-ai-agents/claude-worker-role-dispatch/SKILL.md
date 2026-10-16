---
name: claude-worker-role-dispatch
description: "Dispatch Claude CLI with role, turns cap and gate."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [claude, worker, dispatcher, role-based, quota-gate, turns-cap, farm-safety]
    related_skills: [claude-limit-protection, hermes-orchestration-dispatcher, monolith-modularization-and-architecture-gates]
---

# Claude Worker Role-Based Dispatch

Use this skill when calling Claude Code CLI for any task on the Taadaa Farm. All Claude CLI invocations MUST go through `D:/Taadaa/tools/claude_worker.py`, never via raw `claude -p` in terminal.

## Context: The 72-Turn Disaster (15/10/2026)

When a Coordinator bypassed the Guard by running `claude -p "..." --dangerously-skip-permissions > log.txt 2>&1` without `--model` or `--max-turns`, Claude Sonnet 5.5 ran **72 agentic turns** freely in a 112K-token workspace, consuming **2.117.100 tokens** and pushing quota from 5% to 98% in 20 minutes.

---

## Role Configurations

| Role | Model | Default Turns | Hard Cap Turns | Tools | Fallback |
|------|-------|--------------|----------------|-------|---------|
| `worker` | claude-haiku-5-5 | 8 | **15** | Read,Edit,Write,Bash | `ag_cli.py fix` |
| `planner` | claude-sonnet-5-5 | 6 | **10** | Read,Bash | `ag_cli.py ask` |
| `reviewer` | claude-sonnet-5-5 | 4 | **8** | Read,Bash | `ag_cli.py ask` |

## Usage

```bash
# Worker (Haiku, max 15 turns)
python D:/Taadaa/tools/claude_worker.py --role worker --timeout 55 "Fix the logic in..."

# Planner (Sonnet, max 10 turns, read-only)
python D:/Taadaa/tools/claude_worker.py --role planner --timeout 75 "Design the interface..."

# Reviewer (Sonnet, max 8 turns, read-only)
python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 6 --timeout 55 "Review: ..."

# Quota check
python D:/Taadaa/tools/claude_worker.py --check-quota
```

## Key Safety Mechanisms

### 1. Hard-Cap Turns Clamping
```python
max_turns = max(1, min(args.max_turns or role_cfg["default_turns"], role_cfg["hard_cap_turns"]))
```
Even `--max-turns 999` gets clamped to the role's `hard_cap_turns`.

### 2. Read-Only Enforcement for Planner/Reviewer
```python
if role in ("planner", "reviewer"):
    cmd += ["--disallowedTools", "Edit,Write,NotebookEdit"]
    cmd += ["--dangerously-skip-permissions"]
else:
    cmd += ["--allowedTools", role_cfg["allowed_tools"]]
    cmd += ["--dangerously-skip-permissions"]
```

### 3. Role-Aware Quota Fallback
- `planner` và `reviewer` → `ag_cli.py **ask**` (read-only analysis).
- `worker` → `ag_cli.py **fix**` (code repair allowed).

### 4. Stale Quota Detection: `MAX_QUOTA_STALE_HOURS = 2.0`.

### 5. Narrow Limit Markers (no false positives):
- `"hit your session limit"`
- `"you've hit your limit"`

---

## Standard 3-Phase Workflow for Modules > 200 Lines

**Phase 1 — PLAN (`--role planner`, ≤ 6 turns):**
Sonnet reads requirements; outputs function list, signatures, acceptance criteria into a temp file.

**Phase 2 — BUILD (`--role worker`, ≤ 8 turns/chunk):**
Haiku implements each function as thin-slices (≤ 2 files, ≤ 80 lines). Runs pytest after each.

**Phase 3 — REVIEW (`--role reviewer`, ≤ 4–6 turns):**
Sonnet reads git diff and test suite; outputs APPROVED or REJECTED with specific findings.

---

## Cross-Family Review Discipline

Both `--role reviewer` (Sonnet/Anthropic) AND Closeout Gate (Sol High/OpenAI) are required:
1. **Blind spots within same family:** Haiku and Sonnet may share reasoning blind spots.
2. **Sol High is free:** 115 ChatGPT Web accounts on `:20129`, zero Claude quota consumed.
3. **Closeout Gate enforces physically:** diff budget ≤ 30KB, pytest in isolation, ≥ 85/100 rubric to push.

---

## Pitfalls

- **CẤM DÙNG CLAUDE SONNET ĐỌC FILE VẶT (Quota Bleeding Disaster 15/10/2026):** Tuyệt đối không dùng `--role planner` (Sonnet 5.5) cho các tác vụ chỉ đọc vài chục dòng code, kiểm tra diff hoặc tìm kiếm file. Đọc file/diff phải dùng tool local hoặc Python $O(1)$ để bảo vệ quota 5h không bị đốt sạch từ 69% lên 100% trong 15 phút.
- **CẤM AGENT TỰ Ý OVERRIDE QUOTA GUARD:** Lệnh `claude_quota_guard.py allow <minutes>` là đặc quyền DUY NHẤT của Con người (User). Agent tuyệt đối cấm tự ý gõ lệnh mở rào quota của chính mình khi bị chặn.
- **CẤM DÙNG AG CLI (GEMINI) LÀM REVIEWER:** AG CLI chỉ là worker sửa code (`fix`) hoặc phân tích logic (`ask`). Tuyệt đối không được gán vai Reviewer cho AG CLI/Gemini để tự phê duyệt `[APPROVED]` thay thế Claude Sonnet / Sol High (vi phạm nghiêm trọng nguyên tắc Cross-Family Review).
- **KỶ LUẬT PHÂN LOẠI LỖI & RETRY CHO HAIKU (Intelligent Failure Classification & 2-Attempt Ladder):** Haiku thất bại không chỉ vì hết quota mà còn do kẹt turns/scope. CẤM ném ngay sang Agy CLI khi Haiku còn quota. Haiku là worker O(1) (10-15s), CẤM giao việc tự phân rã kiến trúc mở (sẽ đốt sạch 8-15 turns chỉ để đọc file rồi fail `error_max_turns`). Coordinator bắt buộc phân rã trước thành contract O(1). Khi Haiku fail ở attempt 1:
  1. *QUOTA (session limit, 429, exit 127):* Fallback ngay sang Agy CLI fix (reason: `quota_exhausted`).
  2. *ENV (sai path, thiếu tool, exit 126):* Dừng ngay lập tức, cấm gọi Agy CLI bừa bãi.
  3. *MAX_TURNS / TIMEOUT / TASK_FAIL:* Haiku còn quota -> Dispatcher tự động cho Haiku retry lần 2 (Attempt 2) với tiền tố `[O(1) FOCUS RETRY - DO NOT EXPLORE, TOUCH ONLY TARGET FILE MINIMALLY]`. Chỉ khi attempt 2 vẫn fail mới escalate sang Agy CLI fix (reason: `haiku_exhausted_contract`). (Xem `references/intelligent-failure-classification-and-haiku-retry-ladder-20261016.md`).
- **PROMPT CONTRADICTION & PRECEDENCE (The Stale Injected Prompt Trap):** Khi system prompt bị drift hoặc chứa boilerplate cũ (`BẮT BUỘC dispatch worker qua delegate_task`), Coordinator BẮT BUỘC áp dụng thứ bậc ưu tiên: User Directive (hiện tại) > User Profile / Memory > SOUL / Invariants > Stale System Prompt. CẤM để prompt cũ dắt mũi làm sai Worker hierarchy.
- **CẤM TUYỆT ĐỐI SPAWN `delegate_task` CHO SỬA CODE / TEST (The Gemini Subagent Trap):** Dù trong system prompt khởi tạo session có thể sót câu lệnh cũ (`BẮT BUỘC dispatch worker qua delegate_task`), Coordinator TUYỆT ĐỐI KHÔNG ĐƯỢC spawn subagent `delegate_task` (`ag-gemini-pool-3`) để sửa code hay viết test. Mỗi lượt `delegate_task` ngốn tới 15 calls (~150s), làm loãng context và gây tắc nghẽn nghiêm trọng. MỌI task sửa code/fix bug/viết test BẮT BUỘC dispatch qua Single Dispatch Gateway `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> [--file <file>] "<prompt>"` (T1 Haiku 5.5 CLI -> T2 Agy CLI fix). Chỉ được phép dùng subagent khi CẢ HAI CLI đều cạn quota (`WORKER_CLI_EXHAUSTED`).
- **CỔNG ĐIỀU PHỐI DUY NHẤT CHO TÁC VỤ THƯỜNG (Single Dispatch Gateway `dispatch_worker.py`):** CẤM gọi riêng lẻ `claude_worker.py` hay `ag_cli.py` một cách thủ công rồi tự ý chọn model. Toàn bộ khâu dispatch thông thường BẮT BUỘC chạy qua `python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo>`. Script tự động xử lý chuyển tầng (Haiku -> Agy CLI) khi cạn quota/lỗi và ghi log vào `D:/Taadaa/logs/dispatch.jsonl`.
- **CHỐT PHIÊN TỰ ĐỘNG KHÉP KÍN (Auto-Closeout Pipeline `auto_closeout.py`):** Khi kết thúc task hoặc chốt phiên, BẮT BUỘC gọi `python D:/Taadaa/tools/auto_closeout.py --repo <repo> --files <files>`. Quy trình: Sol 1 lượt -> nếu trượt: Haiku fix -> Claude/Agy review -> 4 nấc kiểm chứng cơ học (py_compile, pytest 100%, test integrity, diff budget <= 150 dòng) -> Auto-Push luôn qua safe_push.py. CẤM quay lại Sol cày điểm, CẤM dừng lại hỏi xin phép Operator.
- **BẪY CÀY ĐIỂM CLOSEOUT GATE & STRIKE PROTOCOL (The 85-Score Infinite Trap):** Khi Closeout Gate đạt 82-84 điểm, CẤM TUYỆT ĐỐI rơi vào vòng lặp spawn worker sửa vụn vặt từng microseconds/timezone/whitespace để nịnh Sol Reviewer kéo dài hàng giờ. Quy tắc Strike chuẩn xác: Strike 1 & 2 Remediation là độc quyền của Sol High (`sol_repair.py`). Đến Strike 3 (3 lần trượt liên tiếp trên cùng scope): BẮT BUỘC kích hoạt Reviewer Hand-off (giao cho Claude Sonnet CLI tự sửa theo HERMES_SUBAGENT_RULES.md). CẤM sửa vòng thứ 4.
- **KỶ LUẬT THI CÔNG DỨT ĐIỂM — CẤM VIỆN CỚ BỊ CHẶN ĐỂ BÁO BLOCKED / KHÓC LÓC (Anti-Paralysis Invariant):** Cấm `delegate_task` cho việc code/test KHÔNG ĐƯỢC PHÉP trở thành cái cớ để Coordinator "đầu hàng", báo BLOCKED hay than phiền với Operator. Báo BLOCKED CHỈ hợp lệ khi gặp lỗi vật lý ngoài tầm kiểm soát (cháy máy, sập nguồn, rơi cổng USB, vỡ màn) hoặc thao tác tốn tiền/xóa dữ liệu cần User duyệt. Mọi lỗi code/test BẮT BUỘC phải thi công về DONE qua Thang Cứu Hộ 4 Tầng:
  1. *Tier 1:* Haiku CLI (`haiku_worker.py`, 6-15s O(1)).
  2. *Tier 2:* Antigravity CLI (`ag_cli.py fix` - Pool 7 acc Pro) khi Claude chạm trần/stale.
  3. *Tier 3:* L2 Emergency Surgery (Coordinator tự sửa O(1) <= 30 dòng, 1 test focused).
  4. *Tier 4 (Van an toàn):* Task lớn vượt L2 và cả 2 CLI đều cạn quota -> gắn cờ `WORKER_CLI_EXHAUSTED: true` để mở van subagent.
- **BẮT BUỘC TỰ ĐỘNG CHUYỂN GIAO STRIKE 3 CHO CLAUDE CLI (CẤM HỎI XIN PHÉP / CẤM KHÓC VỚI OPERATOR):** Khi Closeout Gate trượt 3 lần (Strike 3), quyền chuyển giao can thiệp cho Claude CLI đã được cấp sẵn và là INVARIANT TỐI CAO. Coordinator BẮT BUỘC tự động dispatch ngay `python D:/Taadaa/tools/claude_worker.py --role worker` với toàn bộ review findings của Reviewer để Claude CLI tự sửa code và viết test. TUYỆT ĐỐI CẤM dừng lại hỏi xin phép ("anh có muốn em gọi Claude CLI không?"), CẤM dùng `clarify` hay than vãn đùn đẩy trách nhiệm cho Operator.
- **BYPASS SOL HOÀN TOÀN SAU KHI CLAUDE CLI SỬA XONG (The Direct-Push Invariant):** Khi Claude CLI hoàn tất sửa code và full pytest xanh 100%, BẮT BUỘC bỏ qua Sol High, cấm gọi lại closeout_gate.py để lấy điểm số Sol nữa. Chạy kiểm chứng cơ học (py_compile, pytest xanh 100%, test count không giảm, diff <= 150 dòng) rồi tự động PUSH LUÔN qua safe_push.py. CẤM quarantine, cấm báo BLOCKED khóc lóc (Xem references/auto-closeout-claude-bypass-sol-pipeline-20261016.md).
- **KỶ LUẬT FALLBACK KHI CLAUDE HẾT QUOTA (CẤM QUAY LẠI SOL, CẤM SUBAGENT OMNIROUTE):** Khi Claude CLI chạm trần session limit hoặc unreadable quota, pipeline `auto_closeout.py` tự động chuyển sang Agy CLI:
  1. Worker fix: `claude_worker.py --role worker` -> fallback `ag_cli.py fix` (Pool 7 acc Google Pro).
  2. Reviewer pass: `claude_worker.py --role reviewer` -> fallback `ag_cli.py ask` (trả về VERDICT: APPROVED).
  3. Sau khi Agy CLI duyệt và 4 nấc cơ học xanh: PUSH THẲNG QUA `safe_push.py`, TUYỆT ĐỐI CẤM quay lại Sol cày điểm, CẤM spawn subagent `delegate_task` qua OmniRoute (:20128/:20129) gây trễ và loãng context.
- **CẠM BẪY WORKTREE & PROMPT BỊ CẮT TRÊN WINDOWS MSYS BASH:**
  1. *Dirty Repo Worktree Refusal:* Khi repo có uncommitted changes, Claude CLI mặc định dừng lại hỏi tạo worktree. Bắt buộc thêm chỉ thị: `"Directly edit in place in the current repository without creating any worktrees. Do not touch other uncommitted files."`
  2. *Action-Verb Invariant:* Claude CLI bỏ qua prompt thụ động (`"In file X..."`). Bắt buộc mở đầu bằng động từ hành động trực tiếp (`Add...`, `Export...`, `Refactor...`, `Fix...`).
  3. *MSYS Bash Multiline Truncation:* Trong git-bash / MSYS trên Windows, chuỗi prompt có ký tự xuống dòng `\n` truyền vào CLI wrapper sẽ bị ngắt cụt ngay sau dòng đầu tiên. BẮT BUỘC viết prompt trên 1 dòng duy nhất, nối các câu bằng dấu chấm hoặc chấm phẩy.
  4. *Stale Quota Trap (>2h):* Nếu `plan-usage-history.json` cũ quá 2 giờ, `claude_worker.py` chặn chạy. Cần inject sample mới kèm `time.time() * 1000` hoặc chạy `claude /usage` để làm mới.
- **NEVER** run `claude -p "..." --dangerously-skip-permissions` raw in terminal.
- **NEVER** increase `--max-turns` above role's `hard_cap_turns`; split the task instead.
- **NEVER** use `worker` role for planning/reviewing just to get write access.
- **Misleading old name:** `haiku_worker.py` implied "Haiku only", causing bypasses for Sonnet tasks. `claude_worker.py` is model-agnostic and role-based.
- **Stale quota cache:** Refresh via `claude /usage` or by injecting a fresh sample if >2h stale. Lưu ý: nếu cache `plan-usage-history.json` bị lệch quá 2 giờ (`MAX_QUOTA_STALE_HOURS = 2.0`), `claude_worker.py` sẽ tự động kích hoạt Quota Gate và fallback sang `ag_cli.py`.
- **Nguyên tắc 80/20 trong điều phối worker:** Chỉ dispatch khi giải quyết đúng 20% vấn đề tạo ra 80% giá trị; không dispatch mò mẫm hay làm xáo trộn kiến trúc khi chưa có Patch Contract O(1).
- **Foreground terminal timeout:** Host guard blocks commands > 60s. Use `--timeout 55` or `background=True` for deep reasoning tasks.
- **Windows CLI Stdin Pipe Bug (`Input must be provided either through stdin or as a prompt argument`):** When invoking `claude -p` on Windows via `subprocess.run`, piping prompt text exclusively via `stdin` (`input=prompt_input`) without passing a prompt positional argument after `-p` triggers Node.js stream detection failure in Claude CLI, causing `Error: Input must be provided either through stdin or as a prompt argument when using --print` (exit code 1). Always pass the prompt directly as a CLI argument: `cmd = [claude, "-p", prompt_input, "--model", model, ...]`. Do NOT place `"-p"` alone and pass `input=prompt_input` into `subprocess.run`.
- **Host Model Catalog & Naming Invariant:** The models configured and active on this host are strictly `claude-haiku-5-5` and `claude-sonnet-5-5`. NEVER dispute these model names or attempt to rename/fallback to legacy strings (e.g. `claude-3-5-haiku` or `claude-3-7-sonnet`). Even if Claude CLI prints a warning (`"claude-haiku-5-5" isn't described by this version's model catalog...`), it executes with exit code 0 and handles the prompt correctly. Disputing this model name or diagnosing it as the root cause of an execution failure is a severe violation.
- **Claude CLI Review Background Process Hangs (> 240s):** When running Claude CLI as a background reviewer with `allowedTools "Read,Grep,Glob"` and 8 max-turns on large codebases, processes can hang for 8+ minutes and must be killed with `process(action='kill')`. Root cause: Claude CLI reading 15,000+ line files sequentially across 5 file targets without context budget awareness. Mitigation: in review prompts, specify exact line ranges (e.g. `D:/... (dòng 230-275)`) and reduce `--max-turns 3` for review-only tasks with no write access. If the process exceeds 240s with no new output (observed via `process(action='poll')`), kill and re-invoke with a more focused prompt rather than waiting.
- **Telegram Async Delegation Spam Invariant:** When dispatching multiple sequential worker subagents during an active Telegram session, each `delegate_task(background=True)` completion fires an `[ASYNC DELEGATION BATCH COMPLETE — deleg_...]` English-language log block back into Telegram chat via `_async_delegation_watcher`. This floods the Operator's screen with raw technical logs and is a UX violation. To suppress: `hermes config set display.platforms.telegram.tool_progress off`. Additionally, prefer synchronous dispatch or consolidate results into a single final Vietnamese summary rather than streaming each worker's raw English completion into the chat.
- **GIT_EXTERNAL_DIFF Environment Variable Trap:** On Windows hosts where `GIT_EXTERNAL_DIFF=''` is exported in the environment, Git diff invocations fail with `error: cannot spawn : No such file or directory; fatal: external diff died`. When invoking `git diff` via subprocess in Python helpers or worker scripts, always pop `GIT_EXTERNAL_DIFF` from `os.environ` or pass `--no-ext-diff` directly after `diff`.
- **Mechanical Gate Placement & Regex Indentation Pitfall:** In `guard_dispatch_contract.py`, the hard mechanical block against `delegate_task` for code edits MUST be placed at column 0 immediately preceding `if not file_match:` in Branch 3. Placing it indented under a comment line `# 3. NHÁNH EDIT CODE` causes Python to bind it into the preceding `if not is_code_edit...` block after `sys.exit(0)`, making it unreachable dead code. Furthermore, regex strings checking override tokens (`WORKER_CLI_EXHAUSTED`, etc.) must use raw strings (`r'\b...\b'`) to prevent `\b` from decaying into ASCII backspace (`\x08`).
- **Python Subprocess Wrapper Argument Construction:** In `haiku_worker.py` and `claude_worker.py`, construct the command with the prompt directly in argv: `cmd = [claude, "-p", prompt_input, "--model", model, ...]`. Do NOT place `"-p"` alone and pass `input=prompt_input` into `subprocess.run`. Verify patches with `python -m py_compile` and a real invocation test (`--timeout 30 "Trả về đúng một chữ OK"`).

---

## Tests
27/27 passing in `D:/Taadaa/tools/tests/test_claude_worker.py`:
- Role configs, hard-cap clamping, tool restrictions
- Quota gate (unreadable / stale / 85% / 90%)
- Session limit detection (exact markers only)
- Timeout retry, role-aware fallback routing
- `build_prompt` and `get_claude_quota_status` unit tests

See `references/mechanical-gate-indentation-and-git-diff-trap-20261015.md` for Mechanical Gate indentation bug, regex boundary decay trap, and GIT_EXTERNAL_DIFF environment variable fix (15/10/2026).
See `references/mechanical-gate-pitfalls-and-anti-paralysis-discipline-20261015.md` for Mechanical Gate indentation pitfalls, Strike-3 Reviewer Hand-off, and the Anti-Paralysis Protocol (15/10/2026).
See `references/prompt-precedence-and-score-chasing-circuit-breaker-20261015.md` for Claude Sonnet architecture advice on Prompt Precedence, mechanical gates, and Closeout Gate circuit breaker (15/10/2026).
See `references/strike-3-automatic-claude-handoff-and-worktree-bypass-20261015.md` for Strike 3 automatic Claude CLI hand-off and dirty repo worktree bypass rules (15/10/2026).
See `references/claude-worker-role-dispatch-and-turns-hard-cap-20261015.md` for full incident analysis.
See `references/gemini-pool-subagent-and-closeout-score-chasing-trap-20261015.md` for analysis of the Gemini Pool subagent stall and 85-score Closeout Gate infinite loop (15/10/2026).
See `references/mechanical-gate-delegate-task-lockdown-20261015.md` for mechanical gate dispatch lockdown, delegate_task blocks on code edits, and the 3-tier worker fallback ladder (Haiku -> AG CLI -> L2/subagent escape valve).
See `references/windows-stdin-pipe-and-haiku-5-5-catalog-invariants-20261015.md` for analysis of the Windows Node.js stdin pipe bug (`--print` error) and host-level invariants for `claude-haiku-5-5` & `claude-sonnet-5-5`.
See `references/auto-closeout-claude-bypass-sol-pipeline-20261016.md` for the Claude Auto-Closeout Pipeline (`auto_closeout.py`), bypassing Sol infinite review loops, 4-stage mechanical verification gate, and anti-quarantine direct auto-push (16/10/2026).
See `references/closed-loop-autonomous-completion-and-fail-safe-ladder.md` for Closed-Loop Autonomous Completion, the 4-Tier Fail-Safe Ladder when quota is exhausted, and the Strike 3 Automatic Hand-off Protocol (16/10/2026).
See `references/single-dispatch-gateway-and-subagent-ban-20261016.md` for the Single Dispatch Gateway (`dispatch_worker.py`), the strict subagent ban (`delegate_task` forbidden for code edits), and the Claude Auto-Closeout Pipeline (`auto_closeout.py`) (16/10/2026).
See `references/intelligent-failure-classification-and-haiku-retry-ladder-20261016.md` for the Intelligent Failure Classification (QUOTA vs ENV vs MAX_TURNS), why Haiku must not decompose tasks, and the 2-Attempt Haiku Retry Ladder before escalating to Agy CLI (16/10/2026).
See `references/quota-guard-self-unlock-prevention-and-cross-family-review-20261016.md` for the incident analysis of Quota Guard self-unlock bypass, 100% quota depletion, Claude Code architectural advice, and strict Cross-Family Review enforcement against fake Gemini reviews (16/10/2026).
