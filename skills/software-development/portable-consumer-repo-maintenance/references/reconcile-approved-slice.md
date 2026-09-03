# Reconcile an Approved Implementation Slice from a Dirty Tree

## Trigger

The user asks to "reconcile and finish", "continue", or "complete only Tasks X/Y/Z"
of an implementation that a prior worker left **partially done inside an already
dirty worktree**. The authorization is a strict contract: an allowlist of files,
a narrow scope (e.g. "Tasks 5–7 only"), and hard prohibitions (no git
reset/clean/stash/checkout/revert, no touching unrelated files, no
commit/push/deploy/live/ADB/network/Telegram/credentials, SOURCE_ONLY — no UI
or contract changes).

This is distinct from a from-scratch build and from config-drift portability:
the work already exists; the job is to **audit it against real source and prove
it green**, not to write it fresh.

## Guardrails (treat as the contract, not suggestions)

- **Continue from the current dirty tree.** Never `git reset`/`clean`/`stash`/
  `checkout`/`revert` or rewrite unrelated changes. `git status --short` must
  show only the allowlisted files as your delta.
- **Allowlist-only edits.** Touch ONLY the files the approval named (e.g.
  `device_prepare.py` + its test + a fixture). Do NOT edit scheduler/runtime/
  supervisor/watcher/PowerShell/Core files even if adjacent.
- **SOURCE_ONLY.** Reuse existing typed-handler seams. Do NOT invent new
  `ArtifactManager`/`adb` methods, do NOT add blind `input tap`/selector
  presses. A recovery path must call the existing typed dismiss handler, not
  synthesize a tap.
- **Fail-closed by construction.** No retry loop, no Home press, no state reset
  inside the recovery fn. Success is returned ONLY when (handler dismissed) AND
  (fresh post-action recapture obtained) AND (correct foreground package after
  recapture). Every other path returns `None` → original failure stands.
- **No deploy/live/network.** No commit, push, ADB device action, Telegram, or
  credential use.

## Reconciliation recipe

1. **Locate the real worktree with terminal git (search_files can't reach D:).**
   `search_files`/ripgrep fail on the MSYS `/d/...` mount on this host, so use
   the terminal:
   ```
   cd '/d/Taadaa/tiktok-luot nuoi acc-implementation' && pwd && \
     git status --short --branch && git log --oneline -3
   ```
   Pick the worktree whose branch/status matches the approval; never patch an
   installed package or similarly named copy.

2. **Read the ACTUAL function body + its real dependencies.** Do not trust
   comments/self-reports that a seam "exists". Grep the *real* module for the
   symbol and verify the return shape with the terminal (search_files can't see
   D:):
   ```
   grep -rn "def save_text\|def save_bytes\|def exec_out\|def capture_ui_xml" \
     D:/Taadaa/automation-core-implementation/src/automation_core
   ```
   Confirm the shapes the recovery fn relies on:
   - `ctx.artifacts.save_text(step, filename, content) -> Path` and
     `save_bytes(...)` — real `ArtifactManager` methods.
   - `ctx.adb.exec_out([...], timeout=, check=) -> AdbBytesResult` whose
     `.stdout` is **bytes** (screencap PNG), not a string.
   - `capture_ui_xml(adb, timeout=) -> CaptureResult` with `.xml: str | None`.
   - `get_focused_activity(ctx) -> {"package": str|None, "activity": str|None}`.
   A wrong shape assumption here would invent a contract — verify before
   asserting the implementation is correct.

3. **Confirm the route is wired + gates are fail-closed.** The recovery fn must
   be called BEFORE the original failure path returns (e.g. inside
   `if not core_result.ok:` in the app-prepare step). Grep/inspect for: no
   `for ... in range` retry loop in the recovery fn; no `keyevent`/`monkey`/
   `force_stop`/`home` calls (docstring mentions don't count — grep the code
   body). Success attaches to verified recapture + foreground, never to a
   changed screenshot alone.

4. **Prove green against REAL source with the exact venv.** The consumer imports
   `automation_core` from the implementation src, so set `PYTHONPATH` and run
   with the hermes-agent venv python (a bare `python` resolves to a stale
   site-packages copy):
   ```
   cd '/d/Taadaa/tiktok-luot nuoi acc-implementation'
   export PYTHONPATH=D:/Taadaa/automation-core-implementation/src
   C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
     -m pytest "python_runner/tests/test_device_prepare.py" -q
   C:/Users/Kibe/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
     -m pytest "python_runner/tests/test_device_prepare.py::PackageInstallerRecoveryTests" \
               "python_runner/tests/test_device_prepare.py::PackageInstallerSuccessSemanticsTests" \
               "python_runner/tests/test_device_prepare.py::PackageInstallerBoundedRetryTests" -v
   ```
   Suites are `unittest.TestCase` — node IDs need `file.py::ClassName::method`
   (NOT `::test_name`, which reports "not found").

5. **Report real evidence, separated.** State exact counts: e.g. "35 passed
   (full file)" and "12 passed (focused PackageInstaller classes: 4+4+4)". Show
   `git status --short` proving only allowlisted files changed; confirm the
   fixture exists and is valid XML. State explicitly that no commit/push/reset
   occurred.

## Pitfalls

- **search_files / ripgrep cannot resolve `/d/` on this host** — use terminal
  `find`/`grep` or a venv-python line scan. Don't loop on the failing tool.
- **A prior worker's self-report ("impl done") is never completion proof.**
  Re-read current bytes and run the real tests.
- **Don't trust comment claims about seams** — verify the real return shape
  (`exec_out`→bytes `.stdout`; `capture_ui_xml`→`CaptureResult.xml`;
  `get_focused_activity`→dict). Inventing a contract here is the main failure
  mode.
- **Run tests with the hermes-agent venv + `PYTHONPATH` to automation-core
  src.** Without it the import silently resolves to a stale copy and can
  false-PASS or false-FAIL.
- **Keep success contingent on verified recapture + correct foreground**, not on
  "the tap happened" or "the screenshot bytes changed". Encode that in the
  tests (assert `packageinstaller_recovered` only when handler-true + recapture
  clean + TikTok foreground; assert `recapture_mock` NOT called when handler is
  false).
