# FOCUSED_TEST Format and Monolith Thin-Slice Refactoring

## 1. Hard Guard Invariant: FOCUSED_TEST Format in `delegate_task`
When delegating task with `TASK_KIND: EDIT` to subagents, the coordinator guard strictly validates the format of `FOCUSED_TEST`.
- ❌ **FAILED FORMAT**: `pytest tests/test_foo.py` or `pytest -k test_bar` -> triggers `[COORDINATOR GUARD - CONTRACT VIOLATION]: INVALID_FOCUSED_TEST_FORMAT`.
- ✅ **ALLOWED FORMAT**:
  1. `python -m pytest <file.py>::<test_node> -q` (e.g. `python -m pytest tests/test_download_by_niche.py::TestDownloadByNicheDurationFilters::test_duration_priority_sweet_spot -q`)
  2. `python -m py_compile <file.py>` (e.g. `python -m py_compile scripts/download_by_niche.py`)

Always use one of the two exact patterns above in the `FOCUSED_TEST:` header line of `delegate_task` context.

## 2. Monolith Thin-Slice Refactoring Pattern
Monolith files (> 1,500 lines, e.g. `download_by_niche.py` ~2,000 lines) should NOT be refactored via broad open-ended prompts or full rewrites. Doing so causes:
- Excessive numstat diff violating O(1) limits (> 30 lines).
- Lost invariants (single-channel per folder, diacritic filtering, retry semantics).
- Hallucinated or broken imports across dozens of functions.

### The Thin-Slice Strategy:
1. **Analyze Subsystem Boundaries**: Inspect AST and imports to identify cleanly separable components:
   - Module 1: `downloader/proxy.py` (Proxy pool formatting, rotation, worker thread-local subpool).
   - Module 2: `downloader/dedup.py` (Perceptual hashing `phash`, `video_hashes`, `hash_similarity`, `probe_duration`).
   - Module 3: `downloader/avatar.py` (Frame extraction, square crop 512x512, YOLO representative avatar).
   - Module 4: `downloader/language.py` (Diacritics gate, metadata scoring, Whisper audio scoring).
2. **Autonomous Tool Selection**:
   - Coordinator: Acts as Lead Architect, designs the exact interface and O(1) patch contract.
   - Claude Haiku CLI (`haiku_worker.py`): Performs surgical replacements (replacing 100+ lines of local definitions with a single import statement in 10-15s).
   - Pytest Suite: Serves as immediate objective regression verification (`pytest tests/test_download_by_niche.py` -> 12/12 PASSED).
3. **Execution Invariant**: Extract 1 module per commit, run regression test suite immediately, and verify zero functional drift before proceeding to the next slice.
