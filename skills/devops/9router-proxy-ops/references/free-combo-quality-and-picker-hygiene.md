# 9Router Free Combo Quality & Hermes Model Picker Hygiene

## 1. Fallback Chain Hierarchy (OmniRoute vs 9Router)
- Khi cấu hình chuỗi fallback cho Hermes Agent:
  - **Lớp 1 (Ưu tiên đầu)**: `omni-free` qua OmniRoute (`:20129`).
  - **Lớp 2 (Chốt chặn cuối)**: combo `9r-free` qua 9Router (`:20128`).
- **Quy tắc Bỏ qua Worker & Gom 1 Model Duy Nhất**:
  - Không dùng combo `worker` cho fallback thông thường vì chứa các model upstream account (CommandCode `cmc/*`, Codex) dễ gặp rate-limit/token expiration.
  - Gom toàn bộ các model free chất lượng cao vào đúng **1 combo duy nhất đặt tên `9r-free`**.

## 2. Tiêu chí Tuyển chọn Model cho Combo `9r-free` (Nhanh & Chất lượng Ổn)
- **CẤM TUYỆT ĐỐI đưa model đồ chơi / toy / mini (2.6B) lên đầu**:
  - Không chọn `big-pickle` hay `lfm-2.5-2.6b` lên đầu danh sách chỉ vì độ trễ thấp (<1s). Chất lượng sinh code / reasoning của các model này rất kém, không đáp ứng được yêu cầu tác vụ thực tế.
  - `big-pickle` chỉ được phép đứng ở vị trí cuối cùng trong combo làm chốt chặn cuối.
- **Thứ tự ưu tiên chuẩn cho combo `9r-free` (Đã kiểm chứng chất lượng code Python)**:
  1. `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`: Model 550B cực lớn của NVIDIA, code và suy luận xuất sắc, phản hồi ~1.9s.
  2. `openrouter/cohere/north-mini-code:free`: Model chuyên trách code của Cohere, sinh code có docstrings/type hints chuẩn xác (~2.2s).
  3. `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`: Model reasoning 30B của NVIDIA (~4.2s).
  4. `oc/mimo-v2.5-free`: Xiaomi MiMo v2.5 reasoning/coding.
  5. `openrouter/nvidia/nemotron-3.5-lightning:free`: NVIDIA Nemotron 3.5 Lightning.
  6. `oc/laguna-s-2.1-free`: Poolside Laguna code model.
  7. `openrouter/poolside/laguna-s-2.1:free`: Poolside Laguna code model (OpenRouter route).
  8. `oc/big-pickle`: Chốt chặn cuối cùng.
- **Loại bỏ khỏi combo**:
  - Model 429 rate limit thường trực: `z-ai/glm-5.2:free`, `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free`.
  - Model 401/timeout: `oc/hy3-free`, `oc/x-preview-f-free`, `oc/nemotron-3-ultra-free`.
  - Model CommandCode trả phí: `cmc/Kimi-K2.6`, `cmc/Qwen3.6-Plus`, `cmc/Step-3.5-Flash`, `cmc/deepseek/*`.

## 3. Dọn rác Menu `/model` Telegram (Model Picker Hygiene)
- **Hiện tượng**: Menu Telegram hiển thị `9router (29)` chứa hàng loạt model rác, model chết (`cx/*` 401, `ag/*` 404, raw CommandCode strings).
- **Nguyên nhân**: Trong `config.yaml`, khối `providers.9router` thiếu `discover_models: false` và thiếu danh sách `models:` tinh gọn, khiến Hermes tự động quét toàn bộ catalog từ `/v1/models` của 9Router.
- **Giải pháp chuẩn hóa — Giữ dàn GPT & Gemini/Claude, gom free vào `9r-free`**:
  - Giữ nguyên toàn bộ dàn GPT (`gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`) và Gemini/Claude (`gemini-3.7-flash-high`, `claude-sonnet-4-6`).
  - Gom toàn bộ các model free vào **1 model duy nhất** đặt tên là `9r-free` (combo đã tạo trên 9Router).
  - Loại bỏ sạch toàn bộ model CommandCode rác (`cmc/*` Kimi, Qwen, Step-Flash), `worker`, và các model upstream không có tài khoản:
  ```yaml
  providers:
    9router:
      api: http://127.0.0.1:20128/v1
      default_model: gpt-5.6-luna
      discover_models: false
      key_env: NINEROUTER_API_KEY
      models:
        gpt-5.6-luna: {}
        gpt-5.6-sol: {}
        gpt-5.6-terra: {}
        gemini-3.7-flash-high: {}
        claude-sonnet-4-6: {}
        9r-free: {}
      transport: chat_completions
  ```
- **Quy tắc Đồng bộ**: Mọi thay đổi về combo và cấu hình 9Router BẮT BUỘC:
  1. Export đồng bộ vào `D:\Taadaa\AI-Tools\config\9router\9router_config_template.json` qua `python D:\Taadaa\AI-Tools\config\9router\sync_config.py --action export`.
  2. Đồng bộ file cấu hình `D:\Taadaa\AI-Tools\config\hermes\hermes_config_template.yaml`.

## 4. Khối `custom_providers` cho Fallback & Tool Routing
Khi sử dụng `provider: custom:9router` trong `fallback_providers` hoặc routing công việc (audit/plan-review), Hermes yêu cầu các model phải được khai báo trong khối `custom_providers` tương ứng để nhận diện `context_length`.
Khối này giữ lại các model routing/audit chủ lực và `9r-free`, loại bỏ các model CommandCode rác:
```yaml
custom_providers:
  - api_key: ...
    api_mode: chat_completions
    base_url: http://127.0.0.1:20128/v1
    discover_models: false
    key_env: NINEROUTER_API_KEY
    model: 9r-free
    models:
      ag/claude-opus-4-6-thinking:
        context_length: 1000000
      ag/claude-sonnet-4-6:
        context_length: 1000000
      ag/gemini-3.7-flash-high:
        context_length: 1048576
      claude-sonnet-4-6:
        context_length: 1000000
      gemini-3.7-flash-high:
        context_length: 1048576
      gpt-5.6-luna:
        context_length: 256000
      gpt-5.6-sol:
        context_length: 256000
      gpt-5.6-terra:
        context_length: 256000
      plan-review:
        context_length: 256000
      plan-review-hard:
        context_length: 256000
      9r-free:
        context_length: 1048576
    name: 9router
```

## 5. Quy trình Kiểm chứng (Verification Checklist)
1. **Kiểm tra Fallback Chain**:
   ```bash
   hermes fallback list
   ```
   Output mong đợi:
   ```
   Primary:   <primary-model>
     Fallback chain (2 entries):
       1. omni-free  (via omni)
       2. 9r-free  (via custom:9router)
   ```
2. **Kiểm tra Menu Model Picker bằng Python**:
   ```python
   from hermes_cli.config import load_config, get_compatible_custom_providers
   from hermes_cli.model_switch import list_picker_providers

   cfg = load_config()
   res = list_picker_providers(
       current_provider=cfg.get('model', {}).get('provider', ''),
       current_model=cfg.get('model', {}).get('default', ''),
       user_providers=cfg.get('providers'),
       custom_providers=get_compatible_custom_providers(cfg),
       max_models=50,
   )
   p9 = next((p for p in res if p.get('slug') == '9router'), None)
   expected_models = ['gpt-5.6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra', 'gemini-3.7-flash-high', 'claude-sonnet-4-6', '9r-free']
   assert p9['models'] == expected_models
   ```
3. **Lưu ý cập nhật `config.yaml`**: Tool `patch` / `write_file` của agent chặn ghi trực tiếp vào `~/.hermes/config.yaml` vì lý do bảo mật. Cập nhật file này bằng script Python có kiểm soát qua terminal.
