# D:\Taadaa\Hermes\deploy\sync-from-kibe.ps1
param(
    [string]$KibeIP = "192.168.110.123"
)
$ErrorActionPreference = 'Stop'
$RepoDir = "D:\Taadaa\Hermes"
$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"

Write-Host "== 1. KÉO REPO MỚI NHẤT TỪ GITHUB ==" -ForegroundColor Cyan
git -C $RepoDir pull --rebase fork main

Write-Host "== 2. ĐỒNG BỘ SKILLS ==" -ForegroundColor Cyan
$SyncSkills = Join-Path $RepoDir "deploy\sync-skills.ps1"
if (Test-Path $SyncSkills) {
    & $SyncSkills -RepoRoot $RepoDir -Force
}

Write-Host "== 3. ĐỒNG BỘ CONFIG VÀ SCRIPTS ==" -ForegroundColor Cyan
$CfgSrc = Join-Path $RepoDir "deploy\hermes-home\config.yaml"
$CfgDst = Join-Path $HermesHome "config.yaml"
if (Test-Path $CfgSrc) {
    Copy-Item $CfgSrc -Destination $CfgDst -Force
    # Thay 127.0.0.1 thành IP Kibe để Admin kết nối qua mạng LAN
    $cfgContent = Get-Content $CfgDst -Raw -Encoding utf8
    $cfgContent = $cfgContent -replace "127\.0\.0\.1", $KibeIP
    Set-Content -Path $CfgDst -Value $cfgContent -Encoding utf8
}

$ScriptsSrc = Join-Path $RepoDir "deploy\hermes-home\scripts"
$ScriptsDst = Join-Path $HermesHome "scripts"
if (Test-Path $ScriptsSrc) {
    New-Item -ItemType Directory -Force -Path $ScriptsDst | Out-Null
    Copy-Item "$ScriptsSrc\*" -Destination $ScriptsDst -Recurse -Force
}

$CronSrc = Join-Path $RepoDir "deploy\hermes-home\cron\jobs.json"
$CronDst = Join-Path $HermesHome "cron\jobs.json"
if (Test-Path $CronSrc) {
    New-Item -ItemType Directory -Force -Path (Join-Path $HermesHome "cron") | Out-Null
    if (-not (Test-Path $CronDst)) {
        Copy-Item $CronSrc -Destination $CronDst -Force
    }
}

$PluginsSrc = Join-Path $RepoDir "deploy\hermes-home\plugins"
$PluginsDst = Join-Path $HermesHome "plugins"
if (Test-Path $PluginsSrc) {
    New-Item -ItemType Directory -Force -Path $PluginsDst | Out-Null
    Copy-Item "$PluginsSrc\*" -Destination $PluginsDst -Recurse -Force
}

Write-Host "== 4. CẬP NHẬT .ENV (BẢO TỒN BOT TOKEN ADMIN) ==" -ForegroundColor Cyan
$envFile = Join-Path $HermesHome ".env"
$envContent = if (Test-Path $envFile) { Get-Content $envFile -Raw -Encoding utf8 } else { "" }
$settings = @(
    "HERMES_TELEGRAM_HTTP_POOL_SIZE=1024",
    "HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30.0",
    "HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=15.0",
    "HERMES_TELEGRAM_HTTP_READ_TIMEOUT=30.0",
    "HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=30.0",
    "TELEGRAM_ALLOW_BOTS=all",
    "TELEGRAM_PROXY=http://admin%401:admin%401@192.168.110.2:10001",
    ("OMNIROUTE_BASE_URL=http://" + $KibeIP + ":20129/v1")
)
foreach ($line in $settings) {
    $k = $line.Split("=")[0]
    if ($envContent -match ("(?m)^" + [regex]::Escape($k) + "=")) {
        $envContent = [regex]::Replace($envContent, ("(?m)^" + [regex]::Escape($k) + "=.*$"), $line)
    } else {
        $envContent += [Environment]::NewLine + $line
    }
}
Set-Content -Path $envFile -Value $envContent.Trim() -Encoding utf8

$RestartDst = Join-Path $HermesHome "scripts/restart-when-idle.ps1"

Write-Host "== 5. KÍCH HOẠT WATCHER TỰ RESTART KHI IDLE ==" -ForegroundColor Cyan
if (Test-Path $RestartDst) {
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$RestartDst`"" -WindowStyle Hidden
}

Write-Host "== HOÀN TẤT ĐỒNG BỘ TỪ KIBE! ==" -ForegroundColor Green
& hermes config check
