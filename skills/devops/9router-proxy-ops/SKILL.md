---
name: 9router-proxy-ops
description: Operate and debug the 9Router LLM proxy at localhost:20128.
version: 1.0.0
metadata:
  hermes:
    tags: [9router, llm-proxy, reasoning, commandcode, deepseek, windows]
---
# 9Router Proxy Ops

Ports: 9Router `:20128`; OmniRoute `:20129`. Keep accounts active; never auto-disable or mutate OAuth from screenshot/403. Reviewer routing: `references/reviewer-combo-and-pool-salvage.md`. References: topology `references/omniroute-process-topology-restart.md`; Cockpit `references/cockpit-gpm-oauth-preflight.md`; arch `references/cockpit-cliproxy-9router-architecture.md`; DB cleanup `references/omniroute-sqlite-database-bloat-cleanup.md`; logs `references/omniroute-dashboard-logs-inspection.md`; hidden quota `references/omniroute-provider-limits-hidden-quota-models.md`; reasoning `references/omniroute-gemini-reasoning-dynamic-architecture.md`; combo 503 `references/omniroute-combo-503-all-targets-skipped.md`; combos `references/omniroute-combo-strategies-and-cache-discipline.md`; 9Router Codex OAuth `references/9router-codex-oauth-gpm-graph-pipeline.md`; pool ops `references/9router-codex-pool-round-robin-proxy-ops.md`; salvage `references/phone-verified-account-salvage-and-tainted-proxy-rotation.md`. Sync `D:\Taadaa\AI-Tools\tools\<tool>\`.

## Cost / pricing (CommandCode)

**Billing:** 9router `usageHistory.cost` is a local estimate, not charged credits. Match rows in CommandCode Usage by timestamp/model/tokens. Fair A/B and cache/quota rules: `references/commandcode-billing-verification.md`. Full verified pricing, the Pro-vs-Flash 2.76× ratio, and the correct
A/B cost-measurement method are in `references/commandcode-pricing.md`.
Proxy-block/ban-risk, deal-4× reality, cache patterns, quota-burn diagnosis:
`references/commandcode-proxy-deal-cache.md`.

## Key paths (Windows)
| Thing | Path |
|---|---|
| Install | `C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\` |
| Data/auth | `C:\Users\Kibe\AppData\Roaming\9router\` (`db/data.sqlite`, `machine-id`, `jwt-secret`, `auth/cli-secret`) |
| Hermes config | `~/AppData/Local/hermes/config.yaml`: `model.provider: custom:9router`, `custom_providers[].name: 9router`, fallback `oc/deepseek-v4-flash-free` routed through it (gemini was removed from fallback 2026-08-07 — see reference) |
| Processes | `cli.js --tray --skip-update -p 20128` (tray) + `app/custom-server.js` (server) |

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
