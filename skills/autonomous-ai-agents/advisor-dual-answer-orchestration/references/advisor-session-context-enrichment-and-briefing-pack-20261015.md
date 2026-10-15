# Advisor Session Context Enrichment & Briefing Pack Architecture (15/10/2026)

## 1. Problem Statement: Context Starvation in Advisor Sol
When an Operator asks an evaluative or diagnostic question on Telegram (e.g. *"Sao nhìn lệch v"*, *"Cái này xử lý sao"*, *"Có nên nâng cooldown không"*), Advisor Sol (`gpt-web-sol` on :20129) previously returned curt, irrelevant, or hallucinatory answers (*"cụt lủn, hiểu theo tin nhắn gần nhất"*).

### Root Cause Analysis
1. **Stateless Upstream:** The ChatGPT-Web pool (:20129) runs in stateless mode. Each HTTP completion call has zero session history.
2. **Hermes Coordinator Blindness:** In `agent/conversation_loop.py` (`_consult_advisor_once`), the payload passed to `advisor_consult` was strictly:
   ```python
   f_args = {
       "decision_class": "USER_ADVICE_REQUEST",
       "question": original_user_message,     # Only the isolated final user string
       "current_state": (primary_answer or "")[:4000],
       "evidence": (original_user_message or "")[:4000],
   }
   ```
3. **Tool Isolation:** `consult_advisor.py` wrapped the query into a single message:
   ```python
   payload = {"model": "gpt-web-sol", "messages": [{"role": "user", "content": prompt}]}
   ```
   Sol received zero context about which machine (e.g., Máy 6), which account (e.g., `@alemafxjvxw`), what task just succeeded/failed (e.g., pinned 2 videos, avatar upload lock), or the preceding discussion. Sol was forced to guess blindly based on literal dictionary meaning.

---

## 2. Architecture Blueprint (Designed by Claude Sonnet 5.5)

### Component 1: `agent/advisor_context.py`
Extracts and summarizes recent conversational context without token bloat:

```python
import re
from typing import Any, Dict, List, Tuple

MAX_BRIEF_CHARS = 1500
MAX_TURNS = 5
MAX_MSG_CHARS = 280

_MACHINE_RE = re.compile(r"(?:máy|machine)\s*#?(\d+)", re.IGNORECASE)
_ACCOUNT_RE = re.compile(r"@([a-zA-Z0-9_.]{2,32})")
_SERIAL_RE = re.compile(r"\b([0-9a-f]{14,20})\b", re.IGNORECASE)

def _clip_text(text: str, max_chars: int = MAX_MSG_CHARS) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:180] + "..." + cleaned[-(max_chars - 183):]

def infer_field_ctx(messages: List[Dict[str, Any]]) -> Dict[str, str]:
    """Scans backwards through recent messages to infer machine, account, and serial."""
    machine, account, serial = "?", "?", "?"
    for m in reversed(messages):
        content = m.get("content") or ""
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        if not isinstance(content, str):
            continue
        if machine == "?":
            match_m = _MACHINE_RE.search(content)
            if match_m: machine = match_m.group(1)
        if account == "?":
            match_a = _ACCOUNT_RE.search(content)
            if match_a: account = match_a.group(0)
        if serial == "?":
            match_s = _SERIAL_RE.search(content)
            if match_s: serial = match_s.group(1)
        if machine != "?" and account != "?":
            break
    ctx = {}
    if machine != "?": ctx["machine"] = machine
    if account != "?": ctx["account"] = account
    if serial != "?": ctx["serial"] = serial
    return ctx

def build_session_briefing(
    messages: List[Dict[str, Any]],
    *,
    exclude_last_user: bool = True,
    max_turns: int = MAX_TURNS,
    max_chars: int = MAX_BRIEF_CHARS,
) -> Tuple[Dict[str, str], str]:
    """Builds a condensed OP/AGENT conversation briefing capped at max_chars."""
    if not messages:
        return {}, ""
    conv = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    if exclude_last_user and conv and conv[-1].get("role") == "user":
        conv = conv[:-1]
    recent = conv[-max_turns:]
    lines = []
    for m in recent:
        role = "OP" if m.get("role") == "user" else "AGENT"
        content = m.get("content") or ""
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        if m.get("role") == "assistant" and m.get("tool_calls"):
            calls = m.get("tool_calls") or []
            tool_names = [c.get("function", {}).get("name", "tool") if isinstance(c, dict) else "tool" for c in calls]
            content = f"ran: {', '.join(tool_names[:3])}" + (f" | {content}" if content else "")
        lines.append(f"{role}: {_clip_text(str(content))}")

    while lines and sum(len(l) for l in lines) + len(lines) - 1 > max_chars:
        lines.pop(0)
    return infer_field_ctx(conv), "\n".join(lines)
```

---

## 3. 5-Tier Structured Prompt Format for Sol Web

```text
[Bối cảnh hiện trường]
Máy: {machine} | Nick: {account} | Serial: {serial}

[Diễn biến gần nhất]
OP: ...
AGENT: ran: ... | ...
(tối đa 3–5 lượt trao đổi, <= 1500 ký tự)

[Trạng thái hiện tại của Agent]
{primary_answer đã cắt <= 1000 ký tự}

[Câu hỏi tư vấn]
{question <= 1500 ký tự}

[Yêu cầu]
Đóng vai trò Solution Architect phản biện độc lập. Trả lời súc tích, đi thẳng vào nguyên nhân gốc rễ và giải pháp thực tế, không lý thuyết suông.
```

---

## 4. Safety Guardrails & Token Discipline

1. **Hard Prompt Ceiling:** Total prompt string capped at `MAX_PROMPT_CHARS = 4500` (~1,500 tokens). This prevents reasoning models (`gpt-web-sol`) from encountering token bloat that trips the 45s TTFT ceiling.
2. **Minimal Fallback on Timeout:** If upstream socket encounters thinking timeout (>45s), caller falls back to minimal prompt (only *[Câu hỏi tư vấn]* + 500 characters of recent context) with a 45s budget.
3. **Leak-Proof Secret Redaction:** All API keys (`sk-...`), Bearer tokens, cookies, passwords, and JWTs are stripped before assembling the prompt. Serial and machine indices are non-secret and explicitly preserved for operational context.
