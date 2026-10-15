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

- **NEVER** run `claude -p "..." --dangerously-skip-permissions` raw in terminal.
- **NEVER** increase `--max-turns` above role's `hard_cap_turns`; split the task instead.
- **NEVER** use `worker` role for planning/reviewing just to get write access.
- **Misleading old name:** `haiku_worker.py` implied "Haiku only", causing bypasses for Sonnet tasks. `claude_worker.py` is model-agnostic and role-based.
- **Stale quota cache:** Refresh via `claude /usage` or by injecting a fresh sample if >2h stale.
- **Foreground terminal timeout:** Host guard blocks commands > 60s. Use `--timeout 55` or `background=True` for deep reasoning tasks.

---

## Tests
27/27 passing in `D:/Taadaa/tools/tests/test_claude_worker.py`:
- Role configs, hard-cap clamping, tool restrictions
- Quota gate (unreadable / stale / 85% / 90%)
- Session limit detection (exact markers only)
- Timeout retry, role-aware fallback routing
- `build_prompt` and `get_claude_quota_status` unit tests

See `references/claude-worker-role-dispatch-and-turns-hard-cap-20261015.md` for full incident analysis.
See `references/mechanical-gate-delegate-task-lockdown-20261015.md` for mechanical gate dispatch lockdown, delegate_task blocks on code edits, and the 3-tier worker fallback ladder (Haiku -> AG CLI -> L2/subagent escape valve).
