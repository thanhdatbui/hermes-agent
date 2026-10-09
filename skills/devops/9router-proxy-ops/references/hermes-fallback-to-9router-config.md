# Hermes Fallback → 9Router: Config Pattern & Verified State

**Verified:** 2026-10-07 (session: LLM infra deep-dive)

---

## Architecture: Cockpit Tools vs CLIProxy vs 9Router

### Cockpit Tools (`cockpit-tools.exe`, port 60818)
- **Là GUI wrapper** cho CLIProxy binary (`cockpit-cliproxy.exe` nhúng sẵn trong thư mục cài đặt).
- Port `:60818` (`codex_local_access`) **CHỈ** expose pool Codex/ChatGPT accounts — **KHÔNG** route Antigravity/Gemini ra ngoài.
- Tab "Antigravity" trong GUI chỉ dùng nội bộ (inject token vào Antigravity IDE app), **KHÔNG phải API gateway**.
- Gọi model `gemini-*` vào port `:60818` → **HTTP 404** (đúng hành vi, không phải bug).
- Dòng model hoạt động: `gpt-5.6-luna` (7 acc Hotmail FREE, ~437% quota còn lại).
- Dòng model không hoạt động qua 60818: `gpt-5.6-sol`, Gemini, Claude.

### CLIProxy độc lập (LuisPater, `cli-proxy-api.exe` v7.2.66)
- Tool riêng biệt với Cockpit, Go binary, mã nguồn mở.
- Hỗ trợ OAuth: `-antigravity-login`, `-claude-login`, `-codex-login`, `-kimi-login`, `-xai-login`.
- Trên máy: cài qua WinGet, có 1 auth file: `dokieu04092004@gmail.com` (Antigravity, token hết hạn từ 7/2026).
- **Đang TẮT** (không listen port nào). Không dùng được cho fallback.

### 9Router (`:20128`) — Warm Standby tốt nhất
- Có **7 acc Antigravity OAuth đang ACTIVE** (`isActive=1`):
  - `thanhdatbui19951@gmail.com` (PRO, Claude 96%/Gemini 99%)
  - `jinrakal@gmail.com` (PRO, Claude 100%/Gemini 100%)
  - `marcusephillips52sns@gmail.com`
  - `dinhlan24072000@gmail.com`
  - `toloan12091999@gmail.com`
  - `minhan2745@gmail.com`
  - `dokieu04092004@gmail.com`
- Combo `gpt-5.6-sol`: `["cx/gpt-5.6-sol", "ag/claude-opus-4-6-thinking"]`
  - `cx/` (Codex) **chết** trên 9Router → auto-fallback vào `ag/claude-opus-4-6-thinking`. **Đây là behavior đúng.**
  - 9Router không có chatgpt-web pool 93 acc như OmniRoute — tài sản riêng, không sync được.
- Test thực tế (HTTP 200 thành công): `gemini-3.7-flash-high`, `claude-sonnet-4-6`, `ag/gemini-3.8-flash-tiered`, `gpt-5.6-sol` (via AG Claude Opus).
- requestDetails DB xác nhận acc được dùng: `thanhdatbui19951@gmail.com` provider `antigravity` → `success`.

---

## Hermes Fallback Config — Cách Đúng

### Pitfall: `hermes config set fallback_providers` với list syntax bị lưu dạng string thô

```bash
# SAI — bị parse thành string, không phải list YAML:
hermes config set "fallback_providers" "[{model: omni-worker, provider: '9router'}]"
# → fallback_providers trở thành string "[{model: omni..." thay vì list

# SAI — indexed syntax không được nhận dạng:
hermes config set "fallback_providers[0].model" "omni-worker"
# → warning "not a recognized config key"
```

### Cách đúng — dict syntax (single fallback):
```bash
hermes config set "fallback_providers.model" "omni-worker"
hermes config set "fallback_providers.provider" "9router"
```

Kết quả YAML sau khi set:
```yaml
fallback_providers:
  model: omni-worker
  provider: 9router
```

Hermes đọc được dict này đúng cách. Verify bằng:
```python
import yaml
with open('C:/Users/Kibe/AppData/Local/hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
fb = cfg.get('fallback_providers')
assert isinstance(fb, dict), f"Expected dict, got {type(fb)}: {fb}"
assert fb['model'] == 'omni-worker'
assert fb['provider'] == '9router'
```

### Fix model mapping `omni-worker` trên 9Router

`omni-worker` trong 9Router không có pool Gemini riêng như OmniRoute. Cần map sang `gemini-3.7-flash-high` (AG pool đang sống):

```bash
hermes config set "providers.9router.default_model" "gemini-3.7-flash-high"
hermes config set "providers.9router.models.omni-worker" "{}"
hermes config set "providers.9router.models.omni-worker.model_id" "gemini-3.7-flash-high"
```

Kết quả trong config.yaml:
```yaml
providers:
  9router:
    api: http://192.168.110.123:20128/v1
    default_model: gemini-3.7-flash-high
    key_env: NINEROUTER_API_KEY
    discover_models: false
    transport: chat_completions
    models:
      omni-worker:
        model_id: gemini-3.7-flash-high
      gemini-3.7-flash-high: {}
      gpt-5.6-sol: {}
      gpt-5.6-luna: {}
      gpt-5.6-terra: {}
      claude-sonnet-4-6: {}
      9r-free: {}
```

---

## Summary: Tier Architecture Của Dàn LLM

```
Hermes Agent
    │
    ├── PRIMARY:  OmniRoute :20129 (Node.js PID 115736)
    │             └── Pools: ag-gemini-pool-3 (Gemini 3.8, 87 PRO acc)
    │                        gpt-web-sol (93 Hotmail acc, ChatGPT web)
    │                        codex-luna (97 acc Codex)
    │                        ag-opus-pool (78 Google acc, Claude Opus)
    │
    └── FALLBACK: 9Router :20128 (Node.js standalone)
                  └── Pools: 7 Antigravity OAuth acc (PRO, active)
                             → omni-worker → gemini-3.7-flash-high (AG)
                             → gpt-5.6-sol  → ag/claude-opus-4-6-thinking (AG)

Cockpit Tools :60818 (sidecar, không phải fallback cho Hermes)
    └── Pool: 7 Hotmail FREE acc (Codex)
              → chỉ gpt-5.6-luna, không có Gemini/Sol
```
