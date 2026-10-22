# Multi-Round Adversarial Reviewer Hardening & Fail-Closed Gates (2026-10-22)

## 1. Context & The "Cheap Signal" Trap
In phone farm automation tasks, Coordinators often declare victory prematurely after `pytest` passes offline, skipping device canaries. When forced into an audit by an independent reviewer (e.g. Claude CLI Sonnet), the gate implementation was scrutinized across 6 iterative adversarial rounds.

Each round exposed systemic bypasses that looked "fixed" on the surface but remained open via alternative execution paths.

---

## 2. Six Systematic Gate Bypasses & True Fail-Closed Solutions

### Round 1: False Positive Monolith Dumps & Self-Report Bypass
- **Finding:**
  1. `ui_policy_check.py` scanned whole files (23,000 lines), failing old monoliths on legacy comments.
  2. `--task-type general` was trusted from user/caller CLI input, allowing trivial gate bypass.
  3. GPM branch allowed deferred pass even when offline.
- **Fix:**
  - Make `ui_policy_check` diff-aware (`find_diff_violations` inspects only new/modified lines).
  - Enforce `automation` classification if repository path matches known automation projects, ignoring CLI overrides.
  - Wire `--strict-device` to GPM branch (fail immediately if offline without receipt).

### Round 2: The Raw Image Short-Circuit & Path Basename Vulnerability
- **Finding:**
  1. `canary_runner.py` returned `True, CANARY_IMAGE_VERIFIED` for any file ending in `.png/.jpg/.jpeg`. A caller could `touch fake.png` to bypass all checks!
  2. `detect_task_type` only checked `Path(repo).name` (basename). Subpaths like `D:/Taadaa/tiktok-follow/follow_runner` bypassed detection.
- **Fix:**
  - Completely disallow raw images (`CANARY_IMAGE_RAW_DISALLOWED`). Enforce JSON receipts containing real `media_sha256` matching disk.
  - Inspect full resolved paths (`Path.resolve().as_posix()`) and check working directory via `git rev-parse --show-toplevel`.

### Round 3: Receipt Field Omission & Swallowed Exceptions
- **Finding:**
  1. If a receipt omitted the `repo` key, the mismatch check was skipped (`if rec_repo: ...`), allowing cross-repo receipt reuse.
  2. `build_canary_plan` swallowed exceptions (`except Exception: pass`), failing open.
  3. The `tools` repo itself was not listed in `AUTOMATION_REPOS`.
- **Fix:**
  - Require `repo` in receipt: if missing -> `CANARY_REPO_MISSING_IN_RECEIPT` (FAIL).
  - Fail-closed exception handling -> `CANARY_PLAN_UNAVAILABLE` (FAIL).
  - Add `"tools"` to `AUTOMATION_REPOS`.

### Round 4: Clean Working Tree Dead Code & Stale Receipt Reuse
- **Finding:**
  1. `changed_files_from_git()` only queried uncommitted changes. If code was committed before calling the gate, it returned `[]`, skipping all UI policy checks!
  2. Receipts for old commits could be reused indefinitely within `max_age_seconds`.
- **Fix:**
  - `changed_files_from_git()` now diffs against remote baseline: `git diff --name-only -z origin/main HEAD` (fallback `origin/master`, `HEAD~5`).
  - Verify receipt `commit_sha` against `HEAD`: if different and `git diff --stat <commit_sha> HEAD` has changes -> `CANARY_COMMIT_STALE` (FAIL).
  - Eliminate all fallback verification branches in `has_recent_canary_evidence` (fail-closed on any error).

### Round 5 & 6: Fail-Open Subprocesses & Missing CLI Arguments
- **Finding:**
  1. Git subprocesses in commit verification lacked try/except and returned 0 on error, failing open when commits were unresolvable.
  2. `done_gate.py` only ran UI policy check `if args.repo:` — canonical commands in `AGENTS.md` omitted `--repo`, completely skipping UI policy checks!
- **Fix:**
  - Wrap commit verification in try/except returning `CANARY_COMMIT_VERIFY_FAILED`.
  - Resolve `effective_repo = args.repo or git rev-parse --show-toplevel` so UI policy check ALWAYS executes.
  - Add adversarial test suite (35/35 passing) covering every bypass vector.

---

## 3. Core Lessons for Gate Design
1. **Never Trust CLI Self-Reports:** Derive task types and repository boundaries from filesystem and git metadata, not user-supplied arguments.
2. **Never Short-Circuit on Format:** A `.png` extension proves nothing; require structured receipts with content hashes (`sha256`) and execution metadata.
3. **Always Check the Default Invocation Path:** Ensure canonical commands without optional arguments (like `--repo` or `--files`) execute the full security baseline.
4. **Fail-Closed on All Errors:** A failing git command, missing plan, or unparseable commit must block the gate, never permit entry.
