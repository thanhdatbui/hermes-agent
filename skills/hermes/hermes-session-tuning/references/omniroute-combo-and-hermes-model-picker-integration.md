# Quy Trình Tích Hợp Model/Combo Mới Từ OmniRoute (:20129) Vào Hermes Model Switcher (/model)

## Bối cảnh & Vấn đề
Khi một cụm account hoặc model mới được đưa vào hoạt động trên backend reverse-proxy OmniRoute (ví dụ cụm Argon 4 / Gemini Web Pro gồm 15 tài khoản kẹp proxy dân cư), người dùng mong muốn:
1. Gõ `/model` trên Telegram thấy ngay nút bấm mang tên thân thiện (ví dụ `gemini-web`).
2. Gõ lệnh tự nhiên trong chat (`gemini web`, `gemini-web`, `argon`, `argon 4`) hệ thống tự động resolve và switch đúng target `custom:omni/gemini-web`.
3. Bắn request trực tiếp từ client không bị dính lỗi `HTTP Error 400: Unable to determine provider for model ...`.

Nếu chỉ tạo combo với tên dài (như `gemini-web-argon-pool`) trong OmniRoute mà không chuẩn hóa tên ngắn và không đồng bộ vào Hermes, người dùng sẽ không thấy model trong danh sách và không thể kích hoạt.

---

## 1. Tầng OmniRoute (:20129) — Chuẩn Hóa Combo API
OmniRoute xác định provider và routing dựa trên tên model gửi lên `/v1/chat/completions`.
- Nếu tên model không có tiền tố provider (ví dụ `openai/...`) và không trùng khớp với bất kỳ `name` nào trong bảng `combos`, OmniRoute sẽ trả về:
  ```json
  {"error":{"message":"Unable to determine provider for model 'gemini-web'...","type":"invalid_request_error","code":"bad_request"}}
  ```
- **Cách xử lý**:
  Khi tạo hoặc nhân bản pool, tạo combo mang tên rút gọn chuẩn (e.g. `gemini-web`) trỏ về cùng danh sách models/connections:
  ```python
  import urllib.request, json

  payload = {
      "name": "gemini-web",
      "description": "Gemini Web 4 Argon Pool (15 Google AI Pro Accounts)",
      "models": argon_models,
      "strategy": "cache-optimized",
      "config": {
          "sticky": False,
          "disableSessionStickiness": True,
          "maxGlobalAttempts": 5,
          "targetTimeoutMs": 30000,
          "failoverBeforeRetry": True
      }
  }
  req = urllib.request.Request(
      "http://127.0.0.1:20129/api/combos",
      headers={"Content-Type": "application/json"},
      data=json.dumps(payload).encode("utf-8"),
      method="POST"
  )
  with urllib.request.urlopen(req, timeout=10) as resp:
      assert resp.status in (200, 201)
  ```
- **Kiểm thử Canary trước khi cấu hình client**:
  Gửi probe request test trực tiếp lên endpoint chat:
  ```python
  payload = {
      "model": "gemini-web",
      "messages": [{"role": "user", "content": "ping"}],
      "max_tokens": 10
  }
  # Phải nhận HTTP 200 OK
  ```

---

## 2. Tầng Hermes Agent — Đồng Bộ 4 Điểm Cốt Lõi
Hermes Agent không query live discovery tới `:20129/v1/models` mỗi lần mở menu `/model` (do OmniRoute có thể chứa hàng trăm model thô gây phình context và lag UI). Thay vào đó, Hermes dùng kiến trúc fallback tĩnh qua Provider Plugin.

### Bước 1: Khai báo vào `FARM_MODELS` trong Plugin Omni
Phải bổ sung tên model vào tuple `FARM_MODELS` ở cả 2 vị trí (runtime và venv site-packages):
- `%LOCALAPPDATA%\hermes\plugins\model-providers\omni\__init__.py`
- `%LOCALAPPDATA%\hermes\hermes-agent\venv\Lib\site-packages\plugins\model-providers\omni\__init__.py`

```python
FARM_MODELS: tuple[str, ...] = (
    "omni-worker",
    "omni-free",
    "ag-gemini-pool-3",
    "ag-sonnet",
    "ag-opus",
    "codex-terra",
    "codex-luna",
    "cx/gpt-5.6-luna-high",
    "codex/gpt-5.6-luna-high",
    "gpt-web-sol",
    "gpt-web-luna",
    "gemini-web",
)
```

### Bước 2: Bổ sung Alias và Model Metadata trong `config.yaml`
Trong file `%LOCALAPPDATA%\hermes\config.yaml`:
1. **`model.aliases`**:
   ```yaml
   gemini-web: custom:omni/gemini-web
   gemini web: custom:omni/gemini-web
   argon: custom:omni/gemini-web
   argon 4: custom:omni/gemini-web
   ```
2. **`providers.omni.models`**:
   ```yaml
   gemini-web:
     context_length: 1048576
     supports_vision: true
   ```
3. **`custom_providers`** (entry `name: omni`):
   ```yaml
   models:
     gemini-web:
       context_length: 1048576
       supports_vision: true
   ```

### Bước 3: Cập nhật `provider_models_cache.json`
Hermes lưu danh sách model đã load vào `%LOCALAPPDATA%\hermes\provider_models_cache.json`.
Cần thêm `"gemini-web"` vào mảng `d["omni"]["models"]`:
```python
import json, os
cache_path = os.path.join(os.environ["LOCALAPPDATA"], "hermes", "provider_models_cache.json")
if os.path.exists(cache_path):
    with open(cache_path, "r", encoding="utf-8") as f:
        d = json.load(f)
    if "omni" in d and "gemini-web" not in d["omni"]["models"]:
        d["omni"]["models"].append("gemini-web")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
```

### Bước 4: Kiểm tra Invariant Hạ Tầng (`infra_regression_gate.py`)
Sau khi chỉnh sửa `config.yaml`, luôn chạy Protection Regression Gate để đảm bảo không vi phạm bất biến retry headroom, compression threshold hay watchdog timeouts:
```bash
python D:/Taadaa/tools/infra_regression_gate.py --json
# Bắt buộc: passed == true, violations_count == 0
```

---

## 3. Nghiệm Thu & Kiểm Chứng CLI
Chạy kiểm tra qua python trong môi trường Hermes:
```python
from hermes_cli.config import load_config
from hermes_cli.model_switch import list_authenticated_providers

cfg = load_config()
res = list_authenticated_providers(
    current_provider=cfg.get('model', {}).get('provider'),
    current_base_url=cfg.get('model', {}).get('base_url', ''),
    current_model=cfg.get('model', {}).get('default', ''),
    user_providers=cfg.get('providers'),
    custom_providers=cfg.get('custom_providers'),
    max_models=50,
)
for r in res:
    if r['slug'] == 'omni':
        assert 'gemini-web' in r['models']
        print("PASS: gemini-web is visible in Hermes models list!")
```
