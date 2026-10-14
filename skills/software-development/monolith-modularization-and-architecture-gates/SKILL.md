---
name: monolith-modularization-and-architecture-gates
description: "Use when modularizing monolith scripts with CI gates."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [refactoring, monolith, architecture-gate, thin-slice, code-cleanliness, ci-enforcement]
    related_skills: [farm-anti-overengineering, test-driven-development, code-audit, closeout-review-discipline]
---

# Monolith Modularization and Architecture Gates Discipline

Use this skill when refactoring monolithic production scripts (> 1.500 lines) into modular subpackages without disrupting active workloads, breaking backward compatibility, or letting subsequent AI agents undo the modularization.

## 1. Core Principles & The Monolith Problem

### The Problem
When scripts evolve over months, they accumulate multiple orthogonal domains into a single file (e.g., network proxy rotation, SQLite concurrency, video perceptual hashing, YOLO cropping, language gates, platform scrapers).
- **Context Bloat:** Coding agents (Claude/Gemini) must ingest 20.000–30.000 tokens per request just to read the script, rapidly exhausting token quotas.
- **Accidental Coupling:** Editing one component (e.g. proxy) risks breaking another (e.g. database transactions or audio transcription).
- **Agent Regression Trap:** Without mechanical locks, future AI turns naturally append new code back into the monolith out of least resistance.

### The Invariants
1. **Zero Downtime / Zero In-Flight Disruption:** Running background processes (e.g. 20-thread downloaders or render chains on worker nodes) must never encounter missing imports, broken CLI parameters, or locking contention.
2. **Absolute Backward Compatibility:** Re-export all public domain functions from the original orchestrator so callers importing from the legacy module path never break.
3. **Mechanical Architecture Gates:** Never rely on agent prompt discipline alone. Lock module boundaries via automated unit tests that enforce line count ceilings and forbid inline redefinitions.

---

## 2. Thin-Slice Refactoring Workflow (Strangler Fig Pattern)

Never attempt a big-bang rewrite of a 2.000-line script in a single pass. Decompose systematically into thin vertical slices:

### Step 1: Software Archaeology & Domain Mapping
Inspect the AST and Git history to map natural functional domains:
- **Networking & Transport:** Proxy pool rotation, cookies, thread-local subpools.
- **Deduplication & Media Probing:** Perceptual hashing (DCT), ffprobe duration, similarity metrics.
- **Visual & Framing:** Face/object detection, bounding box crops, avatar generation.
- **Language & Filtering:** VAD audio caching, regex filters, Whisper transcription.
- **Platform Extractors:** Scrapers, API resolvers, downloaders.

### Step 2: Per-Domain Package Extraction
For each domain:
1. Create a dedicated module under `scripts/<package_name>/<domain>.py` (target <= 200 lines).
2. Write independent unit tests (`tests/test_<package>_<domain>.py`) verifying isolated behavior.
3. Re-export public symbols in `scripts/<package_name>/__init__.py`.

### Step 3: Minimal O(1) Integration Patch
1. In the legacy monolith, replace local function implementations with clean import statements from the new package.
2. Keep public variables and functions exported to preserve API compatibility.
3. Verify that line count decreases monotonically per slice.
4. Run the full regression test suite (e.g. `pytest`) after every single slice.

---

## 3. Architecture Gate Test (Anti-Regression Lock)

To prevent future AI agents from inlining code back into the orchestrator, create `tests/test_<package>_architecture_gate.py`:

```python
import re
from pathlib import Path

def test_orchestrator_line_budget():
    """Assert orchestrator line count stays below strict budget (e.g. <= 1400 lines)."""
    root = Path(__file__).parent.parent
    file_path = root / 'scripts' / 'download_by_niche.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        line_count = len(f.readlines())
    
    MAX_LINES = 1400
    assert line_count <= MAX_LINES, f"Monolith bloat detected: {line_count} > {MAX_LINES}"

def test_modules_exist():
    """Verify package structure integrity."""
    root = Path(__file__).parent.parent
    downloader = root / 'scripts' / 'downloader'
    for mod in ['__init__.py', 'proxy.py', 'dedup.py', 'avatar.py', 'language.py', 'platforms.py']:
        assert (downloader / mod).exists(), f"Missing module: {mod}"

def test_no_inline_domain_redefinitions():
    """Ensure domain functions are imported, never redefined inline."""
    root = Path(__file__).parent.parent
    file_path = root / 'scripts' / 'download_by_niche.py'
    content = file_path.read_text(encoding='utf-8')
    forbidden_defs = ['def format_proxy(', 'def phash(', 'def make_avatar_for_folder(']
    for pattern in forbidden_defs:
        assert pattern not in content, f"Domain logic inlined in orchestrator: {pattern}"
```

---

## 4. Coding Agent Quota & Context Optimization

When using CLI agents (Claude Code CLI / Haiku Worker) to refactor or maintain modules:

1. **CLAUDE.md Exemption Rule:**
   Add an explicit rule in `CLAUDE.md`:
   > *"Ngoại lệ: Với các task O(1) vá code tập trung có chỉ định rõ file đích qua `haiku_worker` hoặc `-p`, xử lý trực tiếp file mục tiêu và chạy test, không cần đọc trước toàn bộ AGENTS.md / PROJECT_RULES.md để tiết kiệm context quota."*
   This prevents the agent from reading 70+ KB of documentation before every 10-line edit.
2. **Execution Hard Clamps:**
   - `--max-turns 6`: Limit agent loop turns for O(1) tasks.
   - `--allowedTools "Read,Edit,Write,Bash"`: Strip unused tools from the prompt catalog.
   - `--no-session-persistence` and `--disable-slash-commands`: Eliminate session disk overhead.
3. **Stale Quota Cache Protection:**
   Do not trust stale usage cache files (`plan-usage-history.json`). If Anthropic returns `hit your session limit`, fail-fast to secondary toolpools (e.g. Antigravity Pro pool) immediately.

---

## 5. Multi-Repo Pipeline & Stabilization Protocol

When the user asks to modularize across multiple repos:
1. **Commit Early:** Commit the completed refactor of Repo A immediately (`acb8e11`). Never leave dirty workspace or uncommitted refactors while moving to Repo B.
2. **Stabilization Before Cross-Repo Spread:** As Senior Architects advise: Refactor is risk borrowed upfront. A newly modularized script must undergo live soak or canary validation before ripping apart the next repository.
3. **Proactive Backlog Management:** Maintain an explicit queue of monolith targets (e.g. `feed_session_watchdog.py` 2.088 lines) and propose next steps without prematurely assuming the user wants to stop.
