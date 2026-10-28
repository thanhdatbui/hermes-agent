# Canary Gate Diff-Hook Auto-Binding Architecture

## 1. Context & Motivation (Memory Trap vs Mechanical Gate)
When an agent or developer modifies code affecting specific subsystem hooks (e.g., `upload-hook`, `follow-hook`, `account-switcher`), running a generic baseline canary (like a basic 2-swipe feed test) will bypass the modified code entirely, providing zero verification evidence.
Relying on LLM persistent memory (`MEMORY.md`) to "remember" to pass specific CLI flags (e.g., `--allow-upload-hook`) is an anti-pattern:
- Memory lacks deterministic execution guarantees.
- Storing CLI execution flags consumes the precious context budget (2,200 chars).
- **Core Principle:** Any behavioral rule that dictates CLI arguments based on modified code MUST be mechanized directly into the gate/runner infrastructure, never relegated to LLM memory.

---

## 2. Three-Tier Mechanical Architecture
The verification loop is codified across three mechanical layers:

### A. Matrix Rule Definition (`canary_matrix.json`)
Explicitly maps repository file globs to targeted hook IDs and OCR expectations:
```json
{
  "id": "upload-hook",
  "path_globs": ["*upload*", "**/flows/*upload*", "**/flows/multi_machine_feed_session*"],
  "hook": "upload",
  "scope": "single",
  "ocr": {
    "required_all": [["dành cho bạn", "đang follow", "trang chủ"]],
    "min_chars": 20
  }
}
```

### B. Diff Analysis Engine (`canary_plan.py`)
Inspects actual Git diffs (`HEAD~1` or working tree) and resolves the matching requirements and candidate hooks deterministically:
```python
auto_plan = build_canary_plan(repo_dir, DEFAULT_MATRIX)
reqs = auto_plan.get("requirements", [])
```

### C. Runner Auto-Injection (`canary_runner.py`)
When invoked without an explicit `--hook` flag, the runner queries the diff analysis engine. If a specific hook (e.g., `upload`) is matched by the diff, it automatically appends the requisite CLI flags (`--allow-upload-hook`) to the downstream execution command:
```python
if active_hook and "upload" in str(active_hook).lower():
    cmd.append("--allow-upload-hook")
```

---

## 3. Anti-Overengineering Invariants for Gate Runners
1. **No Ad-Hoc Dry-Run Hijacking:** Never hijack general runner dry-run dispatch to execute a specific subsystem unit test (e.g., hardcoding a single pytest file in `canary_runner.py`). Generic runners must remain canonical and delegate routing via standard arguments.
2. **Deterministic Receipt Binding:** `done_gate.py` binds directly to `canary_receipt.json` matching `tree_diff_sha256` or `diff_sha256`, preventing stale receipts from validating unverified changes.
