---

name: automation-core-development

description: "Develop the shared automation-core control plane (D:\\Taadaa\\automation-core) itself — plan-phase builds touching recovery.py / device_lock.py / cli.py / results.py / global_recovery.py / recovery_runner.py / scheduler. Covers dedicated worktree+branch rules, PYTHONPATH=src testing against the WORKTREE (static venv copy shadows src), full-suite collection blocker, CRLF-safe editing (patch-tool fuzzy matcher mangling), recovery-contract invariants incl. FAILED_LOCKED, the Phase 3 user-explicit lock open (cli.py lock list/inspect/open), and RED/GREEN verification evidence."

version: 1.0.0

author: Hermes Agent

platforms: [windows]

metadata:

  hermes:

    tags: [automation-core, recovery, device-lock, scheduler, worktree, tdd, crlf, verification]

    related_skills: [automation-core-consumer, test-driven-development, concurrent-workspace-safety, git-worktree-merge-reconciliation]

---



# automation-core-development


## 🛑 STOP GATE (bắt buộc — chi tiết: skill taadaa-farm-ops-rules)
Máy live + script chạy/lỗi → KHÔNG tự sửa code, KHÔNG tự chạy lại, KHÔNG tự probe/tay khi chưa được user yêu cầu.
Lỗi → screencap → gửi ẢNH THẬT (MEDIA:<path> dòng riêng, KHÔNG bọc markdown, KHÔNG gửi đường dẫn text) → DỪng chờ user hướng dẫn.
User hướng dẫn bước nào → encode bước đó vào script + test → mới chạy lại. Nghi ngờ → HỎI.

Develop the SHARED CORE repo `D:\Taadaa\automation-core` itself (app-neutral

control plane). Complement of `automation-core-consumer` (consumer adapters):

core owns mechanisms/state machines; consumers own provider/account/workbook

policy. Load this skill when the task edits `src/automation_core/**`,

implements a phase from `.hermes/plans/*.md` in this repo, or runs the

recovery/device-lock/scheduler contract tests.

**Quy tắc phân định Scope (User Rule 2026-08-29)**:
- `automation-core` CHUYÊN xử lý TikTok và các cơ chế/hạ tầng dùng chung (device lock, VPN, startup, scheduler, UI parser).
- Tuyệt đối KHÔNG đẩy các xử lý UI/flow đặc thù của app bên ngoài (như quy trình đăng nhập Google Account, Gmail add mail, Hotmail) vào `automation-core`. Các flow đó thuộc về các repo chuyên trách riêng biệt (`add mail khoi phuc`, `Hotmail`, `Tiktok_Reg`).



## Startup (mandatory)



- Read `AGENTS.md` + `docs/ai/automation-core-development-guide.md` FIRST —

  they encode the recovery contract, worker boundaries (Luna/flash worker is

  the only patch/live executor), commit gate, and no-live-validation rule.

- Audit routing follows the workspace rule: **AG Opus is primary** for plan/code

  audits; Terra is fallback for ordinary cases, Sol for difficult/high-risk

  cases, and OpenCode audit is last fallback. Terra/Sol are read-only auditors,

  never implementation workers. Keep the chosen audit model across re-audits

  unless the route fails or the user changes it. A `delegate_task(role=leaf)`

  does not pin the model; children inherit the parent model, so do not use a

  Luna/Flash child as a pretend auditor.

- Validation is OFFLINE ONLY: never run real ADB/account/mailbox/workbook

  ops as verification. Never `pm clear`.



For the reusable AG routing and safe nine-consumer audit pattern, see `references/taadaa-phase-routing-and-consumer-audit.md`.



## Workspace: dedicated branch + worktree (repo rule)



- Never edit the primary worktree. Create a dedicated branch + worktree from

  clean committed master:

  `git worktree add -b codex/<scope> ../automation-core-<scope>-wt`

- Confirm `git status --porcelain` is clean in your worktree before/after.

- Do NOT commit other-session artifacts (e.g. untracked `.hermes/plans/` in

  the main worktree) — your commit must contain only your phase's files.

- Tool quirk (persistent on this host): `search_files` FAILS on D:\ drive

  paths — it normalizes `D:/...` to `/d/...` and ripgrep reports

  "IO error ... cannot find the path specified" (verified repeatedly).

  Use terminal `grep -rn "<pattern>" src tests` from the worktree root

  instead of retrying search_files with different path spellings.

- **git-bash `git -C <path>` fails on the same D:\ worktree paths too**

  ("fatal: cannot change to '/d/Taadaa/...': No such file or directory")

  even though `ls -d` / `find` resolve them fine (verified 2026-08-12 on

  `tiktok-luot-nuoi-acc-recovery-adapter-p1-wt` and `taadaa/tiktok-follow`).

  Symptoms: `search_files` IO error, `git -C` fatal, `read_file`/`patch`

  work but `rg`/`git` under bash don't. Workaround: drive git/file ops via a

  Python script — `subprocess.run(['git',...], cwd=r'D:\Taadaa\<scope>-wt')`

  or `Path(r'D:\...').read_bytes()` — write the helper with `write_file`

  (heredoc backslash-escaping corrupts `\\`), then run it. Alternatively run

  `git -C` from a different cwd using the Windows-style path

  `D:/Taadaa/...` (forward slashes) which bash sometimes resolves when the

  MSYS `/d/` form fails.



## Testing — the #1 trap: static installed copy shadows src



`automation_core` is installed in the Hermes venv site-packages as a STATIC

copy (0.4.4x dist-info, NOT an editable `.pth`). Plain `python -m pytest`

from ANY cwd imports the INSTALLED copy — your worktree edits are never

exercised and tests can silently pass/fail against OLD code.



- ALWAYS: `PYTHONPATH=src python -m pytest <focused files> -q -p no:cacheprovider`

  (from the WORKTREE root — `src` must be the worktree's src).

- **`PYTHONPATH=.` (repo root) cũng import STATIC COPY — KHÔNG phải src/ (verified 2026-08-17)**: vì

  package nằm dưới `src/automation_core/`, root `.` không chứa `automation_core` top-level → site-packages

  thắng dù PYTHONPATH có `.`. Triệu chứng: test mới ImportError/AttributeError dù code đã thêm; probe

  `python -c "import automation_core; print(automation_core.__file__)"` in ra `...\Lib\site-packages\...`.

  KHÔNG đủ để chỉ dùng `PYTHONPATH=src`. Khi task/tool BẮT BUỘC lệnh `PYTHONPATH=.` (như detector

  verification), phải SYNC source vào site-packages trước:

  ```python

  shutil.copytree(r"D:\Taadaa\automation-core\src\automation_core",

                  r"D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core",

                  dirs_exist_ok=True)

  ```

  rồi chạy `PYTHONPATH=. ... -m pytest`; verify lại bằng probe `automation_core.__file__` + symbol mới.

  Với worktree thì tương tự (dst là site-packages của venv test đang dùng) — đừng sync nhầm sang hermes venv.

- Probe first when unsure:

  `PYTHONPATH=src python -c "import automation_core; print(automation_core.__file__)"`

  → must print `D:\Taadaa\automation-core-<scope>-wt\src\...`.

- WHY the trap exists (root cause verified 2026-08-11): a PERSISTED

  `PYTHONPATH` env var injects the Hermes venv site-packages

  (`C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`)

  into EVERY python run (`echo $PYTHONPATH` shows it, often tripled).

  `PYTHONPATH=src python ...` as a bash command PREFIX REPLACES that var

  (assignment semantics, NOT append) — that is the mechanism behind the

  recipe: it both drops the venv shadow AND puts the worktree `src` first.

  Probe: `python -c "import sys; print(sys.path[:3])"` and

  `python -c "import automation_core; print(automation_core.__file__)"`.

- Baseline collection blocker FIXED (Phase 2 task 2.0, 2026-08-11, commit

  `fix(tests): baseline collection error tools.verify_wheel_metadata (2.0)`):

  repo `tools/` is a NAMESPACE package (no `__init__.py`); the venv has a

  REGULAR `tools` package (with `__init__.py`) which WINS over namespace

  portions regardless of sys.path order, so `from tools.verify_wheel_metadata

  import ...` died at collection. The FIRST fix pinned the repo `tools` into

  `sys.modules` GLOBALLY at import time in `tests/test_package_metadata.py`.

  A later audit flagged that global unconditional patch (MINOR F7) — the

  current pattern is a CONTEXT-SAFE fixture (`wheel_metadata_tools`):

  `types.ModuleType("tools")` + `__path__ = [repo tools]` +

  `monkeypatch.setitem(sys.modules, "tools", repo_tools)` scoped per-test

  (monkeypatch restores afterwards). Never reintroduce the global import-time

  pin. Plain `pytest` passes that file; remaining plain-pytest collection

  errors are the static-copy shadow (installed copy lacks new

  modules/state) — ALWAYS use `PYTHONPATH=src` for authoritative counts.

- Some failures are pre-existing. **CẤM `git stash` để prove pre-existing trong WORKTREE (verified 2026-08-16)**: stash là REPO-GLOBAL — `git stash -q` trên worktree CLEAN tạo KHÔNG CÓ stash mới, rồi `git stash pop -q` pop nhầm **stash cũ của worktree/session khác** (hit: pop nhầm stash '0.2.45 version bump' cũ → UU conflict pyproject.toml 0.4.45, stash entry giữ nguyên). SAFE alternative: (a) nếu file của test fail KHÔNG nằm trong `git diff --name-only master...HEAD` → pre-existing BY DEFINITION, không cần stash; (b) chạy test trong worktree tạm mới tại base commit. Đã lỡ pop nhầm → recovery: `git show stash@{0}:<file>` vs `git show HEAD:<file>` vs `git show :1:<file>` (stage-1 base) → chọn bản HEAD (stash cũ = stale) → cp vào worktree → `git add <file>` → `git status --porcelain` clean → `git stash drop stash@{0}` SAU khi xác nhận nó stale. Tránh `git merge-file -p <(...) <(...) <(...)` (process substitution) trong git-bash trên worktree D: — exit 255/empty; dùng file redirects (`git show stash@{N}:<file> > /tmp/x`) thay thế. `git stash list` TRƯỚC khi pop để biết mình có thể pop nhầm gì.



## Testing — editable-install shadow (THIS host, overrides static-copy recipe)

The static-copy trap above is real on some hosts, but on THIS machine
(`Kibe`, verified 2026-08-22) `automation_core` is installed as an **editable
install** via a `MetaPathFinder` (the `__editable__.automation_core-*.pth` in
the Hermes venv `Lib/site-packages` contains `D:\Taadaa\automation-core\src`
and registers a finder that wins over `sys.path`/`PYTHONPATH` prepends).

Consequences that cost real debugging time this session:

- **`PYTHONPATH=src python -m pytest` from an impl worktree does NOT exercise
  your edits.** The MetaPathFinder resolves `automation_core` to the
  **coordinator** worktree (`D:\Taadaa\automation-core`) regardless of cwd or a
  POSIX `sys.path.insert(0, '.../src')`. Probe: `python -c "import
  automation_core.alerts as m; print(m.__file__)"` — if it prints
  `...\automation-core\src\...` (no `-implementation` suffix) you are testing
  the WRONG checkout.
- **POSIX paths silently fail on Windows Python.** Prepend with a
  **Windows-style** path, NOT `/d/...` (MSYS form). `sys.path.insert(0,
  '/d/Taadaa/automation-core-implementation/src')` resolves to nothing and is
  ignored — `env PYTHONPATH='/d/Taadaa/...'` likewise. Only
  `env PYTHONPATH='D:/Taadaa/automation-core-implementation/src'` works.
- **Working cross-repo override recipe (verified):**
  ```
  VPY="C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"
  cd '/d/Taadaa/tiktok-luot nuoi acc-implementation'
  env PYTHONPATH='D:/Taadaa/automation-core-implementation/src' "$VPY" -m pytest -q python_runner/tests/test_ai_recovery.py -k '...'
  ```
  - The core override (Windows-style) makes `automation_core` resolve to the
    impl core worktree.
  - `python_runner` is NOT installed — it resolves from the **cwd** (impl
    consumer), so run pytest from the consumer impl worktree root.
  - Consumer tests import `scheduler.recovery_runtime` etc. via
    `python_runner/tests/_path_setup.py` (inserts `python_runner/` dir onto
    `sys.path`) and use rootdir importmode, so `python_runner/tests` is on
    `sys.path` automatically.
- **Gate 0 worktree rule still applies:** edits go in a dedicated clean
  `codex/*` worktree/branch for each repo (consumer + core). Confirm both
  `git status --short --untracked-files=all` are clean and HEADs match the plan
  baseline before editing. The coordinator worktrees must stay untouched.

## RED proof against HEAD in a worktree — HEAD-src overlay (no stash)

`PYTHONPATH=src` ALWAYS exercises worktree code, so fresh tests cannot show RED
against current production — and `git stash` is banned in worktrees (pitfall above).
Verified recipe (2026-08-23, ADB timeout recovery):

1. Extract HEAD's `src` tree into an OS-temp overlay WITHOUT touching any working
   file: run `git archive HEAD src` via subprocess and pipe stdout to
   `tar -x -f - -C <tmp>`. Windows tar NEEDS the explicit `-f -` for stdin — bare
   `tar -x` tries to open `\\.\tape0`. `git archive HEAD <path>` keeps the `src/`
   prefix, so the import root is `<tmp>/src`.
2. Probe provenance FIRST: `env PYTHONPATH='<windows-style tmp>/src' python -c "import automation_core.adb as m; print(m.__file__)"` → must print the OVERLAY path.
3. Run the focused tests with that PYTHONPATH; record honest RED counts
   (e.g. 6 failed / 5 passed); then delete the overlay dir.
4. GREEN pass afterwards with `PYTHONPATH=src` from the worktree + provenance probe again.

Pitfalls from consolidating `run`/`run_bytes` into one `_execute` executor (same change):
- Classification helpers that expect str raise `TypeError: a bytes-like object is
  required` on RAW BYTES stderr from the `text=False` path — decode utf-8
  (errors="replace") at the seam before marker matching. Core-only tests stayed
  green through this bug; the CONSUMER suite (`python_runner/tests/test_adb.py`,
  exec-out retry case) caught it. Always run the consumer ADB regression when the
  core ADB seam changes.
- A refactor that reads MORE attributes off `CompletedProcess` (e.g. `.args`)
  breaks legacy test stubs that never defined them — fix the stub faithfully
  (add the real attribute), do not weaken production to tolerate missing attrs.
- Scripted `side_effect` sequences must be traced against the REAL control flow
  before being trusted: with default `connection_retry_attempts=3`, a reboot-window
  scenario needs explicit `connection_retry_attempts=2` or filler script entries get
  consumed as boot probes; match recorded calls by argv SUFFIX (`adb_path`, `-s`,
  serial come first), never by equality with the logical args.
Case study: `references/adb-timeout-recovery-red-green-2026-08-23.md`

## pytest pitfalls on this codebase (reusable)

- **`PYTEST_CURRENT_TEST` is set AFTER fixtures, before the test body.** If
  production code early-returns on `os.environ["PYTEST_CURRENT_TEST"]`, deleting
  production code early-returns on `os.environ["PYTEST_CURRENT_TEST"]`, deleting
  it in a fixture is too early — pytest re-injects it just before the body.
  Delete it at **call time inside the test** (`monkeypatch.delenv(..., raising=False)`
  right before invoking the function under test).
- **Do not `patch.object(agent, "code_patcher")`** (the imported module object).
  It replaces the bare name with a Mock, so `run()`'s `code_patcher.ROLLBACK_THRESHOLD`
  becomes a MagicMock and raises `TypeError: '>=' not supported`. Instead patch
  the **specific functions**: `patch.object(code_patcher, "record_alert", return_value=0)`
  and `patch.object(code_patcher, "apply_and_commit", return_value={...})`,
  plus `patch("ai_recovery/core.module.func", ...)` for functions referenced as
  `module.func`.
- **`agent.main()` takes no positional args (argparse).** Call `agent.run(machine,
  serial, error_reason, alert_img, script, account)` directly to drive the
  entrypoint path in tests; do not call `agent.main([...])`.
- **Never nest `unittest.main()` inside a class body** via the patch tool — a
  stray indentation collapses the `if __name__ == "__main__":` block into the
  last test method → `INTERNALERROR ... SystemExit`. Append new test classes
  OUTSIDE the existing class and keep `if __name__ == "__main__":` at module top
  level. Prefer `git show HEAD:<testfile>` + append + `ast.parse()` + normalize
  CRLF over patch-tool appends on CRLF test files (see Editing section below).
- **`pytest -k 'image.*differ'` is an INVALID regex** (`.` between terms) — never
  use it; use explicit `-k` terms joined by `or`.

## Editing core files (CRLF + patch-tool hazards)



- Repo files are CRLF. The `patch` tool's fuzzy matcher repeatedly

  RE-INDENTS untouched blocks on indentation-sensitive CRLF hunks (happened

  3× in one session on results.py, device_lock.py, global_recovery.py —

  small hunks too, not just giant files). If a patch diff shows unexpected

  re-indentation, STOP and repair via python exact-replace, don't stack more

  patches.

- Reliable edit recipe (one python script per batch):

  read text → for each hunk `assert old in text` + `text.replace(old, new)`

  → `ast.parse()` → write → then `python -m py_compile` + `git diff --check`.

- If the fuzzy matcher ALREADY mangled a file (happened on a CRLF TEST-file

  append: the whole appended block was re-indented +4 and nested inside the

  last test function, lint=IndentationError): rebuild deterministically

  instead of stacking more patches —

  `git show HEAD:<path>` → append the intended block (0-indent defs) →

  `ast.parse()` → normalize `\r\n` → write. Verify with `git diff --stat`

  (additions only, no churn) + `file <path>` reports CRLF.

- Same recipe for appending tests: `git show HEAD:tests/<file>` + append is

  the SAFE append path on CRLF files; avoid `patch`-tool appends entirely.

- `write_file` emits LF → normalizes to CRLF to keep diffs minimal:

  `text.replace('\r\n','\n').replace('\n','\r\n')`. Verify a file stayed

  pure: `file <path>` reports "CRLF line terminators". `git diff --check`

  does NOT flag line-ending churn — check `git diff --stat` for sanity.

- After EVERY source edit: `python -m py_compile <file>`; before reporting:

  `git diff --check`.



## Recovery contract invariants (state machine)



`DETECTED -> CLASSIFIED -> RECOVERY_RESERVED -> RECOVERING -> RECAPTURED ->

GUIDED_RECOVERY_REQUIRED -> RETRYING -> VERIFIED_SUCCESS | FINAL_BLOCKED` +

terminal `FAILED_LOCKED` (Phase 1, 2026-08-11):



- FAILED_LOCKED is terminal and RETENTIVE: device lock stays held

  (status `failed_locked`, `owner_active=False`) until user-explicit open.

- Exactly 5 source edges (CLASSIFIED / RECOVERY_RESERVED / RECOVERING /

  RECAPTURED / GUIDED_RECOVERY_REQUIRED → FAILED_LOCKED). RETRYING is

  deliberately NOT a source — it keeps the legacy FINAL_BLOCKED contract.

- `finalize_failed_locked` is a DEDICATED finalizer (never reuse

  `finalize_blocked`): no attempts≥2 / artifact requirement; minimal redacted

  evidence (reason, signature, attempts, artifact paths if present); missing

  artifact stays FAILED_LOCKED, never success.

- **`finalize_failed_locked` is a METHOD of `RecoveryQueue` (class at

  `recovery.py:152`, method at `:581`) — never a module-level symbol.**

  Plans/verify scripts that write `from automation_core.recovery import

  finalize_failed_locked` (or `import automation_core.recovery.finalize_failed_locked`)

  fail with `ImportError` even though the API exists — the correct existence

  probe is `callable(getattr(RecoveryQueue, "finalize_failed_locked", None))`

  on the imported class. Lesson from the consumer-migration Phase 0 (2026-08-12):

  an extract-wheel smoke failing with ImportError is usually a PLAN contract

  bug (wrong reference), not missing code — fix the verification contract in

  the plan, re-audit the plan, re-run the smoke; do NOT "fix" production code

  to match a wrong reference and never mask the failure.

- **FAILED_LOCKED durability tests must use `max_meaningful_attempts >= 2`

  (the meaningful floor).** With `max_meaningful_attempts=1`,

  `BatchRecoveryOrchestrator` returns a result-level FAILED_LOCKED and keeps

  the lock, but the durable queue state stays `CLASSIFIED` because

  `start_recovery` consumes attempts before the loop reaches

  `finalize_failed_locked` — so `queue.get(id).state == FAILED_LOCKED` fails.

  This is a test-design edge (cap below the contract floor; default meaningful

  = 8, consumer may only tighten), NOT a core bug. Write cap tests at ≥2.

- Strict queues gate direct terminal transitions

  (`TERMINAL_REQUIRES_COMPLETION_GATE` incl. FAILED_LOCKED);

  `RecoveryCompletionGate.verify` accepts FAILED_LOCKED WITHOUT artifacts.

- global_recovery lease: `mark_terminal("FAILED_LOCKED")` valid; watchdog →

  `TERMINAL` (never REQUEST_CHECKPOINT/REPLACE_WORKER); `acquire` refuses to

  overwrite a FAILED_LOCKED lease (`WORKER_LEASE_FAILED_LOCKED`).

- scheduler/base: `_device_lock_available` blocked on failed_locked owners

  (re-fire never reacquires); `_terminal_result_proven` understands

  FAILED_LOCKED; run_consumer retains the lease, never releases.

- recovery_runner: loader/restart skips FAILED_LOCKED targets BEFORE

  lock/detect; budget exhaustion from pre-RETRYING states →

  `finalize_failed_locked` + `_failed_locked_hold`; RETRYING budget path

  keeps old FINAL_BLOCKED + release.

- Redact ALL evidence (`redact_value`) — serial/target id/credentials never

  in persisted state or events.

- Phase 2 (2026-08-11) AI escalation hook: `escalation.py` = hook registry +

  event names (`ESCALATION_REQUIRED`/`AI_ESCALATION_*`) with ZERO

  spawn/provider/credential surface (R2.6 scans it). Hook is consulted at

  NO_HANDLER (single + batch preflight), HARD_STOP, generic reserve/start/

  recapture/verifier exceptions, and preflight-blocked targets; NON_RETRYABLE

  fails closed DIRECTLY and never consults the hook — routed by the

  `NonRetryableFailureError` TYPE (F-3 pattern: type, not message).

  No-hook / hook-fail / success-without-proof → FAILED_LOCKED (lock held);

  proof-backed success → intermediate `FinalResultStatus.ESCALATION_REQUIRED`

  result, NEVER a release (I4 gate stays).

- Design constraint: NO new `RecoveryState.ESCALATION_REQUIRED` was added —

  the escalation signal is event-only. A new pre-RETRYING state would force

  `_FAILED_LOCKED_SOURCE_STATES` AND the R1.7 parametrize helper

  (`_drive_to_state` in tests) to change — a coupled Phase 1 test break.

- `mark_escalation_required` assigns a fresh reservation token + owner when

  none exists (NO_HANDLER from CLASSIFIED has none) so strict-mode

  `finalize_failed_locked` satisfies the reservation gate; `_lock_failed`

  finalizes with `record.owner_id or self.owner_id`.

- `BatchRecoveryOrchestrator.preflight` now RETURNS a per-target

  blocked map (missing handler blocks only that target; duplicate-id /

  missing-verifier still raise for the whole batch). Callers ignoring the

  return value stay compatible.



## Phase 2 audit hardening (MINOR_FIXES F1-F7, 2026-08-11)



Fail-closed invariants added when fixing the 7 MINOR audit findings; full

per-finding map: `references/phase2-minor-fixes-fail-closed-2026-08-11.md`.



- **Pre-record exceptions NEVER return HARD_STOP.** Both `_run_one` except

  tails (RecoveryContractError and generic Exception) route

  record-`None` / state-outside-`_FAILED_LOCKED_SOURCE_STATES` to

  `_lock_failed` → durable FAILED_LOCKED + `_failed_locked_hold`. The AI

  escalation hook is consulted ONLY when a finalizable record exists

  (record in source states); pre-record errors fail closed DIRECTLY, no hook.

  Old `lock.set_status("handoff")` + HARD_STOP returns are gone.

- **Durable FAILED_LOCKED creation recipe (`_lock_failed`)** — when no

  finalizable record exists: `queue.reserve(signature or

  "UNKNOWN_SIGNATURE", root_cause=reason)` → DETECTED →

  `mark_escalation_required` (mints the strict-mode reservation token/owner)

  → `transition(CLASSIFIED)` (DETECTED→CLASSIFIED is the one legal pre-source

  hop) → `finalize_failed_locked(token, owner)`. If finalization itself fails

  (contended/broken store) → result-level FAILED_LOCKED + lock held +

  `finalize_error` in evidence; non-finalizable states (RETRYING) → the same

  result-level fallback. Errors stay in reason/evidence, never swallowed.

- **Swallow-tolerance boundary (F3/F4):** in `_fail_closed`

  (`mark_escalation_required`) and `_append_ai_event`, ONLY

  `"unknown recovery target"` (no durable record yet) may pass silently; any

  OTHER RecoveryContractError surfaces as `escalation_required_error` /

  `event_errors` in the final FAILED_LOCKED evidence. `_append_ai_event`

  returns an error string instead of raising (raising would abandon the lock

  through the orchestrator catch).

- **`EscalationRegistry.call()` injects `budget_remaining` itself**

  (`escalation.py:153,166`: `budget = self.budget` when the kwarg is None,

  default `DEFAULT_ESCALATION_BUDGET=3`, then passed to the hook). An audit

  finding "budget_remaining not passed to escalation.call()" is resolved with

  an inline comment citing those lines — do NOT hand-pass budget args from

  the consumer (core owns the budget; hand-passing creates a second budget

  owner). Verified 2026-08-12 P1 pilot audit finding A.

- **`EscalationRegistry.call` consults ONLY `_hooks[0]`** (F5) — first hook

  authoritative, no dead loop, no unreachable `return None`; raising hook →

  wrapped FAILED outcome, still no fall-through.

- **`_escalation_pending` holds the lock explicitly** (F6) — proof-backed

  hook success → ESCALATION_REQUIRED result passes through

  `_failed_locked_hold` so the lock has status `failed_locked` and is never

  abandoned to GC/`__del__`; no lock → no-op.

- **Test drift**: `test_unexpected_worker_exception_moves_lock_to_handoff`

  (asserted HARD_STOP + handoff) became `..._fails_closed_to_failed_locked`

  (FAILED_LOCKED + failed_locked + durable record); new regression tests

  F2/F3/F4/F6 in `test_recovery_contract.py` (`test_contract_error_before_...`,

  `test_mark_escalation_required_error_is_not_swallowed`,

  `test_ai_event_append_error_is_not_swallowed`,

  `test_escalation_pending_holds_lock_explicitly`).

- **Baseline counts for this phase**: targeted group 156 → 160 (+4 new tests)

  → 161 with test_package_metadata; full suite 550+1 pre-existing → 554+1

  (same pre-existing `test_startup` fail).



Full design record + test maps:

`references/failed-locked-phase1-2026-08-11.md`,

`references/ai-escalation-phase2-2026-08-11.md`,

`references/phase2-minor-fixes-fail-closed-2026-08-11.md` and

`references/lock-open-phase3-2026-08-11.md`.



## Consumer adapter pilot audit (P1, 2026-08-12): REJECT → 3 MAJOR + 3 MINOR



First consumer-adapter pilot commit (`2c2e21d`, worktree

`tiktok-luot-nuoi-acc-recovery-adapter-p1-wt`) got an AG Opus **REJECT**

despite 20/20 focused tests green — evidence that consumer-boundary

fail-closed has its own audit surface beyond the core contract tests.

Findings + the exact fixes (all verified 20/20 again after):



**M1: twin registration helpers must share validation.** `register_feed_recovery_escalation`

(flows) validated `hook is None or not callable(escalate)`; the scheduler-side twin

`register_escalation_hook` (recovery_handlers.py) had ZERO validation and silently

registered `None` → crash later at `escalation.call()` after lock acquisition (orphaned

lock). Fix: identical `TypeError` gate in BOTH wrappers, plus a test asserting `None` /

`object()` raises. Consumer wrappers duplicate core's `EscalationRegistry.register`

validation because the consumer contract boundary is what the audit checks — one wrapper

validating and its twin not is a finding every time.



**M2: never mix consumer enum values into a result dict that core switches on.**

`classify_manual_needed_popup` returned `"status": ExitStatus.MANUAL_NEEDED.value`

(`"manual-needed"`, consumer enum) while every sibling branch used

`FinalResultStatus.*.value` — downstream dispatch on `FinalResultStatus` would never

match, silently dropping the terminal into an unhandled state. Fix: use the core enum

uniformly (`FinalResultStatus.FAILED_LOCKED.value`), keep consumer nuance in a separate

key (`"manual_needed": True`). Test hard-coding `"manual-needed"` masked the type

inconsistency — update the test with the fix, don't keep it green by string.



**M3: one registry owner.** `_feed_recovery_queue()` built a queue AND assigned

`queue.registry`; `FeedRecoveryAdapter.__init__` then overwrote `self.queue.registry`

with a second `build_recovery_handler_registry()` call (double construction + silent

swap). Fix: the adapter is the single owner — the helper builds plain queue state and

the adapter assigns the registry once (`registry or build_recovery_handler_registry()`).



**m1: dead exported API removed.** `expose_recovery_registry()` (no callers, no tests)

added API surface to a security-sensitive module — deleted from body AND `__all__`.

When an audit calls a name "unnecessary API surface", remove it; leaving it invites a

repeat finding.



**m2: vacuous redaction assertions.** Test asserted `"123456"` / `"do-not-store"` /

`"jwt-like-secret"` were absent from evidence — but they were NEVER injected into the

evidence, so the assertion proved nothing (always green). Fix: the adapter now puts real

fixture secrets (`ctx.device_id`, `ctx.account`) into evidence, and the test asserts the

raw values are gone AND `"<redacted>"` (core `redact_value` marker) is present. A

redaction test whose secrets never enter the pipeline is a fake-green.



**m3: brittle core-behavior assumption.** `test_register_hook_idempotent_and_typed`

asserted `escalation.hook_count == 1` after registering the same hook twice — correct

because core `EscalationRegistry.register` dedups by identity (`if hook not in

self._hooks`), but the test documented nothing about it. Fix: comment citing

`escalation.py:125-126` so a future core change that alters dedup fails loudly with the

reason visible.



Working tree vs core pin: pilot used an SELF-BUILT wheel `automation_core-0.4.45`

(sha256 recorded, built from core HEAD `3f63c87`), installed in a FRESH venv

(`p1-feed-venv-v2-20260812`) made from the real Python 3.12 — the first venv attempt

was broken because global `PYTHONPATH` pointed at the hermes venv site-packages

(`env -u PYTHONPATH` prefix on every command fixed it). Always verify

`automation_core.__file__` resolves INSIDE the target venv, and record the wheel source

+ sha in the handoff for the auditor.



Full findings text: `references/consumer-adapter-pilot-audit-reject-2026-08-12.md`.



## Phase 3 (2026-08-11): user-explicit lock open — `cli.py lock list/inspect/open`



A terminal FAILED_LOCKED lock is released ONLY through the explicit CLI/API

path. `acquire_device_lock` still refuses it even with authorized takeover

(`_takeover_payload` keeps `owner_status == "failed_locked" → None` — do NOT

weaken that; the open path is the only door).



- `device_lock.py`: `list_failed_locked_locks` (read-only, dedup by owner

  identity — one logical lock = machine+serial alias FILES), `inspect_device_lock`

  (read-only), `open_failed_locked_lock` (the only opener). Open requires ALL

  of: `takeover_authorized=True` (CLI `--confirm`), non-empty `takeover_reason`,

  scope ∈ {SAME_PROJECT_RECOVERY, FULL_SCOPE_TAKEOVER}; any miss →

  `DeviceLockTakeoverUnauthorized`, nothing mutated. Open accepts only

  `failed_locked` + `owner_active=False`, verifies alias consistency, deletes

  aliases under the same path guards + rollback as `_release_lease_paths`,

  returns `DeviceLockOpenAudit`.

- `recovery.py`: `RecoveryQueue.mark_lock_opened_by_user(target, reason=...)`

  appends durable `LOCK_OPENED_BY_USER` event + `opened_by_user` evidence

  (reason mandatory; non-FAILED_LOCKED record refused). The record STAYS in

  terminal FAILED_LOCKED — NO state-machine transition, never add one (Phase

  1/2 invariant); the event IS the user-requested open marker.

- Ordering rule (bug caught during dev): the authorization gate

  (`open_failed_locked_lock`) must run BEFORE recording the queue event —

  event-first would durably record LOCK_OPENED_BY_USER for an unauthorized

  attempt. Fail-fast pre-check of the queue record (state==FAILED_LOCKED)

  is fine and mutation-free before the gate.

- Alias completeness: addressing by one alias must complete the other from

  the owner payload (`_complete_lock_identity`) or open leaves the sibling

  alias file behind / inspect misses it (both files must be covered).

- Redaction for lock output: `redact_value` covers serial/machine/workbook

  keys; ALSO redact `command` (argv can carry sensitive paths) and emit

  `released_path_count` instead of `released_paths` (filenames contain the

  serial). `_emit` secret regex gained `credential`.

- CLI-surface scan test (R3.5): walk every subparser + option string, assert

  none matches `recover|retry|auto`; `--confirm`/`--reason` exist ONLY on

  `lock open` (list/inspect carry no mutation flag).

- Counts: focused 86 → 98; full suite 554+1 pre-existing → 566+1 (same

  pre-existing `test_startup` fail, never claimed as new). Commit 57355ad.



## Phase 4 (2026-08-14): user-authorized lock gate — automation never auto-locks



User decision (after quantifying 7331 lock-skip events in `.ai-runs` of

`tiktok-luot nuoi acc` over 8 days; each lock also carries a 180 s

readiness_timeout): **automation must not create device locks on its own.**

Only an explicit operator command locks a machine; when automation needs a

machine that is already locked, it must SURFACE the conflict for the user's

decision (release or skip) — never silently `skipped-device-locked`.



- `device_lock.py`: new exception `DeviceLockNeedsUserDecision(RuntimeError)`

  (fields: path/owner/machine/serial/caller_project); new kwarg

  `user_authorized: bool = True` on `acquire_device_lock` AND the `DeviceLock`

  compat class. When `user_authorized is False`: any existing lock for the

  target → raise `DeviceLockNeedsUserDecision`; **NO existing lock → return a

  no-op `_UnlockedDeviceLockLease` (subclass of `DeviceLockLease`; every

  lifecycle call release/finish/set_status/release_with_audit is a no-op) so

  the automation runs UNLOCKED and no lock file is ever created.** Default

  stays `True` so operator/CLI/contract paths and all legacy tests keep

  working; consumers that must not auto-lock pass `False` explicitly.

- **PITFALL — absence of a lock is NOT a conflict:** the first implementation

  raised `DeviceLockNeedsUserDecision` even when no lock existed (owner=None),

  which made every unlocked machine report "locked by ? (pid ?)" /

  `needs-user-decision` with empty owner. The no-op lease is the correct

  semantic: no lock → run free; lock exists → surface for operator decision.

- **PITFALL — param-order contract test:**

  `test_device_lock_preserves_legacy_positional_parameter_order` asserts the

  EXACT `DeviceLock.__init__` parameter list. New kwargs must be appended at

  the END (after `takeover_proof`), never inserted mid-list, AND the test's

  expected name list must be updated to include the new name — both halves,

  or the suite goes red.

- Consumer pattern (run_tiktok.py single mode + multi_machine_feed_session.py

  reservation): pass `user_authorized=False`; catch

  `DeviceLockNeedsUserDecision` BEFORE `DeviceLockUnavailable`; write

  `lock_pending_user_decision.json` into artifacts.run_dir + notice to stderr +

  final_status `needs-user-decision` (NOT `skipped-device-locked`).

- Recovery reacquire paths (`reacquire_recovery_lock`, `recovery-handoff`)

  keep default `user_authorized=True` — they only run for machines already

  locked (reservation succeeded first), so they never auto-create a lock.

- **VPN watcher exception — temporary event lease, not automation auto-lock:**

  a per-machine watcher event that is actively handling reboot/reconnect may

  claim a short-lived lease while proxy/VPN recovery is in progress. This is

  deliberately different from consumer batch auto-locking: release it

  immediately after proxy assignment, live VPN/`tun0` verification, and the

  `proxy_ready` marker. The watcher must not hold device locks while idle.

  Keep the watcher process singleton separately so duplicate watchers cannot

  race; do not implement this exception by passing `user_authorized=False` to

  the temporary watcher lease (that makes an unlocked target return a no-op

  lease and prevents the watcher from protecting its own recovery window).

  Feed/upload/follow/login consumers still pass `user_authorized=False`.

- **Operational simplification:** for a consumer to resume after reboot, the

  decisive gate is per-machine live VPN readiness: proxy assigned, VPN app

  connected, and `tun0` verified. Once those checks pass, the consumer may run;

  no additional long-lived readiness lock is required. A stale `proxy_ready`

  marker must not override a failed live VPN preflight or a boot-id mismatch.

- Ship sequence: `python -m build --wheel` → install with

  `env -u PYTHONPATH <venv>/Scripts/python.exe -m pip install --no-deps --force-reinstall dist/*.whl`

  → verify `DeviceLockNeedsUserDecision` importable from the venv (consumer

  `core/device_lock.py` compat shim must re-export the new name too).

- Counts: focused 92/92 (device_lock + cli + new `test_user_lock_gate.py` 3

  tests); full suite 572 pass + 1 pre-existing `test_startup` fail (proved

  pre-existing via `git stash` — never claim as new).

- **16/08 — user CHỐT mutex-style always-release lock policy.** Đã qua plan-audit Claude opus-5: REJECT (2 CRIT) → MINOR_FIXES ×2 → thiết kế v4:

  - **`release_on_terminal: bool = False` DEFAULT (opt-in — CRITICAL: default True sẽ silently invert recovery FAILED_LOCKED retention)** trên `DeviceLockLease` field + `acquire_device_lock` kwarg LAST + `DeviceLock` compat kwarg LAST + `locks.py` wrapper (forward + `__exit__` gọi canonical `release()` → `_release_lease_paths` unlink, KHÔNG `FileLease.update(status=...)` — status write không xoá file).

  - `finish()`: `if succeeded or self.release_on_terminal: release() else set_status(...)`. `__exit__`: `if release_on_terminal: release(); return` (exception cũng release — intentional, crash path). `_UnlockedDeviceLockLease` giữ no-op override finish/__exit__ (KHÔNG kế thừa parent release trên lock_paths=[]).

  - **CHỈ scheduler/base.py:298 `DeviceLock(...)` truyền `release_on_terminal=True`** — đó là NGUỒN lock-death duy nhất (consumer repos đã `user_authorized=False` unlocked; `recovery_runner` nhận lock từ `target.acquire_lock()` consumer, `recovery.py` FAILED_LOCKED retention = OUT OF SCOPE giữ nguyên).

  - Scheduler re-run theo slot NGÀY; `serve()` KHÔNG gate `failed-locked` (chỉ gate `awaiting-verified-terminal-result`) → retry hôm sau INTENTIONAL (lock = pure mutex). `state["status"]="failed-locked"` = report trail. Retry daily vô hạn cho máy fail vĩnh viễn = chấp nhận (operator gỡ khỏi roster).

  - Test mới `tests/test_release_on_terminal.py`: opt-in tests assert **FILE ABSENCE** (`not path.exists()`), không chỉ "không exception" (owner-checked unlink phải được chứng minh); default-retains; context-exception-releases; compat; legacy wrapper; no-op unaffected. Update `test_device_lock_preserves_legacy_positional_parameter_order` name list (append kwarg).

  - Plan: `.hermes/plans/2026-08-16_230649-release-always-device-lock.md`; chi tiết audit: `references/release-on-terminal-lock-2026-08-16.md`.

  - **IMPLEMENTED 2026-08-16** (worktree `automation-core-release-always-wt`, branch `codex/release-always-lock`, 3 commits: `ded3e9b` canonical device_lock.py, `c000af7` locks.py wrapper, `c12519d` scheduler opt-in). PITFALLS đã gặp khi implement: (1) scheduler FAILED_LOCKED branch phải chuyển từ `lease.set_status("failed_locked")` sang `lease.finish(succeeded=False, failure_status="failed_locked")` — nếu giữ set_status thì dù lease có release_on_terminal=True vẫn KHÔNG release (set_status chỉ ghi status, không unlink); (2) device_lock.py field `release_on_terminal` phải nằm TRƯỚC `_released: bool = field(init=False)` vì field non-default không được đứng sau field default; (3) để chạy scheduler run_consumer trong test cần readiness root cô lập (`CODEX_DEVICE_READINESS_DIR` + viết `proxy_ready` JSON theo `readiness.readiness_path` sha256 name) nếu không sẽ timeout 180s; (4) đọc `git show HEAD:file` rồi append rồi normalize CRLF 1 lần cuối = cách an toàn duy nhất để append đúng trên test CRLF (write_file LF → normalize sau khi ast.parse; KHÔNG normalize nhiều lần — lần 2 sẽ double blank lines).

  - Full suite after implementation: 574 pass + 1 pre-existing `test_startup` fail (baseline 574+1, không đổi count — +2 tests net: 8 release_on_terminal + 2 scheduler mới - 0 removed).



## TDD + evidence discipline

- **Reservation-lock Protocol v2 cross-repo contract** (PowerShell
  `register gmail/run_parallel.ps1` ↔ `automation_core.device_lock`): a queued
  reservation MUST write `status="queued_v2"` + `lock_protocol_version=2` +
  `owner_active=true`, else the Python guard raises
  `DEVICE_LOCK_ACQUIRE_GUARD_UNAVAILABLE` and blocks the night-chain handoff.
  To unit-test the embedded PS1 reservation functions in isolation, extract the
  contiguous function block (lines 88–251 of `run_parallel.ps1`) into a temp
  `helpers.ps1` and dot-source it — the full script refuses dot-source via its
  `GMAIL_CANONICAL_LAUNCHER` guard + heavy inventory body. PITFALL:
  `Try-ReserveQueuedLock` uses atomic `CreateNew`, so reusing ONE lock dir
  across scenarios returns `$null` → false FAIL — give EACH scenario its own
  fresh lock dir. Full contract + isolation recipe:
  `references/reservation-lock-v2-powershell-contract-2026-08-22.md`.



- Write RED tests first (they may fail at COLLECTION with AttributeError when

  referencing not-yet-existing enum members — valid RED evidence; capture

  counts). Run RED, record counts; implement GREEN; run focused suites +

  adjacent regression (mandatory contract); static checks; report:

  exact files/diff, RED counts, GREEN counts, static checks, branch/worktree,

  and commit decision (defer commit when the gate requires audit APPROVED or

  full-suite green is impossible — leave the diff in the worktree).

- Parametrized TDD tests need a FRESH state store/path per iteration

  (reusing one queue JSON across iterations fails iteration 2+ with

  "not reservable"); after a terminal write, later ops on the same store

  legitimately fail — assert the refusal instead of reusing the store.

- When fresh in-turn verification evidence is demanded, use a small

  `hermes-verify-` prefixed script under `%TEMP%` created with

  `tempfile.NamedTemporaryFile` (or equivalent OS-safe `tempfile` path).

  The script must import the worktree source or explicitly validate the

  consumer against its pinned dependency environment, assert the changed

  behavior, assert module provenance/version where relevant, run with an

  explicit environment (`PYTHONPATH` or `env -u PYTHONPATH` as the repo

  contract requires), and delete itself in `finally` even on assertion

  failure. Before reporting, check for and remove stale prior

  `hermes-verify-*` scripts named by the verifier; a temp path appearing in a

  changed-path warning is not a repository change and must not be left

  behind. Report this explicitly as **ad-hoc verification**, never as suite

  green. A passing ad-hoc probe complements but does not replace the

  canonical focused/full pytest result; if the canonical command is not

  detected, do not claim the change is fully verified without this probe.

  Record the exact interpreter, dependency version/provenance, focused test

  count, and cleanup result. If the probe fails, report the concrete failure

  and do not relabel it green.

- For untracked newly-created files, `git diff --check` alone does not inspect

  them. Compile/read them explicitly and include them in an index-free diff

  or equivalent content check before handoff; verify CRLF separately when the

  repository convention requires it.

  Pitfalls from 2026-08-11: (1) state stores — use `tempfile.mkdtemp()` per

  run (a reused queue JSON from a prior partial run fails `reserve` with

  "target is not reservable"); (2) static scans — use the suite's precise

  regexes, a bare `"subprocess" not in text` substring check false-positives

  on docstring prose like "never imports subprocess"; (3) register/unregister

  are identity-based — pass the SAME hook instance; (4) don't chain cleanup

  after `&&` (a failing script skips the rm) — delete in the same command

  with `;` or let the script self-clean.



## release_on_terminal (2026-08-17): scheduler run-lock releases on every terminal outcome



User rule chốt 16/08 + implement 17/08 (merge a6dd30d, plan audit 4 vòng Claude opus-5 APPROVED):

- `release_on_terminal: bool = False` opt-in kwarg trên `DeviceLockLease` (field cuối trước `_released` init=False) + `finish()` (`if succeeded or self.release_on_terminal: release`) + `__exit__` (opt-in → release mọi exit kể cả exception) + `acquire_device_lock` + `DeviceLock` compat (append SAU `user_authorized`) + `locks.py` wrapper (canonical_lease ref; opt-in `__exit__` gọi canonical release unlink, KHÔNG FileLease.update status). `_UnlockedDeviceLockLease` thêm no-op `__exit__` override.

- **Chỉ scheduler/base.py opt-in True** (DeviceLock constructor) → FAILED_LOCKED branch đổi từ `lease.set_status("failed_locked")` giữ lock → `lease.finish(succeeded=False, failure_status="failed_locked")` (release) + state.json giữ record. Retry hôm sau = cố ý (slot ngày, user: "chạy xong dù success/fail/block gì cũng gỡ lock; lock = mutex thuần").

- Recovery contract (recovery_runner/_failed_locked_hold, recovery.py FAILED_LOCKED) KHÔNG đổi — ngoài scope.

- **PITFALL stash-pop conflict (lần 2)**: worktree + master đều có stash rác `On codex/reconcile-vpn-readiness-marker` (0.2.45/0.2.52 version edits tháng 7). `git stash -q` trong MAIN (có file untracked/modified sẵn như dist-machine12*) + `pop` → conflict UU pyproject.toml. Xử lý: `git checkout --theirs` từng file → add → resolve; sau đó XÁC NHẬN nội dung diff (`git diff HEAD -- <file>`) trước khi drop stash — nếu diff là version cũ quay lại thì `git checkout HEAD -- <file>` thay vì pop. Không bao giờ pop stash rác mù; đọc `git diff stash@{0}^ stash@{0}` trước.



## Operator Preempt Device Lock (2026-08-22) — Cướp quyền lock từ cron nền cho lệnh Operator
- Cơ chế `force_preempt=True` và scope `TAKEOVER_SCOPE_OPERATOR_PREEMPT = "OPERATOR_PREEMPT"` trong `automation_core.device_lock`.
- Cho phép script can thiệp ưu tiên (Hotmail login, Reg TikTok, debug...) cướp file lock ngay cả khi tiến trình cron nền đang chạy (`alive=True`, `status="running"`).
- Quy chuẩn 3 bước trên consumer repos: (1) `with DeviceLock(..., force_preempt=True)`, (2) targeted `am force-stop` app nền trên máy đích, (3) dọn dẹp app và về Home (`input keyevent 3`) khi xong.
- **Pitfall khi test / simulate lock (máy giả lập như 995, test_serial):** Tuyệt đối KHÔNG tạo file lock trực tiếp trong thư mục production `~/.codex/device-locks` mà không dọn dẹp trong `finally` (hoặc phải dùng isolated root `CODEX_DEVICE_LOCKS_DIR` với `tempfile.TemporaryDirectory()`). Nếu file test lock bị sót lại, cron watchdog `watch_device_locks.py` sẽ quét trúng và gửi cảnh báo rác `[Máy 995]` về Telegram.
- Chi tiết hợp đồng và metadata takeover: `references/operator-preempt-device-lock-20260822.md`.

## TikTok Logged-Out Modal & Account Recovery / Reconcile Triggering Contract (2026-09-01)

- **Vấn đề vận hành:** Khi tài khoản TikTok bị văng session ("Trạng thái tài khoản: Tài khoản của bạn đã bị đăng xuất..."), runner nếu chỉ bấm OK sẽ tiếp tục chạy trên máy bị thiếu nick hoặc rơi vào fail-closed làm ngưng trệ batch.
- **Kiến trúc thống nhất trong `automation-core`:**
  - **Module `automation_core.tiktok.account_recovery`**:
    - `preflight_reconcile_target`: Kiểm tra tính hợp lệ của `machine_id` (số nguyên dương 1..1000, từ chối boolean/danh sách), định dạng serial alphanumeric và khả năng kết nối ADB trước khi tương tác màn hình.
    - `resolve_machine_serial_from_workbook`: Đọc mapping serial chính xác từ file an toàn `taikhoan_run_safe.xlsx`, tự động fail-closed nếu có xung đột serial hoặc hàng chứa serial trống/lỗi.
    - `trigger_account_reconcile`: Tạo snapshot workbook tạm thời (read-only chmod 0o400) để tránh race condition (TOCTOU), khởi chạy tiến trình con `reconcile_tiktok_accounts.py` với bộ nhớ đệm luồng cố định (`deque maxlen=50KB`), giới hạn timeout an toàn, dọn dẹp sạch process tree và file tạm sau khi kết thúc.
    - **Bảo toàn Casing Serial tuyệt đối:** Giữ nguyên 100% casing verbatim của serial cho mọi lệnh transport ADB (`-s <serial>`) và tham số CLI con. Tuyệt đối KHÔNG thay thế bằng `.casefold()` hay ghi đè casing từ workbook; `.casefold()` chỉ dùng cho phép so sánh logic và tạo tên lock file.
    - **Process Tree Containment an toàn:**
      - Trên Windows: Spawn suspended (`_CREATE_SUSPENDED = 0x00000004`), gán vào Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000`) trước khi resume (`NtResumeProcess`), đảm bảo 100% không leak tiến trình con/cháu.
      - Trên POSIX: `start_new_session=True` và chỉ kill process group khi tiến trình còn active (`proc.poll() is None`) trên nhánh timeout/error để tránh hazard tái sử dụng PGID.
    - **Xử lý Đường dẫn ADB linh hoạt:** `resolve_adb_binary` tự động phân giải file path trực tiếp hoặc chuỗi `"adb"` qua `shutil.which` trả về `Path` executable hợp lệ trước khi gọi child CLI hay tạo `AdbClient`.
    - Cơ chế đọc kết quả JSON summary nghiêm ngặt: kiểm tra kiểu dữ liệu, danh sách tài khoản thiếu (`remaining_device_missing`), đảm bảo không trả về dữ liệu nhạy cảm chưa kiểm duyệt.
  - **Module `automation_core.tiktok_popup`**:
    - `_extract_display_dimensions`: Tự động trích xuất kích thước màn hình thực tế từ XML hierarchy của TikTok (không hardcode kích thước).
    - `_find_verified_logged_out_dialog_container` & `_is_logged_out_modal_present`: Nhận diện cấu trúc modal hộp thoại thông báo "Trạng thái tài khoản" / "đã bị đăng xuất" căn giữa màn hình (`[0.45..0.90W] x [0.15..0.65H]`) thuộc package TikTok (`com.ss.android.ugc.trill`, `musically`, `aweme`), yêu cầu package attribution rõ ràng (từ chối node không có package).
    - `_find_logged_out_dialog_button`: Tìm chính xác nút xác nhận (`OK`, `Đã hiểu`, `Xác nhận`) có thuộc tính `clickable="true"` bên trong hộp thoại.
    - `_verify_tiktok_foreground_and_clean_ui`: Kiểm tra live `dumpsys window windows` (mCurrentFocus thuộc TikTok) và xác thực không có package lạ của bên thứ 3 trong hierarchy cả **trước khi tap (pre-tap)** và **sau khi tap (post-tap)**.
    - `dismiss_and_recover_logged_out_account`:
      - Bước 1: Preflight target an toàn và tạo `AdbClient` bất biến (immutable) gắn chặt với `validated_serial` và `resolved_adb` trong suốt transaction.
      - Bước 2: Kiểm tra focus pre-tap trước khi tap tọa độ để tránh bấm nhầm vào launcher / overlay hệ thống.
      - Bước 3: Nhấn nút `OK` đóng dialog và theo dõi `tap_attempted`.
      - Bước 4: Recapture xác thực dialog đã biến mất, không còn modal/dialog khác, và package foreground vẫn là TikTok.
      - Bước 5: Tự động gọi `trigger_account_reconcile` để kiểm tra danh sách tài khoản trên máy và tự động đăng nhập nick bị thiếu.
- **Tích hợp phía consumer (`tiktok-luot nuoi acc`)**:
  - Đăng ký detector và handler `account_logged_out_popup` (priority 96) trong `python_runner/flows/benign_popup_registry.py` và cập nhật `python_runner/core/classifier.py` / `python_runner/core/benign_popup.py`.
  - Khi runner nuôi nick gặp dialog đăng xuất ở bất kỳ trạng thái nào, hệ thống tự động bấm `OK` và gọi sang module recovery của `automation-core` để kích hoạt flow đăng nhập bù nick.


## Shared TikTok popup dispatch (2026-08-23, updated 2026-08-31)

- **Pitfall: System Permission Dialog Blocks Startup Focus Verification Gate (2026-09-02):**
  - **Triệu chứng:** Phiên nuôi nick bị dừng ngay tại khởi động với lỗi `prepare-tiktok failed to focus TikTok after launch` dù trên màn hình hiển thị popup quyền Android ("Cho phép TikTok truy cập vào danh bạ của bạn?").
  - **Nguyên nhân gốc:** Handler đóng popup (`detect_packageinstaller_permission_dialog`) đã được viết đầy đủ trong Core, nhưng trong `prepare_app_for_automation` / `device_prepare.py`, bước `verify_app_focus` poll kiểm tra `focused_package == target` (`com.ss.android.ugc.trill`). Khi popup hệ thống xuất hiện đè lên, foreground window thuộc `com.google.android.packageinstaller` / `permissioncontroller` -> focus check fail toàn bộ 10 attempts -> script fail-closed và abort phiên **trước khi** luồng chính chạy tới `dismiss_tiktok_popups`.
  - **Quy tắc & Giải pháp:**
    1. Khi chẩn đoán lỗi popup không được đóng, luôn kiểm tra xem lỗi xảy ra ở giai đoạn nào: **Startup Focus Gate** (`prepare_app_for_automation`) hay **Main Checkpoint Loop** (`dismiss_tiktok_popups`).
    2. Vòng lặp verify focus khi launch app cần tích hợp kiểm tra/dismiss các known system dialogs (`packageinstaller`, `permissioncontroller`) để gỡ popup giải phóng giao diện trước khi kết luận không focus được app.

- **Scope rule:** A popup that can appear after account switching, profile navigation, feed actions, or any TikTok redraw belongs in the shared TikTok popup contract (`automation-core`), not in consumer-level workarounds.
- **In-feed & Modal Follow Suggestion Contract (2026-08-31):**
  - **In-feed suggestion cards** ("Bạn bè với...", "Follow bạn", "Gợi ý follow" with "Follow lại" & "Không quan tâm"): classified under `contact_follow_suggestion` in `automation_core.tiktok.benign_popup`, returning direct `action="tap_follow_back"` to tap the "Follow lại" button instead of halting or skipping.
  - **Modal dialogs** ("Follow bạn bè của bạn" / "Follow your friends" with list of users and close `✕`): configured with `pre_action="tap_follow_button"` to tap "Follow lại" / "Follow" (under title bounds, excluding "Đã follow" / "Following"), then `action="tap_follow_back_and_close"` to tap `✕` (`:id/e63`, `:id/c3t`, or semantic close control). If no follow buttons remain, action falls back to `dismiss_close_x`.
  - **Startup & Checkpoint Dispatcher:** `dismiss_tiktok_popups` in `automation_core.tiktok.startup` handles `pre_action in {"tap_follow_button", "tap_follow_back"}` by tapping the target, recapturing XML, and continuing to close/verify without raising unhandled pre-action errors.
- **Standalone vs chained popups (e.g. Facebook permission dialog):** Popups like `facebook_contacts_email_permission` ("Cho phép TikTok có quyền truy cập vào email và danh sách bạn bè trên Facebook của bạn?") appear standalone on Profile/Feed as well as chained after Add Phone. Never gate benign popup dismissals behind a predecessor token (e.g. `_validate_and_consume_add_phone_chain_token`) in consumers — standalone appearances will fail closed as `unexpected popup/dialog marker detected`.
- **Fail-closed focus verification after dismiss:** After tapping a denial button on external/system popups (e.g. Facebook permission), verification must positively prove transition away from external packages (`com.facebook.katana`, `com.facebook.orca`, `com.facebook.lite`). If post-dismiss focus is missing, empty, or still belongs to the external package, dismiss must be marked `dismissed=False` and report unverified/still-visible.
- **ATX Agent local-port extraction & strict deadline bounding in `persistent_ui`:**
  - `adb forward --list` output format is `<serial> <local_port> <device_port>` (e.g. `serial-49 tcp:12345 tcp:7912`). Local port is index 1 (`parts[1]`), not index 2.
  - In `reset_atx_agent(timeout)`: Return `bool(ready)` based on stub readiness in `ps -A` (monkey fallback success is valid even if initial daemon start returned non-zero exit code).
  - All operations (stops, kills, starts, sleeps, ps polling, monkey fallback) must strictly compute and pass `remaining = overall_deadline - time.monotonic()`, immediately exiting `False` when `remaining <= 0` without inflating zero/sub-millisecond budgets.
- **In-app permission / contacts settings dialogs:** Popups prompting for device settings / contact sync ("Để kết nối với những người bạn biết trên TikTok, hãy cho phép truy cập vào danh bạ của bạn trong mục cài đặt thiết bị" with "Không cho phép" and "Mở cài đặt") must be classified in `automation_core.tiktok.benign_popup.detect_contacts_settings_permission_dialog` and wired into `detect_allowed_generic_popup` + `detect_tiktok_popup_action` returning `dismiss_deny_button` ("Không cho phép").
- **Exact label matching vs ad-hoc exclusions:**
  - Canonical detector pattern in `benign_popup.py` requires `_has_exact_label(elements, exact_body_terms)` for the full dialog body text, `_has_exact_label` for primary action ("Mở cài đặt" / "Open settings"), and `_find_exact_label_element` for negative dismiss ("Không cho phép" / "Don't allow" / "Deny").
  - Do NOT use loose substring containment (`term in value`) which fails audit for broad matching.
  - Do NOT invent ad-hoc exclusions (`if any(el.class == "EditText"): return None`) that clutter detector code when exact label matching on the unique multi-word dialog body is already 100% false-positive safe and matches canonical sibling detectors.
- **Review gate & strictness pattern:**
  - Strict model review (`plan-review` via 9Router) requires exact body and button label elements rather than loose substring matching.
  - Action mapping must strictly tap only negative buttons, never accept CTA or settings navigation.
- **Canonical API:** Use `automation_core.tiktok.startup.dismiss_tiktok_popups(...)` after each consumer UI recapture/checkpoint that may be blocked. Keep `dismiss_known_startup_popups(...)` only as the backward-compatible alias; do not add a second consumer-specific detector for the same popup.
- **Account-update action contract:** Require the exact title, security-link body, and a clickable semantic `Để sau` element. The action must be `dismiss_later_button`; never tap the CTA `Liên kết số điện thoại hoặc email`, a generic `Để sau`, or a coordinate chosen without XML evidence.
- **Verification contract:** After the tap, recapture XML and require the popup to be absent. Tests must cover the popup after account switcher and between later feed actions, plus negative cases where the safe button/body is missing. Keep tests offline with XML/mock adapters.
- **Diagnosis pitfall:** Before changing core, inspect both `automation_core.tiktok.benign_popup` and `automation_core.tiktok.startup`. The detector may already exist in core while a consumer fails because it imports/calls the symbol incorrectly. Distinguish “core detector missing” from “consumer integration/call-site missing.”
- **Worktree/provenance gate:** Validate from a dedicated core worktree and prove the imported module path points into that worktree; editable installs can otherwise make focused tests execute the coordinator checkout instead of the edited source.
- Detailed replay/test notes: `references/shared-tiktok-popup-dispatch.md` and `references/startup-focus-permission-popup-gate-20260902.md`.

## Release completeness gate for shared-core fixes

A source/test fix is not complete when the consumer executes a versioned wheel or
pinned artifact. For any shared-core change used by a consumer:

1. After focused source tests pass, bump the package version deliberately and build the artifact from the verified source.
2. Verify artifact metadata, hash, and an embedded production marker (for example the changed ADB argv) before touching the consumer pin.
3. Update only the consumer dependency pin to the new artifact, then run focused consumer tests with an isolated import path or temporary environment. Record module path and distribution version; do not infer provenance from an editable ambient install.
4. Classify consumer failures by seam: separate failures in the changed dependency from failures in concurrently dirty consumer flow files. Do not broaden the fix to make unrelated dirty tests green.
5. During closeout, commit/push core source/test/version and consumer pin as separate exact-scope commits, verify each remote SHA, and report any runtime still importing an older editable copy as a rollout caveat—not as a successful live rollout.

A source-only completion that omits the wheel bump/pin is a partial delivery. Use
`references/shared-core-release-gate.md` for the artifact/provenance checklist.

## Worktree is implementation-only; main/master is the delivery target

A dedicated worktree is required for implementation safety, but it is not the
final delivery location. When the user explicitly says `chốt phiên`, `đóng
phiên`, or asks to clean up:

1. Freeze the exact allowlist and inspect the coordinator worktree, feature
   worktree, branch, upstream, and unrelated branches before mutating Git.
2. Review the exact feature diff independently; do not treat focused tests or a
   worker self-report as approval.
3. Commit only the allowlisted files in the feature worktree, then fetch and
   rebase that branch against the actual upstream branch before integration.
4. Acquire the core merge guard, fast-forward the coordinator `master`/`main`
   only when ancestry and scope match, and rerun focused tests against the
   coordinator tree after integration.
5. Push the coordinator branch and verify `git ls-remote` equals the local
   commit SHA. Only then release the guard and remove the task-owned worktree
   and branch; never delete unrelated worktrees or branches.
6. Final evidence must show the coordinator worktree clean, local/upstream
   synchronized, the guard unlocked, and exactly one remaining coordinator
   worktree if cleanup was requested.

Do not report completion merely because the feature worktree is green or the
worktree was deleted. A worktree is the safe build surface; `master`/`main` is
the shipped surface.

## Pointer



Consumer-side work (building/fixing consumers of this core): load

`automation-core-consumer` instead.



## Pitfall: Telegram alert leak during Unit Tests / Pytest runs (2026-08-22)

- **Triệu chứng:** Khi chạy `pytest` hoặc `unittest` trên consumer repo (như `tiktok-luot nuoi acc` trong `test_multi_machine_feed_session.py`), các test cases giả lập lỗi (`MagicMock`, `NoneType`, VPN error, proxy mapping error) trigger code path gọi `send_farm_machine_alert()`, làm spam hàng loạt tin nhắn và ảnh chụp màn hình lên nhóm Telegram **Farm Alerts**.
- **Nguyên nhân:** Chỉ kiểm tra `if "PYTEST_CURRENT_TEST" in os.environ` là không đủ:
  1. Trong multi-threading (`ThreadPoolExecutor`), biến môi trường của test runner đôi khi không đồng bộ hoặc bị thiếu.
  2. Khi chạy qua `python -m unittest` hoặc test runner tùy biến, `PYTEST_CURRENT_TEST` không tồn tại.
- **Giải pháp chuẩn:**
  Dùng hàm helper `_is_test_environment()` toàn diện trong `automation_core.alerts`:
  1. Kiểm tra env vars: `PYTEST_CURRENT_TEST`, `PYTEST_VERSION`, `UNITTEST_RUNNING`.
  2. Kiểm tra `pytest` / `unittest` trong `sys.modules`.
  3. Quét call stack frames (`inspect.stack()`) tìm dấu vết `pytest`, `unittest`, `test_`, `_test.py`.
  4. Cung cấp override flag `FORCE_TEST_ALERT_DISPATCH=1` cho riêng test suite kiểm thử chính alert module (`tests/test_alerts.py`).


## Pitfall: Relative path resolution từ `__file__` trong core module khi cài vào venv site-packages (2026-08-20)

- **Bẫy `parents[N]` khi module core được cài vào site-packages:**
  Khi code trong `src/automation_core/*.py` dùng `Path(__file__).resolve().parents[3]` để trỏ sang consumer repo láng giềng (`D:\Taadaa\<consumer-repo>`), code chạy đúng khi chạy từ repo `D:\Taadaa\automation-core\src\automation_core`.
  Tuy nhiên, khi wheel được cài vào `D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core`, `parents[3]` trỏ về `D:\Taadaa\python-envs\automation` $\rightarrow$ đường dẫn target bị sai và `.exists()` trả về `False` trong im lặng (silent failure, ví dụ `_AGENT_SCRIPT` trong `alerts.py` không spawn được AI Auto-Recovery agent khi máy gặp lỗi).
- **Bẫy PYTHONPATH leak gây xung đột nhị phân C-extension (PIL/Pillow `_imaging` ImportError):**
  Nếu môi trường host có biến `PYTHONPATH` trỏ vào venv khác (như Hermes venv cpython 3.11) trong khi script farm chạy trên Python 3.12, việc `import PIL` sẽ load nhầm thư viện `PIL` không tương thích binary và văng `ImportError: cannot import name '_imaging' from 'PIL'`. Cần cô lập `sys.modules` và lọc sạch `sys.path` trước khi load các dynamic C-extensions trong alert/recovery producer.
- **Quy tắc sửa:**
  1. Kiểm tra tồn tại qua danh sách các đường dẫn candidate (canonical `D:\Taadaa\<consumer-repo>\...`, env override nếu có, rồi mới tới relative fallback).
  2. Tuyệt đối không chỉ dùng một biểu thức `parents[N]` duy nhất mà không có fallback hoặc logging cảnh báo khi target script/file không tồn tại.
  3. Bọc module import nhạy cảm với binary extension để loại bỏ leaked PYTHONPATH nếu phát hiện import lỗi.



- **Pitfall: Ghost IME state & SamsungKeypad (`com.sec.android.inputmethod`) on chained popups (2026-08-28):**
  - **Triệu chứng:** Sau khi đóng popup Thêm số điện thoại (Add Phone), TikTok hiện tiếp popup quyền Facebook/Contact (`manual-needed:popup`). Runner bị dừng với lỗi `keyboard remained visible after dismiss attempt` dù không có bàn phím trên màn hình.
  - **Nguyên nhân 1:** Android `dumpsys input_method` giữ cờ `mInputShown=true` cũ (ghost IME state) ngay cả khi bàn phím đã đóng. Nếu code kiểm tra `detect_keyboard_state` khi có UI XML mà không trả về kết quả XML (không có node bàn phím) mà lại rơi xuống dumpsys, nó sẽ nhận diện sai là bàn phím còn mở.
  - **Nguyên nhân 2:** Bàn phím Samsung đời cũ (Galaxy S7 / Android 7-8) dùng package `com.sec.android.inputmethod` (chưa có trong `KNOWN_KEYBOARD_PACKAGES`).
  - **Nguyên nhân 3:** `_KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE` và `_blocked_after_close_reason` thiếu các benign popup (`manual-needed:popup`, `packageinstaller/system-dialog`, `account-update-prompt`), khiến runner từ chối chuyển tiếp sang Registry để giải quyết tiếp popup thứ 2.
  - **Quy tắc sửa:**
    1. `KNOWN_KEYBOARD_PACKAGES` bắt buộc bao gồm `com.sec.android.inputmethod`.
    2. Khi có UI XML hợp lệ, `detect_keyboard_state` ưu tiên kết quả UI XML (`visible=False, source="ui_xml"`), không để dumpsys ghi đè.
    3. Cho phép các benign popup nằm trong danh sách màn hình hợp lệ sau khi đóng Add Phone để flow tiếp tục xử lý popup kế tiếp.

## TikTok popup rules — pattern 2 bước + DismissResult fields (2026-08-17)



- **Popup cần 2 thao tác tuần tự (VD \"Follow bạn bè của bạn\": bấm \"Follow lại\" rồi\n  X \"Đóng\") → dùng 2 PopupRule trong `TIKTOK_POPUP_RULES` với markers KHÁC NHAU,\n  KHÔNG cùng markers** (detector chọn rule ĐẦU match → rule 2 không bao giờ chạy):\n  - Rule 1 markers `(\"follow bạn bè của bạn\", \"follow lại\")` — \"Follow lại\" chỉ\n    tồn tại khi CHƯA follow → tap \"Follow lại\" (`id/thb`).\n  - Rule 2 markers `(\"follow bạn bè của bạn\",)` — sau follow, nút thành \"Gửi ..\"\n    → hết marker \"follow lại\" → rule 2 match → tap \"Đóng\"/X. `dismiss_all` loop 3\n    rounds (follow repo `core/popup.py`) xử lý tuần tự mỗi round 1 rule.\n- **`DismissResult` (tiktok_popup.py) KHÔNG có field `dismissed`** — fields là\n  `(detected, action_taken, matched_rule, verified, evidence)`. Consumer\n  `contacts_permission()` từng `getattr(result, \"dismissed\", False)` = luôn False →\n  `dismiss_all` tưởng popup chưa xử lý, không loop round 2. Fix: trả `detected`\n  (đã tap → dismiss_all loop tiếp). Khi viết consumer gọi `dismiss_popup`, đừng\n  đoán field — đọc class DismissResult.\n- **Substring collision trong UI XML text search (`_element_contains` & `_find_clickable_text`, máy 45, 2026-08-21)**:
  - Triệu chứng: Flow nhận diện nhầm đĩa nhạc/âm thanh video bài hát "Closer" thành nút đóng ("close"), tap vào tâm nút đĩa nhạc [999, 1712] khiến máy nhảy vào trang Sound Detail ("Sử dụng âm thanh").
  - Nguyên nhân: `_element_contains` so khớp lỏng `term.lower() in value.lower()` → từ khóa `"close"` bị ăn khớp substring vào `"Closer"`, `"Closed"`, `"Closet"`.
  - Fix chuẩn 2 tầng:
    1. **Core:** Bắt buộc dùng regex word boundary `(?i)\b<term>\b` cho các từ khóa đơn/ASCII (`close`, `save`, `đóng`...) khi tìm kiếm UI elements, tránh mọi va chạm substring.
    2. **Consumer:** Luôn có handler fallback trong Registry (ví dụ `sound_detail_overlay` gửi phím BACK) để tự giải thoát nếu vô tình bị lọt vào subpage/overlay âm thanh.
  - Chi tiết & case study: `references/ui-xml-substring-collision-and-popup-guards-20260821.md`.
- Wheel bump core + consumer verify: rebuild wheel (`python -m pip wheel . -w dist
  --no-deps`), cài `pip install --no-cache-dir --force-reinstall
  "D:\Taadaa\automation-core\dist\<new>.whl"` — **path Windows `D:\...`, KHÔNG
  MSYS `/d/...`** (pip là Windows binary → `/d/` thành `c:\d\` → OSError). Nếu
  `--force-reinstall` không ghi đè file (mtime không đổi): `pip uninstall -y` trước
  rồi install. Verify bằng grep symbol mới trong site-packages + xóa `__pycache__`
  nếu import vẫn thấy code cũ.

## Pitfalls: Account Switcher & Security Update Popups (2026-08-22, updated 2026-09-03)

- **Substring collision in Account Switcher Exclusion Filters (`_EXCLUDED_SWITCHER_TERMS`, 2026-09-03)**:
  - Triệu chứng: Các tài khoản hợp lệ chứa cụm từ liên quan đến trợ giúp/đề xuất (như `@helpme123`, `shelper`, `suggestme_acc`) bị loại trừ nhầm khỏi switcher header và danh sách tài khoản hợp lệ, gây lỗi `manual-needed:account-switcher-not-open` hoặc `ACCOUNT_MISSING`.
  - Nguyên nhân: Sử dụng phép kiểm tra substring lỏng lẻo `any(term in text for term in _EXCLUDED_SWITCHER_TERMS)`.
  - Quy tắc sửa: Bắt buộc dùng regex word boundary `(?i)\b<term>\b` cho từng từ khóa loại trừ: `re.search(r"(?i)\b" + re.escape(term) + r"\b", text)`.

- **Shell Variable Quoting & Preflight Result Consolidation (2026-09-03)**:
  - Khi chèn các biến cấu hình (như global proxy `http://host:port`) vào chuỗi lệnh `adb.shell(["export http_proxy=...; ..."])`, bắt buộc dùng `shlex.quote` để bảo vệ an toàn trước các ký tự shell đặc biệt.
  - Sử dụng helper chuẩn `_offline_result(...)` để đồng nhất định dạng trả về của `AndroidVpnPreflight` trên toàn bộ các nhánh probe thất bại do mất kết nối ADB transport.

- **Circular Import Removal in Benign Popup Registry (2026-09-03)**:
  - Tránh lazy import các hàm phụ trợ từ flow cấp cao (như `from .feed_swipe_smoke import _capture_xml_text`) bên trong `benign_popup_registry.py`.
  - Sử dụng trực tiếp `ctx.dump_hierarchy()`, `getattr(ctx, "xml_text", None)` hoặc fallback sang core persistent UI (`capture_atx_session_ui(ctx.adb)`).

- **Bounded Recursion Gate for Auto-Login Recovery in Profile Switcher:**
  - Khi `verify_and_switch_profile` không tìm thấy account mong muốn trong Account Switcher (`manual-needed:account-switcher-missing-expected`), nó kích hoạt `_maybe_recover_missing_account_via_login` rồi gọi đệ quy `verify_and_switch_profile`.
  - **Quy tắc chặn vòng lặp vô hạn (Infinite Recursion Pitfall):** Bắt buộc truyền cờ `allow_auto_reconcile: bool = True` vào `verify_and_switch_profile`. Khi gọi đệ quy sau khi reconcile thành công, BẮT BUỘC truyền `allow_auto_reconcile=False` và bọc khối recovery bằng `if allow_auto_reconcile and _is_account_switcher_missing_expected_reason(last_reason):`. Nếu sau reconcile tài khoản vẫn thiếu, flow lập tức dừng ở `manual-needed` thay vì tiếp tục trigger vòng lặp vô tận.

- **Canonical Identity Matcher (`matches_switcher_identity`):**
  - Hàm chuẩn `matches_switcher_identity(node_value, target_value)` xử lý so khớp fuzzy identity (@prefix, prefix >= 3 chars, badge trailing digits/symbols `\d+\+?`) được định nghĩa và export tại `automation_core.tiktok.account_switcher` và `automation_core.tiktok`.
  - Phía consumer (`feed_swipe_smoke.py`) import trực tiếp từ `automation_core.tiktok` (với safe fallback) và gán alias `_matches_profile_identity_text = matches_switcher_identity`, loại bỏ hoàn toàn mã trùng lặp.

- **Environment-Variable Priority cho Default Runtime Paths:**
  - Các hằng số mặc định trong `account_recovery.py` và consumer scripts (`DEFAULT_SAFE_WORKBOOK`, `DEFAULT_RECONCILE_SCRIPT`, `DEFAULT_ADB_PATH`, `DEFAULT_LOGIN_PROJECT`...) luôn ưu tiên kiểm tra biến môi trường (`os.environ.get("TIKTOK_SAFE_WORKBOOK")`, `os.environ.get("LOGIN_PROJECT_DIR")`...) trước khi fallback về đường dẫn mặc định trên đĩa.

- **TikTok 46.x Profile Layout & UIAutomator Badge Digit Concatenation (Incident Case 71, Máy 60):**
  - **Triệu chứng:** Script kẹt ở màn hình Profile root hoặc bấm nhầm vào body username copy-ID button (`id/sr3` `@crystal.1.15`), không mở được Switcher hoặc fail-closed với `manual-needed:account-switcher-not-open`.
  - **Nguyên nhân 1 (Body username copy button trap):** Trên layout TikTok 46.x chưa cuộn, `id/sr3` nằm ở vùng body (`y = 370..415`, `bounds left < 300`). Nút này chỉ dùng copy handle, không kích hoạt mở Switcher. `_profile_switch_fallback_anchor` cũ trả về `username_element` mù quáng khiến script tap nhầm vào body.
  - **Nguyên nhân 2 (UIAutomator badge / trailing digit concatenation):** UIAutomator nối dính các badge/button số ở cuối text của display name (`id/su7` -> `"crystal.1.11"`) và username (`id/sr3` -> `"@crystal.1.15"`). Khi cuộn profile (`_profile_scroll`), header username sticky `id/pke` (`bounds=[370,117][730,183]`) xuất hiện với text sạch `"crystal.1.1"`. Phép so khớp chính xác `node_value in identity_values` bị fail do lệch đuôi số (`"crystal.1.1"` != `"crystal.1.11"`).
  - **Xử lý chuẩn:**
    1. Trong consumer (`feed_swipe_smoke.py`):
       - `_profile_switch_fallback_anchor`: CẤM trả về `username_element` khi nó nằm ở vùng body (`center[1] > 260` hoặc `bounds[0] < 300`). Chỉ chấp nhận khi nó là sticky top header (`center[1] <= 250` và `300 <= center[0] <= 780`).
       - `_find_sticky_profile_header`: Sử dụng fuzzy/prefix matching (`_matches_profile_identity_text`: `v1.startswith(v2)` / `v2.startswith(v1)` / `rstrip("0123456789+ ")`) để nhận diện đúng node `pke` khi identity bị dính số badge.
       - `_resolve_profile_switch_anchor`: Khi view ban đầu chưa có sticky header, thực hiện cuộn profile (`_profile_scroll`), recapture XML, re-derive identity (`_profile_identity_from_xml`), và giải quyết `_find_sticky_profile_header`.
    2. Trong `automation-core` (`account_switcher.py`):
       - `find_switcher_anchor`: Áp dụng helper `_matches_switcher_identity` cho cả `preferred_candidates` và `identity_candidates` để hỗ trợ so khớp prefix/fuzzy khi có nhiễu badge uiautomator.
  - Chi tiết & case study: `references/tiktok-46x-profile-switcher-badge-concatenation-case71.md`.
- **TikTok Profile Header Collision — Story Prompt Bubble & Badge Interference (2026-09-01):**
  - **Triệu chứng:** Script kẹt ở màn hình Profile root, không mở được Switcher (`SWITCHER_ANCHOR_AMBIGUOUS` / `SWITCHER_ANCHOR_NOT_FOUND`) hoặc tap nhầm mở Story camera.
  - **Nguyên nhân 1:** Node huy hiệu thông báo/unread (`"9+"`, `\d+\+?`) nằm cạnh tên hiển thị đứng trước `@username` trong XML khiến `profile_identity_from_xml` gán nhầm `display_name = "9+"`.
  - **Nguyên nhân 2:** Bong bóng Story prompt nổi trên avatar (`"Trà hay cà phê?"`, `"Hôm nay bạn thế nào?"`, `"Thêm suy nghĩ..."`) nằm ở top-center (`y < 260`) thỏa mãn `generic_candidates` trong `find_switcher_anchor`. Khi có cả Story bubble và tên thật $\rightarrow$ count = 2 $\rightarrow$ trả về `None` (fail-closed) hoặc tap nhầm vào bubble.
  - **Xử lý chuẩn:** (1) Dùng regex `^\d+\+?$` lọc bỏ badge số/thông báo khỏi `display_name`, (2) Thêm denylist Story prompt vào `_PROFILE_PHOTO_MARKERS` / `_PROFILE_HEADER_CONTROL_MARKERS` trong `account_switcher.py`. Chi tiết: `references/tiktok-profile-header-story-prompt-and-badge-collision-20260901.md`.
- **Tài khoản mục tiêu đã được chọn trong Switcher (`selected="true"`):**
  - Triệu chứng: Script tap vào tài khoản mong muốn trong bảng modal "Chuyển đổi tài khoản" nhưng modal không đóng, che khuất toàn bộ Bottom Navigation Bar và gây lỗi `navigation target profile not found in XML`.
  - Nguyên nhân: Trên TikTok UI, việc tap lại vào tài khoản đang active (`selected="true"` / `checked="true"`) không kích hoạt reload hay tự đóng bottom sheet.
  - Xử lý chuẩn: Trước khi tap tài khoản trong switcher, kiểm tra thuộc tính `selected`/`checked`. Nếu đã là `true`, gửi phím `BACK` (hoặc tap nút Đóng X) để đóng modal sheet thay vì tap mù vào dòng tài khoản.
- **Popup "Tài khoản của bạn cần được cập nhật" (`account_update_prompt`):**
  - Triệu chứng: Xuất hiện sau khi switch hoặc vào profile, yêu cầu liên kết SĐT/email, che khuất thanh bottom bar gây timeout tìm tab Profile/Home.
  - Xử lý: Được định nghĩa trong `automation_core.tiktok.benign_popup` với hằng số `ACCOUNT_UPDATE_PROMPT_SCREEN = "manual-needed:account-update-prompt"`. Tự động bấm "Để sau" (`dismiss_later_button`) để giải phóng giao diện.
- **Phân biệt Header Switcher Anchor `:id/pke` / `:id/pmf` khỏi Edit Name Subpage Node `:id/pkh` (2026-09-02, updated 2026-09-03):**
  - **Triệu chứng:** Switcher anchor không phân giải được trên các máy farm (như Máy 61), fail-closed với lỗi `manual-needed:account-switcher-not-open: profile switch anchor could not be resolved safely`.
  - **Nguyên nhân:** Khi tạo exclusion denylist loại trừ node bấm mở trang Đổi tên (Edit Name Subpage), `:id/pke` bị thêm nhầm vào danh sách exclusion cùng với `:id/pkh`. Trên nhiều bản build TikTok, `:id/pke` hoặc `:id/pmf` là ID chuẩn của TextView header username (tap vào mở switcher bottom sheet bình thường).
  - **Xử lý chuẩn:**
    1. Trong `automation-core` (`account_switcher.py`): Thêm `"pke"`, `"pmf"` vào `_SWITCH_ANCHOR_RESOURCE_SUFFIXES`, gỡ bỏ `":id/pke"` khỏi danh sách exclusion (chỉ giữ các exclusion thực sự cho edit name/content name: `:id/pkh`, `:id/pau`, `:id/s9b`, `tv_content_name`).
    2. Trong consumer (`feed_swipe_smoke.py`): Gỡ bỏ `":id/pke"` khỏi danh sách exclusion của `_find_sticky_profile_header`.
    3. Giữ nguyên các bộ lọc text (`"thêm tên"`, `"add name"`, `"thêm tiểu sử"`, `"add bio"`) và badge guards để đảm bảo an toàn tuyệt đối.

## Farm Alert Scope Expansion & Lock Retention TTL 90m (2026-08-30)
- **Chuẩn hóa Lock Retention TTL 90 phút (5400s):**
  - Trạng thái `status: blocked` chỉ được giữ tối đa 90 phút (1.5 tiếng) để người vận hành kiểm tra hiện trường trước khi reaper tự động thu hồi, ngăn ngừa việc lock bị ngâm lâu làm nghẽn các ca tiếp theo.
  - Khi PID owner đã chết (`alive=False`) và không thuộc diện `blocked` (ví dụ tiến trình host bị crash / kill bất ngờ), reaper BẮT BUỘC nhả lock ngay lập tức (không ngâm).
- **Mở rộng Farm Alert bao phủ toàn bộ ca nuôi acc:**
  - Tích hợp `send_farm_machine_alert` vào cả 3 giai đoạn của ca nuôi acc: (1) Feed session, (2) Follow hook (`_run_follow_hook`), (3) Upload hook (`_run_upload_hook`).
  - Khi bất kỳ hook nào gặp lỗi hoặc timeout, tự động chụp ảnh màn hình gắn Banner Đỏ gửi về Telegram Farm Alerts và giữ lock hiện trường.
- **Tự động Up Avatar cho Video đầu tiên (Video #1):**
  - Trong `Tiktok-video` (`state_machine.py`), khi tài khoản đăng video #1 (`video_number == 1` — nick chưa có video nào), workflow `ENSURE_AVATAR` tự động kích hoạt up Avatar từ folder video tương ứng lên Profile mà không cần cấu hình allow-list thủ công.

## TikTok Fast Login / One-tap login — canonical module (2026-09-01)

Module mới `automation_core/tiktok/fast_login.py` — dùng chung cho mọi consumer (Reg, Feed, Switcher, Login):
- `is_fast_login_screen(xml)` — detect bằng `FAST_LOGIN_MARKERS` và cấu trúc card One-tap (`_find_fast_login_card_node`).
- `extract_fast_login_handle(xml)` — lấy `@handle` từ node prompt/card One-tap (loại bỏ `@` leading, boundary regex).
- `load_all_valid_excel_identities(paths)` — quét tất cả file xlsx trong `DEFAULT_IDENTITY_WORKBOOK_PATHS`, trả `(set[str], is_complete: bool)`.
- `handle_fast_login_screen(device_id, *, workbook_paths, valid_identities, inventory_loader, get_xml_fn, tap_fn, keyevent_fn, find_text_tap_fn, log_fn, package)` — hàm chính; **adapter pattern**: consumer truyền các hàm riêng, không import trực tiếp consumer module vào core.

**Quy tắc an toàn dữ liệu & Fail-Closed (Bắt buộc):**
1. **Kiểm tra schema & threshold độc lập từng workbook:** Bắt buộc kiểm tra riêng rẽ ngưỡng handle (`MIN_HANDLES_PER_WORKBOOK`) và email (`MIN_EMAILS_PER_WORKBOOK`). Tuyệt đối KHÔNG cộng gộp `len(handles) + len(emails)` để tránh tình trạng workbook thiếu cột ID vẫn bị coi là đủ ngưỡng, dẫn đến việc xóa nhầm nick chính thức.
2. **Card-scoping & Innermost container resolution:** Chọn container nhỏ nhất chứa prompt Fast Login (`min(candidates, key=_node_area)`) thay vì root `FrameLayout`, tránh false-positive trên màn hình độ phân giải thấp khi có mention/comment ngoài card.
3. **Dialog-scoped confirmation với exact token boundary:** Khi xóa tài khoản rác, menu 3 chấm (`Khác` / `More`) và dialog xác nhận xóa (`AlertDialog`/`contentPanel`) phải được xác minh tọa độ bounds cụ thể, và dialog bắt buộc khớp đúng `@username` theo exact token boundary `\b<handle>\b` (tránh xung đột tiền tố như `@ann` với `@anna`).
4. **Dọn sạch overlay khi hủy xóa:** Nếu dialog xóa không khớp handle mục tiêu hoặc không xác minh được nút xác nhận, script phải gửi `keyevent(device_id, 4)` (Back) để hạ modal/menu trước khi trả về `False` (fail-closed), không để modal treo che khuất các luồng phía sau.
5. **ATX Bounded Timeout Budget:** Trong `get_ui_xml`, áp dụng công thức 3 lần dump nhanh ($10\text{s}$) $\rightarrow$ gọi `reset_atx_agent(timeout=12\text{s})` $\rightarrow$ retry 2 lần ($8\text{s}$) với `restart_attempts=0` trong tổng deadline $60\text{s}$, tuyệt đối không fallback shell uiautomator.

**Export:** `automation_core.tiktok.__init__` export đầy đủ các symbol mới (`handle_fast_login_screen`, `is_fast_login_screen`, `extract_fast_login_handle`, `load_all_valid_excel_identities`, `FAST_LOGIN_MARKERS`...).
**Test:** `tests/test_fast_login.py` — 14 tests cover toàn diện detect/handle/junk-delete/valid-preserve/fail-closed/unaccented/dialog-scoped, offline (XML fixtures + mock adapters).
**Sau khi sửa core:** `cp -rf src/automation_core/* "/d/Taadaa/python-envs/automation/Lib/site-packages/automation_core/"`.

## Router Transparent Proxy Mode (`wlan0`) & Global HTTP Proxy Egress IP Probe (2026-08-30, updated 2026-09-03)
- **Chuẩn hóa tham số mặc định `interface="auto"` trong `automation_core.preflight`:**
  - Khi farm chuyển sang cơ chế Router Proxy Wi-Fi (`wlan0`), loại bỏ hoàn toàn việc ép buộc tìm `tun0` (ViChanger) trong các hàm preflight (`AndroidVpnPreflight`, `require_android_vpn`, `run_consumer_after_vpn_preflight`, `run_consumer_after_mapped_vpn_preflight`).
  - Giá trị mặc định là `"auto"`. Khi không có `tun0`, preflight tự động probe `wlan0` kết hợp kiểm tra ping gateway/internet hoặc trích xuất egress IP public IPv4 qua `/data/local/tmp/atx-agent curl http://icanhazip.com`.
  - Giúp các consumer scripts (như `Tiktok-video` tại `RESOLVE_DEVICE`, `tiktok-follow`...) khi gọi `require_android_vpn(adb, required=True)` không truyền interface sẽ tự động vượt qua gate an toàn 100%, không bị fail-closed với mã lỗi `upload_subprocess_nonzero` / `VPN_REQUIRED_NOT_CONNECTED`.
- **Nhận diện Global HTTP Proxy cho `atx-agent curl` probe & stdout/stderr combination:**
  - Trên thiết bị Android thiết lập Wi-Fi HTTP proxy thủ công / global proxy (`settings get global http_proxy` hoặc cặp `global_http_proxy_host` / `global_http_proxy_port`), nhị phân `atx-agent` mặc định không tự động đọc cài đặt global proxy của Android OS.
  - `automation_core.preflight._get_device_global_http_proxy` đọc cấu hình `host:port` từ Android settings; khi có proxy, probe egress IP chạy qua export trực tiếp cả chữ thường và chữ hoa (không bọc `sh -c` vì `adb shell` đã chạy qua Android shell, lồng thêm `sh -c` sẽ làm shell nuốt lệnh/tham số):
    `adb.shell([f"export http_proxy=http://{global_proxy}; export HTTP_PROXY=http://{global_proxy}; /data/local/tmp/atx-agent curl --timeout=3s http://icanhazip.com"])`.
  - Trong test / `FakeAdb`, mock command được phân giải qua `len(args) == 1 and "export http_proxy=" in args[0] and "atx-agent" in args[0]` và assert qua `call[0].startswith("export http_proxy=")`.
  - **Trích xuất IP Egress chính xác (`_extract_atx_curl_ip`):**
    - Helper chuẩn `_extract_atx_curl_ip(stdout, stderr)` xử lý 3 tầng:
      1. Tìm public IPv4 từ `stdout` trước (nếu atx-agent in body kết quả ra stdout).
      2. Nếu không có trong `stdout`, tìm pattern phản hồi Go curl trong stderr: `re.search(r"curl\.go:\d+:\s*(\d{1,3}(?:\.\d{1,3}){3})", stderr)` và kiểm tra `_is_public_ipv4()`.
      3. Nếu không có pattern `curl.go`, lọc bỏ toàn bộ các dòng chứa `dns resolve` / `msg="dns"` trong `stderr` trước khi quét candidate còn lại qua `_is_public_ipv4(cand)`.
      4. Trả về IP hợp lệ hoặc `""` (fail-closed).
  - Nếu không có global proxy hoặc probe qua proxy fail, tự động fallback về direct `atx-agent curl` probe; đảm bảo fail-fast nếu gặp lỗi mất kết nối ADB transport.
- **Pitfall: Permission denied khi sync site-packages do file có thuộc tính Hidden (`+H`) trên Windows**:
  - Khi dùng `shutil.copytree` / `copyfile` ghi đè sang `site-packages/automation_core`, nếu file cũ có cờ Hidden (`attrib +H`), Python sẽ báo `PermissionError: [Errno 13] Permission denied`.
  - Khắc phục: Chạy `attrib -H -R -S /S /D "D:\Taadaa\python-envs\automation\Lib\site-packages\automation_core\*"` trước khi sync.

## Phân Biệt Mất Kết Nối ADB/USB Khỏi Lỗi Mạng Wi-Fi / Proxy Preflight (2026-09-01)
- **Vấn đề vận hành:** Khi thiết bị Android bị rớt cáp USB / offline ADB (`device '...' not found`, `device offline`), các lệnh ADB probe trong `check_android_vpn` (`ip addr show wlan0`, `dumpsys connectivity`) trả về `exit_code != 0`. Trước đây hệ thống ghi nhận nhầm là `wlan0 down` / `Wi-Fi not connected` và báo lỗi `required router proxy is unreachable`, gây hiểu lầm là lỗi mạng/proxy.
- **Giải pháp chuẩn:**
  1. `automation_core.adb.is_connection_lost(stderr)` dùng regex `_ADB_DEVICE_NOT_FOUND_RE` và bộ marker chính xác để nhận diện đúng lỗi transport ADB.
  2. `check_android_vpn` kiểm tra `is_connection_lost` trên toàn bộ các probe (`tun0`, `wlan0`, `dumpsys`, `route`, `ping`, `atx curl`, `GET_IP`) và fail-fast trả về `AndroidVpnPreflight(transport_lost=True, error="device offline or ADB/USB disconnected: ...")`.
  3. `require_android_vpn` và `require_vichanger_connected` kiểm tra cờ `transport_lost`, báo lỗi `device is offline or ADB/USB disconnected for <serial>` và không kích hoạt các luồng Wi-Fi recovery vô ích (`svc wifi enable`).