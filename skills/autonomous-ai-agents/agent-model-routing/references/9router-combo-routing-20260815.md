# 9router combo fallback routing — user contract 2026-08-15

## Final routing contract (user chốt)

- Worker và coordinator là MỘT lane → dùng chung 1 combo `worker` (**ĐÃ THỰC THI 2026-08-15**: Hermes `model.default` + `delegation.model` + 9router `custom_providers[].model` đều = `worker`; profiles `taadaa-build-script`/`taadaa-fix-automation` + `kanban.orchestration.roles` đã XÓA vì user bác profile/roles — "là clgt?").
- Toàn bộ fallback đặt TRONG 9router combo; Hermes KHÔNG cấu hình `fallback_providers` (user yêu cầu rõ nhiều lần).
- Audit dùng model GIỎI NHẤT trước, KHÔNG dùng con rẻ trước (user correction: "audit dùng con rẻ trc rẻ = ngu cho hỏng à").
- `ag/claude-sonnet-4-6` là WORKER fallback (đứng TRƯỚC gemini), KHÔNG phải auditor. AG không có sonnet-5 (chỉ `ag/claude-sonnet-4-6`); `v98/claude-sonnet-5` tồn tại nhưng không dùng.
- Opus 5 (chain khó): user yêu cầu qua CLI (`claude -p`) KHÔNG qua `v98/claude-opus-5` HTTP — nhưng CLI đang 401 OAuth revoked nên combo `plan-review-hard` hiện dùng `v98/claude-opus-5` làm stand-in; khi CLI auth hồi → ưu tiên CLI.
- Pro chỉ là fallback, không phải primary; model chain mở để thêm model khác sau.
- Thứ tự combo đổi tay khi model hết quota — user tự đổi, không sửa code.

### Combo `worker` (worker + coordinator) — ĐÃ TẠO (id 2c455eeb) — gemini 3.6→3.7 sweep 17/08
```text
cmc/deepseek/deepseek-v4-flash   ← primary, GIỮ ĐẦU (perf, xem latency bên dưới)
oc/deepseek-v4-flash-free
oc/hy3-free
ag/gemini-3.7-flash-high
ag/claude-sonnet-4-6
gpt-5.6-luna
```

### Combo `plan-review` — ĐÃ TẠO (id e94cd01d)
```text
gpt-5.6-terra → ag/claude-opus-4-6-thinking → cmc/deepseek/deepseek-v4-pro
```

### Combo `plan-review-hard` — ĐÃ TẠO (id 7195fc26)
```text
gpt-5.6-sol → v98/claude-opus-5 (stand-in cho CLI, chờ auth) → cmc/deepseek/deepseek-v4-pro
```

Smoke 2026-08-15: worker→flash 2.25s; plan-review→AG opus-4.6 (terra fallback) 2.6s; plan-review-hard→pro 9.1s. Cần `/new` session để Hermes nạp model `worker`.

## Combo API (9router v0.5.50, dashboard auth)

- `GET /api/combos` — list; `POST /api/combos` body `{name, models:[ids], kind}` — create (name regex `^[a-zA-Z0-9_.\-]+$`); `PUT /api/combos/:id` — update; `DELETE /api/combos/:id`.
- Auth: `POST /api/auth/login` body `{"password": ...}`. Password bcrypt trong `settings.data.password` — KHÔNG đọc ngược, KHÔNG brute-force (lockout sau ~5 lần, response `remainingBeforeLock` giảm dần).
- DB: `~/AppData/Roaming/9router/db/data.sqlite`, table `combos` (id,name,kind,models). `models` là STRING JSON (`'["a","b"]'`), KHÔNG phải array. Backup DB trước khi sửa (`cp ... .bak-before-<ts>`).
- Combo members KHÔNG xuất hiện trong `GET /v1/models` (chỉ model gốc) — muốn biết combo có gì: gọi theo TÊN combo hoặc đọc table combos.

## Pitfalls (đo thật 2026-08-15)

1. **`"stream": false` BẮT BUỘC** với mọi call 9router từ Hermes HTTP. AG models (`ag/gemini-3.6-flash-*`, `ag/claude-opus-4-6-thinking`, `ag/claude-sonnet-4-6`) trả `text/event-stream` (SSE) khi không set stream → client parse JSON fail `"Expecting value: line 1 column 1"`. Set `"stream": false` → 200 JSON chuẩn. Đây từng bị hiểu nhầm thành "model hết quota" — thật ra là thiếu stream flag.
2. `gpt-5.6-*` (luna/sol/terra qua codex provider) → `404 {"message":"No active credentials for provider: codex"}` = credential codex tắt/expired, KHÔNG phải typo model. Bằng chứng combo hoạt động: gọi `gpt-5.6-terra` trả model `claude-opus-4-6-thinking` (primary fail → combo tự fallback sang AG Opus).
3. Model free (`oc/deepseek-v4-flash-free`) fail nhanh (~1s, `429 FreeUsageLimitError`) — vì fail nhanh nên đặt SAU primary để không phạt mọi request. Đảo lên trước = +~2s/request mọi lúc kể cả khi primary chạy tốt.
4. `usageHistory` KHÔNG có latency column (có timestamp/promptTokens/completionTokens/cost) — đo latency bằng request thật.

## Latency đo 2026-08-15 (prompt nhỏ "2+2?", 3 lần/model, stream:false)

| model | ok | median ms |
|---|---|---|
| cmc/deepseek/deepseek-v4-flash | 3/3 | ~3500 |
| cmc/deepseek/deepseek-v4-pro | 3/3 | ~2250 |
| gpt-5.6-luna | 0/3 | 404 (codex creds inactive) |
| oc/deepseek-v4-flash-free | 0/3 | 429 (free quota) |
| ag/claude-sonnet-4-6 | 3/3 | ~3000 |
| ag/gemini-3.6-flash-high | 3/3 | ~6100 (non-stream) |

## Thiết kế flow đã chốt (không profile, không Kanban roles)

Flash coordinator tự gọi 9Router HTTP với model chain (không tạo profile/role cho planner/auditor — delegate_task không chọn model per-call, source-verified). Task nhỏ → Flash làm thẳng; task khó → gọi HTTP chain plan-review → worker subagent Flash làm theo; review nặng → gọi lại chain (model khác con plan nếu muốn, nhưng user bỏ qua — không quan trọng).
