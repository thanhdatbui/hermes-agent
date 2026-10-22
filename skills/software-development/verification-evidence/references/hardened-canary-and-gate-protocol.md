# Hardened Device Canary & Done Gate Protocol

## 1. Threat Model & Anti-Pattern: Cheap Signal Substitution
- **Anti-Pattern:** The coordinator fixes code that directly influences device runtime (e.g. selector bounds, touch coordinates, UI occlusion dismissal, account switcher taps), runs local unit tests (`pytest`), observes all green, and immediately announces completion to the user without executing canary on physical hardware.
- **Why this fails:** Mock XMLs do not capture real-world DPI scaling, rendering latency, touch event rejection, or dynamic OS popup occlusions (e.g. Samsung FOTA). An off-by-pixel tap will pass unit tests but fail on 100% of the live farm machines.
- **Invariant:** A local test pass is necessary but NEVER sufficient for tasks modifying automation flows. The canary gate on live hardware is non-negotiable.

## 2. Hardening Invariants in `done_gate.py` & `canary_runner.py`
To prevent the agent (or subagents) from bypassing device verification, the gate enforces:
1. **Mandatory `--strict-device` on Automation Tasks:**
   - Tasks operating on `AUTOMATION_REPOS` cannot self-report `--task-type general` or pass without fresh hardware evidence.
   - If no valid canary receipt exists, the gate returns exit code 1 immediately.
2. **Fail-Closed Git Toplevel Enforcement:**
   - `--repo` is normalized and verified strictly via `git -C <path> rev-parse --show-toplevel`. If the target is not a valid git repository or fails resolution, the gate aborts immediately (`[GATE-FAIL] Path duoc truyen vao khong phai la git repo hop le!`).
3. **No Raw Image Short-Circuits:**
   - Passing an ad-hoc `.png` or dummy file via `--canary-file` is rejected (`CANARY_IMAGE_RAW_DISALLOWED`). The canary verifier strictly requires a JSON receipt accompanied by matching SHA256 hashes of the actual visual screenshot.
4. **Mandatory & Valid `commit_sha`:**
   - The JSON receipt must explicitly contain a valid `commit_sha` or `head_sha`. Missing, empty, or `"unknown"` values trigger `CANARY_COMMIT_MISSING` / `CANARY_COMMIT_INVALID`.
   - The verified commit must match the current `HEAD` of the target repo. If subsequent code edits occurred after the canary was executed, `git diff --stat <rec_commit> HEAD` flags the receipt as `CANARY_COMMIT_STALE`.
5. **Working-Tree Dirty & Untracked Content Binding:**
   - The canary runner hashes `git diff HEAD` combined with untracked files from `git status --porcelain --untracked-files=all` (with untracked file contents hashed via `git hash-object`).
   - If any tracked file is edited or any untracked file's content is modified after the canary ran, the receipt is immediately invalidated (`CANARY_WORKING_TREE_DIRTY_MISMATCH`).

## 3. UI Policy Check Integrity (`ui_policy_check.py`)
1. **No False Positives on Legacy Monoliths:**
   - Uses diff-aware analysis (`git diff baseline..HEAD`) to evaluate only new or modified code lines against banned tokens (`uiautomator dump`, `atx-agent`, `:7912`), preventing legacy technical debt from blocking urgent hotfixes.
2. **Adversarial Dummy File Defense:**
   - Passing `--files dummy_harmless.py` does not bypass violations in other files. Candidates are calculated as a union: `list(set(git_files + explicit_files))`.
3. **Clean-Tree Remote Baseline Diffing:**
   - When the working tree is cleanly committed, the checker diffs against `origin/main` (or `origin/master` / `HEAD~5`) so that committing before calling the gate cannot scrub prohibited patterns.
4. **Strict Test Directory Allowlist:**
   - Exemption from banned token checks applies only to valid test files (`test_*.py`, `*_test.py`, `conftest.py`) inside legitimate `tests/` directories, preventing evasion via nested faux test folders.
