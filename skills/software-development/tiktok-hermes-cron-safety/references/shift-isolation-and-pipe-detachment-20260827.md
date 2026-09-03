# Shift Isolation, Pipe Detachment & Process Termination Safety (2026-08-27)

## 1. Shift Isolation & Stale Lease Termination
- **The Problem:** When an earlier shift batch (e.g. Ca chiều / Phiên 3) hangs in coordinator post-processing or worker joins, its PID remains recorded in `runner-live-lease/<day>.json`. If subsequent cron ticks only check `_lease_alive` passively, all future shifts (e.g. Ca tối / Row 1) will be blocked indefinitely by `already running — skipping` or lease no-ops.
- **The Invariant:**
  1. When a new shift / cohort plan is detected (`existing_lease.get("cohort_id") != plan.cohort_id`), `_spawn_live` MUST proactively kill all recorded stale PIDs (`taskkill /F /T /PID` on Windows) and unlink the stale lease file.
  2. In `_lease_alive`, if `started_at` exceeds 5400s (90 minutes) or `expires_at < now`, terminate the recorded PIDs before unlinking the lease and returning `False`.
  3. Every new shift must run strictly on its scheduled clock without depending on prior shifts cleanly exiting.

## 2. Windows Process Liveness & Non-Destructive Probing
- **The `os.kill(pid, 0)` Pitfall:** Calling `os.kill(pid, 0)` on Windows actually invokes `TerminateProcess` or raises WinError 87 `SystemError: <class 'OSError'> returned a result with an exception set`. It is NOT safe for passive liveness probing.
- **The Invariant:**
  Use Win32 ctypes `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)` + `GetExitCodeProcess(handle, byref(exit_code))` where `exit_code.value == STILL_ACTIVE (259)`.
  ```python
  def _is_pid_alive(pid: int) -> bool | None:
      """Return True if alive, False if confirmed dead, or None if inaccessible/unknown."""
      if not isinstance(pid, int) or pid <= 0 or pid > 4194304 or isinstance(pid, bool):
          return False
      if sys.platform == "win32":
          try:
              import ctypes
              from ctypes import wintypes
              PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
              STILL_ACTIVE = 259
              kernel32 = ctypes.windll.kernel32
              kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
              kernel32.OpenProcess.restype = wintypes.HANDLE
              kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
              kernel32.GetExitCodeProcess.restype = wintypes.BOOL
              kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
              kernel32.CloseHandle.restype = wintypes.BOOL

              handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
              if not handle:
                  err = kernel32.GetLastError()
                  if err == 87:  # ERROR_INVALID_PARAMETER (dead)
                      return False
                  return None
              try:
                  exit_code = wintypes.DWORD()
                  if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                      return exit_code.value == STILL_ACTIVE
                  return None
              finally:
                  kernel32.CloseHandle(handle)
          except Exception:
              return None
      else:
          try:
              os.kill(pid, 0)
              return True
          except PermissionError:
              return None
          except ProcessLookupError:
              return False
          except (OSError, SystemError, OverflowError):
              return None
  ```

## 3. Windows PID Reuse Prevention & Process Handle Hold Pattern
- **The Race:** If a stale PID is probed, verified, and then killed in separate uncoordinated calls, the process could terminate and its PID get reassigned to an unrelated system/user process before `taskkill` runs.
- **The Invariant:**
  1. Acquire an open process handle `OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)` BEFORE validating command-line.
  2. Require handle acquisition to succeed (fail closed if `h == 0`).
  3. Validate process command-line while holding the open handle.
  4. Terminate the process tree: Invoke `taskkill /F /T /PID <pid>` FIRST to clean descendant workers, then call `TerminateProcess(h, 1)`.
  5. Close all held handles in a `finally` block after termination confirmation.

## 4. Strict Command-Line & Cohort-Binding Validation
- **PowerShell Validation Invariants:**
  - Reject all command execution switches (`-c`, `-command`, `-cwa`, `-enc`, `-encodedcommand`, etc.) before the `-File` switch.
  - Require exactly ONE `-File` (or `-f`) switch in argv.
  - Verify script target is `run-feed-session.ps1`.
  - Validate that `expected_cohort_id` is present as the exact argument to `-CohortArtifact <path>`.
- **Python Validation Invariants:**
  - Reject attached or clustered execution options (`-c`, `-m`, `-C`, `-M`, e.g. `-cCMD`, `-mMOD`, `-xcCMD`).
  - Skip non-script interpreter options (`-W`, `-X <arg>`).
  - Verify script operand is `run_tiktok.py`.
  - Verify `--mode multi-machine-feed-session` is located strictly in the `script_args` slice after `run_tiktok.py` (preventing interpreter option values like `-X --mode=...` from spoofing mode).

## 5. Cron Runner Subprocess Pipe Detachment (`subprocess.Popen`)
- **The Problem:** When `tiktok_runner.py` spawns PowerShell batches (`scripts/run-feed-session.ps1`), if `stdin/stdout/stderr` are inherited or not fully detached, the parent Python wrapper process remains tied to the child's I/O handle. Hermes Gateway scheduler sees the cron script tick as still running, causing `Job '...' already running — skipping` on every subsequent interval.
- **The Invariant:**
  ```python
  creationflags = 0x00000208 if sys.platform == "win32" else 0  # CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
  proc = subprocess.Popen(
      argv,
      cwd=str(repo),
      env=child_env,
      stdin=subprocess.DEVNULL,
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      close_fds=True,
      creationflags=creationflags,
  )
  ```

## 6. PowerShell Parameter Path Formatting (`.as_posix()`)
- **The Problem:** Passing native Windows backslash paths (e.g. `D:\Taadaa\...`) through `subprocess.Popen` to PowerShell parameters can cause PowerShell's argument tokenizer or `[System.IO.Path]::IsPathRooted` to fail with `Illegal characters in path` (due to escaped whitespace / control chars like `\r`, `\t`).
- **The Invariant:**
  Always normalize paths passed to PowerShell parameters via `Path(...).as_posix()` (e.g. `D:/Taadaa/...`).
  ```python
  "-AccountWorkbook", Path(workbook).as_posix() if workbook else "",
  "-AssignmentManifest", Path(assignment_manifest).as_posix(),
  "-CohortArtifact", (Path(env["HERMES_CRON_STATE_ROOT"]) / "cohorts" / day / f"{plan.cohort_id}.json").as_posix(),
  "-ArtifactRoot", (artifact_root / f"row-{row}-{now.strftime('%H%M%S')}").as_posix(),
  "-Python", python_exe.replace("\\", "/"),
  ```

## 7. Assignment Manifest Root Schema & Symlink Safety
- Assignment manifests define `assignment_id`, `day`, `entries`, `blocks`, `constraints` at the root level.
- `block_index` and `session_index` are properties of individual blocks, entries, or cohort plans — NOT root-level keys of the assignment manifest. Root schema checks in `_apply_cohort_identity` must only enforce `("assignment_id", "day", "entries")`.
- Dangling symlinks: `Path.exists()` returns `False` for dangling symlinks. Check `os.path.islink(str(path))` explicitly in `_is_symlink_or_irregular` to ensure dangling symlinks fail closed.
