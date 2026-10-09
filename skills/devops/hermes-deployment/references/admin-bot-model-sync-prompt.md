# Secondary Machine Hermes Model, Gateway & Proxy Sync Recipe

When configuring a secondary Hermes instance (e.g. Admin PC) where Hermes is **already installed and operating with its own Telegram Bot Token**, to match the primary host's (Kibe PC) LLM routing, Telegram pool settings, Viettel proxy, and skills 100%:

---

## Invariant Rules for Multi-Host Hermes Sync

1. **Bot Token Isolation (Strict Rule):**
   - Each host MUST maintain its own unique `TELEGRAM_BOT_TOKEN` in `%LOCALAPPDATA%\hermes\.env`.
   - NEVER copy or overwrite `TELEGRAM_BOT_TOKEN` from Kibe to Admin. Two running instances using the same bot token cause immediate polling conflicts: `Conflict: terminated by other getUpdates request`.
2. **Shared LLM Routing (100% Match):**
   - Model default: `ag-gemini-pool-3` (provider `omni`).
   - OmniRoute endpoint: `http://192.168.110.123:20129/v1`.
   - 9Router endpoint: `http://192.168.110.123:20128/v1` (for `gpt-5.6-luna`, compression fallback, and code review).
   - Fallback chain: `9r-free` (via `custom:9router`) — loại bỏ `omni-free` để tránh dead-end fallback khi OmniRoute sập.
   - Multi-tier subagent delegation: `ag-gemini-pool-3` (OmniRoute) with `max_concurrent_children: 4`, `max_iterations: 100`.
3. **Telegram Network & Pool Resilience (Anti-Stall):**
   - Egress Proxy: `TELEGRAM_PROXY=http://admin%401:admin%401@192.168.110.2:10001` (Viettel line via MikroTik; bypasses FPT DNS failures & packet drops).
   - Pool limits: `HERMES_TELEGRAM_HTTP_POOL_SIZE=1024` and `HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30.0` (prevents `Pool timeout` during multi-agent concurrent turns/image bursts).
   - Heartbeat & Timeouts: Connect 15.0s, Read 30.0s, Write 30.0s.
4. **Git Repository vs. Runtime State Separation:**
   - Git repository `D:\Taadaa\Hermes` holds the canonical source, skills, and deploy templates (`deploy/hermes-home/`).
   - Runtime `%LOCALAPPDATA%\hermes` holds active machine state (`state.db`, active `.env`, `gateway_state.json`).
   - Sync workflow: Kibe pushes to `fork main` -> Admin pulls `fork main` -> copies template `config.yaml` to runtime -> runs `sync-skills.ps1` -> restarts Gateway when idle via `restart-when-idle.ps1`.

---

## 1-Click Self-Configuration Prompt (Send to Admin Telegram Bot or Paste in Admin PowerShell)

Copy and run this self-contained script on the Admin machine (via Admin bot prompt or Admin PowerShell window):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "
$HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$RepoRoot = 'D:\Taadaa\Hermes'
$KibeIP = '192.168.110.123'

Write-Host '== DANG DONG BO HERMES ADMIN THEO CHUAN KIBE ==' -ForegroundColor Cyan

# 1. Keo ban moi nhat tu Git Repo
if (Test-Path $RepoRoot) {
    Write-Host 'Kéo Git pull từ repo D:\Taadaa\Hermes...' -ForegroundColor Yellow
    git -C $RepoRoot fetch fork main
    git -C $RepoRoot pull --rebase fork main
}

# 2. Dong bo config.yaml tu deploy bundle
$srcConfig = Join-Path $RepoRoot 'deploy\hermes-home\config.yaml'
$dstConfig = Join-Path $HermesHome 'config.yaml'
if (Test-Path $srcConfig) {
    Write-Host 'Dong bo config.yaml...' -ForegroundColor Yellow
    Copy-Item -LiteralPath $srcConfig -Destination $dstConfig -Force
    # Thay 127.0.0.1 thanh IP Kibe cho OmniRoute va 9Router
    $cfgContent = Get-Content $dstConfig -Raw -Encoding utf8
    $cfgContent = $cfgContent -replace '127\.0\.0\.1:20129', ($KibeIP + ':20129')
    $cfgContent = $cfgContent -replace '127\.0\.0\.1:20128', ($KibeIP + ':20128')
    Set-Content -Path $dstConfig -Value $cfgContent -Encoding utf8
}

# 2.1 Cau hinh vision va compression ro rang tranh loi provider=auto
& hermes config set auxiliary.vision.provider omni
& hermes config set auxiliary.vision.model omni-worker
& hermes config set auxiliary.compression.provider omni
& hermes config set auxiliary.compression.model ag-gemini-pool-3

# 3. Dong bo script restart-when-idle.ps1
$srcRestart = Join-Path $RepoRoot 'deploy\hermes-home\scripts\restart-when-idle.ps1'
$dstRestart = Join-Path $HermesHome 'scripts\restart-when-idle.ps1'
if (Test-Path $srcRestart) {
    Write-Host 'Dong bo restart-when-idle.ps1...' -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path (Split-Path $dstRestart) | Out-Null
    Copy-Item -LiteralPath $srcRestart -Destination $dstRestart -Force
}

# 4. Dong bo skills
$syncSkillsScript = Join-Path $RepoRoot 'deploy\sync-skills.ps1'
if (Test-Path $syncSkillsScript) {
    Write-Host 'Dong bo Skills tu repo vao runtime...' -ForegroundColor Yellow
    & $syncSkillsScript -RepoRoot $RepoRoot
}

# 5. Cap nhat .env (Giu nguyen TELEGRAM_BOT_TOKEN rieng cua Admin, chi them/sua pool & proxy & endpoint LAN)
$envFile = Join-Path $HermesHome '.env'
if (Test-Path $envFile) {
    Write-Host 'Cap nhat .env an toan (bao ton bot token)...' -ForegroundColor Yellow
    $envContent = Get-Content $envFile -Raw -Encoding utf8
    $updates = @(
        'HERMES_TELEGRAM_HTTP_POOL_SIZE=1024',
        'HERMES_TELEGRAM_HTTP_POOL_TIMEOUT=30.0',
        'HERMES_TELEGRAM_HTTP_CONNECT_TIMEOUT=15.0',
        'HERMES_TELEGRAM_HTTP_READ_TIMEOUT=30.0',
        'HERMES_TELEGRAM_HTTP_WRITE_TIMEOUT=30.0',
        'TELEGRAM_ALLOW_BOTS=all',
        'TELEGRAM_PROXY=http://admin%401:admin%401@192.168.110.2:10001',
        ('OMNIROUTE_BASE_URL=http://' + $KibeIP + ':20129/v1'),
        'OMNIROUTE_API_KEY=sk-068...237c',
        'NINEROUTER_API_KEY=sk-247...708b'
    )
    foreach ($line in $updates) {
        $k = $line.Split('=')[0]
        if ($envContent -match ('(?m)^' + [regex]::Escape($k) + '=')) {
            $envContent = [regex]::Replace($envContent, ('(?m)^' + [regex]::Escape($k) + '=.*$'), $line)
        } else {
            $envContent += [Environment]::NewLine + $line
        }
    }
    Set-Content -Path $envFile -Value $envContent.Trim() -Encoding utf8
}

# 6. Khoi chay One-Shot Watcher de restart Gateway an toan khi idle (nap bien .env moi)
Write-Host 'Kich hoat One-Shot Idle Watcher...' -ForegroundColor Yellow
Start-Process powershell.exe -ArgumentList \"-NoProfile -ExecutionPolicy Bypass -File $dstRestart\" -WindowStyle Hidden

Write-Host '== DONG BO HOAN TAT 100%! ==' -ForegroundColor Green
"
```

---

## Continuous Sync Workflow (Mỗi lần Kibe sửa config thì làm gì?)

Khi máy Kibe sửa cấu hình (`config.yaml`), script hoặc skills:

1. **Phía Kibe:**
   - Cập nhật file mẫu trong repo:
     - `copy C:\Users\Kibe\AppData\Local\hermes\config.yaml D:\Taadaa\Hermes\deploy\hermes-home\config.yaml`
   - Commit và push lên GitHub:
     ```bash
     git -C "D:\Taadaa\Hermes" add deploy/hermes-home/config.yaml skills/
     git -C "D:\Taadaa\Hermes" commit -m "chore(deploy): sync updated config and skills"
     git -C "D:\Taadaa\Hermes" push fork main
     ```

2. **Phía Admin:**
   - **Tự động theo Cron (không cần thao tác):** Cron job `sync-hermes-skills-to-git` trên Admin chạy mỗi 30 phút tự động kéo `fork main` về.
   - **Hoặc yêu cầu tức thì qua chat Telegram Bot Admin:**
     Gửi tin nhắn cho Bot Admin:
     `Hãy kéo git pull D:\Taadaa\Hermes fork main, copy deploy/hermes-home/config.yaml vào AppData/Local/hermes/config.yaml và chạy restart-when-idle.ps1.`

---

## Critical Pitfall: Omni Provider Plugin Hardcoded to 127.0.0.1 (2026-09-11)

**Problem:** The Omni provider plugin (`deploy/hermes-home/plugins/model-providers/omni/__init__.py`) originally committed in `186e2dc5d` hardcoded:
```python
base_url="http://127.0.0.1:20129/v1"
env_vars=("OMNIROUTE_API_KEY",)  # Missing OMNIROUTE_BASE_URL!
```
When `sync-from-kibe.ps1` copied this plugin to Admin, it overrode Admin's provider config to point to **Admin's own localhost (127.0.0.1)** instead of Kibe's LAN IP. Result: All model calls on Admin failed with "Provider unreachable" → fallback also failed → bot completely broken.

**Root Cause:** 
1. `env_vars` omitted `"OMNIROUTE_BASE_URL"` → Hermes runtime provider resolution couldn't map the environment variable.
2. `base_url` was hardcoded to `127.0.0.1:20129` → remote hosts without local OmniRoute instance got connection refused.

**Fix applied (commits f06449819, 0a773410f, 8924a8cb0):**
- Updated both `deploy/hermes-home/plugins/model-providers/omni/__init__.py` AND local runtime plugin `%LOCALAPPDATA%/hermes/plugins/model-providers/omni/__init__.py`:
  ```python
  import os
  ...
  env_vars=("OMNIROUTE_API_KEY", "OMNIROUTE_BASE_URL"),
  base_url=os.getenv("OMNIROUTE_BASE_URL", "http://192.168.110.123:20129/v1").rstrip("/"),
  fallback_models=FARM_MODELS,
  ```
- Updated deploy template `config.yaml` and Kibe's runtime `config.yaml` to use `192.168.110.123` (Kibe static LAN IP) instead of `127.0.0.1` for all endpoints.
- Updated `.env` on Kibe: `OMNIROUTE_BASE_URL=http://192.168.110.123:20129/v1`
- Sync script already generates correct `OMNIROUTE_BASE_URL` from `$KibeIP`.

**Lesson:** NEVER hardcode `127.0.0.1` in deploy templates that get synced to other machines. Always use `os.getenv()` with LAN IP fallback, and include the corresponding `_BASE_URL` in `env_vars`.