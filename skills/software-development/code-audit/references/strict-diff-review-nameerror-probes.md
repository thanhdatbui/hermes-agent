# Strict Diff Review — NameError Probes, Wheel-Pin Checks, Lease-API Contracts

Worked case: 2026-08-18, strict pre-commit security+logic review of `git diff`
across 4 Taadaa repos (`register gmail`, `Tiktok_Reg`, `add mail khoi phuc`,
`automation-core`), JSON-verdict output only. The diff passed `ast.parse` on
every file yet contained three guaranteed runtime NameErrors, a broken wheel
pin, a leaked device lock, and a retry-determinism regression.

## 1. Scope: what counts as "the diff"

- Per repo: `git status --short` + `git diff --stat` in parallel.
- Review tracked `.py` diffs AND read new untracked `.py` files that ship the
  next run (`_run_all_targets.py`, `_detect_clean.py`, launchers). Untracked
  ≠ out of scope; they are the next batch's entrypoints.
- Ignore AGENTS.md / PROJECT_RULES.md / docs churn (auto-rule-file noise).
- `ast.parse` every changed file — floor, not gate.

## 2. AST undefined-name probe (the big win)

`ast.parse` OK does NOT mean no crash. A cleanup block copied from a different
module referenced three names that don't exist in scope:

```python
# run_add_recovery.py:3282-3287 (add mail khoi phuc)
if _wait_until_google_account_absent(device, account):
    log(f"   [device-clean] Close recent apps, return Home on {serial}")  # serial undefined
    adb_shell(serial, "input", "keyevent", "3")                            # adb_shell undefined
    adb_shell(serial, "input", "keyevent", "187")
    time.sleep(0.5)
    adb_shell(serial, "input", "tap", "540", "1600")
    adb_shell(serial, "input", "keyevent", "3")
    return {"status": "REMOVED_AND_VERIFIED", "account": target_account,  # target_account undefined
            "matched_account": matched_account}
```

The module only defines `shell(device, *args)` — no `adb_shell`, no module-level
`serial`, no `target_account` (only the parameter `account`). The success path
crashes with NameError exactly when the account was removed and bookkeeping
should complete — the worst possible place to crash.

Probe pattern:

```python
import ast
src = open("run_add_recovery.py", encoding="utf-8-sig").read()   # BOM! utf-8 alone raises at line 1
tree = ast.parse(src)
mod_names = set()
for node in tree.body:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
            if isinstance(t, ast.Name):
                mod_names.add(t.id)
    elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        mod_names.add(node.name)
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "TARGET":
        defined = {a.arg for a in node.args.args}
        used = {n.id for sub in ast.walk(node) for n in [sub] if isinstance(sub, ast.Name)}
        print(sorted(n for n in (used - defined) if n in SUSPECTS))
```

Confirm no `global` statements and no module-level assigns before declaring a
name undefined. Also verify the *correct* helper exists (`def shell(` at
line 361) so the fix is "use `shell(device, ...)` and `account`".

### Pitfalls
- **BOM:** `open(f, encoding="utf-8")` on these files → `SyntaxError: invalid
  non-printable character U+FEFF`. Use `utf-8-sig`.
- **`search_files` cannot read these repos** — `D:\...` / `/d/...` paths fail
  with "IO error: The system cannot find the path specified" (MSYS path
  conversion breaks native rg). Use `cd '/d/Taadaa/...' && grep ...` in
  terminal instead.
- **Hardcoded `(540, 1600)` recents-clear tap** — resolution-dependent; the
  repo already has `close_all_recent_apps` in automation-core that does this
  properly. Flag raw coordinate taps that replicate a library function.

## 3. Wheel-pin vs source symbol verification

Consumers import new automation-core APIs. Three-way check:

1. **Source check** — `grep -n "def <symbol>" automation-core/src/...` (the
   dev copy on `sys.path`).
2. **Pinned-wheel check** — extract the EXACT wheel named in
   `requirements-automation-core.txt` to a temp dir and probe symbols:
   ```bash
   RUNTIME=/d/Taadaa/Hotmail/.ai-runs/runtime-core-0.4.24/Lib/site-packages/automation_core
   grep -c "def close_all_recent_apps" "$RUNTIME/startup.py"     # present in 0.4.24
   grep -c "def resolve_proxy_mapping_path" "$RUNTIME/preflight.py"  # ABSENT in 0.4.24
   ```
   Found: `close_all_recent_apps` OK in 0.4.24, but
   `resolve_proxy_mapping_path` and the `content insert` rotation lock are NOT
   — the gmail script imports the former and the startup.py diff adds the
   latter. The consumer crashes under the pinned env.
3. **Pin-existence check** — `ls dist/`: the pin referenced
   `automation_core-0.4.24-py3-none-any.whl` but dist/ only had 0.4.36–0.4.45.
   Fresh env install fails outright. Fix: bump pin to an existing wheel and
   verify it contains the needed symbols (`unzip -l` / `unzip -p`).

Also check the installed interpreter, not bare `python` — bare `python` on the
farm resolves the system site-packages (stale copy) while the venv
(`D:\Taadaa\python-envs\automation\Scripts\python.exe`) has the real
editable install. Probe `automation_core.__file__` first.

## 4. Class-method API contract (silent no-op leases)

New code called `lease.finish(...)` on `DeviceLockLease`:

```python
if hasattr(lease, "finish"):        # False — no such method
    lease.finish(succeeded=..., failure_status="blocked")
elif hasattr(lease, "set_status"):  # runs only for non-success targets
    lease.set_status("blocked" ...)
```

`device_lock.py` only defines `set_status` / `release`. For SUCCESS targets
neither branch runs → the lock is never released → stale lock files block the
next batch run (machines reported "locked" when actually free). **A
`hasattr`-guarded call to a method that doesn't exist is a silent no-op** —
verify the class's real method list first:
`awk '/class DeviceLockLease/,/^class [^D]/' device_lock.py | grep "def "`.

## 5. Behavior invariants to spot-check (recurring in this codebase)

- **Random-salt username generation breaks retry determinism.** `build_username`
  now appends `random.choices(...)` per call; `acc["id"]` is set once per acc
  so a single run is stable, but a re-run for the same STT regenerates a
  different username than the one Gmail already consumed → duplicate/ghost
  account on resume. Retry must read the pending username from result dir.
- **Destructive `pm clear` + `am force-stop` with no pre-state evidence.**
  `launch_gmail_home` now `pm clear`s Gmail (logs out ALL Google accounts on
  the device) and force-stops GMS. A failed run silently wipes previously
  registered accounts; no `dumpsys account` baseline, screenshot, or rollback.
- **Jitter minimums vs small elements.** `_jitter` min offset raised ±4-6 →
  ±8-20; controls <16px wide (checkboxes, radio dots) get missed taps. Clamp
  to `min(±20, element_w/3)`.
- **Loosened substring classifiers.** `_is_home_feed_xml` now accepts bare
  `"live"`, `"tim kiem"`, `"hop thu"`, `"thich"` — these appear in login,
  signup, and settings nav bars everywhere → false-positive home-feed
  detection misroutes the flow. Require `trang chu` + feed-specific markers.
- **Positional workbook reads.** New proxy-dedup block reads `r[1]`/`r[2]`
  positionally while `serial_is_mapped_in_workbook` is header-driven. Column
  order drift silently misreads; use the header-driven lookup.
- **`None` password propagation.** `password_filled` flag gates whether
  `try_login_fallback_from_registration` receives a password; `None` flows
  into `fill_password_and_login` which compares `visible_value != password`
  and may log false mismatches. Guard at the boundary.

## 6. Verdict contract

- `passed: false` unless BOTH `security_concerns` and `logic_errors` are empty
  (fail-closed, matching requesting-code-review's rule).
- Blockers: guaranteed crashes (NameError on a success path), broken wheel
  pins, leaked locks. Everything else → suggestions.
- Summary: one paragraph, name the blocker and the fix order, don't enumerate
  every suggestion again.
