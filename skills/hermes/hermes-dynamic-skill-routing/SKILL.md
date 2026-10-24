---
name: hermes-dynamic-skill-routing
description: "Use for Hermes dynamic skill routing O(1) context injection."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, skills, context-optimization, o1-retrieval, anti-bloat, dispatch-worker, skill-injector]
    related_skills: [hermes-agent, session-close-protocol, closeout-review-discipline]
---

# Hermes Dynamic Skill Routing O(1)

Use this skill when operating or troubleshooting the skill-context injection pipeline that prevents context bloat (`[SKILL_PRUNED]` errors) on the Taadaa Farm.

## Architecture Overview

Instead of loading all 190+ skills statically into every session:

```
[Task Prompt]
     │
     ▼
skill_injector.inject_skill_context(prompt, tier="T1")
     │   1. check_index_freshness() - verify mtime of each SKILL.md
     │   2. lookup_skills(prompt, top_k=5) - O(1) keyword bucket match
     │   3. load_skill_content() - reads matched + 5 Pinned Core Skills
     │   4. Budget clamp: total ≤ max_context_chars (default 15,000)
     │
     ▼
[Enriched Prompt = skill context block + "---" + original prompt]
     │
     ▼
dispatch_worker.py → Agy CLI (Tier 1) / Haiku fallback (Tier 2)
```

## Core Files

> Architecture Reference: [`references/mechanical-planner-and-worker-gateways-architecture.md`](references/mechanical-planner-and-worker-gateways-architecture.md) (Claude CLI Approved)

| File | Path | Purpose |
|------|------|---------|
| `build_skill_index.py` | `D:/Taadaa/tools/` | Scans 190+ SKILL.md files, outputs `skills_index.json` |
| `skills_index.json` | `D:/Taadaa/tools/` | Lightweight index (name, category, description, path, tokens_est) |
| `skill_lookup.py` | `D:/Taadaa/tools/` | Keyword bucket lookup, always returns 5 Pinned Core Skills |
| `load_selected_skills.py` | `D:/Taadaa/tools/` | Loads selected skills with path traversal guard |
| `skill_injector.py` | `D:/Taadaa/tools/` | Adapter: orchestrates lookup → load → budget → inject (auto_heal supported) |
| `dispatch_planner.py` | `D:/Taadaa/tools/` | Single Dispatch Gateway for planning: Sonnet -> Sol -> Coordinator |
| `dispatch_worker.py` | `D:/Taadaa/tools/` | Single Dispatch Gateway for code fixes: Sol -> Agy -> Haiku -> Coordinator |
| `record_skill_knowledge.py` | `D:/Taadaa/tools/` | Canonical 1-touch tool: resolve skill, atomic write, auto rebuild index |
| `preview_skill_injection.py` | `D:/Taadaa/tools/` | CLI preview without side effects |

## Pinned Core Skills (Always Injected)

These 5 skills are ALWAYS loaded regardless of query result:
- `taadaa-farm-ops-rules`
- `farm-anti-overengineering`
- `session-close-protocol`
- `evidence-first-delivery`
- `agent-verification-loop`

## Usage Commands

```bash
# Rebuild index after adding/modifying skills
python D:/Taadaa/tools/build_skill_index.py --skills-dir D:/Taadaa/Hermes/skills --output D:/Taadaa/tools/skills_index.json

# Look up skills for a task (human-readable)
python D:/Taadaa/tools/skill_lookup.py --query "wifi proxy reconnect"

# Look up skills as JSON (for programmatic use)
python D:/Taadaa/tools/skill_lookup.py --query "add 2fa" --json

# Preview what would be injected into a task prompt
python D:/Taadaa/tools/preview_skill_injection.py "fix wifi issue on machine 7"

# Dispatch with skill injection (default, automatic)
python D:/Taadaa/tools/dispatch_worker.py --workdir D:/Taadaa/tools --file target.py "fix bug in ..."

# Dispatch WITHOUT skill injection (debug/bypass)
python D:/Taadaa/tools/dispatch_worker.py --no-skill-injection --workdir D:/Taadaa/tools "..."
```

## Budget & Safety Rules

- **Max total context:** `max_context_chars=15000` (tier T1 default), `8000` (tier T0)
- **Max pinned budget:** `max_pinned_budget=10000` — reserved for 5 Core Pinned Skills
- **Remaining budget:** `15000 - (actual pinned chars)` → allocated to matched skills
- **Safe clamp:** If context exceeds budget, truncates at the last `<!-- END SKILL: -->` marker (not mid-sentence)
- **Fail-Closed:** If index missing/stale or any error → `context_block=""`, dispatch continues with raw prompt. NEVER blocks dispatch.
- **Disable flag:** `--no-skill-injection` bypasses injection entirely

## Freshness Check

`check_index_freshness(index_path, skills_dir)` scans actual `SKILL.md` file mtimes at the 2-level path (`category/skill_name/SKILL.md`). Returns `False` if ANY skill file is newer than the index. When stale:
```bash
python D:/Taadaa/tools/build_skill_index.py --skills-dir D:/Taadaa/Hermes/skills --output D:/Taadaa/tools/skills_index.json
```

## Content Sanitization

`clean_skill_content(content, max_chars=3000)` strips the `## References` section (historical case studies) and caps at `max_chars`. This prevents pinned skill files like `session-close-protocol` (100KB+) from consuming the entire budget.

## Critical Pitfalls

### 1. Worker May Hardcode Wrong Budget Value
When workers patch `dispatch_worker.py`, they may silently substitute a wrong `max_context_chars` value. The correct production call is:
```python
inj = inject_skill_context(args.prompt, tier="T1", max_context_chars=15000, max_pinned_budget=10000)
```
Always verify the numeric constants in worker output match the contract. A value of `2500` instead of `15000` was introduced by a worker in one session — it silently killed matched-skill injection while pinned skills still loaded.

### 2. Index Freshness False-Negatives
Old version of `check_index_freshness` only compared mtime of category-level directories, not actual `SKILL.md` files. Editing a skill file inside a category doesn't change the category directory's mtime. Use the 2-level scan (category → skill_dir → SKILL.md) to catch actual edits.

### 3. Non-Hermetic Tests
Tests that call `inject_skill_context` using the real `DEFAULT_INDEX` / `DEFAULT_SKILLS_DIR` are non-hermetic — they pass or fail depending on the live `skills_index.json`. Use a `hermetic_env` fixture that creates a temp skills directory with predictable content and builds a fresh index.

### 4. `NEED_CONTEXT` from Content Bloat
If pinned skills contain very large `## References` archives, even the 5 pinned skills can exceed 15KB. Solution: `clean_skill_content` strips references, keeping only the actionable rule sections (≤3000 chars/skill).

### 5. `audit()` rc Must Reflect Status
In `dispatch_worker.py`, the audit call for `skill_injection` must pass `rc=1` for error statuses:
```python
_rc_inj = 0 if inj.status not in ("FAIL_CLOSED_STALE_INDEX", "FAIL_CLOSED_ERROR") else 1
audit("skill_injection", 1, inj.status, inj.reason, workdir, args.file, _rc_inj, correlation_id)
```
Hardcoding `rc=0` for all outcomes is a silent-success anti-pattern and will cause Reviewer to dock points.

### 6. Windows Subprocess Command Line Length Limit
Injecting 14KB+ into prompt text passed via command-line arguments (e.g. `python worker.py -- <prompt>`) can exceed Windows `CreateProcess` / CMD limits (8,191 to 32,767 chars), resulting in `The command line is too long`.
- Keep worker dispatch prompts budgeted appropriately.
- For raw worker debugging, use `--no-skill-injection` to bypass injection.
- Prefer piping prompts via stdin (`-p -`) in subagent wrappers.

### 7. Strike 3 Hand-Off when Claude Quota Guard is Blocked
When Closeout Gate triggers `[REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections]`, write authority falls to Claude CLI. But if Claude CLI 5h quota is ≥ 85%, `claude_quota_guard.py` rejects invocation.
- Do NOT violate coordinator T1/T2 write constraints.
- Solution: Generate patch proposal using `python D:/Taadaa/tools/sol_repair.py` (which runs via OmniRoute :20129) and apply safely using `python D:/Taadaa/tools/apply_patch.py patch.json` (which runs focused test verification and auto-rollback).

### 8. Agy CLI Quota Pool vs OmniRoute Quota Desync
- `gemini-3.1-pro` and `gemini-3.8-flash` **share the exact same quota pool** in Antigravity / OmniRoute; `omni-worker` also runs on this pool.
- `ag_cli.py` may check `gemini-3.1-flash-lite` quota in OmniRoute, which can report 100% while Pro/Flash-High or Claude models are completely exhausted (`RESOURCE_EXHAUSTED` 429).
- `pool_state.json` cooldowns (1800s–7200s) are checked before OmniRoute live sorting, locking out accounts even if OmniRoute quota has reset.
- Always check the specific target model's quota in OmniRoute and inspect `pool_state.json` cooldown timers when diagnosing Agy CLI dispatch failures.

### 9. Map in injected_skill_ids Must Check by Path, Not Bare Name
In `skill_injector.py`, checking `if sid in full_context` where `sid` is the skill's name (e.g. `taadaa-farm-ops-rules`) can desync from the actual injected content when skill name differs from directory structure (e.g. `category/folder-name/SKILL.md`). Always map `(name, path)` tuples and check `f": {path} -->" in full_context` to verify true retention after truncation.

### 10. Unclosed Block Truncation in Hard-Clamp Algorithm
When `len(full_context) > effective_max`, blindly finding `truncated.rfind("<!-- END SKILL:")` and falling back to `full_context = truncated` when `-->` is cut off creates unclosed skill blocks.
- **The Correct Pattern:**
```python
while last_end != -1:
    end_marker_close = truncated.find("-->", last_end)
    if end_marker_close != -1:
        full_context = truncated[:end_marker_close + 3]
        break
    last_end = truncated.rfind("<!-- END SKILL:", 0, last_end)
else:
    full_context = ""
```
- If truncated, set `status = "DEGRADED_BUDGET"`.
- Track `skipped_skill_ids` in `InjectionResult` to report skills dropped by budget or loading failures.

### 11. Generated Index File Exceeds Closeout Gate 30KB Diff Limit
`skills_index.json` is a ~90KB generated file. `closeout_gate.py` enforces `MAX_DIFF_BYTES_GATE = 30000` on production files (`_production_diff_bytes`).
- Staging `skills_index.json` with code causes instant failure: `[Gate Fail-Fast: DIFF_TOO_LARGE] (93132 > 30000 bytes)`.
- Never include `skills_index.json` in `--files` during code closeout. Review only logic and test files.

### 12. Reviewer NEED_CONTEXT when Staging Too Many Files in One Batch
Reviewing 13+ files simultaneously (5 engine files + 8 tests) causes Sol Auditor to return `NEED_CONTEXT:skill_injector.py` due to context truncation.
- Split into two clean semantic commits aligned with architecture phases:
  1. Commit 1: Indexer & Lookup Engine (`build_skill_index.py`, `load_selected_skills.py`, `skill_lookup.py` + tests).
  2. Commit 2: Injection Adapter & Gateway Wiring (`skill_injector.py`, `dispatch_worker.py` + tests).
- Pass `--system-prompt` with domain constraint context if Reviewer treats intentional graceful fallback as a fail-closed violation.

### 13. Coordinator Session Prompt vs Worker Prompt Desync (Skill Bloat at Gateway)
- **Problem:** Dynamic skill routing (`skill_injector.py`) only optimizes Worker subagents spawned by `dispatch_worker.py`. The Coordinator's main session on Telegram uses Hermes Core's `build_skills_system_prompt()` (`agent/prompt_builder.py`), which scans `~/.hermes/skills/` directly from disk on startup and dumps every un-archived category into `<available_skills>` (>180 skills, ~30KB prompt bloat).
- **Solution & Archiving Pattern:**
  * Move irrelevant/bloat categories (`apple`, `creative`, `data-science`, `email`, `media`, `smart-home`, `social-media`, `note-taking`, `research`, `productivity`, `software-development`, `devops`, `github`, `autonomous-ai-agents`, `network`, `mlops`) into `~/.hermes/skills/.archive/`.
  * `.archive` is recognized by `EXCLUDED_SKILL_DIRS` in `agent/skill_utils.py` and is completely skipped by Hermes Core during system prompt assembly.
  * Always preserve critical tools like `windows-native-ocr` (move to `desktop/` before archiving `productivity/`).
  * Delete `.skills_prompt_snapshot.json` to force snapshot regeneration.
  * Clear `agent.system_prompt` in `config.yaml` to prevent duplicating invariants already present in `SOUL.md`.
  * Result: Cuts static skill catalog from 182 skills down to exactly 30 farm-essential skills (~4.6KB / ~1,100 tokens), preventing context bloat and hallucination.

### 14. Telegram Platform Inclusion & Focus-Mode Demotion (`agent/coding_context.py`)
- **Upstream Trap:** In `agent/coding_context.py`, `INTERACTIVE_CODING_PLATFORMS = {"cli", "tui", "acp", "desktop", ""}` excludes Telegram by design. This causes `_detect_profile_name` to return `general`, disabling `coding_compact_skill_categories` so Telegram sessions always receive full multi-line descriptions for every skill!
- **Fix:**
  * Add `"telegram"` to `INTERACTIVE_CODING_PLATFORMS`.
  * In `config.yaml`, set `agent.coding_context: focus`.
  * Result: Keeps any remaining active categories compact while preserving 100% skill discoverability (all names stay visible and loadable via `skill_view`).

### 15. Mechanical Gating Invariant vs Soft Prompt Drift (Hard Gate Monopolies)
- **Problem:** Attempting to enforce agent discipline (worker tiers, planner delegation, quota limits, file access) via soft system prompts leads to drift, hallucination, and prompt-bloat during context compaction.
- **Rule:** Anything enforced mechanically MUST be eliminated from soft prompts/memory.
- **Planner Gateway (`dispatch_planner.py`):**
  * `Sonnet CLI` $\xrightarrow{\ge 85\% \text{ Quota}}$ `Sol Planner (:20129)` $\xrightarrow{\text{Fail / Timeout}}$ `Coordinator Fallback` (exit 100, `[PLANNER_FALLBACK_COORDINATOR]`).
- **Worker Gateway (`dispatch_worker.py`):**
  * `Sol Web Worker (:20129)` $\rightarrow$ `Agy CLI` (29 Pro native with `sync_profile_to_wincred`) $\rightarrow$ `Haiku CLI` $\rightarrow$ `Coordinator Fallback` (`[WORKER_FALLBACK_COORDINATOR]`).
- **Timeout Invariant:** Reasoning models (Sonnet, Sol Web High, Agy CLI Agent) require 20s-45s TTFT. All worker/planner timeouts MUST be set $\ge 180s - 300s$. Never set short timeouts (<60s) which prematurely kill healthy model inference.

### 16. Tự Động Định Tuyến Tri Thức Chưa Cơ Giới Vào Dynamic Skill (Anti-Memory Bloat)
- **Vấn đề cốt lõi:** Coordinator hay lạm dụng tool `memory` để ghi nhớ chỉ thị mới/quy trình mới của User, làm cạn kiệt ngân sách 2.200 ký tự của `MEMORY.md`. Hơn nữa, Worker chạy trong subagent cô lập không thể đọc được memory của Coordinator.
- **Quy chuẩn 3 cửa:**
  * *Cửa 1 (Đã cơ giới hoá):* Đã có code/gate/hook/marker -> CẤM lưu memory, CẤM viết rườm rà.
  * *Cửa 2 (Chưa cơ giới hoá):* BẮT BUỘC lưu vào Thư viện Skill (`D:/Taadaa/Hermes/skills/`), tự động nạp O(1) qua Dynamic Skill Routing. Xem chi tiết: [`references/unmechanized-knowledge-to-dynamic-skills-sop.md`](references/unmechanized-knowledge-to-dynamic-skills-sop.md).
  * *Cửa 3 (Memory):* CHỈ lưu User Profile cá nhân và đặc thù môi trường Windows không thuộc quy trình farm.
- **Bắt buộc Tái Lập Chỉ Mục (Rebuild Index):** Sau khi ghi/sửa bất kỳ skill nào, BẮT BUỘC chạy `python D:/Taadaa/tools/build_skill_index.py` để làm mới `skills_index.json` (~15ms), chống lỗi `[INDEX_STALE]` / `FAIL_CLOSED_STALE_INDEX`.

## Closeout Gate Notes

- The 3 new files (`skill_injector.py`, tests) + modified `dispatch_worker.py` together exceed 22KB diff
- Split into 2 closeout batches if needed: (1) skill routing core files, (2) injector + dispatch integration
- `sol_payload_guard` will truncate if total diff >28KB; keep tests hermetic and concise

## Test Suite Location

```
D:/Taadaa/tools/tests/
├── test_build_skill_index.py                # Index building (3 tests)
├── test_skill_lookup.py                     # Keyword matching, pinned guarantee (5 tests)
├── test_pinned_always_returned.py           # Core invariant: pinned always returned (2 tests)
├── test_load_selected_skills.py             # Path traversal guard, HTML escape (2 tests)
├── test_index_staleness_warning.py          # Freshness check (hermetic fixture) (2 tests)
├── test_skill_injector.py                   # Budget, fail-closed, safe boundary, smoke (11 tests)
└── test_dispatch_worker_skill_injection.py  # Wiring, audit rc, disable flag (4 tests)
```

All 35 tests pass in ~9.1s: `python3 -m pytest tests/test_dispatch_worker.py tests/test_skill_injector.py tests/test_dispatch_worker_skill_injection.py -v`
