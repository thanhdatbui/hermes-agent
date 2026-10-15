# Session Context Enrichment and Redaction Hardening (15/10/2026)

## Problem: Context Starvation in Advisor Sol (ChatGPT-Web Pool :20129)
When an Operator asks an evaluative question (e.g. *"Sao nhìn lệch v"*, *"Có nên nâng cooldown không?"*), `_consult_advisor_once` previously sent only the single latest message string as `prompt` to `:20129 gpt-web-sol`.
Because ChatGPT-Web pool accounts are stateless HTTP completions, Sol had zero session history, resulting in generic, disconnected, or hallucinated advice ("nói đéo liên quan gì").

## Architecture: 5-Tier Structured Prompt Pack

```text
[Bối cảnh hiện trường]
Máy: {machine} | Nick: {account} | Serial: {serial}

[Diễn biến phiên làm việc gần nhất]
OP: {user message 1}
AGENT: {assistant summary 1}
...

[Trạng thái hiện tại của Coordinator]
{primary_answer <= 1000 chars}

[Câu hỏi tư vấn của Operator]
{query <= 1500 chars}

[Yêu cầu]
Đóng vai trò Solution Architect phản biện độc lập. Trả lời súc tích, đi thẳng vào giải pháp và nguyên nhân kỹ thuật, không lý thuyết suông.
```

## Hard Invariants and Reviewer Lessons (Claude Sonnet 5.5 Audit)

1. **Early Redaction (Che trước khi cắt text):**
   - Redaction must execute on raw content BEFORE any text clipping (`_clip_text`) or regex extraction.
   - Slicing a string mid-secret leaves truncated tokens (e.g. `sk-` + 10 chars) that fail pattern matching and leak upstream.

2. **Full-Spectrum Secret Redaction Patterns:**
   - **Dict keys with prefix/suffix:** Do NOT use exact match `str(k).lower() in _SECRET_KEYS`. Use substring match: `any(sk in re.sub(r"[-_]", "", str(k).lower()) for sk in _SECRET_KEYS)`. This catches `MY_API_KEY`, `GITHUB_TOKEN`, `db_password`.
   - **Quoted JSON keys:** Match `([\"']?)(?:[\w_-]*(?:password|api[_-]?key|access[_-]?token|cookie|authorization|auth[_-]?header|secret|private[_-]?key|client[_-]?secret|token))\1\s*:\s*([\"']?)[^\"'\r\n,;}]+\2`.
   - **Authorization Headers:** Redact the entire credential: `re.compile(r"\bauthorization\s*:\s*[^\r\n,;]+", re.IGNORECASE)` to catch `Authorization: Basic dXNlcjpwYXNz`.
   - **Multi-key Cookies:** Use `re.compile(r"\bcookie\s*[:=]\s*[^\r\n]+", re.IGNORECASE)` to catch the entire line `Cookie: a=1; b=2; c=3`, not just the first key-value pair.
   - **Python 3.11+ Regex Flag Invariant:** NEVER place `(?i)` in the middle of a regex string (causes `re.error: global flags not at the start of the expression`). Use separate compiled patterns with `re.IGNORECASE`.

3. **Serial Regex Without False Positives:**
   - Raw pattern `\b[0-9a-zA-Z]{8,24}\b` matches common ADB log words like `device unauthorized` or `device connection lost`, causing Advisor to falsely target a serial named `"unauthorized"`.
   - Fix: `re.compile(r"(?:serial|thiết bị|device)\s*[:=]\s*(?=[a-zA-Z0-9]*\d)([a-zA-Z0-9]{8,24})\b", re.IGNORECASE)` requiring `:` or `=` and at least one digit.

4. **Dynamic Briefing Truncation (Never Truncate Query from Tail):**
   - Cutting the entire assembled prompt with `[:MAX_PROMPT_CHARS]` slices off the tail containing `[Câu hỏi tư vấn của Operator]` and `[Yêu cầu]`.
   - Fix: Calculate available budget `avail = MAX_PROMPT_CHARS - len(field) - len(state) - len(query) - len(req) - 50`. If `briefing` exceeds budget, drop lines from the TOP (oldest turns first), guaranteeing 100% preservation of the operator's query.

5. **Safe Fallback in Conversation Loop:**
   - `build_session_briefing` runs inside `try/except`. If context extraction fails, fallback to empty briefing without crashing the advisor trigger or losing the primary response.
   - Thread-safe metric increments must use `_advisor_metric_inc(st)` under `_ADVISOR_METRICS_LOCK`.
