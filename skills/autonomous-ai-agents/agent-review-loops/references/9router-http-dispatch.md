# 9router HTTP Dispatch (plan/audit từ Hermes, không qua CLI)

Dùng endpoint OpenAI-compatible của 9Router để gọi planner/auditor khi direct HTTP là route đã được policy cho phép. **Không coi host/port/path hoặc model ID ghi trong một session cũ là cấu hình hiện hành.** Ưu tiên wrapper/reusable script của `9router-proxy-ops`; direct HTTP là fallback có artifact đầy đủ.

## Endpoint discovery, auth và transport gate

1. Resolve live 9Router base URL từ cấu hình/runtime hiện hành hoặc canonical wrapper; không hard-code port từ ghi chú lịch sử.
2. Auth bằng `NINEROUTER_API_KEY`; không in key vào prompt/log/artifact.
3. Probe authenticated `GET <base>/v1/models`, chọn model theo routing policy hiện hành, rồi smoke-test text ngắn trước prompt lớn.
4. Chỉ POST vào chat-completions path mà live router/config hoặc canonical wrapper xác nhận. Historical installs thường dùng `<base>/v1/chat/completions`, nhưng đó là ví dụ, không phải invariant.
5. Lưu riêng request metadata (base URL đã redacted, model, timeout, input hash), body/prompt, raw response và parse result.

HTTP 404/401/429/5xx, timeout, body rỗng/truncated hoặc JSON không parse được là `AUDIT_TRANSPORT_FAILED` / `BLOCKED_UNKNOWN`, **không phải** verdict. Diagnostic một lần bằng live config/models/canonical wrapper rồi chuyển route fallback; đừng đoán hàng loạt endpoint và đừng ghi một lỗi tạm thời thành capability âm lâu dài.

## Model IDs lịch sử (chỉ để nhận dạng artifact cũ; luôn re-discover)

| Model ID | Trạng thái | Ghi chú |
|---|---|---|
| `cmc/deepseek/deepseek-v4-flash` | ✅ OK | Hermes main |
| `cmc/deepseek/deepseek-v4-pro` | ✅ OK | Plan/rescue — **PHẢI ép `tools:[]`+`tool_choice:"none"`** |
| `cmc/deepseek/deepseek-v4-pro-max` | ❌ 403 | commandcode FORBIDDEN |
| `cx/gpt-5.6-luna` / `gpt-5.6-luna` | ✅ OK | (sau khi user add GPT upstream vào 9router) |
| `cx/gpt-5.6-terra` / `gpt-5.6-terra` | ✅ OK | Audit khó vừa |
| `cx/gpt-5.6-sol` / `gpt-5.6-sol` | ✅ OK | Audit khó thật — CHẬM (4-8 phút) |
| `v98/claude-opus-4-8` | ⚠️ OK nhỏ / 403 payload lớn | upstream new_api_error với prompt dài |
| `v98/claude-sonnet-4-6` | ❌ 403 | upstream new_api_error |
| `cmc/moonshotai/Kimi-K2.6` | ⚠️ OK nhưng `finish=length` | truncate giữa chừng, cần vòng tiếp |
| `gemini/gemini-3.6-flash` | ✅ OK | vision/auxiliary |

**Trước khi dùng model nào**: smoke-test nhỏ (`max_tokens:10`, "Reply exactly: OK") — tránh gửi prompt 30KB vào model 403.

## Workaround: v4-pro tự phát minh tool_calls giả

deepseek-v4-pro (chat_completions) đôi khi trả về `tool_calls` thay vì `content` — tự tưởng mình là agent có tool (gọi `todo_write` v.v.), content rỗng. Fix:
- Payload: `"tools": [], "tool_choice": "none"` — ép trả text thuần.
- Prompt thêm: "TRẢ LỜI THUẦN TEXT MARKDOWN — KHÔNG dùng tool, không gọi function, không <tool_calls>."
- Nếu vẫn trả tool_calls: salvage bằng cách parse `function.arguments` từng cái.

## Bẫy: Sol chậm + truncate

- Sol (gpt-5.6-sol) mất 4-8 phút cho plan 15-30KB. **Chạy background** (terminal background=true, script python) với `timeout=840` — foreground 300s bị kill.
- Output hay bị cắt (`finish_reason:"length"` dù content dài). **Luôn ghi content ra file artifact** ngay khi nhận; đọc file, không tin tail process.
- Cắt giữa → gọi vòng tiếp: "trả lời NGẮN (dưới X chữ) phần còn thiếu: [các tiêu chí]" — kèm plan (có thể cắt plan xuống 15KB để đủ budget).

## Script mẫu (python, dùng trong execute_code/background)

```python
import json, os, urllib.request
key = os.environ["NINEROUTER_API_KEY"]
payload = {
    "model": "cx/gpt-5.6-sol",       # hoặc cmc/deepseek/deepseek-v4-pro
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 8000,
    "temperature": 0.2,
    # v4-pro: "tools": [], "tool_choice": "none"
}
# `base_url` phải được resolve từ live config/canonical wrapper ở preflight.
req = urllib.request.Request(
    base_url.rstrip("/") + "/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
)
with urllib.request.urlopen(req, timeout=840) as resp:
    data = json.loads(resp.read().decode())
content = data["choices"][0]["message"].get("content") or ""
# LUÔN ghi file artifact + in len(content) + finish_reason
```

## Quy trình plan→audit→thực thi (chứng minh 2026-08-06)

1. **Backup + sha256** file trước (`cp AGENTS.md AGENTS.md.pre-scope-<ts>.bak`).
2. **v4-pro lên plan** → lưu `*_PLAN_v4pro.md`.
3. **Sol audit plan** → lưu `*_AUDIT_sol.md`. REJECT → sửa plan → audit lại.
4. Sol REJECT ≥3 vòng cùng lý do cấu trúc → **dừng, đổi cách tiếp cận** (đừng vòng vô hạn).
5. APPROVE mới cho worker thực thi sửa file thật → verify diff/validator/marker.
