# Tool Config Sync Rule

## Rule
Mọi config, script, watchdog và startup launcher liên quan đến AI tools (OmniRoute, 9Router, Hermes Gateway, startup) BẮT BUỘC lưu và đồng bộ vào repo:
**`D:\OneDrive\AI-Tools\tools\`**

## What this covers
- `9router/quota_manager.py`
- `9router/9router.vbs` / `9router_watchdog.ps1`
- `hermes-gateway/Hermes_Gateway.cmd` / `Hermes_Gateway.vbs`
- `omniroute/*`
- `startup/*`
- `cliproxy/*`
- `factory-cursor-bridge/*`
- `v98-audit-vscode/*`

## Workflow
1. Edit file in `D:\OneDrive\AI-Tools\tools\<tool>\`
2. Test locally
3. Commit to repo
4. Deploy to other machines via `hermes deployment` if needed

## Pitfall: Config Drift
Never edit Hermes config directly in `C:\Users\Kibe\AppData\Local\hermes\config.yaml` without syncing back to `D:\OneDrive\AI-Tools\tools\` first. The repo is the source of truth.