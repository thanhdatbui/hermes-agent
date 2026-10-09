# Hermes /model Picker — Canonical `omni` Live-Discovery Bypass (2026-09-11)

## Hiện tượng
Telegram `/model` hiện `OmniRoute (1241)` / `Provider: OmniRoute (1-8 of 50)` với
hàng loạt `auto/*`, `no-think/*`, `openrouter/*`, `oc/*`, `aihorde/*`... dù
`config.yaml` đã set `discover_models: false` và `providers.omni.models` chỉ có
5 model farm (`omni-worker`, `omni-free`, `ag-gemini-pool-3`, `ag-claude`, `ag-opus`).

## Root cause chain (đã verify live)
1. Picker gọi `list_picker_providers(current_provider='omni')` trong
   `hermes_cli/model_switch.py` → nhánh 2b canonical provider.
2. Nhánh này gọi `cached_provider_model_ids('omni')` →
   `provider_model_ids('omni')` → generic live fetch qua
   `providers` profile `OmniProfile.fetch_models()` tới
   `http://127.0.0.1:20129/v1/models`.
3. OmniRoute `/v1/models` (catalog.ts) gom toàn bộ catalog:
   openrouter ~514 + opencode/oc ~207 + aihorde ~165 + dva + no-auth... = ~1240.
4. `discover_models: false` trong config KHÔNG được nhánh canonical kiểm tra —
   live fetch vẫn chạy, cache 1h vào `provider_models_cache.json`.

## Fix chuẩn (scope lock 1 file)
File DUY NHẤT: `~/.hermes/plugins/model-providers/omni/__init__.py`
- Set `fallback_models=("omni-worker","omni-free","ag-gemini-pool-3","ag-claude","ag-opus")`
- Override `fetch_models()` → `return None` để chặn live discovery.
- Xóa cache `provider_models_cache.json` (key `omni`) rồi verify.

## Verify
```python
from hermes_cli.models import cached_provider_model_ids
print(len(cached_provider_model_ids('omni')))  # phải ra 5
from hermes_cli.config import load_config, get_compatible_custom_providers
from hermes_cli.model_switch import list_picker_providers
cfg = load_config()
provs = list_picker_providers(current_provider='omni',
    user_providers=cfg.get('providers'),
    custom_providers=get_compatible_custom_providers(cfg))
print([(p['slug'], p['total_models']) for p in provs if p['slug']=='omni'])
# expect [('omni', 5)]
```

## Kỷ luật chẩn đoán
- Khi user chụp ảnh picker có `Provider (N)` số lớn, CẤM kết luận "bình thường"
  chỉ từ `GET /v1/models` count. BẮT BUỘC trace `list_picker_providers` path
  và `cached_provider_model_ids(<slug>)` trước khi trả lời.
- CẤM sửa `hermes-agent/venv`, `runtime-sync-package-backups`, hay OmniRoute
  `catalog.ts`. Scope lock đúng 1 file plugin trên.
