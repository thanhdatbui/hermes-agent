# PowerShell 7 Pitfalls in the Command Code Audit Wrapper (and PS7-requiring scripts)

Verified 2026-08-04 while extending `D:\Taadaa\tools\invoke-command-code-9router-audit.ps1`
with `-ReasoningEffort` for the deepseek fallback. Two pre-existing crashes
made the wrapper fail on EVERY invocation via `-File` — worth knowing for any
PS7 script that calls functions with `-Text`-style params and has a default
empty-string string param.

## Pitfall 1 — `-or` inside a function call binds as ONE argument

```powershell
# BROKEN — PS7 sees TWO values for -Text:
if (Test-SensitiveText -Text $Prompt -or Test-SensitiveText -Text $ContextText) {
```
Fails with:
```
Cannot bind parameter because parameter 'Text' is specified more than once.
```
Root cause: PowerShell does not treat `-or` as an argument separator inside a
command invocation; it collects `-Text $Prompt -or Test-SensitiveText -Text
$ContextText` as multiple values for the single `-Text` parameter. This is NOT
a syntax error caught by the parser — it only blows up at runtime when the
function is actually called.

**Fix** — split into separate statements:
```powershell
$sensitivePrompt = Test-SensitiveText -Text $Prompt
$sensitiveContext = $false
if (-not [string]::IsNullOrEmpty($ContextText)) {
    $sensitiveContext = Test-SensitiveText -Text $ContextText
}
if ($sensitivePrompt -or $sensitiveContext) { ... }
```

## Pitfall 2 — Mandatory param rejects empty-string default

```powershell
function Test-SensitiveText {
    param([Parameter(Mandatory = $true)][string]$Text)
}
# ...
Test-SensitiveText -Text $ContextText   # $ContextText defaults to ''
```
Fails with:
```
Cannot bind argument to parameter 'Text' because it is an empty string.
```
Root cause: `[Parameter(Mandatory=$true)]` + `[string]` rejects `''` (it is
not `[AllowEmptyString()]`). Any caller passing an empty default string
crashes the whole script.

**Fix** — guard the call: only invoke when non-empty, or add
`[AllowEmptyString()]` to the param.

## Pitfall 3 — `#requires -Version 7.0` + `powershell.exe` (PS5.1)

- `powershell.exe` on Windows is ALWAYS Windows PowerShell 5.1
  (`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`). It rejects
  any script with `#requires -Version 7.0`:
  `ScriptRequiresUnmatchedPSVersion`.
- After the codex error-1920 PATH fix (prepending `~/.codex/shell` with a
  PS5.1 `pwsh.exe`), even `pwsh` in PATH resolves to PS5.1 — so a
  `#requires -Version 7.0` script fails via `pwsh` too.
- **Fix**: invoke PS7-requiring wrappers by absolute store path
  `C:\Program Files\WindowsApps\Microsoft.PowerShell_<ver>_x64__8wekyb3d8bbwe\pwsh.exe`
  (PS7 installs on Windows are MSIX store apps). Fall back to bare `pwsh`
  only when that path does not exist. Discover with:
  ```bash
  ls -la "/c/Users/<user>/AppData/Local/Microsoft/WindowsApps/pwsh.exe"   # symlink → real store path
  where pwsh
  ```

## Wrapper-specific notes (Taadaa)

- The wrapper only writes audit artifacts INSIDE the workspace (guards
  `-ArtifactPath` with `Test-WithinRoot`); a temp path outside `D:\Taadaa` is
  silently ignored and the artifact falls back to
  `D:\Taadaa\.codex\audit\command-code-audit-*.json`. When testing, read the
  artifact path from the console JSON output (`"artifact": "..."`) rather than
  assuming your `-ArtifactPath` was honored.
- Console JSON deliberately omits `reasoning_effort`/`model` — those live in
  the artifact file. Verify effort by reading the artifact, not the console.
