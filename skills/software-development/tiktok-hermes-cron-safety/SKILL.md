---
name: tiktok-hermes-cron-safety
description: Phase 9A.x → 9C.x production-safety work in the Taadaa Hermes-cron entrypoint inside the EXACT authority worktree — strict TDD (RED first), NO-LIVE (never touch device/host/workbook/credential), AG Opus exact-byte audit, then an exact-allowlist commit gated on APPROVED (no commit before the verdict). Fail-closed seams F1–F5, wrapper templates + deploy/hash (9B.1), declarative job spec (9B.2), timezone preflight (9B.2b), transaction staging create→pause→edit→verify (9B.3), offline manual-run smoke (9B.4), pilot preflight + one-shot activation permit (9C.1).
---

# TikTok Hermes-Cron Production-Safety Remediation (Phase 9A.x → 9B.x)

## Cohort-wide dispatch and reconciliation

For whole-ca machine freezing, late-manifest selection, bounded stagger, and fail-closed `partial`/`timeout` reconciliation, see [`references/cohort-dispatch-reconcile-20260826.md`](references/cohort-dispatch-reconcile-20260826.md). For shift isolation, cron pipe detachment (`DEVNULL` + `DETACHED_PROCESS`), non-destructive ctypes Windows liveness checks, PID reuse prevention with handle hold, and PowerShell parameter path normalization (`.as_posix()`), see [`references/shift-isolation-and-pipe-detachment-20260827.md`](references/shift-isolation-and-pipe-detachment-20260827.md). For proxy cluster downtime triage (`test.taadaa.click`), fail-closed VPN preflight behavior, queue starvation, and the single-source-of-truth `taikhoan_run_safe.xlsx` Device ID date-string normalization, see [`references/proxy-cluster-outage-and-source-of-truth-triage.md`](references/proxy-cluster-outage-and-source-of-truth-triage.md). For cohort target identity validation traps (optional `"tik"` field in feed-only manifests) and clearing stale failed-reservation `status: blocked` device locks that cause fleet starvation, see `tiktok-feed-session/references/cohort-target-validation-optional-tik-field.md`. The reference captures the production `entries[]` + `blocks[]` schema distinction and the direct-script import-path pitfall.

## Triggers

- User asks to "remediate / close / fix the Phase 9A.x production-safety gaps"
- Mentions `live_entrypoint.py`, "live-safe one-shot", "activation permit", "fail-closed",
  or any of the seams F1–F5 in `python_runner/hermes_cron/`.
- 9B.x tasks: tracked wrapper templates + deploy/hash (9B.1: `scripts/hermes_cron/tiktok_*.py`
  + `scripts/deploy_hermes_cron_wrappers.ps1`), declarative job spec + schedule validation
  (9B.2: `scripts/hermes_cron_schedule.json` + `python_runner/hermes_cron/job_spec.py`).
- Keyword combo: "authority worktree", "NO-LIVE", "strict TDD", "no commit", "result artifact".

## Hard constraints (from the task contract)

1. **Exact worktree.** Operate in `D:\Taadaa\context-worktrees\tiktok-luot-nuoi-acc-phase9-authority-<hash>\`
   (the `<hash>` changes per session). Resolve it with `git branch --show-current` / `git rev-parse --show-toplevel`
   before editing. Never edit the dirty origin `D:\Taadaa\tiktok-luot nuoi acc` directly.
2. **NO-LIVE.** The offline suite MUST NOT touch a real device, ADB, TikTok, workbook content, host config,
   or credential. Inject `lock_reader` / `host_validator` / `launcher` stand-ins in tests. The production
   *defaults* in the module inspect the real shared lock / host config / canonical script — that is fine,
   tests never invoke the defaults' external side effects.
3. **No commit until AG Opus exact-byte APPROVED.** Leave the working tree
   uncommitted while implementing/auditing; after the auditor returns the first
   line `APPROVED` for hashes matching the worktree, run the guarded exact-
   allowlist commit helper (no amend, no push). See
   `references/ag-opus-audit-invocation.md` for the invocation + commit checklist.
4. **Strict TDD.** Write the failing (RED) adversarial test BEFORE the production code; confirm it fails for
   the right reason; then implement GREEN; then run the full module suite for regressions.

## The five seams to close (class knowledge)

- **F1 verifier** (`_verify_artifact_observation`): require literal `"ACCEPTED"` (a truthy bool `True` is
  REJECTED), real regular non-symlink evidence files under `artifact_root` (an artifact summary + an
  independent PNG profile screenshot), exact bindings (`permit_id`, `manifest_id`/SHA, `entry_id`,
  `worker_id`, `machine`, `serial`, `row`, evidence SHA256) cross-checked against the permit, and a
  fail-closed freshness window. Reject missing/outside-root/symlink/non-regular/traversal/fake-PNG/
  same-file/hash-mismatch/stale-or-future-timestamp observations.
- **F2 consume-once** (`_consume_once`): atomic `os.open(O_CREAT | O_EXCL | O_WRONLY)` on the marker file
  itself; the marker's existence is the claim (so a crash after the atomic create still consumes and can
  never replay). `os.fsync(fd)` + `fsync(dir_fd)`. Marker written alongside the permit (permit parent chain
  already validated non-symlink).
- **F3 device lock — REMOVED 2026-08-15 (user decision).** `_production_lock_reader`,
  `_LOCK_ACTIVE_BLOCKED`, and the `lock_reader` seam were deleted from `live_entrypoint.py` /
  `hermes_cron_live_entrypoint.py` by direct user order ("xoá hết auto device-lock; lock chỉ khi user
  ra lệnh"; 7000+ lock errors/week logged). Do NOT reintroduce lock reading/acquiring in the live entry
  path. The read-only canonical API (`automation_core.device_lock.device_lock_paths`) still exists and is
  still used by `multi_machine_feed_session._target_lock_aliases` ONLY to verify handoff-evidence aliases
  (that is evidence verification, not auto-lock — keep it).
- **F4 host config** (`_production_host_validator`): validate via `taadaa_host.load_host_config` +
  `assert_machine_in_range` against real `TAADAA_HOST_CONFIG`. Permit may carry only `host_id`, which must
  match the resolved host. Self-asserted `machine_min`/`machine_max`/`lock` are NOT in the permit schema.
- **F5 manifest** (`_select_manifest_entry` + `_validate_permit`): validate via canonical
  `hermes_cron.manifest.load_snapshot` (exact bytes/SHA + entry id preserved/recomputed). A full canonical
  assignment manifest may have many entries; exactly one unique entry is selected by `entry_id`. A fabricated
  one-entry JSON missing required schema is rejected.

## Fail-closed invariants (do not violate)

- Every failure path returns `FAILED` (or `DISABLED` for "already consumed / no permit") after the
  2026-08-15 auto-lock removal — **no more `FAILED_LOCKED` from the live entrypath**; it never
  retries/releases/restarts/recovers. `FAILED_LOCKED` still exists ONLY as a classification/reporting
  enum value consumed from `automation_core` (results/recovery enums, `job_spec.stale_classification`,
  watcher classification sets) — that is an external contract, NOT auto-lock, and must be kept. `DISABLED`
  still means "already consumed / no permit".
- The module never self-approves: the launcher returns an observation that must pass F1 against real evidence.
- The canonical launcher argv is fixed: `powershell -File scripts/run-feed-session.ps1 -Row <r> -Machines <m>
  -AccountWorkbook <wb> -SkipAccountWorkbookSync -AssignmentManifest <m> -WorkerId <w> -ArtifactRoot <a>
  -Python <py> -Run` — no shell, `cwd=repo`. No `ProductionFeedLauncherAdapter` / offline feed adapter.
- Console script must derive the permit only from `permit_file` arg or `HERMES_LIVE_PERMIT_FILE` env — never
  from business argv — and must never print secrets/rows.

## Coordinator exact-byte gate

For implementation followed by independent audit/commit, use
[`references/exact-byte-audit-and-fixture-lessons.md`](references/exact-byte-audit-and-fixture-lessons.md)
(philosophy) and [`references/ag-opus-audit-invocation.md`](references/ag-opus-audit-invocation.md)
(the concrete run-it mechanics + guarded-commit checklist + MSYS path pitfall).
Key rules: wait until the sole writer has stopped; include untracked files in the snapshot; bind every file by
hash and exact bytes; rerun the full gate and rebuild the audit bundle after every edit (including any edit to
a test file to fold in a flakiness fix — recompute hashes and re-audit the enlarged allowlist so committed ==
audited); commit only the exact allowlist whose hashes received `APPROVED`. Never patch the shared worktree
concurrently with a worker. When an uncommitted working-tree change from a PRIOR task turns up during audit
(e.g. a deterministic-clock test fix), fold it into the allowlist and re-audit rather than leave it as WIP.

**EOL trap (`core.autocrlf=true`, hit 2026-08-15 on 9D.1):** this host has `core.autocrlf=true` — the working
copy is CRLF while the blob is LF, and the `patch` tool rewrites an edited file's ENTIRE EOL style to CRLF.
Audit bindings are sha256 of working-copy bytes, so if you LF-normalize AFTER the audit, every hash changes and
the APPROVED verdict is void (cost a full second audit round-trip). Fix: LF-normalize ALL allowlist files
(`data.replace(b'\r\n', b'\n')`) BEFORE building the audit bundle so audited sha256 == working-copy sha256 ==
staged-blob sha256; sanity-check the staged blob with `git show :<path>`. Re-audit whenever ANY byte (including
EOL) changed after a verdict — `git diff` may look identical because git treats CRLF/LF as equal, but the hash
binding does not.

**`git add -A -- <pathspec>` fails with `pathspec '...' did not match any files` when deletions were already
staged** (e.g. a prior `git rm`). Use bare `git add -A` and rely on the exact staged-path check
(`git diff --cached --name-only -z` == allowlist) to prove nothing extra landed.

## Canonical verification commands (run from the worktree)

```
cd '/d/Taadaa/tiktok-luot nuoi acc' && cd '/d/Taadaa/context-worktrees/tiktok-luot-nuoi-acc-phase9-authority-<hash>'
PYTHONTZPATH='D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo' \
PYTHONPYCACHEPREFIX="${TEMP}/pcc_<rand>" \
/d/Taadaa/python-envs/automation/Scripts/python.exe -m pytest \
  python_runner/tests/test_hermes_cron_p1_r2.py python_runner/tests/test_hermes_cron_regressions.py \
  python_runner/tests/test_hermes_cron_contract.py python_runner/tests/test_hermes_cron_blocks.py \
  python_runner/tests/test_hermes_cron_fleet.py python_runner/tests/test_hermes_cron_watcher.py \
  -p no:cacheprovider -q
```
Then `python_runner\hermes_cron\live_entrypoint.py` (and the new script) with `py_compile`, plus
`git diff --check` / `git status` / allowlist+hash+LF+BOM checks. The result artifact goes to
`C:\Users\Kibe\AppData\Local\hermes\cache\terminal\phase9-9aN-fixM-worker-result.json` (see references/result-artifact.md).

### 9B.2b — fail-closed scheduler-timezone preflight (`timezone_preflight.py`)

- **Mirror `hermes_time.now()` exactly** (read `D:\...\hermes-agent\hermes_time.py` first to ground it):
  `HERMES_TIMEZONE` env → config.yaml `timezone` key → `datetime.now().astimezone()`
  OS-local fallback. Invalid configured tz falls back safely, never crashes.
- **Read-only, never mutate.** Raw config read via a line-scan for the `timezone:` key
  (no yaml dependency, no write); OS timezone via read-only `tzutil /g`.
- **Verdict machine-readable:** `raw_config_timezone`, `os_timezone`, `resolved_timezone`,
  `resolved_offset`, `hcm_equivalent`, `observed_at`, `verdict`, `no_config_mutation=true`.
- `hcm_equivalent` == (`utcoffset() == timedelta(hours=7)`); any other offset / unreadable →
  `FINAL_BLOCKED`; **staging/activation permitted ONLY on PASS**.
- Gate functions: `is_activation_allowed(verdict)`, `require_preflight_pass(verdict)` raises
  `TimezonePreflightBlocked`, `stage_job(verdict, stage_fn)` runs the callable ONLY on PASS —
  this is the 9B.3 job-creation gate (no job created without a recorded PASS).
- Real probe confirmed the FACT: raw `""`, OS `SE Asia Standard Time`, resolved `7:00:00`,
  verdict `PASS`. Write evidence to `C:\Users\Kibe\AppData\Local\hermes\cache\terminal\phase9-9b2b-tz-preflight.txt`.
- Commit message: `feat(cron): fail-closed scheduler timezone preflight`.

### 9B.3 — transaction staging create → pause → edit → verify (`staging.py` + `hermes_cron_stage_jobs.ps1`)

- **Contract grounded in installed CLI help** (re-probe with `hermes cron create --help` etc. — never
  assume): `create <schedule> [prompt] --name --deliver --repeat --skill --script --no-agent --workdir`,
  NO `--paused` flag exists (create is enabled by default); `pause <id>`; `edit <id> --schedule <five-field>`;
  **`update` subcommand does NOT exist** — the only negative guard. Human `hermes cron list --all` format:
  `  <hexid> [active|paused]` header + `    Name:/Schedule:/Repeat:/Next run:/Deliver:/Script:/Mode:` lines
  (parsed conservatively, never `--json`).
- **Engine `run_transaction(spec, *, run_cli, list_jobs, human_list, journal_path, preflight_verdict, ...)`**
  with ALL side effects injected (fakes in tests → NO-LIVE). Steps: preflight PASS gate → journal
  (`CREATE_PENDING`) → before-snapshot → create → parse `Created job: <id>` (lost stdout → reconcile via
  owned name `phase9-staging-<txn_id>`) → human/canonical id-drift check → unique-new-ID check →
  `_job_matches_create` → pause → `_assert_paused` → edit (paused-only) → `_assert_edited_paused`
  (next_run_at must stay byte-equal, never re-armed) → journal `DONE`.
- **Rollback** removes ONLY ownership-proven IDs (not in before-snapshot AND name starts with the prefix),
  preserves every unrelated record (verify all before-ids still present), writes journal `ROLLED_BACK`.
  Zero or >1 reconciliation candidates → `FINAL_BLOCKED`, never blind retry/create.
- **Fail-closed seams:** `reject_update(argv)` raises `CronUpdateForbidden` if `"update"` appears;
  deployed wrapper SHA-256 + workdir verified BEFORE create (mismatch → no CLI call at all); create
  schedule = one-shot ISO timestamp, repeat=1, horizon 24h..7d from `create_started_at`.
- **PS1 wrapper** (`scripts/hermes_cron_stage_jobs.ps1`) runs the preflight itself, then passes its own
  verdict via `$env:HERMES_CRON_STAGING_PREFLIGHT` (a hardcoded/unset env passed to the Python engine is a
  dead-path defect — the audit caught it; always set the env from the script's own computed value). Verify
  PS1 with the PowerShell parser, NEVER py_compile.
- **Test fakes:** stateful `FakeJobStore` (jobs dict + cli() command vector recorder); job ids MUST be
  hex (`0001abcd`), because the human-list regex only accepts `[0-9a-fA-F]{4,}` — a fake id like `j0001`
  parses to `[]` and fails the drift check. `human_list` must mirror the real `list --all` layout.
- Commit message: `feat(cron): thêm transaction staging paused và rollback`.

### 9B.4 — offline manual wrapper smoke (`manual_run.py`)

- **Explicit kill-switch required** (`HERMES_CRON_OFFLINE_SMOKE=1` env); missing → `KillSwitchMissing`,
  no run. NEVER `hermes cron run`/`resume`, never live entrypoint (`live_entrypoint.py`,
  `hermes_cron_live_entrypoint.py`, `tiktok_runner.py`), never workbook/repo-exec/device/credential flags.
- **Smoke invokes the deployed wrapper DIRECTLY** as `[target_python, wrapper_path, *wrapper_args]`
  (target python explicit, no shell, cwd = repo root). Successful run → EMPTY stdout (nonzero alerts).
- **Paused-state invariant:** canonical before/after snapshot must be field-equivalent for owned IDs
  (sort by id); drift raises.
- Commit message: `test(cron): khóa manual run ở paused offline mode`.

### 9C.1 — pilot preflight & one-shot activation permit (`pilot.py`)

- **Row selector is production-owned** in `pilot.py` (`PILOT_ROWS = frozenset(range(1,7))`); rows 0/7..9
  rejected (`PilotRowOutOfRange`) by `build_activation_permit`, `preflight`, AND `validate_activation_permit`.
  Machines outside 1..80 → `PilotMachineOutOfRange`. 9A.5 parser may accept overflow rows; pilot.py is the
  gate that must NOT activate them (independent RED node `test_pilot_selector_rejects_rows_7_to_9`).
- **Safe projection:** `safe_projection(mapping)` raises `PilotCredentialReadForbidden` on any key
  containing secret/token/password/credential/cookie/session; `preflight(..., safe_projection_fn=...)` is
  injectable so tests prove nothing credential-specific is read.
- **Extending the live permit schema is a mirror-loader job, never a canonical-loader edit:**
  `live_entrypoint._load_permit` / `canonical_permit` are STRICT — `allowed_keys =
  {"schema_version", *_REQUIRED_PERMIT_KEYS}` and `raw != canonical_permit(permit)` rejects every extra key.
  A pilot permit adds `logical_day`/`expiry`/`nonce`/`consumed` → WRITE via `models.canonical_json` (loose
  serializer, NOT `canonical_permit`), and READ via a mirror loader `_load_pilot_permit` that keeps ALL
  canonical safety checks (absolute, regular, non-symlink, `_assert_no_symlink_parents`, forbidden keys,
  manifest regular non-symlink, schema_version) but widens `allowed`. Do not weaken the canonical loader.
- **Consume marker name:** `_consume_marker_path(permit_path)` = `permit_path.with_suffix(".consumed.json")`
  → `permit.consumed.json`, NOT `permit.json.consumed.json`. Tests asserting marker existence must use the
  real name. `_consume_once` does NOT mutate the permit dict — consume-once is proven by the 2nd call
  returning False (marker claim), NOT by re-validating the dict (it still passes after consume).
- **Sibling-function kwarg mismatch trap:** `build_activation_permit` takes `manifest=` + `now_fn=`;
  `preflight` takes `manifest_path=` and NO `now_fn`. A shared `_pilot_kwargs()` test helper feeding both
  must adapt before the preflight call: `kw["manifest_path"] = kw.pop("manifest"); kw.pop("now_fn", None)`
  — else `TypeError: got an unexpected keyword argument`.
- **Consume tests need a real manifest file:** `_load_pilot_permit` fail-closes on `manifest` not a regular
  file, so consume tests must create a real temp manifest (`tmp_path / "manifest.json"`), not a fake
  `D:\repo\manifest.json` path.
- Atomic write = temp file + `os.replace`; expiry = now + `PERMIT_EXPIRY_MINUTES` (10), validated with
  injectable `now`; `validate_activation_permit` fail-closes on consumed/expired/unknown-key/forbidden-key.
- Commit message: `feat(cron): thêm pilot preflight và activation permit một lần`.
- 9C.2 (single live entry) is a SEPARATE HUMAN-GATED task — permit code is offline-only; never run a live
  entry from the preflight/permit path without explicit user row+machine approval.

- **Watcher notification delivery (`deliver: origin` / `deliver: <target>`):**
  The watcher cron job (`phase9-watcher-tiktok-feed`) runs on scheduled offsets (e.g. `7,22,37,52 * * * *`) with `deliver: origin` and `no_agent: true`.
  Under Hermes `no_agent` semantics:
  1. Empty stdout from `tiktok_watcher.py` is **SILENT** — nothing is sent to Telegram/chat, preventing spam when machines operate normally.
  2. When failures or anomalies occur, `tiktok_watcher.py` prints the sanitized summary/alert to stdout, which Hermes immediately forwards to the origin chat/group.
  3. `tiktok_runner.py` remains `deliver: local` because its executions spawn detached live feed sessions asynchronously without polluting chat output.

### Shift Isolation in Cron Runners & Detached Spawn Requirements

1. **Shift Isolation (Ca mới tự ngắt ca cũ):**
   - A stuck or hung batch from a previous shift (e.g. Ca 2 row 3) must NEVER block a subsequent shift (e.g. Ca 3 row 1).
   - In `tiktok_runner.py`, when `_spawn_live` encounters a new cohort ID or an expired/stale lease (>90m), it must actively terminate the stale PIDs (`taskkill /F /T /PID <pid>`), unlink the old lease, and proceed with dispatching the new cohort immediately.
2. **True Detached Process Spawning on Windows (`CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` + `DEVNULL`):**
   - When spawning background PowerShell workers (`run-feed-session.ps1`) from a cron wrapper:
     `proc = subprocess.Popen(argv, cwd=str(repo), env=child_env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, creationflags=0x08000200)`
   - **CẠM BẪY NGHIÊM TRỌNG:** Tuyệt đối CẤM dùng `DETACHED_PROCESS = 0x00000008` (hay `0x00000208`) khi gọi `powershell.exe`. PowerShell 5.1 yêu cầu console subsystem hợp lệ, khi nhận `DETACHED_PROCESS` nó sẽ lập tức thoát (exit 0/crash) mà không thực thi script con. BẮT BUỘC dùng `0x08000200` (`CREATE_NO_WINDOW = 0x08000000` kết hợp `CREATE_NEW_PROCESS_GROUP = 0x00000200`) để vừa ẩn cửa sổ vừa chạy độc lập.
   - Leaving standard streams unredirected keeps the parent pipe open in Hermes Gateway, causing `_running_job_ids` in Hermes Cron Scheduler to stay locked with `Job '...' already running — skipping` for hours.
3. **PowerShell `IsPathRooted` Path Traps & Posix Slash Normalization:**
   - Always normalize path arguments to forward slashes (`Path(...).as_posix()`, `value.replace('\\', '/')`) before passing `-File`, `-AccountWorkbook`, `-ArtifactRoot`, `-Python`, etc. to PowerShell launcher scripts. Backslashes cause `\r`, `\t`, `\n` escape corruption resulting in `Illegal characters in path` errors.
4. **Farm Operation Invariant: "Lỡ ca không bù" (Late-night No-Catchup):**
   - If an evening shift is missed or delayed into late night (e.g. >23:00), DO NOT run catch-up feed sessions.
   - Late night swiping produces unnatural behavior flags on TikTok and clashes with the 01:00 AM night registration pipeline (`night-chain-reg-pipeline`) and 04:00 AM cache cleanup (`end-of-day-clear-tiktok-cache`). Missed sessions are dropped cleanly.

### Windows `os.kill(pid, 0)` dead-PID pitfall (Python on Windows / WinError 87)

In Python on Windows (e.g. Python 3.12), calling `os.kill(pid, 0)` on a dead or invalid PID can raise
`SystemError: <class 'OSError'> returned a result with an exception set` (wrapping `OSError: [WinError 87] The parameter is incorrect`)
rather than catching cleanly as a normal `ProcessLookupError` or `OSError`.
When implementing or maintaining live process lease checks in runner scripts (e.g. `_lease_alive` in `tiktok_runner.py`),
always catch `(OSError, SystemError)` or probe process aliveness via `ctypes.windll.kernel32.OpenProcess` with `GetExitCodeProcess`
to prevent unhandled crashes during cron runner ticks.

### Windows Exit Code 3221226091 (0xC000026B / STATUS_DLL_INIT_FAILED_LOGOFF)

When Hermes Gateway restarts while a `no_agent` cron script (`tiktok_watcher.py`, `tiktok_runner.py`) is executing,
Windows aborts the child process station with exit code `3221226091` (`0xC000026B`).
This is an OS-level termination caused by Gateway process recycling, not a Python syntax/logic error.
Probing the script directly verifies it exits 0 when Gateway is stable.

### Gateway reset, stale scheduler state, and silent HANDOFF output

After a Gateway restart or machine reset, distinguish scheduler health from actual farm liveness. `enabled`, `scheduled`, `last_status: ok`, and empty no-agent output prove only that a wrapper tick returned; they do not prove a feed launcher or child session started. Follow the verification sequence and output contract in [`references/gateway-reset-stale-state-and-silent-handoff.md`](references/gateway-reset-stale-state-and-silent-handoff.md). In particular, verify every lease PID and a fresh live artifact before claiming dispatch. Do not restart Gateway or touch unrelated locks/processes as a shortcut.

**Mandatory evidence precedence when answering “phiên nào / đã hoàn tất chưa / phiên tiếp theo là gì”:**
1. Read the newest actual Hermes cron output delivered by the watchdog/runner and bind it to `Run Time`, logical day, ca, and `Phiên N/3`. A watchdog report such as `Ca 1 - Phiên 2/3 ... hoàn tất` is direct completion evidence and overrides stale/planned metadata.
2. Check the corresponding runner/watcher job record and recent `agent.log` only to corroborate the tick/result; `last_status=ok` alone is not completion proof.
3. Only then read the assignment manifest to identify the next *planned slot*. A manifest entry with `status=planned`, `slot_time`, or `next_run_at` is schedule metadata, not evidence that an earlier slot did not run.
4. Separate these terms in the answer: **cron tick** (job invocation time), **slot/khung giờ** (manifest window), and **phiên** (session index/ca). Never answer “chưa chạy” from `next_run_at` or a planned manifest entry when a newer watchdog output says the session completed.
5. If the watchdog summary has an arithmetic/count inconsistency (for example `73/72` while `69 success + 4 fail = 73`), report the session as completed based on the explicit completion line, and separately flag the summary-count bug. Do not downgrade completion to “not run”.
6. If no fresh watchdog/runner output exists, say `chưa xác minh` and then use manifest/lease/process evidence with the source and timestamp stated explicitly.

For a user asking “phiên tiếp theo”, after confirming the latest completed session from cron output, select the next session index/ca chronologically from the manifest and report its actual first slot time/window. Do not report the watchdog tick or runner job’s next invocation as the session itself.

**User-correction hardening (2026-08-27):** If the user provides a screenshot, Telegram reply, or direct cron-output artifact showing `Ca X - Phiên Y/3 ... hoàn tất`, treat that as primary live evidence. Read the corresponding saved output file and its `Run Time` before consulting manifests. Never answer “chưa chạy/chưa gọi” solely because an older manifest still says `planned` or because the scheduler's `next_run_at` points at a later tick. If the report's denominator is inconsistent, calculate only as a separate report-quality issue; do not override the explicit completion state. When a prior answer was wrong, acknowledge it plainly in the first sentence, state the corrected evidence, and avoid making the user re-prove the same fact.

**Bridge-contract gate before live retry:** compare the runner's PowerShell argv with the PS1 `param(...)` block and the `run_tiktok.py` parser. Every argument emitted by the runner must be declared and forwarded. A runner passing `-CohortArtifact` to a PS1 that lacks that parameter fails immediately with `ParameterNotFound` before Python/ADB starts. Also resolve `ACTIVE.json` pointers to the referenced full assignment manifest before passing `-AssignmentManifest`; passing the pointer itself reaches assignment preflight with the wrong schema and aborts. Reproduce safely by running the exact launcher command **without `-Run`**, capture stdout/stderr, then add `-Run` only after preflight passes.

**Recovery reporting discipline:** after a repair, report separately: scheduler tick, lease/PID, child command line, fresh artifact creation, and machine progress. A new lease alone is not dispatch proof; a live parent alone is not machine-progress proof. If a detached child exits before artifacts, stop blind retries, foreground the same bridge command without `-Run`, fix the first concrete error, and re-verify.

### Gateway reset, stale scheduler state, and silent HANDOFF output

After a Gateway restart or machine reset, distinguish scheduler health from actual farm liveness. `enabled`, `scheduled`, `last_status: ok`, and empty no-agent output prove only that a wrapper tick returned; they do not prove a feed launcher or child session started. Follow the verification sequence and output contract in [`references/gateway-reset-cron-recovery.md`](references/gateway-reset-cron-recovery.md). In particular, verify every lease PID and a fresh live artifact before claiming dispatch. Do not restart Gateway or touch unrelated locks/processes as a shortcut.

**Bridge-contract gate before live retry:** compare the runner's PowerShell argv with the PS1 `param(...)` block and the `run_tiktok.py` parser. Every argument emitted by the runner must be declared and forwarded. A runner passing `-CohortArtifact` to a PS1 that lacks that parameter fails immediately with `ParameterNotFound` before Python/ADB starts. Also resolve `ACTIVE.json` pointers to the referenced full assignment manifest before passing `-AssignmentManifest`; passing the pointer itself reaches assignment preflight with the wrong schema and aborts. Reproduce safely by running the exact launcher command **without `-Run`**, capture stdout/stderr, then add `-Run` only after preflight passes.

**Recovery reporting discipline:** after a repair, report separately: scheduler tick, lease/PID, child command line, fresh artifact creation, and machine progress. A new lease alone is not dispatch proof; a live parent alone is not machine-progress proof. If a detached child exits before artifacts, stop blind retries, foreground the same bridge command without `-Run`, fix the first concrete error, and re-verify.

### Deployed scripts sync (`%LOCALAPPDATA%\hermes\scripts\`) & Cron Pause Triage

1. **Sync Repo Scripts to Deployed Scripts**:
   Hermes cron jobs call wrapper scripts located at `%LOCALAPPDATA%\hermes\scripts\` (`C:\Users\Kibe\AppData\Local\hermes\scripts\`).
   When editing `scripts/hermes_cron/tiktok_runner.py`, `scripts/hermes_cron/tiktok_watcher.py`, or `tiktok_picker.py` in the repository,
   ALWAYS sync them to `%LOCALAPPDATA%\hermes\scripts\` (`cp scripts/hermes_cron/tiktok_*.py /c/Users/Kibe/AppData/Local/hermes/scripts/`)
   so that cron runs the latest production code instead of stale wrappers.

2. **Triage Cron Not Running / Idle Farm**:
   When scheduled farm runs do not trigger or appear stopped:
   - Run `cronjob(action='list')` to check if jobs (`phase9-runner-tiktok-feed`, `phase9-watcher-tiktok-feed`, `taikhoan-run-safe-sync`, `reap-dead-owner-locks`, `tiktok-feed-session-watchdog`) are in `state: paused`.
   - Resume paused jobs using `cronjob(action='resume', job_id='<id>')`.
   - Inspect active leases under `D:\Taadaa\runtime\<host>\cron-state\runner-live-lease\<day>.json` and process list (`tasklist /FI "IMAGENAME eq powershell.exe"`, `tasklist /FI "IMAGENAME eq python.exe"`).
   - If stalled, trigger an immediate test tick via `cronjob(action='run', job_id='<runner_job_id>')`.

3. **Feed Session Mock Isolation with Active Action Hooks**:
   When downstream hooks (such as `_maybe_follow_video`) are active in `_feed_session_flow`, unit/integration tests running mock `DeviceContext` must explicitly patch `_maybe_follow_video` (or provide appropriate ATX session mocks) to prevent `UIDumpError: ATX_SESSION_UNAVAILABLE` during test execution.

### Hung Watcher / Runner Timeout Recovery & Daily Manifest Catch-Up

When the feed cron appears stalled with no Telegram alerts and `already running — skipping` in `agent.log`:
1. **Check hung background processes:** Search for orphaned `hermes_cron_watcher.py` or runner processes (`psutil` / `ps -ef`). A 3600s runner script timeout can leave child watcher processes alive, causing Hermes cron to skip subsequent ticks indefinitely.
2. **Kill orphaned processes:** Terminate the hung watcher/runner PIDs.
3. **Clean stale runner lease:** Remove stale previous-day lease files in `D:/Taadaa/runtime/kibe/cron-state/runner-live-lease/<prev_day>.json`.
4. **Check / Generate today's manifest:** Verify `D:/Taadaa/runtime/kibe/cron-state/manifests/<today>/` has an active assignment manifest. If absent (e.g. 06:00 picker was blocked by the hung lease), invoke `python "C:/Users/Kibe/AppData/Local/hermes/scripts/tiktok_picker.py"` to create today's manifest.
5. **Kickstart cron:** Run `cronjob(action='run', job_id='<runner_id>')` and `cronjob(action='run', job_id='<watcher_id>')` to re-arm the scheduled pipeline. Verify live feed session workers start under `D:/Taadaa/runtime/kibe/live/<today>/`.

### Error Scene Lock Policy & SurfaceFlinger Protected Screen Fallback

1. **Mandatory Hard Lock on Error (TTL 2 Hours):**
   - When a device encounters an error, stops mid-feed, or enters `manual-needed` / `fail`, it MUST be locked with `status: "blocked"` and `ttl: 7200` (2 hours) at `~/.codex/device-locks/machine_<n>.lock.json` to hold the exact on-screen evidence.
   - If the operator does not intervene within 2 hours (7200s), the lock reaper (`reap-dead-owner-locks`) is permitted to auto-reap the lock.
2. **Alert without Screenshot Fallback (SurfaceFlinger `PERMISSION_DENIED`):**
   - When an app window or overlay sets `FLAG_SECURE` or hardware DRM surface / scrcpy virtual display is active on Samsung S7 / Android 8.0, `adb exec-out screencap -p` returns 12 null bytes (`FB is protected: PERMISSION_DENIED`).
   - Fix: `_capture_device_screencap` in `automation_core.alerts` implements a multi-layer fallback. Layer 2 proxies to **ATX-Agent / UiAutomator2 JSON-RPC (port 7912 / 9008)** calling `takeScreenshot(1.0, 90)` directly from Android UI graphic buffers.
   - See detailed recipe: [`references/surfaceflinger-fb-protected-screencap-fallback.md`](references/surfaceflinger-fb-protected-screencap-fallback.md).


### Live triage: scheduled ticks skipped by a hung runner lease

When the Hermes cron job is `enabled` and `agent.log` shows repeated `already running — skipping`, do not conclude that cron is disabled or that no tick occurred. Distinguish the layers with fresh evidence.

**Critical distinction:** `already running — skipping` is emitted by Hermes' job-level scheduler guard (`_running_job_ids` / active invocation), not by a device lock and not by `runner-live-lease`. A stale `runner-live-lease` can block `_spawn_live` only after the wrapper has actually started; it cannot by itself explain Hermes skipping the job unless the prior wrapper invocation is still alive or hung. Prove these independently before assigning root cause:

1. **Hermes scheduler invocation:** inspect the job record (`last_run_at`, `last_status`, `next_run_at`), cron output timestamp, and `agent.log` for the exact skip line. Repeated `already running` means the scheduler still has a prior invocation registered.
2. **Runner liveness:** inspect the exact `tiktok_runner.py` / `run-feed-session.ps1` PID tree and CPU time. A live launcher with no child progress may be hung; a missing recorded PID means the scheduler invocation/claim is stale. Do not trust `execution_success` or empty stdout as proof of machine launches.
3. **Runner lease/artifacts:** read `runner-live-lease/<logical-day>.json`, compare every recorded PID/expiry with the process tree, and inspect per-device artifacts for terminal summaries.
4. **Device locks:** inspect `~/.codex/device-locks/` separately; never conflate device lock state with Hermes job state.

For a user request to fix the issue, do not stop at diagnosis: after ownership is classified, repair only the stale scheduler/lease state or the narrowly implicated code path, then run a fresh tick and verify a new artifact/process. If repository bootstrap is blocked by a dirty tree, preserve unrelated edits but inspect/classify dirty paths read-only and report the exact blocker; do not claim the cron fix is complete without fresh verification.

Safe recovery sequence, only after the user authorizes recovery: stop only the exact stuck feed launcher PID (not proxy watchers, Gateway, or unrelated PowerShell), verify its children are gone, remove only the matching stale runner lease/claim, manually kick runner and watcher, then verify a new artifact directory and the actual child command line. The child command must show the intended `--max-workers` value. If the scheduler's in-memory guard remains after the lease is cleared, a controlled Gateway scheduler restart may be required; do not perform it implicitly.

If a foreground elevated PowerShell window is unrelated to the runner, attribute it from the exact command line before acting. A `netsh advfirewall firewall add rule` command with an unquoted rule name containing spaces produces the `A specified value is not valid` help screen; a trailing `pause` leaves `Press Enter to continue`. Verify the intended rule by name/port, and if the elevated process is access-denied from the current shell, ask the operator to press `Ctrl+C` or close that exact window rather than killing broad PowerShell processes.

The scheduler-vs-runner evidence pattern is maintained in [`references/scheduler-vs-runner-stale-state.md`](references/scheduler-vs-runner-stale-state.md).
For triaging coordinator `ThreadPoolExecutor` shutdown hangs that lock the runner lease and trigger `Report Lock Device` overdue alerts, see [`references/coordinator-threadpool-hang-and-stale-lease-triage.md`](references/coordinator-threadpool-hang-and-stale-lease-triage.md).

### Per-device feed timeout is separate from the outer cron timeout

A batch runner can remain alive while one target is stuck inside an inner ADB/UI poll loop. A `ThreadPoolExecutor` worker has no deadline merely because the parent cron script has one, and `future.result()` can wait forever. When triaging `already running — skipping`, inspect each machine artifact/process separately: a target with `summary.txt` and terminal `success`/`failed` is closed; a target with repeated poll/wait records, no summary, and a live child is not.

The fix contract is per-target monotonic deadline (default 900 seconds), a deadline check at every inner poll/sleep boundary, terminal per-device summary + manifest in `finally`, policy-gated TikTok force-stop/HOME cleanup, and handoff/lock evidence before non-success lock transition. A timed-out target must not cancel sibling workers. The regression recipe is maintained in `tiktok-feed-session/references/per-device-timeout-finalization.md`.

### Cross-project device-lock blocking (gan-proxy / tiktok-log-in vs feed session)

- **Cron Scheduler vs Device Lock Semantics:**
  Hermes Cron scheduler operates strictly on clock schedule (e.g. `*/15 * * * *`) and does NOT check device lock files (`~/.codex/device-locks/machine_<n>.lock.json`) before triggering runner ticks.
  Checking, filtering, or skipping locked devices is the responsibility of the consumer/runner script.
  When auto device-lock was removed from the live entrypoint (Phase 9D.1), runner dispatches to manifest targets unless an explicit lock preflight / selection filter skips locked machines.

- **Collision symptom:** When user locks a machine (e.g. `tiktok-log-in`, manual maintenance) during scheduled feed hours, the cron runner may still trigger batch execution for that machine if the preflight doesn't halt early, resulting in errors like `account-switcher-missing-expected` (when an expected account is not yet logged in).

- **Dead-owner lock reaper vs `status: blocked` locks (Premature lock reaping race):**
  When an automation or login tool transitions a device lock to `status: "blocked"` and its process exits:
  1. *The Trap:* A periodic dead-owner reaper (`reap-dead-owner-locks.py`) checking only `owner_process_alive()` will treat dead PIDs on `status: "blocked"` locks as abandoned locks and move them to `device-locks-reaped/`.
  2. *The Consequence:* Once the lock file is quarantined, the scheduled cron runner (`tiktok_runner.py`) sees the machine as free/unlocked and spawns a feed session on it, overriding the operator's manual lock / login operation.
  3. *Invariable Rule:* Dead-owner reapers MUST preserve `status: "blocked"` locks until their 2-hour TTL (7200s) has expired. Only `status: "running"` locks with dead PIDs or expired `blocked` locks may be reaped.
  4. *Runner-level Guard:* `tiktok_runner.py` must proactively scan `~/.codex/device-locks/` via `_get_active_locked_machines()` and exclude locked machines before constructing `-Machines` for `run-feed-session.ps1`.

When `gan-proxy` (`gan_proxy_fleet.py`) holds an active or retained device lock in `~/.codex/device-locks/machine_<n>.lock.json`,
the canonical `run-feed-session.ps1` correctly flags the machine as `needs-user-decision` (`script-blocker`) and skips execution
to avoid collision. When triaging why a scheduled row did not run on a machine, check:
1. `D:\Taadaa\runtime\kibe\live\<day>\row-<r>-<time>\...\summary.txt` for `needs-user-decision` / lock owner.
2. `~/.codex/device-locks/machine_<n>.lock.json` to verify PID and owning project (`gan-proxy`, `tiktok-log-in`, etc.).
3. Remember rule: NEVER auto-delete or touch `gan-proxy` device lock files without user authorization.

## Session-vs-tick reporting (cập nhật 2026-08-27)

- Khi người dùng hỏi “cron tiếp theo gọi là phiên nào”, phải phân biệt hai lớp: **phiên farm trong full assignment manifest** và **tick của Hermes scheduler**. Không trả lời mỗi `next_run_at`.
- Cách xác định: đọc manifest của logical day; bỏ qua `ACTIVE.json`, `ACTIVE.lock` và file control không parse được; lọc `slot_time >= now` theo HCM; lấy slot sớm nhất và nhóm entry cùng slot. Báo `session_index`, `account_row`, `slot_time–slot_end`, số/list máy.
- Sau đó mới nêu tick runner có khả năng dispatch. Hai mốc có thể lệch (ví dụ phiên bắt đầu 08:05 nhưng runner tick là 08:15). Nếu có `already running — skipping`, nói rõ phiên chỉ mới planned/due, **chưa xác minh dispatch/chạy thật**.
- Báo cáo phải ngắn, trực tiếp, không dump cả manifest; không gọi job `enabled=true` là bằng chứng phiên đã chạy.

## Recovery evidence and session-hook guard (2026-08-26)

When a user asks whether a farm session has started after a Gateway reset, answer from fresh evidence, not scheduler metadata. Report separately: scheduler tick, lease/PID, child command line, fresh run artifact, and machine-level terminal progress. `last_status=ok`, `enabled/scheduled`, a lease, or a live parent process alone are insufficient. Do not claim a session is complete until the run manifest and per-machine publications are terminal; distinguish machine counts from follow-action counts.

For a detached child that exits early, stop blind retries and reproduce the exact bridge in safe preflight mode without `-Run`. Compare runner-emitted PowerShell parameters against the PS1 `param(...)` block and Python CLI parser, resolve `ACTIVE.json` to the full assignment manifest, and verify the target automation interpreter with `run_tiktok.py --help` while removing inherited `PYTHONPATH`. After any live retry, verify a new artifact and child process before reporting success.

Session hooks must bind to canonical cohort identity. `_session_index` must be populated from the frozen cohort/assignment before hook dispatch; missing or invalid identity must fail closed, never default to a live-eligible final session. Upload is production-eligible only for `session_index == 3`. `force_upload_hook` and recovery-test flags may support isolated offline tests but must not bypass this live invariant. Add a regression asserting session 2 writes a skip result and does not invoke the upload subprocess.

If bootstrap reports `DIRTY-ALLOWLIST-CONFLICT`, preserve the existing dirty work and report the exact conflict; do not overwrite, reset, or claim the fix is complete. Keep user-facing reports concise in Vietnamese, explicitly separating mục đích, kết quả, blocker, and what is or is not verified.

Session-specific evidence and the 2026-08-26 incident mapping are in [`references/gateway-reset-session-recovery-20260826.md`](references/gateway-reset-session-recovery-20260826.md).

## Session identity, upload gating, and dirty-scope handling

- **Classify a run by canonical identity, not by directory clock/name.** Before interpreting upload artifacts, read the child `run_manifest.json` and bind `cohort_id`, `assignment_id`, `block_index`, `session_index`, `entry_id`, and `worker_id`. A run started later than its nominal slot can still be the intended session; wall-clock folder names alone are not evidence.
- **Final-session upload gate is exact and fail-closed:** upload may be invoked only when canonical `session_index == 3`. Sessions 1 and 2 must not invoke the upload hook or reserve upload timeout budget. Missing/invalid session identity must not default to session 3. `force_upload_hook` and recovery flags are not live bypasses; they may be used only in isolated offline tests that assert the gate.
- **When a report appears to show upload in session 2, verify identity first.** Inspect the actual child manifest and upload result; do not infer from the runner start time. If the manifest says session 3, the upload is expected and the earlier classification was wrong.
- **Dirty-tree bootstrap must distinguish path overlap from hunk overlap.** A dirty file in the allowlist is not automatically a conflict. Keep unrelated prior edits, read the diff, patch with unique context, and block only on proven same-line/hunk overlap or when safe separation is impossible. A filename-only gate is too broad and must be corrected in both shell and PowerShell bootstrap implementations.
- **Live recovery reporting remains evidence-first and concise:** separate scheduler tick, lease/PID, child command, fresh artifact, machine terminal counts, and blockers. State explicitly what is verified and do not call a run successful from `last_status=ok`, a lease, a live parent, or a folder count alone.

Session-specific notes and reproduction evidence are maintained in [`references/gateway-reset-session-recovery-20260826.md`](references/gateway-reset-session-recovery-20260826.md).

## User-corrected cron/session evidence protocol (2026-08-27)

When answering whether a farm session ran, completed, or what session comes next, use this order:

1. **Primary evidence:** newest Telegram screenshot or saved Hermes watchdog/runner output. If it explicitly says `Ca X - Phiên Y/3 ... hoàn tất`, treat that as completion proof. Bind it to the report timestamp, logical day, ca, session index, and success/fail machine list.
2. **Corroboration:** inspect the corresponding cron output file, job record, and `agent.log` for the invocation/tick. `enabled`, `scheduled`, `last_status=ok`, `next_run_at`, a lease, or a live parent are not completion proof by themselves.
3. **Planning only:** use the full assignment manifest after the latest completion is established to select the next chronological farm session. `planned`, `slot_time`, and `next_run_at` are schedule metadata; they must never override fresher completion output.
4. **Terminology:** report separately: Hermes cron tick, farm slot/window, and farm session `Phiên N/3`. A runner tick at 08:15 is not automatically the farm session beginning at 08:05.
5. **Inconsistent arithmetic:** if the explicit completion line exists but the denominator is wrong, preserve the completion conclusion and flag the count/report-quality defect separately. Do not downgrade it to “not run”.
6. **Missing direct output:** say `chưa xác minh`, name the source and timestamp, and state the evidence limit. Do not manufacture a conclusion from planned metadata.
7. **User-provided artifact wins:** a screenshot or direct cron-output artifact from the user is primary live evidence. Read the corresponding saved output if available before consulting manifests. If the previous answer was wrong, acknowledge it plainly in the first sentence and give corrected evidence immediately.

**Anti-regression check before replying:** ask “Am I using a fresh completion artifact, or only a future/planned scheduler record?” If only the latter, do not claim the session has not run.

## Workbook sync lock debugging: recovery-before-outer-lock invariant (2026-08-27)

For a transaction that acquires locks for several workbooks and then recovers a persistent journal:

- Reproduce with a **no-publish probe** that acquires/releases each canonical workbook lock individually; do not run the real sync concurrently with cron.
- Inspect journal PID and snapshot paths. Verify the PID independently and exclude the probe’s own process, shell wrappers, and command-line text from process matching.
- Distinguish another live owner, a stale journal/snapshot, and an in-process self-deadlock. A lock file may be absent while an in-process `RLock` is held; a stale journal is not itself a current lock owner.
- If the outer function already holds workbook locks, recovery that calls `atomic_workbook_update()` on the same workbooks can self-timeout because the JSON lock-file protocol is not owner-reentrant even when the thread lock is an `RLock`. Recover **before** acquiring the outer lock set, or add an explicit same-owner lease path with regression coverage; never delete the journal or bypass the lock blindly.
- When two sync invocations appear, inspect parent/child PID trees and creation times. Stop only an invocation proven to be the agent’s own reproduction; preserve the scheduled owner until classified. Never kill Gateway or broad Python/PowerShell processes as a shortcut.
- After a fix, verify in layers: focused regression test (RED then GREEN), `py_compile`, no active sync processes, canonical lock directory clean, journal state intentional, then one official wrapper/cron invocation. A successful lock probe alone does not prove workbook sync or journal recovery succeeded.
- **Do not create duplicate evidence while investigating.** A direct invocation of the real sync script can race the cron wrapper and create a second writer. Prefer temp workbooks/lock roots and injected fakes. If a live process must be stopped, identify the exact wrapper→child chain first, stop only that chain, and verify its locks are released or stale before retrying.
- **A live PID is time-sensitive evidence.** Recheck the PID immediately before any recovery decision; a worker’s earlier “owner alive” report can become stale. Conversely, a later “PID missing” result does not prove which invocation owned the lock without parent/child and creation-time evidence.

## User-corrected evidence-first response protocol (2026-08-27)

When the user asks whether a farm cron session ran, completed, or what comes next, answer from the newest direct completion artifact first: a Telegram screenshot, watchdog output, runner output, or saved cron output. Explicit text such as `Ca X - Phiên Y/3 ... hoàn tất` is completion proof and outranks stale manifest/scheduler metadata. Read the corresponding saved output and `Run Time` when available, then use job records/logs for corroboration, and only afterward use the full manifest to select the next chronological farm session. `planned`, `slot_time`, `next_run_at`, `enabled`, and `last_status=ok` are not completion proof. Keep **cron tick**, **farm slot/window**, and **farm session** separate; if counts are arithmetically inconsistent but the completion line and success/fail groups are explicit, preserve the completion conclusion and flag the report-quality defect separately. If no direct artifact exists, say `chưa xác minh` with source and timestamp rather than infer.

User-facing reports for this class of task should be concise Vietnamese and structured as: **Mục đích → Kết quả → Blocker/Chưa xác minh**. If the assistant previously misclassified a completed session, acknowledge the mistake in the first sentence and state the corrected evidence immediately; do not make the user re-prove a fact already shown in a direct artifact.

For the detailed workbook-sync incident recipe, see [`references/workbook-sync-lock-order-and-duplicate-dispatch.md`](references/workbook-sync-lock-order-and-duplicate-dispatch.md).

## Pitfalls (Windows / pytest / this codebase) — see references/windows-pytest-pitfalls.md
and references/ag-opus-audit-invocation.md (MSYS→Windows path bug that silently loses
files written to `C:/Users/...` from a D:-cwd MSYS shell).

Symlink creation needs a privilege not granted in CI shells (wrap in try/except, skip the leg when refused);
`monkeypatch.setattr` lambdas that call the patched attribute recurse infinitely (capture the original first);
`canonical_json` returns **bytes** (use `write_bytes`, not `write_text`); `sha256_file()` reads the file at
call time so compute declared hashes AFTER writing the final bytes; `manifest.validate_manifest` rejects
same-account multi-entry legacy (non-block) manifests — build a single-entry fixture or don't call
`load_snapshot` on a synthetic duplicate. `load_snapshot` also requires the filename to be exactly
`<assignment_id>.json`; canonical bytes saved as `manifest.json` still fail identity validation. Isolate each
negative/positive fixture in a fresh child directory so prior `wb/`, consume markers, evidence, or lock aliases
cannot contaminate later cases. Always run the NEW adversarial tests RED before implementation, then explicit
required node IDs and the full Phase suite; a green `-k` slice is diagnostic evidence only.

**Module-level imports follow module-level constants.** When appending tests/constants to an existing test
module, anything used at module level (`NOW = datetime(...)`, `timezone`) must be imported at module TOP.
A pre-existing test file that imported `datetime` only *inside* functions throws `NameError: name 'timezone'
is not defined` the moment you append a module-level constant. Same for `json` in a production module that
only used `__import__("json")` in one function — hoist `import json` to module top before referencing it from
new functions.

**Keep evidence hashes in sync with the audited candidate.** After fixing an audit MINOR and re-auditing,
regenerate the evidence JSON too. A stale SHA in the evidence self-report vs the audited binding is flagged
by AG as a worker typo (harmless but noisy). The binding hash is the authority; evidence should match the
committed bytes so the report is truthful and the next auditor isn't chasing a phantom mismatch.

## 9D.1 — remove ALL auto device-lock from the consumer repo (2026-08-15, user order)

**Why (log evidence to cite back to the user):** `python_runner/runs/scheduler.jsonl` showed repeated
`ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'`
(14–15/08, every shift, 3.9s exit 1), repeated `"multi-machine-feed-session skipped locked machine(s)"`
(04/07/08/10/08 → manual-needed), `DEVICE_LOCK_STATUS_OWNERSHIP_MISMATCH`, and a
`device-lock-release-audit.jsonl` with 52 manual releases. That is the "dọn cứt lock 30ph–1h" the user
keeps paying. Root cause: installed `automation_core.device_lock` changed its API (dropped
`DeviceLockNeedsUserDecision`), and the consumer imported stale symbols — EVERY batch died on import.
Removing auto-lock removes both the import break and the skip/release treadmill. Logs live on `D:` —
**never OneDrive** (`D:\Taadaa\tiktok-luot nuoi acc\python_runner\runs\`), and actual batch runtime dirs
are `D:\CodexRuntime\tiktok-*`; `~/.codex/device-locks/` holds the accumulated lock files.

**Scope decisions (user-confirmed):**
- Remove: `acquire_device_lock` / `DeviceLockUnavailable` / lease / reservation / `release_recovery_lock`
  / `reacquire_recovery_lock` / `.finish(succeeded=)` / `lock_reader` / `_production_lock_reader` /
  `_LOCK_ACTIVE_BLOCKED` / `device_lock_root_from_config` / `_is_verified_success` (was only for
  `device_lock.finish`).
- Keep: handoff/deferred-locked evidence (`recovery_lock_handoff.json`, `_prior_target_evidence`,
  `_write_deferred_locked_child_artifacts`) — it is an artifact-backed "this target failed before, defer
  it" guard, NOT auto-lock, and never caused a logged error. Keep `FAILED_LOCKED` enum values consumed
  from automation_core (external contract). Keep `core/device_lock.py` compat re-export (other tools
  import it). Keep `scripts/release-device-lock.py` + `tools/machine74_*.py` + `dismiss_verify_dialog.py`
  (manual/tooling paths; user still needs release tool for gan-proxy locks — **never touch gan-proxy lock
  files**).
- `multi_machine_feed_session._device_lock_root` stays — used only to VERIFY handoff aliases, not to
  acquire.

**Cascade pitfalls when deleting a module-level symbol that tests patch:**
- `unittest.mock.patch("run_tiktok.acquire_device_lock")` (and `patch(...device_lock...)`) raises
  `AttributeError: module 'run_tiktok' does not have the attribute ...` → remove the patch from
  `setUp`/`tearDown` in EVERY test class that had it (test_run_plan_smoke, test_feed_session_smoke,
  test_account_dry_run, ...). One setUp failure = whole class fails (dozens of tests).
- Tests importing a deleted helper (`from run_tiktok import _is_verified_success`) fail at collection
  (test_device_lock_lifecycle) — delete the test file; a test of removed auto-lock behavior is dead.
- Tests whose *fixture* generated lock aliases via `device_lock_paths(...)` must keep producing the
  handoff JSON shape without the auto-lock API: emit `machine_<n>.lock.json` / `serial_<s>.lock.json`
  names manually in the fixture (handoff verification only cares about the alias names).
- `_run_child` / worker fakes change arity (`_run_child(ctx, account, resolved_adb)` — the
  `device_lock` 4th arg is gone): update every `fake_run_child`/`worker` signature.
- Removing a `try/finally` that held the lease leaves a dangling `try:` — dedent the whole block, don't
  just delete the `finally`. py_compile catches it.
- Test files that ONLY tested the removed API (`test_device_lock.py`, `test_device_lock_lifecycle.py`)
  get deleted; baseline-failing tests unrelated to the change (device_prepare action-order, popup
  "called 2 times") stay failing — verify by `git stash` + rerun that they fail at HEAD too, so you never
  claim a regression you didn't cause.

**Result state (2026-08-15):** 13 files modified + 2 deleted, +260/−1097 lines; full suite
`1398 passed, 29 skipped, 6 failed` where all 6 failures are pre-existing baseline
(device_prepare ×5, feed_session_smoke ×1). Committed as `638ef91` after AG Opus APPROVED
(the EOL trap forced a second LF-normalized audit; the commit helper used bare `git add -A`
because the two deletions were already staged by `git rm`).

## 9D.2 — live-pilot fixes found while running 9C.2 (2026-08-15)

### PYTHON_EXE must be a Windows path, never MSYS (`/d/...`)

`live_entrypoint.py` hardcoded `PYTHON_EXE = "/d/Taadaa/python-envs/automation/Scripts/python.exe"`
(MSYS style). The canonical launcher argv passes it as `-Python <py>` to PowerShell, which cannot
resolve `/d/...` → `CommandNotFoundException` → `launcher_failed` (RC 1) with the permit already
consumed. Fix: `PYTHON_EXE = r"D:\Taadaa\python-envs\automation\Scripts\python.exe"` (raw Windows
path) and update BOTH test assertions that pinned the old string (test_hermes_cron_contract.py:287,
test_hermes_cron_regressions.py:707). Committed `8aa4b4df`. General rule: any path handed to
PowerShell or a child subprocess on Windows must be a native Windows path — MSYS paths only work
inside git-bash.

### `_spawn_subprocess` must strip `PYTHONPATH` from the child env

The Hermes session exports `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`
(duplicated). A child spawned with the inherited env resolves `import PIL` to the Hermes venv's PIL
(`_imaging` broken) instead of the automation venv → `ImportError: cannot import name '_imaging'
from 'PIL'` → `launcher_failed`. Fix in `_spawn_subprocess`:
`env = dict(os.environ); env.pop("PYTHONPATH", None)` so the child resolves strictly from its own
venv. Before blaming the child's venv, verify it actually HAS the dep
(`ls automation/Lib/site-packages/PIL`) — env shadowing is the usual cause on this host.

### Running a live entry via `run_once` (9C.2 mechanics)

- `python_runner/` has NO `__init__.py` — PEP 420 namespace package. Import as
  `from python_runner.hermes_cron.live_entrypoint import run_once` with BOTH `REPO` and
  `REPO/python_runner` on `sys.path` (module internals use `from python_runner.hermes_cron...`).
  MSYS argv (`/d/...`) passed to Python is silently un-resolvable — pass Windows paths.
- Permit MUST be canonical (13 `_REQUIRED_PERMIT_KEYS` + `schema_version`), NOT the pilot schema:
  `run_once` → `_load_permit` rejects any extra key (`permit_invalid:permit has unknown keys`).
  Build it directly with `models.canonical_json(...)`; `build_activation_permit` adds
  `logical_day/expiry/nonce/consumed` which the canonical loader rejects.
- Manifest MUST be a full canonical assignment manifest: a fabricated `{"entries":[...]}` fails
  `manifest_invalid:SOURCE_CONFIG_INVALID`. Build via `manifest.build_manifest_payload(day, source,
  seed, owner_id, worker_id, [entry], [])` with `source = SourceConfig.from_dict(...)` and
  `entry = manifest._entry(account, day, "provisional:<day>", slot_dt, "feed_only", seed)`; the
  manifest filename MUST be `<assignment_id>.json`.
- Permit is consumed once (marker `permit.consumed.json`) even when the launcher fails — build a
  FRESH permit per retry attempt.
- Full working recipe: `references/live-entry-run-recipe.md`.

### 9C.2 failure mode "feed not confirmed" — read success criteria before judging (user-corrected)

When the live entry fails with `feed not confirmed`, do NOT claim "needs 30 swipes". The flow
selects `selected_total_videos = random.randint(min_total, max_total)` (default config 15–30 —
user's deliberate human-like design, verified in `feed_swipe_smoke.py` ~14631) and success is
`completed_swipes >= selected_total` on the VERIFIED account (~10584); a session that reaches the
count is SUCCESS even with transient recovered blockers ("feed not confirmed" rows that recovered
are promoted to success, ~10628–10660). A run that stops early does so because a swipe landed on a
TikTok LIVE (multi-guest live is NOT a normal feed → `feed not confirmed` → stop) — that is correct
safe design, not a bug. Check `summary.txt` `selected_total_videos`/`swipes_completed` and the last
`swipe_N_after` screenshot before deciding whether to re-run.

**Measured session time (2026-08-16, pilots):** machine 5 (16 swipes) = 11 min; machine 6 (17
swipes) = 11.5 min (start/end in `summary.txt` UTC). So a 15–30-video feed session ≈ **11–12 min**
in practice (faster than the old 12–24' estimate). A machine's day (3 acc × 3 sessions) ≈ 100 min
≈ 15–20% of the 9–13.5h budget → **time is not the bottleneck**; user decided NOT to raise the
session count (raising sessions does not raise follow — `budget_per_day: 30` caps it).

## 9D.3 — LIVE feed misclassified as `manual-needed:popup` (2026-08-16)

**Symptom:** live 9C.2 entry died at `feed not confirmed` after a swipe landed on a real
TikTok LIVE (multi-guest live). Log: `classify_screen → manual-needed:popup` reason
`known live_room_invite popup detected`. `detect_allowed_generic_popup` (automation_core)
matched the live stream as a `live_room_invite` overlay → `GENERIC_POPUP_SCREEN` =
`manual-needed:popup` → flow ran the popup-dismiss path → post-dismiss observe failed →
session aborted (16/30 swipes).

**Fix (consumer repo, verified on the real ui.xml):** `core/classifier.py` — add
`_is_live_feed_screen(root, elements)`: true when LIVE markers (`đang live`, `nhấn để xem
live`) AND feed tab row (`trang chủ`, `bạn bè`, `đã follow`, `đề xuất`) co-occur; a real
room-invite overlay has NO feed tab row. Call it BEFORE `detect_allowed_generic_popup`,
return `ScreenClassification("for-you", 0.85, manual_needed=False)`. Verified: LIVE ui.xml
→ `for-you`; normal feed (swipe_15) → `following` unchanged; `_is_live_feed_screen` False
on non-live feed. Committed `cf49b7f5`.

**Level-of-fix decision (user-directed):** determine consumer vs core level BEFORE fixing.
Grep who calls the detector: `detect_live_room_invite_overlay` / `detect_allowed_generic_popup`
are used ONLY by the feed-session repo's `core/classifier.py`; tiktok-follow uses its own
`core/popup.py` + `automation_core.dismiss_popup` (never the generic-popup chain) →
consumer-level fix is correct; do NOT touch automation_core.

## 9D.4 — drop the synthetic `verifier_record.json`; F1 observation from real evidence (user order 2026-08-16)

**User correction ("Nguỵ trang cc gì phiền phức chế đâu ra v"):** the 9C.2 design demanded a
`verifier_record.json` that the canonical feed session NEVER writes → machine-6 run ended
`verifier_not_accepted` even though the feed itself SUCCEEDED (`summary.txt status: success`,
17 swipes, profile screenshot present). The synthetic file was invented by the plan/code, not
by the real flow — user rejected it. **Never invent verification files the canonical script
does not produce; success proof must come from real evidence the flow already writes.**

**Fix (`live_entrypoint.py`):** `_production_launcher`, when `verifier_record.json` is
missing/unreadable, calls `_build_observation_from_evidence(artifact_root, permit)`:
- requires `artifact_root/summary.txt` (regular non-symlink) containing `final_status:
  success` or `status: success` AND
- a `profile`-named PNG under the root (most recent regular non-symlink `screen.png` whose
  path contains `profile`; feed session writes
  `.../feed-session-smoke/profile_preflight_identity_guard/attempt_1/screen.png`)
- on success sets `verified="ACCEPTED"`, copies ALL identity fields from the permit (no
  fabrication), computes real SHA-256 of summary + screenshot, `verified_at` = now.
- any missing piece → `verified=None` (fail closed). `verifier_record.json` still honored if
  present (backward compatible).
- Tests: 3 appended (accept real evidence; fail closed w/o success marker; fail closed w/o
  screenshot). Contract file 36 passed. Committed `bf9086f4`.

## EOL traps that recurred on 9D.3/9D.4 (mixed-EOL files)

- **`patch` tool corrupts INDENTATION on multi-line replacements in CRLF files (bit us twice
  2026-08-17):** a multi-line `old_string`/`new_string` edit silently added leading spaces to
  continued lines (a `def run():` body landed at 20-space indent → IndentationError; lint then
  mislabels it "pre-existing"). After any multi-line patch, re-read the hunk; prefer
  single-line `old_string`s. Reliable mechanism for exact edits on this repo's CRLF files:
  write a python script with write_file FIRST (long bash heredocs carrying mixed quotes die
  with "unexpected EOF while looking for matching `'`"), then run:
  `data = io.open(p, encoding="utf-8", newline="").read()` →
  `assert data.count(old) == 1` → `data.replace(old, new)` → write back with `newline=""`.
- **Mixed-EOL baseline (e.g. classifier.py: 681 CRLF + 73 LF):** the `patch` tool converts
  the whole file to CRLF → whole-file diff churn. Restore (`git checkout -- <file>`), then
  LF-normalize the WHOLE file ONCE (`data.replace(b'\r\n', b'\n')`) and accept the EOL churn;
  add an "EOL NOTE" to the audit prompt so AG verifies the only semantic change is your lines.
- **`git diff --check` flags `\r` on ADDED lines as trailing whitespace** when working-copy
  EOL differs from the index. LF-normalize the inserted blocks (or whole file) first.
- **Staged-hash mismatch in the commit helper** (`staged hash mismatch for X`): autocrlf
  converts CRLF→LF at `git add`, so the staged blob ≠ working-copy bytes the audit hashed.
  Fix: LF-normalize working copy, `git reset -q HEAD -- <file> && git add -- <file>`, verify
  `git show :<file>` hash == working hash, rebuild the audit bundle, RE-AUDIT, then commit.
- **`new blank line at EOF` fails `git diff --check`** after appending tests: strip trailing
  blank lines, keep exactly one final `\n` (`data.rstrip(b'\r\n') + b'\n'`).
- **`git diff -- <path>` is empty for a staged+modified file** (`MM` status) — the audit
  builder must diff against HEAD (`git diff HEAD -- <path>`) or the bundle silently misses it.
- **AGENTS.md external change:** another agent/workstream can leave tracked dirty files
  (e.g. AGENTS.md session-start context) during your commit. Default: exclude from your
  allowlist and keep unstaged. When the user says "commit luôn phần ng khác sửa", fold it
  into the allowlist, add an audit note (doc-only, user-requested), rebuild + re-audit.

## Picker scheduling semantics (how cron picks machines — answer from code, not guesswork)

- **⚠️ Lane sets below are OUTDATED — superseded 2026-08-18 (user chốt 18/08): parity lanes are
  ROW-parity: `LANES = (("A", (2, 4, 6)), ("B", (1, 3, 5)))` — A = even days rows 2,4,6;
  B = odd days rows 1,3,5.** The CURRENT design is the 3-ca/3-phiên block-mode section below;
  anything here describing A=(1-3)/B=(4-6) or "1 entry/account row-slot" is HISTORICAL.
- **Not random machine pick.** Accounts outside today's lane → skipped `CAPACITY_EXCEEDED`.
- **Per-machine ordering/gaps are deterministic, not random:** `machine_day_seed` =
  sha256(day|machine|assignment_seed); `rng.sample(due, ...)` + `pair_gap = rng.choice((60,
  75, 90))` — same day+machine → same plan. Manifest persisted before execution so a later
  pick with same digest/seed reuses published bytes (never reshuffles mid-day).
- **Timeline (CURRENT pre-plan HEAD: BLOCK_ANCHORS = 07:00, 14:00, 21:00):** each
  machine/day = 3 blocks × 2 FEED_ONLY sessions (1h each); session 2 starts `PAIR_GAP`
  (60-90 min) after session 1 END; next block starts `INTER_BLOCK_GAP` (180-300 min) later.
  NOT "all machines at 06:00" — 06:00 only opens the logical-day window; first session
  starts 07:00. **⚠️ HISTORICAL — replaced by the approved follow-hook-3-session-jitter
  plan (section below); do not re-derive constants from this bullet.**
- **⚠️ 3 blocks = 3 DIFFERENT accounts (user-corrected 2026-08-16, đừng đọc sai lần 2):**
  `for account in order: block_index = 1,2,3` — mỗi block thuộc 1 account RIÊNG (picker.py
  ~271-295). Nghĩa là: **1 ca (block) = 1 acc; 1 ngày = 3 ca = 3 acc khác nhau**; mỗi acc có
  2 phiên/ngày (đang nâng lên 3 theo plan follow-integration) → 1 máy = 3 acc × 2-3 phiên.
  KHÔNG phải "1 acc chơi 6 phiên". Khi nói "nâng 2→3 phiên" nghĩa là nâng SỐ PHIÊN CỦA MỖI
  ACC trong ca của nó (1 ca vẫn 1 acc), không phải thêm block cho cùng acc.
- **`_feed_decision` due rules:** never-success → due (2 sessions); elapsed ≥3 days
  (`HARD_OVERDUE`) → 3 sessions; ==2 days (`NORMAL_DUE`) → 1; 0-1 days → NOT_DUE; in-flight
  reservation → skip. Requires exactly 3 schedulable lane accounts per machine, else lane
  skipped `UNSCHEDULABLE_CAPACITY`.

## ✅ CURRENT 2026-08-18 — 3-ca/3-phiên block-mode picker (parity lane chẵn/lẻ, committed `df9051d`)

**This is the CURRENT picker design** — the row-slot section below is HISTORICAL. Full verified
detail + fleet-test structure in
[`references/block-mode-picker-20260818.md`](references/block-mode-picker-20260818.md).

### Design (answer from code: `blocks.py` + `picker.py::_entries`)

- **3 ca (block)/máy/ngày**, anchors `BLOCK_ANCHORS = ("06:00", "12:30", "19:00")`; **mỗi ca 1 acc
  = 3 phiên 60'** (`session_index` 1/2/3, `block_id` bound). Session slots:
  s1 = anchor + jitter; s2 = s1_end + pair_gap; s3 = s2_end + pair_gap;
  `PAIR_GAP_MINUTES = (35, 60)` grid 5 (`range(35, 61, 5)`); `JITTER_MINUTES = (-20, -15, 15, 20)`.
- **Lane theo ROW-PARITY (user chốt 18/08):** `LANES = (("A", (2, 4, 6)), ("B", (1, 3, 5)))` —
  ngày chẵn → rows 2,4,6; ngày lẻ → rows 1,3,5. **KHÔNG phải** A=(1-3)/B=(4-6).
  * Chi tiết phân bổ ca ngày chẵn: Ca 1 (06:00–11:00) chạy Row 2 (chính); Ca 2 (12:00–17:00) chạy Row 4 (warm); Ca 3 (18:00–23:30) chạy Row 2 (chính).
  * Chi tiết phân bổ ca ngày lẻ: Ca 1 (06:00–11:00) chạy Row 1 (chính); Ca 2 (12:00–17:00) chạy Row 3/5 (warm); Ca 3 (18:00–23:30) chạy Row 1 (chính).
  * **Grace / Catch-up slot 18:00:** Đầu ca tối (18:00), scheduler có thể kích hoạt nốt các slot bị lỡ/chờ lock của Ca 2 (Row 4) cho 1-2 máy trước khi chuyển hẳn sang Row 2 từ 18:35.
- **Ca 1/2/3 ↔ row[0/1/2] của lane hôm đó** — acc giữ giờ cố định theo row (row 2 luôn ca 06:00
  ngày chẵn). Không còn shuffle account theo seed: seed chỉ quyết định jitter + pair_gap.
- **Máy thiếu acc ở row của ca → BỎ CA** (không bắt buộc đủ 3 blocks; validate chỉ chặn >3 blocks
  / trùng block 1 máy).
- **Acc ngoài lane hôm đó → skipped `CAPACITY_EXCEEDED`** (giữ coverage: entries+skipped = mọi
  account trong source). `UNSCHEDULABLE_CAPACITY` KHÔNG còn dùng cho acc ngoài lane.
- **Jitter:** RNG riêng `random.Random(machine_day_seed(logical, machine, seed) ^ (0x9E3779B9 *
  block_index))`; **block 1 clamp jitter âm → 0** (anchor 06:00 = window start, jitter âm sẽ đẩy
  s1 trước window → RESERVED_BLOCK_CONFLICT); blocks 2/3 giữ ±20.
- `_feed_decision`: cap 3 sessions/day; never-success → due; elapsed ≥3 (HARD_OVERDUE) → due;
  ==2 (NORMAL_DUE) → due; 0-1 → NOT_DUE; in-flight → skip.
- `CONSTRAINTS` trong `manifest.py` phải khớp blocks.py: `lanes: [{"lane":"A","rows":[2,4,6]},
  {"lane":"B","rows":[1,3,5]}]`, `block_anchors: ["06:00","12:30","19:00"]`,
  `sessions_per_block: 3`, `pair_gap_minutes: [35,60]`, `slot_grid_minutes: 5`. **assignment_id
  hash phụ thuộc CONSTRAINTS → đổi lanes/anchors làm đổi MỌI golden vector.**

### Test-suite alignment khi picker đổi shape (2026-08-18, 73 fail → 250/250 pass)

Symptom→cause map (giống đợt 17/08): `journal._entry_target(entry_id)` validate mọi event target
(machine/serial/account_row) với manifest entry → `IDENTITY_MISMATCH` / `invalid journal
transition` / `MANIFEST_IDENTITY_MISMATCH`. Fix TESTS, không production:
- **`entries[0]` KHÔNG còn là acct-a row 1.** SOURCE 3 acc (rows 1-3) + day 2026-08-10 (chẵn, lane
  A rows 2,4,6) → chỉ acct-b row 2 được schedule (block 1); rows 4/6 không có acc → ca 2/3 bỏ.
  entries[0..2] = 3 phiên của acct-b. Mọi journal target phải là `{"machine":1,
  "serial":"SERIAL_A", "account_row":2}` (TARGET, không còn TARGET1 row 1).
- **Muốn acct-a row 1 được schedule → dùng ngày LẺ** (2026-08-11, lane B rows 1,3,5).
- **Skipped sets đổi:** acc ngoài lane → `CAPACITY_EXCEEDED` (không phải UNSCHEDULABLE_CAPACITY);
  test assert set skipped phải gồm cả CAPACITY_EXCEEDED.
- **Forge machine-999 phải rehash `assignment_id` với account_ids = entries ∪ skipped** (validate
  derive coverage như vậy; chỉ entries → MANIFEST_IDENTITY_MISMATCH trước khi tới CLI gate).
- **`select_due_entries` sau nửa đêm:** day chỉ có 1 block (rows 1-3 ngày chẵn) → mọi session hết
  window → `[]` (không `[entries[8]]`).
- **Golden vector contract test:** block 1 ngày chẵn = acct-2 row 2 @ 06:00 (jitter clamp 0);
  `block_id = block-v1-<sha256("2026-08-10|1|1|acct-2")[:32]>`; entry_id có `block_id` +
  `session_index`. **Recompute bằng cách CHẠY code thật, không suy đoán.**

## ⚠️ SUPERSEDED 2026-08-17 — picker is now ROW-SLOT, not blocks/lanes

The lanes/blocks/jitter scheduling model in this section (and the jitter plan below) is
**HISTORICAL** — the picker was rewritten. `picker.py::_entries` now emits **1 entry per
feed-due account** anchored to its physical row — `row_slots = {1:"06:00", 2:"08:00",
3:"10:00", 4:"12:30", 5:"15:00", 6:"17:30"}` — with `blocks: []` and **no**
`block_id` / `session_index` anywhere. Lanes are gone (every day schedules the same 6
rows); rows 7-9 → skipped `UNSCHEDULABLE_CAPACITY`; `clear_cache_due()` is always False
(no block 3). Full verified detail, the fleet-test structure (45 passed + 1 xfail), and
the **production bug `ReasonCode.NOT_DUE` missing** (crashes picks for just-fed accounts)
live in
[`references/row-slot-picker-20260817.md`](references/row-slot-picker-20260817.md).

### Test-suite alignment after a picker output-shape change (2026-08-17, p1_r2 46→116 fail→pass)

When the picker entry shape changes, journal/watcher/notification tests fail EN MASSE —
even tests that never call the picker — because `journal._entry_target(entry_id)`
(`journal.py:155`) validates every event's `target` dict (`machine`/`serial`/`account_row`)
against the manifest entry. Old fixture claims died: under blocks "entries[0] = acct-b row 2
@ 05:40 jitter" becomes **entries[0] = acct-a row 1 @ 06:00**. Symptom→cause map:
`IDENTITY_MISMATCH` / `invalid journal transition` / `MANIFEST_IDENTITY_MISMATCH` /
`INVALID_PATH` (notification `target_hash`). Fix the TESTS, never production:
- Keep `TARGET` (row 2) for row-2 probes but add `TARGET1 = {"machine": 1, "serial":
  "SERIAL_A", "account_row": 1}`; every journal/watcher/`NotificationKeyMaterialV1`/
  `ExecutionReservationV2.create`/`RecoveryReservationV2.create` using `entries[0]`
  must pair it with the row-1 target.
- Block-mode forgery paths must be rewritten (e.g. `test_r10_watcher_cli_*` looped
  `forged["blocks"]` + `block_id_for` → now splice `machine`/`serial` on entries and
  rebuild `entry_id_for(...)` WITHOUT block/session args; `validate_manifest(forged,
  None)` then passes and the CLI gate is what the test asserts).
- Row-slot slot windows: `select_due_entries(as_of="<next-day>T00:00:00")` returns `[]`
  (all slots long past their 90' window), not `[entries[8]]`.
- Per-test fix map + counts: `references/row-slot-picker-test-alignment-20260817.md`.

## Follow-hook + 3-session + jitter plan (APPROVED 2026-08-16, NO-LIVE) — ⚠️ HISTORICAL, never implemented; superseded by the committed row-slot picker (`597d7e7` 2026-08-17); do not re-derive constants from this section

Plan: `D:\Taadaa\tiktok-luot nuoi acc\.hermes\plans\2026-08-16_follow-hook-3-session-jitter.md`
(worktree branch `phase9-authority-910a8add`, HEAD `bf9086f4`). Origin of this change:
user phản đối anchor cố định ("tự nhiên 7h đồng loạt máy chạy sao k chạy từ 6h và khởi động
ngẫu nhiên thêm cụm kèm delay giữa các máy") — plan chốt: anchor cửa sổ + jitter deterministic.

**Approved constants (thay thế mọi constant cũ):**
- `BLOCK_ANCHORS = ("06:00", "12:30", "19:00")`; `PAIR_GAP_MINUTES = (35, 60)`;
  `_PAIR_GAP_GRID_MINUTES = 5` → `_VALID_PAIR_GAPS = range(35, 61, 5)` = {35,40,45,50,55,60};
  `JITTER_MINUTES = (-20, -15, 15, 20)`; `INTER_BLOCK_GAP_MINUTES = (90, 300)` (chỉ contractual
  non-jittered feasibility test, KHÔNG enforce runtime — anchors cố định quyết định).
- `build_block_sessions(day, *, block_index, pair_gap_minutes, jitter_minutes: int = 0)` →
  **3-tuple** `(s1,s1+60), (s2,s2+60), (s3,s3+60)`; s1 = anchor + jitter (jitter CHỈ dịch S1);
  s2 = s1+60'+gap; s3 = s2+60'+gap. `_validate_pair_gap` message:
  `"pair_gap must be one of 35..60 grid 5"`. `AccountBlock` thêm `jitter_minutes: int = 0`
  (default → backward-compat).
- Picker: loop 3 sessions `((1, slots[0]), (2, slots[1]), (3, slots[2]))`; jitter từ RNG RIÊNG:
  `jitter_rng = random.Random(machine_day_seed(logical, machine, seed) ^ (0x9E3779B9 * block_index))`
  → `jitter = jitter_rng.choice(JITTER_MINUTES)` → truyền GIÁ TRỊ vào
  AccountBlock/build_block_sessions (blocks.py KHÔNG tự tạo rng). `picker.py:241` hardcode
  `rng.choice((60,75,90))` → `pick_pair_gap(day, machine, seed, rng)`.
- **REACTIVE phiên 2/3:** session_slots[1], session_slots[2] KHÔNG ghi giờ cố định bắt buộc —
  phiên 2/3 = `last_feed_success_at` + random 35-60' per-machine (runner tính động; picker chỉ
  định khung: anchor phiên 1 + tối đa 3 phiên/ca).
- feed_swipe_smoke: `DEFAULT_FEED_FOLLOW_RATES[FEED_TYPE_FOR_YOU]` 5 → 6 (organic follow ~1/30
  video = người thật).
- multi_machine_feed_session: `_session_index` qua `child_config["_session_index"]` từ entry
  manifest; chỉ bật `_verify_current_account` khi `_session_index == 1` (phiên 2/3 giữ
  `_verify_profile` nhẹ); hook follow cuối phiên khi `final_status in {"success","degraded"}`
  → subprocess `python "D:\Taadaa\tiktok-follow\follow_runner\run_follow.py" --machine N
  --config "D:\Taadaa\tiktok-follow\follow_runner\config.example.yaml" --account-row-index R`
  (KHÔNG import chéo); gate sensitive (stop_reason chứa login/OTP/2FA/captcha/security/verify →
  skip ghi `sensitive-skip`); FOLLOW_FAILED → ghi `follow_failed: true` (không dừng phiên);
  ghi `follow_result.json` vào child artifact. `max_workers` mặc định 30 (`ctx.config["_max_workers"] = 30`
  nếu chưa set) + stagger 2-8s sẵn có = 2 lớp chống đồng loạt.

**⚠️ BLOCKER phát hiện khi implement (đã phân tích, CHƯA sửa — chờ parent duyệt allowlist):**
allowlist plan chỉ có blocks.py/picker.py/feed_swipe_smoke.py/multi_machine_feed_session.py +
tests, NHƯNG `python_runner/hermes_cron/manifest.py` hardcode topology 2-phiên và sẽ CRASH
ngay khi picker build 3 sessions:
- `manifest.py:423-447`: `session_index not in (1,2)` reject; `len(block_entries) != 2` reject;
  `entry_ids` len phải = 2.
- `manifest.py:392`: `pair_gap not in (60,75,90)` reject (không chấp nhận grid 5 mới).
- `manifest.py:397`: `session_slots != [list(slot) for slot in build_block_sessions(...)]`
  → 3-tuple sẽ reject.
- `manifest.py:21-31` `CONSTRAINTS` chứa `sessions_per_block: 2`, `block_anchors:
  ["07:00",...]`, `pair_gap_minutes: [60,90]`, `inter_block_gap_minutes: [180,300]`,
  `slot_grid_minutes: 15` — assignment_id hash phụ thuộc CONSTRAINTS.
- `manifest.py:491`: inter-block gap hardcode `< 180` phút reject (plan muốn (90,300)).
- Picker gọi `validate_manifest(payload, self.source)` ngay sau build (`picker.py:174`) → sẽ
  raise `SOURCE_CONFIG_INVALID` chứ không tạo được manifest 3 sessions.
- Test golden-vector ngoài allowlist hardcode 6 entries / 07:00 anchors / 2 sessions-per-block:
  `test_hermes_cron_fleet.py` (~15 test: `len(entries)==6`, `session_index in [1,2]`, anchors
  cũ, gap ∈ (60,75,90), inter-block 180'), `test_hermes_cron_contract.py` (golden vector hash
  CONSTRAINTS cũ + `slot_time 07:00` + `run_entry as_of 07:30`), `test_hermes_cron_p1_r2.py`
  (line 2062 `selected == [entries[5]]` → sẽ thành `entries[8]`), `test_hermes_cron_regressions.py`
  + `test_hermes_cron_watcher.py` (dùng Picker → slot 07:00 không còn cố định khi jitter áp
  vào S1). Jitter deterministic per day+machine+block_index nên manifest vẫn deterministic,
  nhưng giá trị đổi.
- **Cần parent chốt trước khi implement:** (a) cho phép sửa `manifest.py` (2→3 sessions,
  gap grid 5, anchors mới, inter-block 90-300); (b) cho phép update các test fleet/contract/
  p1_r2/regressions/watcher; (c) xác nhận jitter áp vào slot_time ghi manifest (đổi golden
  vectors) hay chỉ runtime.
- Multi_machine test file thật là `python_runner/tests/test_multi_machine_feed_session.py`
  (KHÔNG có test_feed_session_smoke.py) — pattern test: `make_ctx(temp_dir, workbook, machines=...)`
  + `patch("flows.multi_machine_feed_session.feed_session_smoke", side_effect=fake_feed)`; thêm
  test hook follow theo plan §4: invoked_after_success / skipped_on_sensitive_failure /
  skipped_on_non_success / uses_subprocess_not_import / switcher_disabled_for_session_2_3 /
  switcher_session_index_from_config / max_workers_default_30. Feed test file thật:
  `test_feed_swipe_smoke.py`.

### Implementation status 2026-08-16 (worker đã chạy, CHƯA hoàn thành) — ⚠️ STALE: superseded 2026-08-17 by the committed row-slot picker (`597d7e7`); the models.py slot-grid blocker and golden-vector work never landed

**Allowlist ĐÃ ĐƯỢC user duyệt mở rộng 16/08 ("Sửa luôn") — không cần hỏi lại:**
- CODE (6): `blocks.py`, `picker.py`, `manifest.py`, `feed_swipe_smoke.py`, `multi_machine_feed_session.py`.
- TESTS (6): `test_hermes_cron_blocks.py`, `test_hermes_cron_fleet.py`, `test_hermes_cron_contract.py`,
  `test_hermes_cron_p1_r2.py`, `test_hermes_cron_regressions.py`, `test_hermes_cron_watcher.py`.
- Vẫn KHÔNG sửa: follow repo, workbook, config thật, AGENTS.md, cron jobs, runtime state, installed
  scripts, plan file.

**Red đã viết xong (chưa verify đỏ/green):** blocks.py tests viết lại hoàn chỉnh (3-tuple, jitter chỉ
dịch S1, gap grid 5, message "35..60 grid 5", `jitter_minutes: int = 0` default); fleet (~12 test →
9 entries / session_index [1,2,3] / anchors mới / range(35,61,5) / inter-block 90 / 2-machine 18
entries); contract (golden vector, `len(grid_slots)==229`, is_schedulable 17:35); p1_r2
(entries[5]→[8], as_of 07:30→06:30). regressions + watcher CHƯA sửa. GREEN chưa bắt đầu.

**⚠️ BLOCKER MỚI — `models.py` ngoài allowlist:** plan + contract test yêu cầu
`slot_grid_minutes 15→5` (`len(grid_slots("2026-08-10")) == 229`), NHƯNG `SLOT_GRID_MINUTES = 15`
nằm trong `python_runner/hermes_cron/models.py` — KHÔNG có trong allowlist 6 file code. Hoặc xin
thêm models.py vào allowlist, hoặc đổi test về 77 (lệch plan). Chưa có quyết định.

**Golden vector KHÔNG được suy ra bằng tay:** slot `05:40` / jitter `-20` cho seed 7/block 1 trong
contract test là GIẢ ĐỊNH chưa verify (chưa chạy picker RNG thật). Luật: recompute bằng cách CHẠY
code sau khi picker implement xong (`jitter_rng = random.Random(machine_day_seed(...) ^
(0x9E3779B9 * block_index)).choice(JITTER_MINUTES)`), không bao giờ khắc giá trị đoán vào test.

**Môi trường verify flows tests:** `test_multi_machine_feed_session.py` + `test_feed_swipe_smoke.py`
không collect được vì `automation_core.escalation` không resolve được — python đang load
`automation_core` từ Hermes venv (stale, thiếu escalation) thay vì
`D:\Taadaa\python-envs\automation\Lib\site-packages` (có escalation.py). Trước khi claim pass/fail
cho multi_machine_feed_session.py, kiểm tra `python -c "import automation_core; print(automation_core.__file__)"`
resolve đúng venv (fix: chèn site-packages automation vào sys.path trước khi chạy). 6 cron test files
chạy ngon không cần bước này.

**Report format cho implementation runs (user-mandated):** báo cáo cuối PHẢI gồm đúng 4 mục —
danh sách file đã sửa / test pass-fail (kèm baseline trước-sau) / `git diff --check` / deviation
(liệt kê mọi lệch so với plan + lý do). Nếu chưa chạy được thứ gì (env, iteration limit), nói thẳng
"chưa verify" — không bịa số.

## Live-entry workbook mapping (row vs machine — user-corrected 2026-08-15)

- `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` is the ONLY source for a live entry's
  machine→serial→account. Column `May` holds the MACHINE number; Excel row ≠ machine number
  (machine 5 sits at Excel row 26 because rows 2..25 carry machines 1..4 across slots). Find the
  machine by scanning column `May`, not by row arithmetic.
- `account_row` (1..6) is the slot OF THE ACCOUNT ON THAT MACHINE (machine 5 has multiple rows /
  serials), not the Excel row.
- `D:\OneDrive\Tiktok\Tik1.xlsx` is row-1 accounts ONLY — never use it for row-2 (or any row>1)
  lookups (user correction: "tik1 là chỉ acc của row1").
- serial `9885e64b4a434a3037` = machine 5, account row 2 → account `[REDACTED]`.

## Phase 9B.1 / 9B.2 lessons (2026-08-13, implemented by coordinator after 3 delegate crashes)

### 9B.1 — no-agent wrapper templates (`scripts/hermes_cron/tiktok_{picker,runner,watcher}.py`)

- **Pattern = 9A.5 `live_entrypoint.py`:** no business argv (reject non-empty argv fail-closed, exit
  nonzero, no child), env-driven activation (`HERMES_CRON_*_ENABLED=1` or a regular non-symlink permit
  file via `HERMES_CRON_PERMIT_FILE`), default-off/inert (absent/invalid → exit 0, EMPTY stdout, no child),
  absolute repo root via `Path(__file__).resolve()` walking to `.git`, explicit
  `TARGET_PYTHON_DEFAULT="/d/Taadaa/python-envs/automation/Scripts/python.exe"` (overridable via
  `HERMES_CRON_TARGET_PYTHON`), child cwd = repo root, allowlist env only.
- **⚠️ LIVE-WIRING 2026-08-17 — Hermes cron tool has NO per-job env field** (verified in
  `cron/jobs.py` + `cron/scheduler.py`: no_agent script runs with the GATEWAY process env via
  `_sanitize_subprocess_env(os.environ.copy())` + `cwd=workdir`; `_run_job_script` uses
  `sys.executable`). So wrappers CANNOT receive `HERMES_CRON_*` via cron config. Three-part
  repo-anchored contract that replaced env-only activation (commits `5e35ee9` + follow-up):
  1. **Activation permit file**: `<repo>/runtime/hermes-cron/permits/<wrapper-kind>.permit`
     (regular, non-symlink). `is_activated()` falls back to `_default_permit_file()` when
     `HERMES_CRON_*_ENABLED`/`HERMES_CRON_PERMIT_FILE` are absent. File exists → active;
     absent → inert (exit 0, empty stdout). No env needed at all.
  2. **`runtime/hermes-cron/env.json`**: config fallback read by `repo_env_overrides()` /
     `merged_env()` (process env WINS over file; missing file/key → fail-closed exit 3, same as
     env-only contract). Operator creates it at live-approval time; NEVER leave it in the repo
     while running `test_hermes_cron_wrappers.py` — the tests assert default-off and fail when
     the file/permit exists (delete after E2E probes).
  3. **`--execute` gate in `hermes_cron_runner.py`**: offline harness still refuses
     `--execute/--repo/--feed-workbook` UNLESS `runtime/hermes-cron/permits/tiktok_runner.permit`
     exists; live permit → `ProductionFeedLauncherAdapter(enabled=True)` +
     `run_entry(execute=live)`. Wrapper forwards `HERMES_CRON_REPO`/`HERMES_CRON_FEED_WORKBOOK`
     to satisfy the gate.
- **⚠️ MSYS default python path breaks child spawn**: `target_python()` must convert the MSYS
  default `/d/Taadaa/...` to `D:\Taadaa\...` (Windows `CreateProcess` cannot resolve `/d/...` →
  `FileNotFoundError: [WinError 2]`); env-override paths pass through unchanged.
- **⚠️ Indent bug from fuzzy patch (bit us 2026-08-17)**: after patching `target_python()`, the
  `return value` line ended up INSIDE the `if` block → function returned `None` for non-MSYS paths
  → `subprocess` `TypeError: os.fsdecode expected str not NoneType` (`argv[0]=None`). Always
  `py_compile` AND run the wrapper test file after editing wrappers; do not trust "lint: ok".
- **no_agent cron = script-only = ZERO AI key (user insight 2026-08-17)**: an agent-mode cron job
  needs a provider key IN THE GATEWAY process env (the VBS launcher `Hermes_Gateway.vbs` sets only
  HERMES_HOME/PYTHONIOENCODING/VIRTUAL_ENV/PYTHONPATH → missing `NINEROUTER_API_KEY` → 401
  "No active credentials"). Script-only (`no_agent=true`) jobs never touch an LLM — they run like
  Windows Task Scheduler (0 tokens, 0 key). If a cron job only runs a script, create/convert it as
  `no_agent=true`; do NOT patch the gateway env for it.
- **HCM logical day:** 00:00-01:59 → previous day; 02:00-05:59 → exit 0 empty stdout (silent); 06:00-23:59
  → current day. `as_of` = real now; `reference_time` = run-bound same-run timestamp (never static future);
  deterministic seed from logical day + config digest.
- **Windows child spawn requires infra env:** a stripped child env fails `WinError 193 %1 is not a valid
  Win32 application` when `argv[0]` is a `.py`/`.cmd` under a sanitized PATH. The wrapper MUST forward
  non-secret Windows infra vars (`SystemRoot`, `SystemDrive`, `ComSpec`, `PATHEXT`, `TEMP`, `TMP`) in
  addition to the allowlist, or the child cannot start. Sanitize PATH via `HERMES_CRON_CHILD_PATH`.
- **Fake "target python" for NO-LIVE tests = `.cmd` shim, not `.py`:** on Windows a `.py` cannot be
  exec'd as `argv[0]` (WinError 193). Write a `fake_python.cmd` that re-execs real python with a `-c`
  recorder (argv/cwd/env_keys → `fake_record.json`); set `HERMES_CRON_CHILD_PATH` = python dir +
  `C:\Windows\System32`. Assert exact argv/cwd/env (not grep), and assert `rec is None` for
  no-child/silent/default-off cases.
- **Env allowlist test must be case-insensitive + shim-aware:** the `.cmd` shim injects `SYSTEMROOT`/
  `COMSPEC`/`PROMPT` into its own env, so assert "no forbidden/secret/agent keys leak" (substring scan
  upper-cased: `SECRET`, `TOKEN`, `PASSWORD`, `AGENT*`, `HERMES_WORKDIR`, `HERMES_LIVE_PERMIT_FILE`,
  `CREDENTIAL`, `API_KEY`) rather than exact-set equality against the allowlist.
- **Deploy PS1:** byte-copy the 3 tracked templates to exact installed targets
  (`%LOCALAPPDATA%\hermes\scripts\tiktok_*.py`), compute+verify SHA-256 after each copy, fail closed on
  missing source / unexpected destination / schema drift / hash mismatch. Installed files are runtime
  artifacts, never commit paths. Test via temp-dir copy + hash equality/mismatch (NO-LIVE; never actually
  run the PS1).

### 9B.2 — declarative job spec (`job_spec.py` + `scripts/hermes_cron_schedule.json`)

- Exact schedules: picker `0 6 * * *`, single runner `*/15 * * * *`, watcher `7,22,37,52 * * * *`
  (watcher offsets must be disjoint from runner minute offsets 0/15/30/45; validate via
  `cron_minute_offsets(...).isdisjoint(...)`).
- Fail-closed: reject hour 24/25 and non-five-field cron; exactly one runner; watcher omitted/DEFERRED
  unless the failure-producer task is APPROVED; Hermes create command = EXACTLY the wrapper (business args
  live in the wrapper); process lease with stale → `FAILED_LOCKED`, no auto-reclaim; runner at 06:00 yields
  the publication lease to picker; runner spawns a detached ExecutionReservationV2 child and never depends
  on the Hermes script timeout for child lifecycle.

### Time-of-day-dependent test trap (hit 2026-08-13)

A wrapper test that uses "real now" (`no HERMES_CRON_NOW`) passes at 20:xx but FAILS after midnight HCM
(02:00-05:59 silent window returns exit 0 / no child). Any test that must exercise the ACTIVE path must set
an explicit daytime `HERMES_CRON_NOW` (e.g. `2026-08-13T10:30:00+07:00`); never rely on wall-clock time in
the suite, or the suite is flaky across the silent window.

## Cron runtime config generation (live-approval inputs — hit 2026-08-17)

When going live the operator must generate 3+ inputs by hand (full recipe + builder script pattern:
`references/cron-runtime-config-generation-20260817.md`). Pitfalls that cost 4+ failed picker runs:

- **`StatePaths` requires `offline_root` to be an ANCESTOR of `state_root`** (`models.py`:
  `if resolved != off and off not in resolved.parents: raise INVALID_PATH`). I first set
  `offline_root = <state>/offline` (child) → `INVALID_PATH`. Fix: `offline_root` = PARENT
  (`D:/Taadaa/runtime/kibe`, with `state_root = .../kibe/cron-state`). Do not guess — check the
  containment direction in `models.py:396-416`.
- **Manifest requires `owner_id == worker_id`** (`manifest.py:264`: `owner_id != worker_id` →
  `MANIFEST_IDENTITY_MISMATCH`). `env.json` must set them equal (e.g. both `hermes-cron-kibe`).
- **Feed/post state JSON must use the FULL validator schema, not a journal-style shorthand.**
  `JsonFeedStateReader` → `_validate_feed_state` requires EXACTLY
  `{account_id, last_feed_success_at, unresolved_reservation, terminal_facts, state_revision}`
  (never-success = `last_feed_success_at: None, unresolved_reservation: false, terminal_facts: []`);
  `_validate_post_state` requires `{account_id, status, video_available, target_count, state_revision}`
  (status `DUE` ⇒ `video_available` bool; `video=true` ⇒ `target_count` int ≥1, `video=false` ⇒ count None).
  `state_revision` must EXACTLY equal the revision in the generated source config
  (`SourceConfig.state_revision(account_id[, post=True])`) or the picker skips every account
  (`INVALID_FEED_STATE` / `POST_STATE_UNAVAILABLE`). The generator's `canonical_journal_facts.json`
  uses `feed_state={"status":"ready"}`, `post_state={"status":"due"}` — that is the generator INPUT
  (its own content-hash), NOT the runtime state JSON. Write runtime states AFTER
  `generate_config` by reading `feed_state_revisions`/`post_state_revisions` from the output.
- **Physical slots MAY be non-contiguous (user rule 2026-08-17, "row trống thì bỏ qua máy đó")**:
  a machine can hold accounts at rows 1,2,4 (row 3 empty from the reg workbook). The generator
  previously REJECTED gaps (`sorted(slots) != range(1, len+1)`) — relaxed to "unique + ≥1"
  (`physical slots are duplicated or invalid`). Runtime reads the account FRESH from the workbook
  each run (`select_feed_session_accounts(workbook, machines, row_index)` — index = position in the
  machine's row group INCLUDING empty rows), so row 3 → empty ⇒ machine skipped, row 4 → account runs.
  Empty-username rows now produce a `config_errors` row (skip machine) instead of silently running
  with no account.
- **Serial/live data traps when building the projection**: cells may carry a leading quote-prefix
  (`'lipsellczaw`) — strip `'`; some safe-workbook rows have a DATE in the serial column
  (`21/07/2026` — bad manual edit) — override serial from the canonical device map
  (`Tik1.xlsx` `Máy|device ID` per machine), never let a date through as a serial.
- **Picker lane gotcha (answer from code, not assumption)**: `lane_for_day` = A (rows 1-3) on even
  days, B (rows 4-6) on odd days; a machine needs ≥3 schedulable accounts IN TODAY'S LANE else the
  whole lane is `UNSCHEDULABLE_CAPACITY` (picker.py ~277). On 2026-08-17 (lane B) ZERO of 74 machines
  qualified because most machines only have accounts at rows 1-4 → manifest `entries: 0`. If the farm
  is lightly populated, a lane day can schedule nothing. User was asked to choose: relax picker to
  "≥1 acc in lane runs" vs keep strict-3 (decision PENDING 2026-08-17).
- **`env.json` must not linger in the repo during tests** — wrapper tests assert default-off; delete
  it (and any stray `.permit`) before `pytest test_hermes_cron_wrappers.py`.
