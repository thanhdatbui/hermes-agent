# Command Code DeepSeek V4 Flash — route + benchmark (2026-08-17)

Session detail: benchmark DS V4 Flash vs Gemini 3.7 Flash trên task Android automation (Taadaa). Đây là vòng Command Code — vòng đầu (`oc/deepseek-v4-flash-free`) đầy đủ ở `model-benchmark-dsv4-vs-gemini-2026-08-17.md`.

## Route Command Code qua 9router (đã verify 17/08)

- **Model ID đúng**: `commandcode/deepseek/deepseek-v4-flash`
- **SAI**: suffix `(high)`/`(max)` → 403 `"Model/provider not recognized: anthropic:deepseek/deepseek-v4-flash(high)"` (upstream commandcode.ai); prefix `cc/` → resolve thành provider `claude`, no creds.
- **Credentials**: bảng `providerConnections` trong `~/AppData/Roaming/9router/db/data.sqlite`, provider=`commandcode`, authType=apikey. User add `lequynh27032002` (priority 1, `testStatus: active`, 17/08 10:33). `modelLock_deepseek/deepseek-v4-flash` key trong `data` JSON = model ID thật. Connection `isActive=0` hoặc thiếu → `No active credentials for provider: commandcode-direct`.
- **Route trả `reasoning_content`** (giống combo DS) → max_tokens phải lớn (≥20000) nếu không `content` rỗng.
- OpenCode CLI cũng có provider `commandcode-direct` (baseURL `https://api.commandcode.ai/provider/v1`, key `{env:CMD_API_KEY}`) — không có CLI command-code riêng trên máy; "CLI command code trong 9router" user nói = connection trong 9router, không phải binary.

## Tool-call XML quirk (v4, API thuần)

Gọi `commandcode/deepseek/deepseek-v4-flash` qua `/v1/chat/completions` (không có tool executor) → model sinh XML tool-call vào content:
```xml
<invoke name="grep">...  <invoke name="bash">...  <invoke name="glob">...
```
4/5 task v4 chỉ có tool XML, không có trả lời. Đây là hành vi train theo pattern agent CLI — KHÔNG phải model dở.

## So sánh 3 harness (v4/v5/v6)

| Harness | DS CC kết quả |
|---|---|
| v4: raw API, prompt thường | ❌ 4/5 task = tool XML |
| v5: raw API + `[CẤM TUYỆT ĐỐI] Bạn KHÔNG có tool, không được gọi bash/grep/glob/read file. Chỉ trả lời text trực tiếp dựa trên code đã dán.` | ✅ 5/5 trả lời thật, chất lượng cao (18-131s/call) |
| v6: `hermes chat -q ... -m commandcode/deepseek/deepseek-v4-flash --provider 9router -Q` (agent loop) | chạy đúng cách model dùng tool thật (đang chạy khi kết thúc session) |

## Kết quả v5 (prompt cấm tool, 2 model, 5 task)

| Task | DS CC | Gemini 3.7 | Nhận xét |
|---|---|---|---|
| T6 canonical_header đ-bug | ✅ 131s — root cause SÂU: `d+U+0335 COMBINING SHORT STROKE OVERLAY` (decomposed) bị nuốt → map đ→d | ✅ 42s — đúng (đ không NFD-decompose) | DS sâu hơn |
| T7 budget rollover timezone | ✅ 85s — **PHẢN BIỆN ĐÚNG**: code bản 1 đã astimezone HCM nên KHÔNG có bug; bug chỉ thật nếu `_today()` naive | ✅ 26s — xác nhận bug có thật | DS thắng (planted bug) |
| T8 device_lock fail-closed | ✅ 39s — P0/P1 `owner is None` khi file hỏng; ghi chú code bị cắt | ✅ 23s — P0 fail-open + fix O_CREAT\|O_EXCL | ngang |
| T11 safety_check fail-closed | ✅ 49s — review đúng, nhận xét snippet thiếu | ✅ 18s — P0 fail-open unknown screen | G gọn hơn |
| T12 VPN source-error | ✅ 18s — heuristic fragile, false +/- negative, fix typed exception | ✅ 10s — đúng gọn | ngang |

**Chấm**: DS CC 7.5-8.5/10 (phân tích sâu, phản biện tốt) vs Gemini 8.5-9/10 (ổn định, nhanh gấp 2-3×). Khi DS CC trả được → chất lượng NGANG HOẶC CAO HƠN Gemini; vấn đề là tốc độ + hay "than code bị cắt" thay vì tự xử lý.

## Route status tổng (17/08, live)

- `deepseek-v4-flash` (combo) — OK, reasoning_content, member đầu oc/ds-free
- `cmc/deepseek/deepseek-v4-flash` — 404 (provider cmc không active creds)
- `v98/deepseek-v4-flash` — 503 `service_migrated` (v98store → cheapkeyai.shop, reset sau 30s)
- `oc/deepseek-v4-flash-free` — OK task ngắn, 502/timeout task dài (free tier nghẽn)
- `commandcode/deepseek/deepseek-v4-flash` — OK sau khi user thêm creds (17/08)
- `ag/gemini-3.7-flash-high` — OK, resolve thành `gemini-3.7-flash-tiered`
- `opencode-go/*`, `commandcode-direct/*` — "No active credentials"

## File benchmark

- `C:/Users/Kibe/run_benchmark_v4.py` / `v5.py` / `v6.py` — harness (v6 = hermes chat loop)
- `C:/Users/Kibe/benchmark_raw_results_v4.json` / `v5.json` — kết quả thô
- Log: `C:/Users/Kibe/benchmark_run5.log` (v4), `benchmark_run6.log` (v5)
