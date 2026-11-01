# Repository-Wide Baseline Hash Traps & Scoped Transaction Architecture

## 1. The Systemic Paralysis Pattern (Bại liệt do Over-Engineering)
When patch automation pipelines (`unified_patch_pipeline.py`) enforce repository-wide filesystem integrity via pre-execution snapshot hashing (P0/P1 baseline hash):
- **False Assumption:** Every untracked or modified file on the repository represents unauthorized tampering or worker escape.
- **Production Reality:** Large automation repos (`D:/Taadaa/tools`) accumulate hundreds of transient artifacts (untracked debug scripts, runtime receipt logs, AST cache indices, local configs).
- **The Death Spiral:**
  1. Step S0 Precheck calculates SHA256 hashes of 500+ untracked/dirty files.
  2. A precheck or in-process utility (e.g. `find_existing_logic.py`) appends a legitimate token receipt to a ledger (e.g. `find_existing_logic_receipts.jsonl`).
  3. Step S2 Patch detects that a file outside the patch scope had its SHA256 altered.
  4. The pipeline concludes `Worker vi phạm scope — sửa nội dung file baseline NGOÀI scope`.
  5. The pipeline triggers an unconditional `FAIL-CLOSED` and `ROLLBACK`, discarding valid edits.
  6. Compliance Watchdog records a Worker failure; Guards block follow-up recovery commands.
  7. **Outcome:** 100% defense posture, 0% engineering velocity.

---

## 2. Invariant: Scoped Transaction vs. Repository-Wide Hashing
1. **Never Take Repository-Wide Baseline Hashes:**
   - Pre-patch integrity verification must be restricted strictly to `target_files` (files within the declared edit scope).
   - Untracked files and pre-existing dirty working trees must NEVER trigger scope violation rollbacks unless they match an explicit prohibited target list.
2. **Decouple Runtime Artifacts from Git Tracked Trees:**
   - Utility scripts (`find_existing_logic.py`, `gate_compliance_watchdog.py`) must write receipt ledgers, caches, and runtime audit logs into dedicated runtime directories (`D:/Taadaa/runtime/`, `~/.codex/`, `AppData/Local/...`) or ignore them completely in Git (`.gitignore`).
   - A tool executed by the pipeline must not alter files inside the repo working tree during the patch lifecycle.
3. **Contextual Guard Guidance (No Android Guidance for Code Tasks):**
   - When a guard intercepts broad filesystem scans (`GUARD_DANGEROUS_ROOT`, `GUARD_PYTHON_WALKER`), the guidance MUST provide file-search alternatives: `search_files(target='files', pattern='...')` or `git ls-files`.
   - CẤM TUYỆT ĐỐI injecting farm Android inspection hints (`python D:/Taadaa/tools/inspect_machine.py <N>`) into code exploration tasks, which leads agents into recursive ADB lock failures.
