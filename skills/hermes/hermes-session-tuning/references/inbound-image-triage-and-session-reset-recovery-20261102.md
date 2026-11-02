# Inbound Image Triage & Session Reset Recovery Discipline

## 1. Context & Trigger
When the user sends a bare `?` with an attached image (e.g. screenshot of Telegram chat or desktop UI), particularly right after an automated session reset (`Session automatically reset (inactive for 24h). Conversation history cleared`):
- **Anti-Pattern (Rập khuôn / Chào đối phó):** Bot starts a fresh turn, ignores the attached image or answers with a canned introductory message ("Hermes Agent đã sẵn sàng..."), completely dropping the user's ongoing conversation/questions.
- **Root Cause:** A gateway crash-loop or session restart wipes short-term context. The user sends a screenshot of the previous chat window containing questions they asked before the reset.

## 2. Mandatory Protocol for Inbound Chat Screenshots
1. **Never Reply with Canned Greeting:** If an image is attached to `?`, never output generic ready-text. The user is asking "Why haven't you answered this?" or "Answer what's on this screen."
2. **Read Back History via `session_search`:**
   - Extract keywords from the screenshot.
   - Run `session_search` to recover previous conversation turns and locate the exact questions/topics asked before the session reset.
   - Reconstruct the conversation thread rather than treating the incoming prompt as a standalone query.
3. **Address Every Question Point-by-Point:**
   - Enumerate all distinct questions shown in the user's screenshot.
   - Provide concrete, evidence-backed answers (quoting real code, test outputs, or actual pipeline state).
   - If questions relate to prior code changes or governance debates (e.g., advisor reporting, mechanical gates, gate consolidation), verify in the codebase before answering.

## 3. Anti-Overengineering Rule
- When asked if an existing procedure/lesson needs more mechanical gates vs being over-engineered:
  - Distinguish between **True Mechanical Code Invariants** (e.g. `sanitize_advisor_prompt`, `supports_vision: true`, single entrypoint pipelines) and **Prompt/Gate Bloat** (adding endless repetitive text warnings or multi-step manual reviews).
  - Do not add new gates when an invariant is already mechanically enforced by code. Acknowledging that existing code handles it and rejecting gate sprawl is the correct, disciplined response.
