# Đồng Bộ Combo OmniRoute (:20129) Lên Giao Diện Model Hermes

## Bối Cảnh
Khi tạo mới hoặc đổi tên combo trên OmniRoute (:20129) như `codex-terra`, `codex-luna`, `gpt-web-sol`, Hermes **sẽ không hiển thị** các combo này nếu chỉ sửa `config.yaml`.

Lý do:
- Provider `omni` được load từ plugin tại `C:/Users/Kibe/AppData/Local/hermes/plugins/model-providers/omni/__init__.py`.
- Lớp `OmniProfile` tắt live discovery (`fetch_models()` trả về `None`).
- Hermes chỉ đọc từ `fallback_models` (biến `FARM_MODELS` trong plugin) và ghi vào disk cache `C:/Users/Kibe/AppData/Local/hermes/provider_models_cache.json`.

---

## Quy Trình 4 Tầng Đồng Bộ Chuẩn

### Tầng 1: OmniRoute API / Dashboard (:20129)
- Đổi tên combo: `PATCH /api/combos/{id}` hoặc `PUT` với payload `{"name": "codex-terra"}`.
- Tạo combo mới: `POST /api/combos` (ví dụ `gpt-web-sol` clone từ `chatgpt-web-pool`).
- Quy chuẩn tên combo: Kebab-case (`codex-terra`, `codex-luna`, `gpt-web-sol`).

### Tầng 2: Plugin Provider Hermes (`omni/__init__.py`)
- File: `C:/Users/Kibe/AppData/Local/hermes/plugins/model-providers/omni/__init__.py`
- Bổ sung tên combo vào `FARM_MODELS`:
```python
FARM_MODELS: tuple[str, ...] = (
    "omni-worker",
    "omni-free",
    "ag-gemini-pool-3",
    "ag-claude",
    "ag-opus",
    "codex-terra",
    "codex-luna",
    "gpt-web-sol",
)
```

### Tầng 3: Hermes `config.yaml`
- File: `C:/Users/Kibe/AppData/Local/hermes/config.yaml`
- `model.aliases`: Khai báo cả dạng gạch nối, dạng có dấu cách và dạng rút gọn:
```yaml
model:
  aliases:
    codex-terra: custom:omni/codex-terra
    codex-luna: custom:omni/codex-luna
    gpt-web-sol: custom:omni/gpt-web-sol
    "codex terra": custom:omni/codex-terra
    "codex luna": custom:omni/codex-luna
    "gpt web sol": custom:omni/gpt-web-sol
    terra: custom:omni/codex-terra
    luna: custom:omni/codex-luna
```
- `providers.omni.models` & `custom_providers`: Bổ sung context_length.
- `agent.reasoning_overrides`: Ghim reasoning effort nếu cần.

### Tầng 4: Xóa Disk Cache Hermes & Nghiệm Thu
- Chạy `clear_provider_models_cache('omni')` để làm mới `provider_models_cache.json`.
- Kiểm tra `cached_provider_model_ids('omni', force_refresh=True)` và `list_picker_providers()`.
