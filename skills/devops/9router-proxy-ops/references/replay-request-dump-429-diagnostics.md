# Replay request-dump diagnostics — "client 429 / curl OK" (verify 17/08, Antigravity case)

Dùng khi: một client (Hermes session/spawn) nhận 429 `RESOURCE_EXHAUSTED` nhưng curl thẳng tới model giống hệt → 200.
Bài học trung tâm: **đừng đoán (quota/size/RPM) — replay body thật rồi bisect**.

## 1. Reproduce bằng ĐÚNG body client gửi
- `~/AppData/Local/hermes/sessions/request_dump_<session-id>_<ts>.json` chứa `{method, url, headers, body}` = request chính xác Hermes đã gửi (kể cả body khi lỗi). Body thường: `model / messages / tools / max_tokens / reasoning_effort` (2 messages = system + user; ~29 tool schemas; max_tokens 65536).
- Replay nguyên body qua curl/python → tái hiện 429. Nhỏ hơn: request của Hermes (đúng system prompt thật) → 429; curl tự bịa prompt ngắn → 200.

## 2. Field bisect — loại trừ shape
Đổi từng field một: `max_tokens` 65536→40, `tools`→generic 2-30 schemas, bỏ `reasoning_effort`, `stream` true/false, system filler 30K→100K tokens.
Kết quả 17/08: TẤT CẢ biến thể field đều 200 ⇒ KHÔNG phải shape/size/quota — nghiêng về NỘI DUNG prompt.

## 3. Content bisect — cô lập prefix
Cắt system prompt theo dải ký tự (không cần tokenizer): `[0:5550]` 429 vs `[5550:11101]` 200 → `[0:2775]` 429 vs `[2775:5550]` 200 → `[0:1387]` 429 → phrase-level variants.
Lưu ý: block `<available_skills>` (~12K chars) và nửa sau prompt đều 200 — chỉ prefix identity dính.

## 4. Fingerprint của LITERAL DENYLIST (khác rate limit)
Biến thể gần-đúng đều 200, ĐÚNG chuỗi canonical → 429 lặp lại 100%:
- Đổi tên agent (Hermes→Alice) → 200; đổi org (Nous Research→Google) → 200; bỏ cụm "intelligent AI assistant" → 200; persona Claude/Anthropic → 200; riêng lẻ "Hermes Agent" / "Nous Research" → 200.
- Chuỗi bị chặn (canonical): `You are Hermes Agent, an intelligent AI assistant created by Nous Research.`
- Rate limit trái lại: fail đồng đều mọi biến thể. Asymmetry "chỉ fail đúng 1 chuỗi" = literal denylist.
- 17/08: denylist của Antigravity chặn trên MỌI family (gemini + claude sonnet/opus), MỌI account AG. Request có dòng mở đầu KHÁC (VD repo context: "You are Hermes Agent running a Taadaa Android automation farm...") → 200 — vì sao subagent trong repo có AGENTS.md vẫn chạy được dù main session fail.

## 5. modelLock NHIỄU bisect (bẫy lớn)
- Sau 429 thật, 9router lock account theo model: `2s→4s→6s→13s→...→300s` (tăng dần). Trong cửa sổ lock, mọi request reject ~0.01s KHÔNG chạm upstream — đó là artifact, KHÔNG phải kết quả test (bisect 17/08: B-F fail 0.01s hàng loạt = lock, không phải thật).
- Mitigate: (a) chờ cooldown giữa các test; (b) chèn TINY HEARTBEAT request ("say OK") trước mỗi test thật để chứng minh bucket còn sống; (c) càng nhiều account active càng tốt — 1 account duy nhất = lock làm mọi test fail đồng loạt; 2 account + rotation → tiny vẫn 200 giữa các lần 429 ⇒ chứng minh content-trigger chứ không phải bucket (thí nghiệm 04:02 17/08: tiny 200 trên thanhdatbui, replay 429 trên cả 2 account).

## 6. Fix class — identity slot #1 = SOUL.md
- `~/AppData/Local/hermes/SOUL.md` = identity slot #1 (prompt_builder.load_soul_md; thay DEFAULT_AGENT_IDENTITY hardcode ở `agent/prompt_builder.py` + `hermes_cli/default_soul.py`).
- Sửa SOUL.md → session MỚI (/new) mới nạp identity mới; session đang chạy giữ prompt cũ (vẫn 429) — phải /new.
- Verify: `hermes chat -m ag/gemini-3.7-flash-high -q "..."` → 200 trả lời thật.
- Workflow tối giản identity: inventory các section khác trong system prompt (Finishing the job / Parallel tool calls / memory guidance / help guidance) TRƯỚC — identity chỉ nên giữ phần core CHƯA cover. Bản 17/08 cuối (22 tokens, Opus MINOR_FIXES approve): `You are Hermes Agent, a helpful and direct AI assistant. Admit uncertainty when appropriate.`
- Audit độc lập cho prompt rewrite: `D:/Taadaa/reports/ag-audit/ag_audit_direct.py <prompt-file> ag/claude-opus-4-6-thinking <out> <timeout>` — script chỉ gửi user-role (KHÔNG system message) nên không dính denylist khi prompt có chứa chuỗi bị chặn.
