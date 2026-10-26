# Auto-Wiring, Active Pivot & Farm Gate Compliance Invariants (2026-10-26)

## 1. Context & Root Cause Analysis (6H Compliance Audit)
Periodic audit via `gate_compliance_watchdog.py` identified top operational interception bottlenecks:
1. `[Worker Dispatch] subagent_edit_blocked`: `delegate_task` invoked for code editing instead of `dispatch_worker.py`.
2. `[Worker Dispatch] investigate`: `delegate_task` missing required `BUDGET: <= 8 calls` syntax.
3. `[Anti-Scan Terminal] GUARD_SEARCH_FILES_ROOT` & `GUARD_DANGEROUS_ROOT`: calling `search_files` or recursive scripts on root `D:/Taadaa` or `D:/Taadaa/tools`.
4. `[Anti-Scan Terminal] GUARD_DEVICE_LOCK_REQUIRED`: invoking adb commands without JIT device lock.
5. `[Cronjob Window] CONSOLE_WINDOW`: spawning Windows subprocesses without `CREATE_NO_WINDOW (0x08000000)`.

---

## 2. Decision Boundary: Auto-Wiring vs Active Pivot (Claude CLI Consensus)

> **Core Invariant:** An interception may ONLY be auto-wired (mutated in-flight) if the transform is lossless, idempotent, and strictly preserves authorization, executor, Tier, and scope. Otherwise, fail-fast with a pre-filled, copy-pasteable `REQUIRED_ACTION_O1` (Active Pivot).

1. **Investigate Route (`delegate_task`): Auto-Wiring**
   - Safe to auto-inject `BUDGET: <= 8 calls` for read-only / investigation goals.
   - Tag with `AUTO_INJECTED_DEFAULT` in telemetry.
   - **Never** auto-inject for write/edit tasks where budget reflects a Tier determination.
2. **Subprocess Console Windows: Auto-Wiring**
   - On Windows (`sys.platform == 'win32'`), subprocesses popping CMD windows disrupt operator foreground activity.
   - Inject `creationflags |= 0x08000000` (`subprocess.CREATE_NO_WINDOW`).
   - Must OR-merge flags; never overwrite caller flags; skip if `CREATE_NEW_CONSOLE` or `DETACHED_PROCESS` was explicitly passed.
3. **Code-Edit via `delegate_task`: Active Pivot (Not Auto-Rewire)**
   - Do NOT silently rewrite `delegate_task` into `dispatch_worker.py` because `dispatch_worker` requires contract verification (Context Pack, anchor check, Tier assignment, canary gate).
   - Gate MUST return a pre-filled, executable CLI command:
     `python D:/Taadaa/tools/dispatch_worker.py --workdir <repo> --file <target> "<prompt>"`
4. **Root Disk Scans: Active Pivot (Not Auto-Narrow)**
   - Do NOT auto-narrow paths (e.g. `D:/Taadaa` -> `D:/Taadaa/tools`). Guessing scope risks returning silently incomplete results and violates Scope Lock.
   - Fail-fast with pre-filled allowlisted subfolder or machine log path (`D:/Taadaa/tools/<file>` or `D:/Taadaa/runtime/admin/live/...`).
5. **Device Lock Required: Active Pivot (Not Auto-Acquire)**
   - Do NOT auto-acquire locks. Device locks are strictly bound to `host + pid + lock_id`. Auto-acquiring from an arbitrary process causes lock leaks and races.
   - Fail-fast with exact JIT lock command: `python D:/Taadaa/tools/inspect_machine.py <N>` or `with_device_lock.py --machine <N> -- <cmd>`.

---

## 3. Compliance Telemetry & Unit Test Artifact Pollution
- Up to 70% of reported blocks in rolling compliance reports can originate from unit test suites testing gate rejections (e.g. `Review then apply constant change`, `grep -rn foo D:/Taadaa`, `count_active_locks`).
- Watchdogs (`gate_compliance_watchdog.py`) must maintain comprehensive test artifact exclusion filters to prevent false alarm fatigue while accurately monitoring live production health.
