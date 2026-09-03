# OpenCode free (`oc/*`) qua 9router — updated 2026-08-23

## Cơ chế Auth & Upstream (Hoàn toàn noAuth / Free)
- Provider `opencode` (alias `oc`) trên 9router được set `noAuth: true`.
- 9Router tự động gán header `Authorization: Bearer public`, `User-Agent: opencode`, `x-opencode-client: desktop` và route thẳng lên upstream endpoint `https://opencode.ai/zen/v1/chat/completions` (Claude format lên `/zen/v1/messages`).
- **KHÔNG CẦN** API key, tài khoản hay auth credential nào trong `~/.local/share/opencode/auth.json` đối với `oc/*` (chỉ `opencode-go` / `ocg` mới cần key $5/mo).
- Danh sách model public free lấy từ `https://opencode.ai/zen/v1/models`.

## Model mới & Dynamic Routing: `x-preview-f-free` (Ox Alpha Free)
- Model ẩn danh (Ox Alpha Free) có ID: **`x-preview-f-free`**.
- Gọi qua 9router: **`oc/x-preview-f-free`** (bắt buộc prefix `oc/`; gọi không prefix -> 404; gọi `oc/ox-alpha-free` -> 401 ModelError).
- Hỗ trợ dynamic passthrough: dù model chưa có sẵn trong danh sách hiển thị `/v1/models` hay bảng `kv`, 9Router vẫn pass request với prefix `oc/` thẳng lên upstream Zen API.
- Phản hồi kèm suy luận `reasoning_content` (tương tự R1/O-series), cost `$0.000`.
- Lưu ý: Stream mode (`stream: true`) có thể bị nghẽn tải/timeout trên upstream Zen tùy thời điểm; non-stream (`stream: false`) phản hồi ổn định hơn.

## Combo & KV (DB `C:\Users\Kibe\AppData\Roaming\9router\db\data.sqlite`)
- `combos` table:
  - Combo `worker`: `["oc/x-preview-f-free", "cmc/deepseek/deepseek-v4-flash", "oc/deepseek-v4-flash-free", "oc/hy3-free", "ag/gemini-3.7-flash-high", "ag/claude-sonnet-4-6", "gpt-5.6-luna"]`
  - Combo `opencode-free`: `["oc/deepseek-v4-flash-free", "oc/mimo-v2.5-free", "oc/big-pickle", "oc/hy3-free", "oc/nemotron-3-ultra-free", "oc/north-mini-code-free"]`
- Update combo trực tiếp trong SQLite:
  ```python
  import sqlite3, json, datetime, os
  conn = sqlite3.connect(os.path.expanduser(r'~\AppData\Roaming\9router\db\data.sqlite'))
  # UPDATE combos SET models=... WHERE name='worker'
  ```

## Diagnose "server command code sập"
- `opencode run --model <bất kỳ>` (opencode-go, freemodel, commandcode-direct) đều trả `UnknownError: Unexpected server error` + ref id khác nhau mỗi lần → lỗi tầng GATEWAY opencode (auth `sk-gon...` trong auth.json hoặc service opencode.ai outage), KHÔNG phải model cụ thể.
- Phân biệt nhanh: curl 9router `cmc/deepseek/deepseek-v4-flash` (sống = commandcode/deepseek OK) + `oc/deepseek-v4-flash-free` (sống = model opencode free OK). Cả 2 sống mà opencode CLI chết = gateway opencode.
- Log upstream thật: `~/.local/share/opencode/log/opencode.log` — `stream error ... AI_APICallError: Monthly usage limit reached` / `[503] The request queue is full` / `[502] Nvidia ResourceExhausted` = quota upstream; `UnknownError` = gateway.
- opencode CLI không có process nền mặc định (chỉ 9router `cli.js --tray` + `custom-server.js`); `opencode serve` mới là headless server (port mặc định 0, cần `--port`).

## Hermes fallback chain code anchors (reasoning KHÔNG kế thừa)
- `agent/agent_init.py` ~1166: `_fallback_chain` build từ `fallback_providers` (list) / `fallback_model` (legacy dict) — session init, đổi config cần `/new`.
- `agent/chat_completion_helpers.py` `try_activate_fallback` (~1372): skip logic (dedup provider/model/base_url, `_unavailable_fallback_keys` session-suppression, `_fallback_entry_unavailable_without_network`), swap client in-place, **re-resolve reasoning** ~1690: `agent.reasoning_config = resolve_reasoning_config(load_config(), agent.model)`.
- `hermes_constants.py` `resolve_reasoning_config` (~999): ưu tiên `agent.reasoning_overrides.<model>` (spelling-tolerant) → global `agent.reasoning_effort`; session-scoped `/reasoning --session` override thắng tất cả (resolve trước).
- `hermes_cli/fallback_config.py` `get_fallback_chain`: merge `fallback_providers` + legacy `fallback_model`, dedup theo (provider, model, base_url); Gemini implicit fallback được upgrade thành `custom:9router` nếu config có named 9router endpoint.
- `agent/auxiliary_client.py` `_try_main_fallback_chain` (~4113): auxiliary task dùng chung main chain; skip provider bị fail + main provider + "auto".
