# Windows Sandbox Error Signatures — Real Examples

## Symptom: `program not found`

```
[2026-07-27 09:22:46.019 codex.exe] setup refresh: spawning codex-windows-sandbox-setup.exe
[2026-07-27 09:22:46.025 codex.exe] setup refresh: setup refresh failed to launch helper:
  helper=codex-windows-sandbox-setup.exe, cwd=D:\Taadaa\gan-proxy, error=program not found
```

No full path → codex can't find the binary. Happens when sandbox binaries are missing from the
directory next to `codex.exe`.

## Symptom: `unsupported protocol version 4`

```
exec error: windows sandbox: runner failed during ReadSpawnRequest:
  runner: unsupported protocol version 4
```

Sandbox binaries (from 0.146 alpha) speak protocol v4, but codex.exe (0.144.1) expects v3.
Mismatched versions after auto-update.

## Symptom: `CreateProcessAsUserW failed: 1920`

```
exec error: windows sandbox: runner failed during SpawnChild:
  CreateProcessAsUserW failed: 1920 (The file cannot be accessed by the system.)
  cmd=C:\Users\Kibe\AppData\Local\Microsoft\WindowsApps\pwsh.exe
```

Sandbox process runs under a restricted token that cannot access WindowsApps paths.
Fix: create `pwsh.exe` wrapper from System32 PowerShell.

## Symptom: `CreateProcessWithLogonW failed: 2`

```
exec error: windows sandbox: CreateProcessWithLogonW failed: 2
```

Error code 2 = file not found. `codex-command-runner.exe` is missing from the directory
next to `codex.exe`. Copy from runtime's `codex-resources/`.

## Working Log Pattern (After Fix)

```
[2026-07-27 10:24:31.323 codex.exe] helper copy: validating command-runner
  source=C:\Users\Kibe\AppData\Local\Programs\OpenAI\Codex\bin\codex-command-runner.exe
  destination=C:\Users\Kibe\.codex\.sandbox-bin\codex-command-runner-0.144.1.exe
[2026-07-27 10:24:31.330 codex.exe] helper launch resolution: using copied command-runner path
[2026-07-27T03:24:31.339] read-acl-only mode: applying read ACLs
[2026-07-27T03:24:31.363] read ACL run completed
```

## Successful Exec (With Wrapper Fix)

```
exec "C:\Users\Kibe\.codex\shell\pwsh.exe" -Command 'echo test'
  succeeded in 970ms: test
```

Codex found our `pwsh.exe` wrapper from `~/.codex/shell/` (in PATH before WindowsApps).

## Diagnostic: Multiple Installations Detected

From `codex doctor`:
```
PATH entries (2)
  C:\Users\Kibe\AppData\Local\Programs\OpenAI\Codex\bin\codex.exe       ← v0.145.0 in PATH
  C:\Users\Kibe\AppData\Local\OpenAI\Codex\bin\69066b736e1e17a4\codex.exe  ← v0.146 alpha (stale)
```

And on disk:
```
C:/Users/Kibe/.codex/packages/standalone/releases/
  0.142.5-x86_64-pc-windows-msvc/
  0.144.1-x86_64-pc-windows-msvc/
  0.145.0-x86_64-pc-windows-msvc/     ← current runtime
```

Only `0.145.0` is active; older releases can be pruned.

## Timeline: How This Typically Happens

1. Microsoft Store Codex installed → sandbox at `C:\Program Files\WindowsApps\OpenAI.Codex_*/`
2. User installs CLI version separately → new executable in `Programs\OpenAI\Codex\bin\`
3. Auto-update creates new runtime at `AppData\Local\OpenAI\Codex\bin/<hash>/`
4. Microsoft Store version uninstalled or updated → sandbox binaries disappear
5. Codex can no longer find `codex-windows-sandbox-setup.exe` → exec broken
6. MCP node_repl still works (separate runtime), masking the issue
