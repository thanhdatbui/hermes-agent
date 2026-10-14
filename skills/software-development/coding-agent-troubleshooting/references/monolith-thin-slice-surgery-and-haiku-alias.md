# Monolith Thin-Slice Surgery & Claude CLI Model Alias Pitfall

## 1. Claude CLI Model Alias Pitfall

When calling `claude -p` from scripts (e.g. `haiku_worker.py`):
- Passing explicit full version strings like `--model claude-haiku-5-5` triggers a CLI warning:
  ```
  "claude-haiku-5-5" isn't described by this version's model catalog; update Claude Code...
  Warning: Advisor disabled — base model 'claude-haiku-5-5' has no advisor rank...
  ```
- **Fix**: Use the canonical short alias: `--model haiku` (or `sonnet`, `opus`). Claude Code CLI internally resolves `haiku` to the active Claude 3.5/5.x Haiku build with correct token window settings and zero warnings.

## 2. Monolith Thin-Slice Surgery Pattern (Coordinator + Haiku Worker)

Refactoring large monolith scripts (>1,500 lines) poses high risk:
- Asking heavy models (Claude Sonnet/Opus, Gemini Ultra) to "refactor and modularize" produces hundreds of lines of diff across dozens of functions, risks regressions, burns expensive quota, and violates O(1) surgery gates.

### The Proven 5-Step Workflow:
1. **Coordinator Pre-Cut**:
   - Coordinator identifies cleanly separated utility clusters (e.g. proxy loading, formatters, thread-local management).
   - Writes the new modular target file directly (e.g. `scripts/downloader/proxy.py`).
2. **Exact O(1) Contract for Haiku**:
   - Provide Haiku with an exact instruction: remove local definitions and replace with `from <module> import (...)`.
   - Constrain Haiku to touch ONLY that single block.
3. **Sub-minute Execution**:
   - Haiku CLI executes in ~10-15s, returning a crisp, targeted diff (e.g. -107 lines removed, +11 lines import added).
4. **Focused Unit & Regression Gate**:
   - Add targeted unit test for the new module (`tests/test_downloader_proxy.py`).
   - Run existing regression suites (`tests/test_download_by_niche.py`).
   - Both must pass 100% before committing.
5. **Incremental Progress**:
   - Repeat for subsequent clusters (e.g. avatar generation, language filters, platform resolvers) slice by slice.
