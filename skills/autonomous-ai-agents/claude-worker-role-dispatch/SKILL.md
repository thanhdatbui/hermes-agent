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

- **CẤM TUYỆT ĐỐI SPAWN `delegate_task` CHO SỬA CODE / TEST (The Gemini Subagent Trap):** Dù trong system prompt khởi tạo session có thể sót câu lệnh cũ (`BẮT BUỘC dispatch worker qua delegate_task`), Coordinator TUYỆT ĐỐI KHÔNG ĐƯỢC spawn subagent `delegate_task` (`ag-gemini-pool-3`) để sửa code hay viết test. Mỗi lượt `delegate_task` ngốn tới 15 calls (~150s), làm loãng context và gây tắc nghẽn nghiêm trọng. Mặc định Tier 1 BẮT BUỘC là `python D:/Taadaa/tools/haiku_worker.py` (6-15s O(1)), tự động fallback sang `ag_cli.py fix` (Tier 2). Chỉ được phép dùng subagent khi CẢ HAI CLI đều cạn quota (`WORKER_CLI_EXHAUSTED`).
- **BẪY CÀY ĐIỂM CLOSEOUT GATE (The 85-Score Infinite Trap):** Khi Closeout Gate đạt 82-84 điểm, CẤM TUYỆT ĐỐI rơi vào vòng lặp spawn worker sửa vụn vặt từng microseconds/timezone/whitespace để nịnh Sol Reviewer kéo dài hàng giờ. Tối đa 2 lần Sol Repair (`sol_repair.py`). Đến Strike 3 trượt liên tiếp trên cùng scope: BẮT BUỘC kích hoạt Reviewer Hand-off (giao cho Claude CLI tự sửa theo HERMES_SUBAGENT_RULES.md) hoặc dừng lại báo cáo sự thật hiện trường kèm diff/test PASS cho Operator, không được tự ý loop trong bóng tối.
- **NEVER** run `claude -p "..." --dangerously-skip-permissions` raw in terminal.
- **NEVER** increase `--max-turns` above role's `hard_cap_turns`; split the task instead.
- **NEVER** use `worker` role for planning/reviewing just to get write access.
- **Misleading old name:** `haiku_worker.py` implied "Haiku only", causing bypasses for Sonnet tasks. `claude_worker.py` is model-agnostic and role-based.
- **Stale quota cache:** Refresh via `claude /usage` or by injecting a fresh sample if >2h stale. Lưu ý: nếu cache `plan-usage-history.json` bị lệch quá 2 giờ (`MAX_QUOTA_STALE_HOURS = 2.0`), `claude_worker.py` sẽ tự động kích hoạt Quota Gate và fallback sang `ag_cli.py`.
- **Nguyên tắc 80/20 trong điều phối worker:** Chỉ dispatch khi giải quyết đúng 20% vấn đề tạo ra 80% giá trị; không dispatch mò mẫm hay làm xáo trộn kiến trúc khi chưa có Patch Contract O(1).
- **Foreground terminal timeout:** Host guard blocks commands > 60s. Use `--timeout 55` or `background=True` for deep reasoning tasks.
- **Windows CLI Stdin Pipe Bug (`Input must be provided either through stdin or as a prompt argument`):** When invoking `claude -p` on Windows via `subprocess.run`, piping prompt text exclusively via `stdin` (`input=prompt_input`) without passing a prompt positional argument after `-p` triggers Node.js stream detection failure in Claude CLI, causing `Error: Input must be provided either through stdin or as a prompt argument when using --print` (exit code 1). Always pass the prompt directly as a CLI argument: `claude -p "<prompt>" ...`.
- **Host Model Catalog & Naming Invariant:** The models configured and active on this host are strictly `claude-haiku-5-5` and `claude-sonnet-5-5`. NEVER dispute these model names or attempt to rename/fallback to legacy strings (e.g. `claude-3-5-haiku` or `claude-3-7-sonnet`). Even if Claude CLI prints a warning (`"claude-haiku-5-5" isn't described by this version's model catalog...`), it executes with exit code 0 and handles the prompt correctly. Disputing this model name or diagnosing it as the root cause of an execution failure is a severe violation.
- **Claude CLI Review Background Process Hangs (> 240s):** When running Claude CLI as a background reviewer with `allowedTools "Read,Grep,Glob"` and 8 max-turns on large codebases, processes can hang for 8+ minutes and must be killed with `process(action='kill')`. Root cause: Claude CLI reading 15,000+ line files sequentially across 5 file targets without context budget awareness. Mitigation: in review prompts, specify exact line ranges (e.g. `D:/... (dòng 230-275)`) and reduce `--max-turns 3` for review-only tasks with no write access. If the process exceeds 240s with no new output (observed via `process(action='poll')`), kill and re-invoke with a more focused prompt rather than waiting.
- **Telegram Async Delegation Spam Invariant:** When dispatching multiple sequential worker subagents during an active Telegram session, each `delegate_task(background=True)` completion fires an `[ASYNC DELEGATION BATCH COMPLETE — deleg_...]` English-language log block back into Telegram chat via `_async_delegation_watcher`. This floods the Operator's screen with raw technical logs and is a UX violation. To suppress: `hermes config set display.platforms.telegram.tool_progress off`. Additionally, prefer synchronous dispatch or consolidate results into a single final Vietnamese summary rather than streaming each worker's raw English completion into the chat.
- **Python Subprocess Wrapper Argument Construction:** In `haiku_worker.py` and `claude_worker.py`, construct the command with the prompt directly in argv: `cmd = [claude, "-p", prompt_input, "--model", model, ...]`. Do NOT place `"-p"` alone and pass `input=prompt_input` into `subprocess.run`. Verify patches with `python -m py_compile` and a real invocation test (`--timeout 30 "Trả về đúng một chữ OK"`).

---

## Tests
27/27 passing in `D:/Taadaa/tools/tests/test_claude_worker.py`:
- Role configs, hard-cap clamping, tool restrictions
- Quota gate (unreadable / stale / 85% / 90%)
- Session limit detection (exact markers only)
- Timeout retry, role-aware fallback routing
- `build_prompt` and `get_claude_quota_status` unit tests

See `references/claude-worker-role-dispatch-and-turns-hard-cap-20261015.md` for full incident analysis.
See `references/gemini-pool-subagent-and-closeout-score-chasing-trap-20261015.md` for analysis of the Gemini Pool subagent stall and 85-score Closeout Gate infinite loop (15/10/2026).
See `references/mechanical-gate-delegate-task-lockdown-20261015.md` for mechanical gate dispatch lockdown, delegate_task blocks on code edits, and the 3-tier worker fallback ladder (Haiku -> AG CLI -> L2/subagent escape valve).
See `references/windows-stdin-pipe-and-haiku-5-5-catalog-invariants-20261015.md` for analysis of the Windows Node.js stdin pipe bug (`--print` error) and host-level invariants for `claude-haiku-5-5` & `claude-sonnet-5-5`.
