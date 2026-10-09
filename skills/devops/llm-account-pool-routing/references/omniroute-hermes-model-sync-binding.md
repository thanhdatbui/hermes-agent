# Đồng Bộ Combo OmniRoute (:20129) Vang Lên Giao Diện Model Của Hermes

## Bối Cảnh & Vấn Đề Thường Gặp
Khi tạo mới hoặc đổi tên một combo trên OmniRoute (ví dụ: `codex-terra`, `codex-luna`, `gpt-web-sol`), nếu chỉ thêm vào `config.yaml` của Hermes thì khi gõ `/model` trên Telegram hoặc CLI, Hermes **vẫn không hiển thị** model đó.

Lý do:
- Provider `omni` được đăng ký như một plugin provider nội bộ tại `C:/Users/Kibe/AppData/Local/hermes/plugins/model-providers/omni/__init__.py`.
- Lớp `OmniProfile` cài đặt `fetch_models()` trả về `None` để cố tình chặn live discovery (tránh kéo về hàng trăm model rác từ upstream).
- Hermes coi provider `omni` là canonical provider trong `hermes_cli.model_switch`, nên nó chỉ đọc danh sách model từ `fallback_models` (chính là biến `FARM_MODELS` trong plugin) và lưu vào file disk cache `C:/Users/Kibe/AppData/Local/hermes/provider_models_cache.json`.
- Do đó, nếu không cập nhật đồng bộ cả 4 tầng, model sẽ bị ẩn hoàn toàn khỏi danh sách model của Hermes.

---

## Quy Trình 4 Tầng Đồng Bộ Chuẩn

### Tầng 1: OmniRoute API / Dashboard (`:20129`)
- Tạo hoặc đổi tên combo qua REST API `http://127.0.0.1:20129/api/combos`:
  - Đổi tên combo: `PATCH /api/combos/{id}` hoặc `PUT /api/combos/{id}` với payload `{"name": "<tên-kebab-case>"}`.
  - Tạo mới combo: `POST /api/combos` với đầy đủ `name`, `description`, `strategy` (thường là `cache-optimized` hoặc `p2c`), `models`, `config`.
- Quy chuẩn tên combo trên OmniRoute: **Kebab-case** (ví dụ: `codex-terra`, `codex-luna`, `gpt-web-sol`).

### Tầng 2: Plugin Provider `omni` (`__init__.py`)
- File: `C:/Users/Kibe/AppData/Local/hermes/plugins/model-providers/omni/__init__.py`
- Cập nhật biến `FARM_MODELS`:
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
- Đảm bảo `fallback_models=FARM_MODELS` trong khởi tạo `omni = OmniProfile(...)`.

### Tầng 3: Hermes `config.yaml`
File: `C:/Users/Kibe/AppData/Local/hermes/config.yaml`
1. **Model Aliases (`model.aliases`)**:
   Bổ sung cả dạng kebab-case lẫn dạng có dấu cách và dạng rút gọn để người dùng gõ tự nhiên đều nhận diện được:
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
2. **Khai báo trong `providers.omni.models` và `custom_providers`**:
   ```yaml
   providers:
     omni:
       models:
         codex-terra: {context_length: 256000}
         codex-luna: {context_length: 256000}
         gpt-web-sol: {context_length: 256000}
   ```
3. **Reasoning Effort Overrides (`agent.reasoning_overrides`)**:
   Nếu model cần ghim mức reasoning cụ thể:
   ```yaml
   agent:
     reasoning_overrides:
       codex-terra: medium
       codex-luna: medium
   ```

### Tầng 4: Xóa Disk Cache & Xác Thực Nghiệm Thu
Sau khi sửa code plugin, cache cũ vẫn còn lưu trong `provider_models_cache.json`. Cần xóa cache bằng Python:
```python
from hermes_cli.models import clear_provider_models_cache, cached_provider_model_ids
clear_provider_models_cache('omni')

# Nạp lại và kiểm tra
models = cached_provider_model_ids('omni', force_refresh=True)
print("Omni models:", models)
assert 'codex-terra' in models and 'codex-luna' in models and 'gpt-web-sol' in models
```

Kiểm tra lệnh phân giải model picker của Hermes:
```python
from hermes_cli.model_switch import list_picker_providers, resolve_alias
print("Alias codex terra ->", resolve_alias("codex terra", "omni"))
print("Alias gpt web sol ->", resolve_alias("gpt web sol", "omni"))
```

---

## Cạm Bẫy (Pitfalls) Cần Tránh
1. **Chỉ sửa `config.yaml` mà quên plugin `omni/__init__.py`**:
   Hermes coi `omni` là canonical provider đã được import sẵn trong package `providers`. Khi render picker, `list_authenticated_providers` ưu tiên đọc `fallback_models` của plugin và bỏ qua `config.yaml`.
2. **Không xóa disk cache sau khi patch plugin**:
   File `provider_models_cache.json` lưu giữ model list với TTL 1 giờ. Nếu không gọi `clear_provider_models_cache()`, người dùng mở `/model` vẫn chỉ thấy danh sách cũ.
3. **Quên tạo alias dạng có dấu cách (`"codex terra"`)**:
   Người dùng thường gõ `/model codex terra` thay vì `/model codex-terra`. Cần khai báo alias có dấu cách bọc trong dấu ngoặc kép trong `config.yaml` để resolver map mượt mà.
