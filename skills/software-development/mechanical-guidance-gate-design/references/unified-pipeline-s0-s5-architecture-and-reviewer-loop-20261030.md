# Unified Pipeline S0..S5 Full-Spectrum Gate Integration & Reviewer Feedback Loop

## 1. Context & Architectural Root Cause
When transitioning from disparate mechanical gates to a consolidated single-command pipeline (`unified_patch_pipeline.py`), mechanical enforcement must prevent:
1. **Lying Coordinator / Fake Dispatch Claims**: Agents asserting "worker is running" before actual dispatch receipt or when rejected by whitelist guards.
2. **Post-Hold Code Tampering**: Mutating repository code between S5 (Hold & Report) and Confirm, bypassing visual evidence.
3. **Dirty Baseline Tamper-Leak**: Modifying pre-existing dirty files outside target scope, which standard set-diff (`current_changed - baseline_changed`) blindly ignores.
4. **Half-Patched Dirty Tree Leaks**: Partial multi-file failures leaving dirty code on disk when test or canary fails.
5. **Prompt-Induced Greeting Degradation in One-Shot CLI Audits**: Long source code prompts in headless CLI (`claude -p` / `sol_reviewer`) causing the model to interpret code as passive context and emit greetings ("Xin chào, tôi có thể giúp gì..."), failing automated review parsing.

## 2. Six-Stage Unified Lifecycle (`unified_patch_pipeline.py`)

### S0: Precheck (Gate 1 & Gate 5 Scope Lock)
- **Gate 1**: Rejects `kind="batch"` (`render/download`) from code surgery.
- **Gate 5 Scope Lock**: Resolves `--file` arguments relative to git repo (`is_relative_to(repo)`), verifies file existence on disk, rejects path traversal.
- **Multi-Process RepoLock**: Acquires OS-level file lock (`D:/Taadaa/runtime/locks/pipeline_repo_<hash>.lock`) on Windows via `msvcrt.locking` to prevent concurrent pipeline collision.
- **Baseline Content Snapshot**: Captures raw SHA256 hashes of all existing dirty/untracked files outside scope (`baseline_changed - scope`) into `baseline_file_hashes`. If an out-of-scope baseline file is modified later, it triggers immediate scope-violation rollback.

### S1: Plan (Gate A & Gate B)
- Runs `gate_b_planner.py` with multi-tier fallback:
  * Tier 1: Gemini Web (Argon 4 Pool, 120s timeout).
  * Tier 2: Claude CLI (`claude -p`, 150s timeout).
  * Tier 3: Sol Worker (`:20129` `gpt-web-sol`, 120s timeout).
- Overall S1 subprocess timeout clamped to 420s to ensure Tier 3 has execution runway.
- Output validated fail-closed: requires `edits` list (1-5 items), `file` in `target_files`, `old_string` unique (`count == 1` after CRLF->LF normalization).

### S2: Patch (Gate C Execution & Independent Verification)
- Groups edits by file and sequentially dispatches `dispatch_worker.py` (Qoder T0 -> Sol T1 -> Agy T2 -> Haiku T3).
- **Independent Verification**: Evaluates `expected_contents[rel] = pre.replace(old, new, 1)` only when `pre.count(old) == 1`. Requires byte-exact match with real file post-patch.
- **Git Scope Gate**: Runs `get_git_changed_files(repo)` and `detect_baseline_content_drift()`. Any newly modified/untracked file outside `target_files` triggers immediate `full_rollback()`.

### S3: Verify (Focused Unit Test)
- Executes `--test-cmd` with subprocess timeout 60s.
- On test failure or timeout: calls `full_rollback(repo, pre_bytes, baseline_changed, scope)` to restore scope files and clean out-of-scope artifacts via `git checkout HEAD -- <file>` and unstage/delete.
- Re-runs `evaluate_stage_scope_gate()` post-test to verify tests didn't drop untracked side-effects outside scope.

### S4: Canary (Gate 6 Step-by-Step Evidence)
- Automatically mandated for farm/device changes (`is_farm_device_related(target_files, task)`).
- Runs `canary_runner.py` on idle device with JIT device lock.
- **Media Validation**: Requires regular image file (`.png/.jpg/.jpeg/.webp`), non-empty (`size > 0`), and fresh timestamp (`mtime >= t0_canary`).
- On failure/timeout: executes `full_rollback()`.

### S5: Hold & Anti-Tamper State Signing
- Computes `diff_hash_at_hold` = `git diff HEAD` + `\0UNTRACKED\0` + sorted `path:sha256(content)` of all untracked files.
- Signs `state.json` with HMAC-SHA256 using machine host secret `D:/Taadaa/runtime/secrets/pipeline.key`.
- Outputs structured text report + `MEDIA:<path>` and exits with code 0 (`AWAITING_USER`).
- Reports honest test status: `Test: SKIPPED (không có test-cmd)` instead of false claims.

## 3. Confirm Phase & Closeout Gate Binding
- `unified_patch_pipeline.py confirm --run-id <id> --text "Done"`:
  * Validates HMAC signature of `state.json`.
  * Matches user confirmation regex strictly: `^(done|chốt|chốt phiên|đóng phiên)$`.
  * Verifies current git diff hash equals `diff_hash_at_hold`.
  * If diff changed, rejects unless `--rebaseline` is passed. `--rebaseline` requires $\ge 1$ prior rejected closeout attempt and enforces that git drift only touched files within original scope.
  * Clamps retry limit (`MAX_CLOSEOUT_RETRIES = 3`) to prevent infinite review loops.
  * Invokes `closeout_gate.py` for final independent approval ($\ge 85$).

## 4. One-Shot Headless Reviewer Pattern (`run_claude_oneshot.py`)
- Headless CLI and HTTP models (`claude -p`, `gpt-web-sol` via `:20129`) often mistake large source code inputs for conversation context, responding with conversational greetings.
- **Fix Pattern**:
  * Inject an imperative action directive at **Token 0 (line 1)** of prompt:
    `"Review khắt khe mã nguồn sau đây và xuất ngay báo cáo theo đúng định dạng SCORE và VERDICT. TUYỆT ĐỐI KHÔNG CHÀO HỎI, KHÔNG XUẤT CÂU HỎI LẠI."`
  * Repeat closing instruction after the untrusted source code block.
  * For Windows CMD pipes, route directly via REST API (`urllib.request` to OmniRoute `:20129`) to bypass shell pipe quirks and buffer truncation.
