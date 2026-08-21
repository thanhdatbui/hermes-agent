# Hermes Role/Model Chain — Combo 9router (2026-08-15)

## Tóm tắt

- **Coordinator + Worker dùng CHUNG 1 combo `worker`** trên 9router (không cấu hình fallback Hermes).
- **Plan/review** dùng combo riêng (`plan-review` thường, `plan-review-hard` khó) gọi qua HTTP 9router.
- Toàn bộ fallback model nằm trong **combo 9router**, Hermes KHÔNG dùng `fallback_providers`.
- Mọi call HTTP 9router **bắt buộc `"stream": false`** (AG models trả SSE khi thiếu → fail parse).

## Combo đã tạo (9router dashboard, 2026-08-15)

| Combo | Models (thứ tự = priority) | Vai trò |
|---|---|---|
| `worker` | `cmc/deepseek/deepseek-v4-flash`, `gpt-5.6-luna`, `oc/deepseek-v4-flash-free`, `oc/hy3-free`, `ag/claude-sonnet-4-6`, `ag/gemini-3.6-flash-high` | Hermes main session + worker subagent |
| `plan-review` | `gpt-5.6-terra`, `ag/claude-opus-4-6-thinking`, `cmc/deepseek/deepseek-v4-pro` | Plan/audit thường |
| `plan-review-hard` | `gpt-5.6-sol` | Plan/audit khó — **sol-only**; Sol fail qua 9router → gọi Claude CLI pinned `claude-opus-5` với quyền Read-only ngoài combo |

## Cấu hình Hermes (đã áp dụng)

```yaml
model:
  default: worker          # combo name, không slash → 9router resolve combo
  provider: custom:9router
delegation:
  model: worker            # subagent cũng dùng combo worker
  provider: custom:9router
  reasoning_effort: high
custom_providers:          # 9router entry
  - name: 9router
    base_url: http://127.0.0.1:20128/v1
    api_mode: chat_completions
    key_env: NINEROUTER_API_KEY
    discover_models: false
    model: worker
    models:
      worker: { context_length: 1048576 }
```

- `fallback_providers` **không bật** (None) — fallback do 9router combo lo.
- Profile worker `taadaa-build-script`/`taadaa-fix-automation` giữ nguyên (Kanban roles).
- Cần `/new` (session mới) để Hermes nạp model mới.

## Cách gọi plan/review (HTTP 9router)

```python
payload = {
  "model": "plan-review",            # hoặc "plan-review-hard"
  "messages": [{"role": "user", "content": prompt}],
  "max_tokens": 8000,
  "temperature": 0.2,
  "reasoning_effort": "max",          # BẮT BUỘC cho plan/review
  "stream": False,                    # BẮT BUỘC
  "tools": [], "tool_choice": "none", # ép text thuần (v4-pro fake tool_calls)
}
# POST http://127.0.0.1:20128/v1/chat/completions
# Authorization: Bearer $NINEROUTER_API_KEY
```

- Combo tự fallback khi model trước fail (429/403/quota/credential inactive).
- **Audit dùng con giỏi nhất, không rẻ trước** — chain đã đặt Opus/Sol trước.
- Ghi evidence mỗi call: `model thực dùng` (trong response), `latency`, `finish_reason`, `cost`.

## Smoke test đã chạy (2026-08-15)

| Combo | Kết quả | Model thực dùng | Latency |
|---|---|---|---|
| `worker` (qua Hermes runtime resolve) | ✅ `WORKER_OK` | `deepseek/deepseek-v4-flash` | 2,25s |
| `plan-review` | ✅ `COMBO_OK` | `claude-opus-4-6-thinking` (AG Opus, fallback từ Terra vì codex credential inactive) | 2,6s |
| `plan-review-hard` | ⚠ historical result cần rerun | Historical smoke đã rơi sang DeepSeek fallback, không phù hợp policy sol-only hiện tại | — |

## Bài học / lưu ý

- `oc/deepseek-v4-flash-free` hiện **429** (free quota) — fail nhanh ~1s, vẫn ổn làm fallback cuối.
- `gpt-5.6-luna`/`sol` 404 khi gọi model lẻ (`No active credentials for provider: codex`) — chỉ chạy qua combo; khi bật lại credential codex thì tự vào đúng vị trí.
- **`stream: false` là bắt buộc** — AG models (gemini/opus/sonnet) trả SSE khi thiếu, phá JSON parse.
- 9router combo resolution: model name **không slash** → lookup `combos` table; model có slash → provider direct, combo không dùng.
- Model `(high)`/`(max)` suffix là display-only — không gửi vào payload.
