# Codex audit fallback: 60818 (Codex API Service) down → route qua 9router

## Symptom
`codex exec --ephemeral --sandbox read-only --model gpt-5.6-sol < prompt.md` fail lặp lại:
```
ERROR: Reconnecting... 1/5 ... 5/5
ERROR: stream disconnected before completion: error sending request for url (http://localhost:60818/v1/responses)
```
2 lần retry cùng lỗi = không phải transient.

## Phân biệt 2 cổng (đừng nhầm)
- **60818 = "Codex API Service"** — provider `codex_local_access` trong `~/.codex/config.toml`
  (`base_url = "http://localhost:60818/v1"`, `experimental_bearer_token=...`, wire_api=responses).
  Service nền của codex CLI, KHÔNG watchdog, chết là chết — retry vô ích.
- **20128 = 9Router** — provider `9router` (`base_url = "http://localhost:20128/v1"`, env
  `NINEROUTER_API_KEY`). Watchdog: `C:\Users\Kibe\AppData\Roaming\9router\9router_watchdog.ps1`
  (powershell hidden, mutex `Local\9Router_Supervisor_Mutex_v2`, kiểm tra port mỗi 5s + tự
  restart node server.js). 9router KHÔNG phụ thuộc service codex.

## Verify
```bash
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 60818 -ErrorAction SilentlyContinue | Select-Object OwningProcess,State | Format-Table -AutoSize"
# rỗng = service 60818 chết → chuyển route
curl -s -m 8 http://localhost:20128/v1/models   # 20128 còn sống (có thể cần Bearer NINEROUTER_API_KEY)
```

## Fallback audit (chạy được ngay khi 60818 chết)
```bash
codex exec --ephemeral --sandbox read-only --model-provider 9router --model gpt-5.6-sol < prompt.md > transcript.txt 2>&1
```
Cùng model `gpt-5.6-sol`, chỉ đổi provider. Model list trên 9router (verify 16/08): gpt-5.6-luna,
gpt-5.6-sol, gpt-5.6-terra, deepseek-v4-flash/pro, opencode-free, opencode-audit,
gemini-3.6-flash-high, claude-sonnet-4-6, worker, plan-review, plan-review-hard, freemodel/*.

## Codex CLI trap (tốn 2 lần thử)
`codex exec -p "chuỗi dài"` → `error: invalid value ... for '--profile <CONFIG_PROFILE_V2>'`
vì `-p` = `--profile`, KHÔNG phải `--prompt`. Prompt dài: `< prompt.md` stdin redirect (đã dùng
ổn định cho prompt >30KB), hoặc positional arg `codex exec "prompt"`.

## Lưu ý khi audit prompt
- Prompt file nên < 8K tokens (stream timeout nếu quá lớn — chia nhỏ).
- Verdict dòng cuối = APPROVED/REJECT + findings `1. P1 — path:line — mô tả`.
