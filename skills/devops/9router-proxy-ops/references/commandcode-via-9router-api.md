# Gọi model Command Code qua 9router API (verified 2026-08-17, 9router 0.5.55)

## Route names — cái nào chạy, cái nào sai

| Route | Kết quả |
|---|---|
| `commandcode/deepseek/deepseek-v4-flash` | ✅ OK (reasoning_content + content) |
| `cmc/deepseek/deepseek-v4-flash` | ✅ OK (model mặc định trong `D:\Taadaa\tools\invoke-command-code-9router-audit.ps1`) |
| `commandcode/deepseek/deepseek-v4-flash(high)` | ❌ 403 FORBIDDEN "Model/provider not recognized: anthropic:deepseek/..." — suffix variant (high/max) không được công nhận |
| `cc/deepseek/deepseek-v4-flash` | ❌ "No active credentials for provider: claude" — prefix `cc/` map nhầm sang provider claude |
| `oc/deepseek-v4-flash-free` | ❌ ĐÂY LÀ OPENCODE, không phải Command Code |

**User nói "chạy command code" = route prefix `commandcode/` (hoặc `cmc/`), TUYỆT ĐỐI không phải `oc/` (opencode).** Lỗi 2026-08-17: dùng `oc/deepseek-v4-flash-free` khi user yêu cầu command code → user bực.

## KHÔNG có CLI command-code riêng trên máy

Đã kiểm tra: `npm ls -g`, `~/AppData/Local/Programs`, scoop/choco, `where.exe`, PATH. Chỉ có opencode, 9router, openclaw, gemini CLI. Command Code tồn tại **dưới dạng provider bên trong 9router**:
- Executor: `C:\Users\Kibe\AppData\Roaming\npm\node_modules\9router\app\...` (OmniRoute source: `open-sse/executors/commandCode.ts`, baseUrl `https://api.commandcode.ai`, headers `x-command-code-version` + `x-cli-environment: external`)
- Wrapper audit duy nhất: `D:\Taadaa\tools\invoke-command-code-9router-audit.ps1` (model `cmc/deepseek/deepseek-v4-flash`, allowed: cmc/ds-v4-flash, cmc/ds-v4-pro, deepseek-v4-flash, deepseek-v4-pro; yêu cầu NINEROUTER_API_KEY; endpoint local 127.0.0.1:20128)

Gọi kiểu raw: `POST http://localhost:20128/v1/chat/completions` header `Authorization: Bearer $NINEROUTER_API_KEY`, body `{"model":"commandcode/deepseek/deepseek-v4-flash", ...}`.

## Pitfall chính: model sinh tool-call XML thay vì trả lời

Command Code DeepSeek train theo pattern Claude Code → khi gọi `/v1/chat/completions` thuần (không có tool loop), nó sinh `<invoke name="grep|glob|bash|Bash">` + `<parameter>` thay vì trả lời (content rác / rỗng).

**Mitigation đã test (run 6, 5 task thật):**
- Prepend system prompt: "Bạn là model chat thuần, KHÔNG có tool/terminal/file access. CẤM sinh XML `<invoke>`/`<use_mcp_tool>`/`<bash>`. Chỉ trả lời trực tiếp. Toàn bộ code đã có trong prompt."
- Kết quả: 4/5 task trả lời được (T7/T8/T11/T12 đúng hướng, chất lượng khá), nhưng **T6 vẫn fail cứng**: 20,000 tokens ra = toàn reasoning_content (49K chars), content rỗng, latency 170s.
- Chi phí: latency 20–170s (vs Gemini 14–42s), tokens_out 1.8K–20K (vs 0.5–1.2K). Reasoning nuốt hết max_tokens → phải set max_tokens lớn (20K) mới hy vọng có content.

**Kết luận routing:** commandcode qua API thuần chỉ hợp cho audit-style prompt (có VERDICT line, chấp nhận chậm), KHÔNG hợp task build/fix chat nhanh. Muốn tool-call thật phải chạy qua CLI có tool loop (không tồn tại trên máy này) hoặc 9router chuyển tiếp tool-call loop (chưa có).

## Discovery: tìm route đúng từ DB 9router

Khi user nói "vừa thêm credentials" mà route báo "No active credentials for provider: X":

```bash
python -c "
import sqlite3
db = sqlite3.connect(r'C:/Users/Kibe/AppData/Roaming/9router/db/data.sqlite')
for r in db.execute('SELECT provider, name, priority, isActive, data FROM providerConnections').fetchall():
    print(r[0], '|', r[1], '| prio', r[2], '| active', r[3])
    # data JSON chứa modelLock_<model-id> → lộ format model ID chính xác
"
```

- Columns: `id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt`.
- `data` JSON có key `modelLock_<model-id>` (VD `modelLock_deepseek/deepseek-v4-flash`) → model ID format cho provider đó.
- `testStatus: "active"` trong data = credentials OK; `unavailable` = đang lỗi/backoff.
- Model lock cũ (`modelLock_...` có timestamp) có thể giữ 403 sai 2 phút sau lần thử route sai — thử lại route đúng sau khi đã xác định format.

## Benchmark harness (pattern tái dùng)

- 5 task thật từ repo farm (canonical_header, budget rollover, device_lock review, safety_check review, VPN source-error), mỗi task cùng prompt cho cả 2 model.
- Ghi: elapsed, tokens_in/out, content_len, reasoning_content (CC có reasoning riêng).
- So sánh theo: trả lời đúng yêu cầu hay không (không phải độ dài), bắt đúng bug P0, latency, token burn.
- File mẫu đã có: `C:/Users/Kibe/run_benchmark_v4.py` (đã patch system-prompt chặn XML).
