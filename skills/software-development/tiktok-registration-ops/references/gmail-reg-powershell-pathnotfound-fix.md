# Gmail Reg — PowerShell PathNotFound (Get-Content) Fix

## Symptom
Phase 1 (Reg Gmail) alert shows:
```
FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
```
`run_night_chain_pipeline.py` captures PS1 stdout+stderr as one string. This PS1 error leaks into
`gmail_out`, causes `parse_summary_line()` to surface it as the Phase 1 detail, and triggers a
misleading alert. Exit code 1 is **separately** caused by `$fail -gt 0` at the end of
`run_parallel.ps1` (line 848) — the PathNotFound is noise in the output, not the primary failure.

## Root Cause — `Remove-OwnedQueuedLock` in `run_parallel.ps1` (line 163)

```powershell
# DANGEROUS — no Test-Path guard, no ErrorAction protection
$owner = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
```

Called during lock cleanup. A competing process may delete the lock file **between** the
`Try-ReserveQueuedLock` race and this cleanup call → `PathNotFound` non-terminating error leaks to
stderr.

## Fix — `D:/Taadaa/register gmail/run_parallel.ps1` line 162-163

```powershell
# BEFORE:
$owner = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json

# AFTER (add Test-Path guard + silent fallback):
if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
$owner = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json
```

## Secondary Guard — `Get-ReadOnlyDeviceLockProbe` (line 127)

Already inside `try/catch` so the `ErrorAction Stop` is caught. This is safe as-is. No change
needed unless race condition rate is high enough to justify adding a pre-loop `Test-Path`.

## Other Get-Content calls in run_parallel.ps1

| Line | Location | Guard | Safe? |
|------|----------|-------|-------|
| 127 | `Get-ReadOnlyDeviceLockProbe` | `try/catch + ErrorAction Stop` | ✓ |
| 163 | `Remove-OwnedQueuedLock` | **NONE** | ✗ → fix here |
| 210 | `Try-ReserveQueuedLock` | `try {} catch {}` | ✓ |
| 270 | `Get-RunResultFromLog` | `try + Test-Path` | ✓ |

## How Python captures the error

`run_gmail_batch()` in `run_night_chain_pipeline.py` uses:
```python
proc = subprocess.run(cmd, capture_output=True, text=True, ...)
output = proc.stdout + "\n" + proc.stderr
```
Both streams are merged into `output`. Even non-terminating PS1 errors (printed to stderr) get
included here and appear in `parse_summary_line()` / alert detail.

## Important: exit_code=1 vs PathNotFound

The exit code 1 from Phase 1 is **not caused** by the PathNotFound error. It comes from:
```powershell
# run_parallel.ps1 line 847-849
if ($fail -gt 0) {
    exit 1
}
```
The PathNotFound is a concurrent artifact that pollutes the output. Fix the lock-file race
condition to clean up alert messages; fix the actual machine failures separately.

## Verification (no live run)

```powershell
# Syntax-check only — safe, no execution:
powershell -NoProfile -NonInteractive -Command `
  "& { . 'D:/Taadaa/register gmail/run_parallel.ps1' }"
```
Running the dot-source path hits the early-exit guard at line 364-366:
```powershell
if ($MyInvocation.InvocationName -eq '.') {
    return
}
```
So it loads functions and returns without launching any machines.
