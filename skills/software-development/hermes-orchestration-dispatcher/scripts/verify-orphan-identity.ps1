# Read-only verification: does the orphaned child pass Test-ExistingChildIdentity -AllowOrphanedParent?
# No side effects - only reads process/lease state.
# Usage: powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File verify-orphan-identity.ps1
# Edit $leasePath if the lease lives elsewhere.
$ErrorActionPreference = 'Stop'
$leasePath = 'D:\Taadaa\tiktok-luot nuoi acc\python_runner\runs\schedule-recovery-watch-lease.json'

function ConvertTo-ArgumentLiteral {
    param([Parameter(Mandatory = $true)][string]$Value)
    if ($Value -notmatch '[\s"]') { return $Value }
    return '"' + $Value.Replace('"', '\"') + '"'
}

function Get-ProcessCommandLine {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    try {
        return [string](Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop).CommandLine
    } catch {
        return $null
    }
}

function Test-CommandLineContains {
    param(
        [Parameter(Mandatory = $true)][string]$CommandLine,
        [Parameter(Mandatory = $true)][string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($CommandLine) -or [string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }
    return $CommandLine.IndexOf($Value, [StringComparison]::OrdinalIgnoreCase) -ge 0
}

function Test-CommandLineArgument {
    param(
        [Parameter(Mandatory = $true)][string]$CommandLine,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($CommandLine) -or
        [string]::IsNullOrWhiteSpace($Name) -or
        [string]::IsNullOrWhiteSpace($Value)) {
        return $false
    }
    $literal = ConvertTo-ArgumentLiteral -Value $Value
    $pattern = '(?i)(?<!\S)' + [regex]::Escape($Name) + '\s+' +
        [regex]::Escape($literal) + '(?=\s|$)'
    return $CommandLine -match $pattern
}

function Test-CommandLineFlag {
    param(
        [Parameter(Mandatory = $true)][string]$CommandLine,
        [Parameter(Mandatory = $true)][string]$Name
    )
    if ([string]::IsNullOrWhiteSpace($CommandLine) -or [string]::IsNullOrWhiteSpace($Name)) {
        return $false
    }
    $pattern = '(?i)(?<!\S)' + [regex]::Escape($Name) + '(?=\s|$)'
    return $CommandLine -match $pattern
}

$lease = Get-Content -Raw -LiteralPath $leasePath | ConvertFrom-Json
$leaseFullPath = [IO.Path]::GetFullPath($leasePath)
$binding = $lease.child_binding
$processId = [int]$lease.child_pid
$process = Get-Process -Id $processId -ErrorAction SilentlyContinue

Write-Host "lease_id: $($lease.lease_id)"
Write-Host "parent_pid: $($lease.pid)  alive: $([bool](Get-Process -Id ([int]$lease.pid) -ErrorAction SilentlyContinue))"
Write-Host "child_pid: $processId  alive: $([bool]$process)"
Write-Host "state: $($lease.state)"

if (-not $process) {
    Write-Host "RESULT: child not alive - not an orphan-child case (both dead)"
    exit 0
}

$identityChecks = [ordered]@{
    binding_fields_complete = $true
    child_process_alive = $true
    parent_dead_or_allow = $true
    start_time_match = $false
    executable_match = $false
    binding_match = $false
    commandline_match = $false
    ppid_ok = $false
}

foreach ($f in @('lease_id','worker_session_id','repo_root','parent_process_start_time','child_process_start_time','child_command_identity')) {
    if ([string]::IsNullOrWhiteSpace([string]$lease.$f)) { $identityChecks.binding_fields_complete = $false; Write-Host "MISSING lease field: $f" }
}
foreach ($f in @('schema','lease_id','worker_session_id','parent_process_start_time','child_process_start_time','command_identity','repository_root','repo_root','lease_path','module')) {
    if ([string]::IsNullOrWhiteSpace([string]$binding.$f)) { $identityChecks.binding_fields_complete = $false; Write-Host "MISSING binding field: $f" }
}
if ([int]$lease.parent_pid -le 0 -or [int]$binding.parent_pid -ne [int]$lease.pid) { $identityChecks.binding_fields_complete = $false }

if (Get-Process -Id ([int]$lease.pid) -ErrorAction SilentlyContinue) {
    $identityChecks.parent_dead_or_allow = $false
    Write-Host "PARENT ALIVE - would fail (fail-closed)"
}

try {
    $expectedStart = [DateTime]::Parse([string]$lease.child_process_start_time).ToUniversalTime()
    $actualStart = $process.StartTime.ToUniversalTime()
    $identityChecks.start_time_match = ($actualStart -eq $expectedStart)
    Write-Host "child start expected: $($expectedStart.ToString('o')) actual: $($actualStart.ToString('o')) match: $($identityChecks.start_time_match)"
} catch {
    Write-Host "start time parse error: $_"
}

$parentInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction Stop
$executablePath = [string]$parentInfo.ExecutablePath
$expectedExecutable = [IO.Path]::GetFullPath([string]$binding.command_identity)
$identityChecks.executable_match = (-not [string]::IsNullOrWhiteSpace($executablePath)) -and ([IO.Path]::GetFullPath($executablePath) -ieq $expectedExecutable)
Write-Host "executable: $executablePath vs expected $expectedExecutable match: $($identityChecks.executable_match)"

$commandLine = Get-ProcessCommandLine -ProcessId $processId
Write-Host "commandline: $($commandLine.Substring(0, [Math]::Min(180, $commandLine.Length)))"

$expectedChildCommand = [IO.Path]::GetFullPath([string]$lease.child_command_identity)
$expectedRepoRoot = [IO.Path]::GetFullPath([string]$lease.repo_root)
$bindingRepositoryRoot = [IO.Path]::GetFullPath([string]$binding.repository_root)
$bindingRepoRoot = [IO.Path]::GetFullPath([string]$binding.repo_root)
$expectedLeasePath = [IO.Path]::GetFullPath($leaseFullPath)
$bindingLeasePath = [IO.Path]::GetFullPath([string]$binding.lease_path)

$identityChecks.binding_match = [string]$binding.schema -eq 'tiktok-schedule-recovery-child-binding-v1' -and
    [string]$binding.lease_id -eq [string]$lease.lease_id -and
    [string]$binding.worker_session_id -eq [string]$lease.worker_session_id -and
    [int]$binding.parent_pid -eq [int]$lease.pid -and
    [int]$lease.parent_pid -eq [int]$lease.pid -and
    [string]$binding.parent_process_start_time -eq [string]$lease.parent_process_start_time -and
    [int]$binding.child_pid -eq [int]$lease.child_pid -and
    [string]$binding.child_process_start_time -eq [string]$lease.child_process_start_time -and
    $expectedExecutable -ieq $expectedChildCommand -and
    $bindingRepositoryRoot -ieq $bindingRepoRoot -and
    $bindingRepositoryRoot -ieq $expectedRepoRoot -and
    $bindingLeasePath -ieq $expectedLeasePath -and
    [string]$binding.module -eq 'scheduler.recovery_runtime'
Write-Host "binding_match: $($identityChecks.binding_match)"

$identityChecks.commandline_match = (Test-CommandLineArgument -CommandLine $commandLine -Name '-m' -Value 'scheduler.recovery_runtime') -and
    (Test-CommandLineArgument -CommandLine $commandLine -Name '--watch-lease' -Value $binding.lease_path) -and
    (Test-CommandLineArgument -CommandLine $commandLine -Name '--watch-lease-id' -Value $binding.lease_id) -and
    (Test-CommandLineArgument -CommandLine $commandLine -Name '--watch-parent-pid' -Value ([string][int]$binding.parent_pid)) -and
    (Test-CommandLineFlag -CommandLine $commandLine -Name '--watch') -and
    (Test-CommandLineContains -CommandLine $commandLine -Value $expectedRepoRoot)
Write-Host "commandline_match: $($identityChecks.commandline_match)"

$identityChecks.ppid_ok = ([int]$parentInfo.ParentProcessId -eq [int]$lease.pid)
Write-Host "ppid: $($parentInfo.ParentProcessId) expected $($lease.pid) ok: $($identityChecks.ppid_ok)"

$final = $identityChecks.Values -notcontains $false
Write-Host "FINAL Test-ExistingChildIdentity -AllowOrphanedParent => $final"
exit 0
