# Universal Hooks & Multi-Host Zero-Rewrite Architecture (Kibe ↔ Admin)

## 1. Problem Statement & Anti-Pattern (Regex Runtime Patching)
In earlier multi-machine deployments:
- `config.yaml` hardcoded local user paths: `python C:/Users/Kibe/AppData/Local/hermes/hooks/...`.
- `sync-from-kibe.ps1` and `apply_sync_admin.py` relied on string replacement / regex passes to substitute `C:/Users/Kibe` with `C:/Users/Admin` and `127.0.0.1` with `192.168.110.123`.
- Hook internal state files (`circuit_breaker.json`, `progress_supervisor_state.json`) hardcoded `C:/Users/Kibe`.

**Failure Mode:**
- Any update to `config.yaml` on Kibe risked breaking Admin if regex match patterns drifted or failed.
- Tools called on Admin crashed with `File not found` whenever hooks referenced non-existent paths.
- Running scripts across different elevation levels or different Windows usernames caused hard runtime crashes.

---

## 2. Canonical Solution: Universal Machine-Agnostic Architecture

### Rule 1: Canonical Hook Location at Shared Drive
Move all executable hooks to a machine-agnostic path present on all farm nodes:
`D:/Taadaa/tools/hooks/`
Because `D:\OneDrive\Taadaa_Sync_Shared\tools` is linked via NTFS Junction to `D:\Taadaa\tools`, any change committed on Kibe is immediately visible on Admin via OneDrive sync.

### Rule 2: Self-Aware Dynamic Paths in Hook Code
Hook Python scripts must never hardcode user directories. Use environment-aware runtime resolution:
```python
import os
from pathlib import Path

HERMES_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "hermes"
CACHE_DIR = HERMES_DIR / "cache"
RUNTIME_DIR = HERMES_DIR / "runtime"
```

### Rule 3: Universal LAN IP for Proxies
Both OmniRoute (:20129) and 9Router (:20128) listen on LAN interfaces (`0.0.0.0`). Kibe connects to its own LAN IP (`http://192.168.110.123:20129/v1`) with 100% parity to `127.0.0.1`.
By standardizing `config.yaml` on `192.168.110.123`:
- Both Kibe and Admin use an **identical 1:1 `config.yaml`**.
- No regex substitution is needed during deployment or synchronization.

### Rule 4: Zero-Rewrite Synchronization
`sync-from-kibe.ps1` and `apply_sync_admin.py` become pure synchronization utilities:
1. Pull / copy canonical `config.yaml` directly without regex transformation.
2. Preserve only the machine-specific `.env` (`TELEGRAM_BOT_TOKEN`).

---

## 3. Implementation in Sync Utilities

### `sync-from-kibe.ps1` (Admin PC Pull Script)
No regex substitution is needed for localhost or hooks path. The config sync section is simplified to a direct copy:
```powershell
Write-Host "== 3. ĐỒNG BỘ CONFIG VÀ SCRIPTS ==" -ForegroundColor Cyan
$CfgSrc = Join-Path $RepoDir "deploy\hermes-home\config.yaml"
$CfgDst = Join-Path $HermesHome "config.yaml"
if (Test-Path $CfgSrc) {
    Copy-Item $CfgSrc -Destination $CfgDst -Force
}
```

### `apply_sync_admin.py` (OneDrive Shared Sync Script)
Directly copies the canonical `config.yaml` without parsing or rewriting hooks dictionaries:
```python
# 4. Cập nhật config.yaml
print("[4/4] Đang cập nhật config.yaml...")
shared_config_file = shared_sync_dir / "config.yaml"
if shared_config_file.exists():
    shutil.copy2(shared_config_file, config_path)
    print("-> Đã copy config.yaml thành công!")
```

---

## 4. Verification Check
Verify that no legacy user paths exist across any deployment config:
```bash
python -c "import yaml; [print(f, 'chua hook cu') for f in ['C:/Users/Kibe/AppData/Local/hermes/config.yaml', 'D:/Taadaa/Hermes/deploy/hermes-home/config.yaml', 'D:/OneDrive/Taadaa_Sync_Shared/hermes-sync/config.yaml'] if 'C:/Users/Kibe/AppData/Local/hermes/hooks' in open(f, encoding='utf-8').read()]"
```
Output should be completely empty.
