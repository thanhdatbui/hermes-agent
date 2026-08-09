# Hermes subagent model routing + vision capability — source-verified facts (2026-08-05, cập nhật)

Session: user hỏi liệu Hermes app (chạy trên model `cmc/deepseek/deepseek-v4-flash` qua 9router) có làm được "Luna/high worker + subagent các model khác cho plan/audit" như Codex app. Đã đọc source `delegate_tool.py`, catalog Codex app, và test vision qua 9router.

## Kết luận (đã sửa sau khi kiểm tra catalog Codex app)

- **Hermes app**: `delegate_task` không nhận model; subagent chạy model do config `delegation.*` quyết định (không set → inherit parent). Không mix model theo vai qua subagent. Plan/audit model khác → bắt buộc CLI wrapper bên ngoài (đúng thiết kế AGENTS.md Taadaa).
- **Codex app**: spawn subagent được NHƯNG **chỉ trong catalog GPT của app** (10 model: gpt-5.6-luna/sol/terra, gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.3-codex-spark, GPT Image 2, codex-auto-review — file `~/.codex/cockpit-local-access-model-catalog.json`). Gemini/Claude/Command Code/DeepSeek KHÔNG có trong catalog app (chỉ trong `config.toml` CLI) → **Codex GUI cũng không spawn subagent model ngoài GPT được**; audit các model đó luôn qua CLI wrapper dù dùng Codex hay Hermes.
- **Subagent model khác main nhưng CÙNG provider**: Hermes làm được qua `delegation.provider` + `delegation.model` (vd `9router` + `cmc/deepseek/deepseek-v4-pro`). Model khác provider → CLI.

## Bằng chứng source

File: `<HERMES_HOME>/hermes-agent/tools/delegate_tool.py` (HERMES_HOME = `C:\Users\Kibe\AppData\Local\hermes`)

- `def delegate_task(goal, context, tasks, max_iterations, role, background, parent_agent)` — không có tham số model. (dòng ~2342)
- `_resolve_delegation_credentials(cfg, parent_agent)` (~2998): chỉ đọc `delegation.model/provider/base_url/api_key/api_mode` từ config. Không có gì từ model call.
- `_build_child_agent(...)` (~1049): `model=creds["model"]`; khi creds rỗng → `effective_model = model or parent_agent.model` → **inherit parent**.
- Reasoning: `child_reasoning = parent_reasoning`; chỉ override khi `delegation.reasoning_effort` set (parse qua `parse_reasoning_effort`). YAML boolean `false` được giữ nguyên (tắt thinking), không bị ép thành inherit — code cố tình xử lý `if delegation_effort or delegation_effort is False`.
- Set `delegation.provider` → child dùng API direct, **không kế thừa ACP transport của parent** (`override_provider and not override_acp_command → effective_acp_command = None`).
- `api_mode` KHÔNG inherit khi child provider ≠ parent provider (bug #20558: inherit mode sai endpoint → 404; khi khác provider thì `effective_api_mode = None` để re-derive từ provider defaults).
- Khi không set delegation gì: `provider=None, base_url=None, api_key=None, api_mode=None` → child inherit toàn bộ từ parent (model + base_url + key + fallback chain + provider filters).

## Config đã test chạy được (Hermes app → Luna/high worker)

`C:\Users\Kibe\AppData\Local\hermes\config.yaml` hiện có:

```yaml
model:
  default: cmc/deepseek/deepseek-v4-flash
  provider: custom:9router
  base_url: http://127.0.0.1:20128/v1
  api_mode: chat_completions
custom_providers:
  - name: cockpit
    base_url: http://localhost:60818/v1
    key_env: COCKPIT_API_KEY
    model: gpt-5.6-luna
    api_mode: codex_responses
    models: {gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra, ...}
delegation:
  max_iterations: 50
```

Muốn subagent = Luna/high (đúng rule AGENTS.md), thêm:

```yaml
delegation:
  provider: cockpit
  model: gpt-5.6-luna
  reasoning_effort: high
  max_iterations: 50
```

Muốn subagent = DeepSeek v4 Pro (cùng provider 9router, khác model main Flash):

```yaml
delegation:
  provider: 9router
  model: cmc/deepseek/deepseek-v4-pro
```

Verify:
- `COCKPIT_API_KEY` có trong `.env` (dòng ~479).
- `resolve_runtime_provider('cockpit', 'gpt-5.6-luna')` → `{'provider': 'custom', 'api_mode': 'codex_responses', 'base_url': 'http://localhost:60818...', 'model': 'gpt-5.6-luna', ...}`.
- `GET http://localhost:60818/v1/models` → trả list gồm `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, ... (endpoint sống).
- `GET /health` → `{"error":{"code":"not_found","message":"endpoint not supported"}}` — **bình thường**, cockpit không có /health; đừng lấy cái này làm bằng chứng endpoint chết.
- `resolve_runtime_provider('9router', 'cmc/deepseek/deepseek-v4-pro')` → trả bundle 9router (chat_completions).

## Codex app catalog (kiểm chứng 2026-08-05)

- File: `~/.codex/cockpit-local-access-model-catalog.json` — đúng 10 model, toàn GPT (slug: gpt-5.6-sol/terra/luna, gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex, gpt-5.3-codex-spark, gpt-image-2, codex-auto-review).
- `~/.codex/config.toml` có `[model_providers.9router]`/`[model_providers.omni]` (`base_url=http://localhost:20128/v1`, `wire_api="responses"`, `env_key=NINEROUTER_API_KEY`) — CLI-only, KHÔNG trong catalog app.
- `/v1/models` của 9router trả đủ gpt-5.6-luna/sol/terra, deepseek-v4-flash/pro/pro-max, gemini-2.5-pro/3-pro/3.1-pro-preview, v98/claude-opus-4-1, v98/qwen3-vl-plus, v98/gpt-5.1-codex... (danh sách thay đổi — test lại).

## Hermes vision fallback cho main model text-only (source `agent/auxiliary_client.py`)

- `resolve_vision_provider_client(provider, model, base_url, api_key, async_mode)`:
  - Explicit `base_url` override thắng mọi thứ → client dùng được (`provider_for_base_override` = `custom` nếu không truyền tên).
  - `provider="auto"`: 1) main provider nếu hỗ trợ vision (trừ `_PROVIDERS_WITHOUT_VISION` = kimi-coding), 2) OpenRouter, 3) Nous, 4) custom endpoint, 5) native Anthropic. `_VISION_AUTO_PROVIDER_ORDER = ("openrouter", "nous")` — KHÔNG có 9router trong auto chain.
  - Main model text-only (DeepSeek) → `_main_model_supports_vision()` trả False (catalog `agent/image_routing.py::_lookup_supports_vision`) → skip main provider, fall qua aggregator chain → **DeepSeek Flash không tự xem ảnh trừ khi config `auxiliary.vision` chỉ tới model vision OK**.
- Cấu hình:
  ```yaml
  auxiliary:
    vision:
      provider: openrouter        # hoặc custom + base_url 9router + model vision OK
      model: <vision-model>
  ```
- Test thực tế (venv `hermes-agent/venv/Scripts/python.exe`, `async_call_llm` + `data:image/png;base64,...`):
  - `gc/gemini-3.1-pro-preview`, `gc/gemini-3-pro-preview`, `gc/gemini-2.5-pro` → HTTP 403 `[gemini-cli/...] [403] (reset after ...)` — giới hạn phía 9router, thay đổi theo thời gian.
  - `v98/qwen3-vl-plus`, `v98/gpt-5.1-codex` → 200 nhưng nội dung "không thấy ảnh / model không hỗ trợ vision" — không nhận image input thật.
  - → Tại 2026-08-05 chưa có model vision sống qua 9router. Cần OpenRouter/Nous hoặc model khác. **Trạng thái thay đổi được — luôn test lại từng model trước khi kết luận.**
- `_PROVIDER_VISION_MODELS = {"xiaomi": "mimo-v2.5", "zai": "glm-5v-turbo"}` — model vision riêng theo provider.

## Lệnh kiểm tra nhanh

```bash
# Catalog model Codex app
python3 -c "import json; d=json.load(open('C:/Users/Kibe/.codex/cockpit-local-access-model-catalog.json')); [print(m.get('slug')) for m in d['models']]"
# Models 9router
curl -s -m 5 http://localhost:20128/v1/models -H "Authorization: Bearer $NINEROUTER_API_KEY"
# Models cockpit
curl -s -m 5 http://localhost:60818/v1/models -H "Authorization: Bearer $COCKPIT_API_KEY"
# Test vision model qua 9router (dùng venv hermes)
cd "$HOME/AppData/Local/hermes/hermes-agent" && ./venv/Scripts/python.exe -c "<async_call_llm test, xem SKILL.md>"
```

## Trình tự kiểm tra cho session tương lai

1. `hermes config path` → lấy config.yaml.
2. Đọc `delegation:` block — đã set provider/model chưa?
3. Chưa set → subagent inherit model parent (thường là deepseek-flash qua 9router) → KHÔNG phải Luna/high.
4. Muốn Luna/high → set `delegation.provider: cockpit` + `delegation.model: gpt-5.6-luna` + `reasoning_effort: high`; muốn DeepSeek Pro → `provider: 9router` + `model: cmc/deepseek/deepseek-v4-pro` (config ngoài repo Taadaa — hỏi user trước khi đổi).
5. Plan/audit model khác → CLI wrapper (`tools/invoke-*-audit.ps1`, `claude-final-audit`, hoặc `codex exec --model gpt-5.6-sol` cho plan audit), không qua subagent — kể cả khi dùng Codex app (catalog không có model ngoài GPT).

## CẬP NHẬT 2026-08-06: user chốt KHÔNG pin delegation + file rule riêng

- Config trên đĩa kiểm tra lại: `delegation:` chỉ có `max_iterations: 50` (model/provider/reasoning_effort trống → inherit deepseek cha). **User quyết định KHÔNG set `delegation.model/provider`** (không cần subagent Luna; model ngoài hệ vẫn đi CLI wrapper). Ghi chú cũ "cockpit :60818 delegation = gpt-5.6-luna/high" trong memory là SAI so với đĩa — đã sửa.
- Tạo `D:\Taadaa\HERMES_SUBAGENT_RULES.md` — file rule riêng cho Hermes app (không phải Codex/Claude), ngoài mọi git repo nên không auto-load → không đụng AGENTS.md, không phát sinh Configuration Policy Audit Gate. Trỏ tới nó bằng **memory** (cơ chế duy nhất inject mọi session, mọi cwd).
- Bối cảnh source (đã đọc `agent/prompt_builder.py`): priority context file `.hermes.md`(walk→git root) → `AGENTS.md`(cwd) → `CLAUDE.md`(cwd) → `.cursorrules`(cwd), **first match wins, chỉ load 1 file không merge**. `D:\Taadaa` không phải git repo → `.hermes.md` root chỉ load khi cwd=root (và sẽ CHE AGENTS.md) còn trong repo con thì không load → không dùng được làm file rule chung. `hermes.md` (không chấm) không bao giờ auto-load.
- `hermes config get` không tồn tại (chỉ `show/edit/set/path/env-path/check/migrate`); `hermes config show` không in section delegation → đọc thẳng `config.yaml`.
