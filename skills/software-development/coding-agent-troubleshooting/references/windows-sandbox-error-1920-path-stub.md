# Error 1920: WindowsApps pwsh Store Stub vs PATH — Full Diagnostic (2026-08-04)

## Symptom

Every `codex exec --sandbox ...` fails regardless of model, with:
```
exec error: windows sandbox: runner failed during SpawnChild:
  CreateProcessAsUserW failed: 1920 (The file cannot be accessed by the system.)
  cmd=C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\pwsh.exe
```
Plain text replies still work; only shell exec breaks. This hits gpt-5.6-luna
AND the 9Router deepseek fallback equally.

## Root Cause Chain

1. `C:\Users\<user>\AppData\Local\Microsoft\WindowsApps\pwsh.exe` is a
   **Microsoft Store stub** — `ls -la` shows a symlink (~300KB) pointing into
   `C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.4.0_x64__...\pwsh.exe`.
2. Sandbox spawns processes under a restricted token; `CreateProcessAsUserW`
   cannot start a Store-packaged app → error 1920.
3. Codex resolves `pwsh.exe` from PATH. On this machine the WindowsApps entry
   (`/c/Users/<user>/AppData/Local/Microsoft/WindowsApps`) sorts BEFORE
   `~/.codex/shell`, so codex picks the stub even though a working
   PowerShell 5.1 copy exists at `~/.codex/shell/pwsh.exe`.

## The Existing `~/.codex/shell/pwsh.exe`

- 455KB, `file` reports `PE32+ executable for MS Windows 10.00 (console)`,
  PowerShell 5.1 (`$PSVersionTable` = 5.1.19041.6456).
- DIFFERENT file from the WindowsApps store binary (byte 61 differs).
- `which -a pwsh` shows BOTH: `/c/Users/<user>/AppData/Local/Microsoft/WindowsApps/pwsh`
  (first) and `/c/Users/<user>/.codex/shell/pwsh` (second) → the stub wins.

## Fix (Verified Working)

Per-command (immediate):
```bash
PATH="/c/Users/<user>/.codex/shell:$PATH" codex exec -m <model> --sandbox workspace-write "run shell: echo OK"
```
Result: codex spawns `C:\Users\<user>\.codex\shell\pwsh.exe`, exec succeeds
(`OK`), for both gpt-5.6-luna and deepseek-v4-flash.

Persistent: prepend `~/.codex/shell` to User PATH so it beats the machine-wide
WindowsApps entry, or reorder the entries.

## Verification After Fix

Sandbox log line must show the wrapper, not the store stub:
```bash
grep "START:" ~/.codex/.sandbox/sandbox.$(date +%Y-%m-%d).log
# GOOD:  START: C:\Users\...\.codex\shell\pwsh.exe
# BAD:   START: C:\Users\...\WindowsApps\pwsh.exe
```

## Key Diagnostic Moves That Found This

- `where pwsh` / `which -a pwsh` → reveals BOTH candidates and their order.
- `file ~/.codex/shell/pwsh.exe` vs `file <WindowsApps path>` → proves they
  are different binaries (455KB real vs ~300KB store stub symlink).
- `ls -la` on the WindowsApps path → shows the symlink target into
  `C:\Program Files\WindowsApps\Microsoft.PowerShell_...`.
- Comparing error log `cmd=` path vs which-order → the stub is what codex spawns.
- Confirming the SAME error on gpt-5.6-luna (main route) → it is an environment
  bug, not a deepseek/9Router problem.

## Note

The old documented fix (`cp System32 powershell.exe ~/.codex/shell/pwsh.exe`
+ `SetEnvironmentVariable PATH User ...`) only creates the wrapper — it does
NOT guarantee PATH precedence. The PATH-order fix is the missing half; without
it the store stub still wins and 1920 persists.
