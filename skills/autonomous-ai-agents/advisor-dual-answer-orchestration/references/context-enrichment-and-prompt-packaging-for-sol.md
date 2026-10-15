# Advisor Sol Context Enrichment & Dynamic Prompt Packaging

## Problem & Root Cause (15/10/2026)
Operator reprimand: "Advisor nó cứ k hiểu ngữ cảnh session của tao mà mày ném lên cho nó xong nó tl đéo liên quan gì. Advisor chatgpt sol web ấy, kiểu nó cứ bị cụt lủn hiểu theo tin nhắn gần nhất t nhắn thôi".
Root cause:
- `consult_advisor.py` and `conversation_loop._consult_advisor_once` previously only forwarded `original_user_message` (the single latest user question), omitting session conversation history, target machine, account handle, and recent actions.
- Upstream reasoning model (`gpt-web-sol` on `:20129`) is stateless across turns, leading to generic theoretical advice disconnected from current farm ground truth.

## Architecture & Implementation
1. **`agent/advisor_context.py` (Hermes Core):**
   - `build_session_briefing(messages)`: Extracts last 3–5 user/assistant turns (excluding active user query), clips each turn to <=280 chars, limits total briefing to <=1500 chars (popping oldest turns first). Assistant tool calls are summarized as `ran: tool1, tool2`.
   - `infer_field_ctx(messages)`: Scans in reverse from latest message to infer `machine` (e.g. `máy 6`), `account` (e.g. `@alemafxjvxw`, using negative lookbehind `(?<![\w@])@` to avoid email domains), and `serial` (`(?:serial|thiết bị|device)\s*[:=]?\s*<hex>`).
   - `redact_secrets(text)`: Runs **immediately before** clipping and regex scanning to prevent token fragments from escaping or being misclassified as serials.

2. **Integration into Hermes Loop:**
   - `agent/conversation_loop.py`: `_consult_advisor_once` and `_maybe_append_advisor_for_final_response` forward `messages=messages`, extracting `field_context` and `session_briefing` into `f_args`.
   - `tools/advisor_tool.py`: Accepts `session_briefing` and `field_context`, runs `_redact`, and bundles them into the request payload.

3. **5-Layer Prompt Packaging (`D:/Taadaa/tools/consult_advisor.py`):**
   - Layers: `[Bối cảnh hiện trường]` + `[Diễn biến phiên làm việc gần nhất]` + `[Trạng thái hiện tại của Coordinator]` + `[Câu hỏi tư vấn của Operator]` + `[Yêu cầu]`.
   - **Dynamic Briefing Budget**:
     Calculates available characters for briefing: `avail = max(0, MAX_PROMPT_CHARS - len(field) - len(state) - len(query) - len(req) - 50)`.
     Lines of briefing are popped from the top if exceeding budget.
   - **Invariant**: The user's core query (`query[:1500]`) and system instruction `[Yêu cầu]` are NEVER truncated at the prompt tail.
   - Dual-layer `redact_secrets` is enforced before sending to port 20129.

## Blocker Post-Mortem (Claude CLI Reviewer Strike 1 -> Remediation)
- **B1 (Egress leak)**: `consult_advisor.py` previously lacked redaction on custom caller routes. Fixed by enforcing `redact_secrets` across all prompt construction and direct fallback paths.
- **B2 (Late redaction & Regex bypass)**: Clipping before redaction cut secrets across chunk boundaries. Fixed by doing `redact_secrets` first. Email addresses were misidentified as `@accounts`; fixed with `(?<![\w@])@`. Raw 16-hex strings were misidentified as serials; fixed with prefix requirement `(?:serial|thiết bị|device)\s*[:=]?\s*...`.
- **B3 (Tail truncation trap)**: Truncating `full_prompt[:4500]` cut the query and instructions at the end. Fixed by prioritizing the query/requirements and trimming the briefing from the top.
