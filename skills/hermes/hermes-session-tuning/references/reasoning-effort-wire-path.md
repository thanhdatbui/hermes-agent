# Reasoning effort wire path — Hermes config → 9router console log

Verified 2026-08-06, Hermes v0.18.2 (upstream aaf96885), 9router v0.5.45.

## Hermes side (Python, HERMES_HOME = C:\Users\Kibe\AppData\Local\hermes\hermes-agent)

1. **Config** (`config.yaml`): `agent.reasoning_effort: max` + optional `agent.reasoning_overrides: {model: level}` (per-model wins)
2. **Resolve** — `hermes_constants.py:999 resolve_reasoning_config()`:
   - priority: per-model override → global `reasoning_effort`
   - `parse_reasoning_effort_for_model()` (`:835`) rejects efforts not in `reasoning_efforts_for_model()`; DeepSeek V4 = `("low","high","max")` (`:802`)
   - test: `python3 -c "from hermes_cli.config import load_config; from hermes_constants import resolve_reasoning_config; print(resolve_reasoning_config(load_config(), 'cmc/deepseek/deepseek-v4-flash'))"` → `{'enabled': True, 'effort': 'max'}`
3. **Gate** — `run_agent.py:5411 _supports_reasoning_extra_body()`: True cho custom:9router localhost:20128 + model `cmc/deepseek/*`, `ds/deepseek-*`, `deepseek-v4-*`. Custom endpoints khác → False (không gửi reasoning). Nous Portal/GitHub Models/LMStudio có gate riêng.
4. **Payload** — `agent/transports/chat_completions.py:472-481`: khi `supports_reasoning` và không phải LM Studio → `extra_body["reasoning"] = {"enabled": True, "effort": <effort>}` (mặc định "medium" nếu không có reasoning_config). `:501-502` gắn vào `api_kwargs["extra_body"]`. **Lưu ý**: nếu provider có `provider_profile` (providers/ registry) thì đi `_build_kwargs_from_profile` — bỏ qua reasoning extra_body. 9router là custom → legacy path → reasoning được gửi.
5. **Chokepoint chung**: `chat_completion_helpers.py:1681` — per-model override > global. Config mới chỉ resolve lại khi session init / /model switch / fallback activation.

## 9router side (Node, C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\.next-cli-build\server\chunks\)

Minified — đọc bằng python `open(f, encoding='utf-8', errors='replace')` + `re.finditer` (grep thường fail vì dòng dài).

- **Model suffix override** — chunk 8499.js hàm `nF`/`i`:
  - `model(max)` → `{mode:"level", level:"max"}`; `(high)` → level high
  - `(auto)` → `{mode:"auto"}`; `(none|off)` → `{mode:"none"}`
  - `(1234)` → `{mode:"budget", budget:1234}`
  - Không suffix → `{cleanModel, override:null}` → đọc từ body
- **fmtThink** (chunk 1829.js `m`): in `off`/`auto`/`Nk`/level từ `{mode}` → đây là nguồn `THINK:X` trong console log
- **sS/đọc body** (chunk 8499.js hàm `j`): ưu tiên `output_config.effort` → `thinking.type` → `reasoning_effort`/`reasoning.effort` → `thinkingConfig` → `enable_thinking`
- **Transformer commandcode** (chunk 318.js `class i extends e.H`, `transformRequest`): chỉ `b.stream=!0`, **giữ nguyên body** → thứ lên wire = thứ Hermes gửi
- **Translate openai→commandcode** (chunk 8499.js `GH:()=>ak`): sau translate gọi `(0,l.z)(b,c,v,q,w)` (hàm `s`) — nếu body có reasoning/effort hợp lệ thì dùng, nếu không thì model override (suffix), nếu không → null → provider default

## Vì sao log ra THINK:auto dù config max?
1. Request chạy trước khi đổi config — reasoning_config resolve lúc session init → cần `/new` hoặc `/model` (config mới KHÔNG áp cho session cũ)
2. Fallback: `fallback_providers: gemini/gemini-3.6-flash` qua cùng 9router — gemini có `reasoning_overrides: high`, và `_build_gemini_thinking_config` dùng thinkingLevel thay vì reasoning_effort
3. Hermes version đang chạy khác code trên disk (chạy từ venv site-packages copy)

## Cách ép chắc chắn
- Đổi model thành `cmc/deepseek/deepseek-v4-flash(max)` / `(high)` — suffix override cứng trong 9router, không phụ thuộc body Hermes gửi
- Verify thật: mở tab Console Log 9router, gõ tin ở session mới, xem dòng `POST ... THINK:X`

## Test nhanh bằng curl (không đụng Hermes)
```bash
curl -s -m 10 -X POST http://127.0.0.1:20128/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"cmc/deepseek/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"max_tokens":5,"stream":false}'
```
→ response `model: deepseek/deepseek-v4-flash`, có `reasoning_content` = thinking đang bật. 9router dashboard API cần auth (`/login`).
