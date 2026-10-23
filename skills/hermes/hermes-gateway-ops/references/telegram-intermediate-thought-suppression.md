# Telegram Intermediate Text Suppression & Model Thought Leakage

## Context & Problem
When running reasoning-heavy models or worker-tier models (such as `omni-worker`, `luna`, `flash`) via Hermes Gateway (especially Telegram), models occasionally exhibit **thought leakage**. 
Instead of keeping monologue/audit thoughts within `<thought>` blocks or hidden internal states, the model writes planning thoughts, data cross-checks, or exclamations (`LOOK AT THAT`, `BINGO`, `THEY ALREADY EXIST IN...`) directly into the response text (`content`) during an intermediate turn that also invokes tools.

Because Hermes treats `response.content` as an intentional message for the operator, the Telegram gateway immediately dispatches it via `send_message`, causing chat pollution and spamming the conversation with raw intermediate internal reasoning.

---

## Technical Constraints & Hermes Settings Verification
1. **No Native Config Setting in Hermes:**
   - In `~/.hermes/config.yaml`, settings like `display.show_reasoning: false` or the slash command `/reasoning hide` **ONLY** suppress formal `<thought>` tags emitted by models supporting explicit reasoning delimiters (e.g. DeepSeek R1, Claude Thinking).
   - They do **NOT** suppress plain text emitted inside `content` alongside `tool_calls`.
2. **Gateway Pass-Through Architecture:**
   - Hermes messaging gateway (`hermes_cli/gateway/platforms/telegram.py`) operates in streaming / turn-based pass-through: any non-empty `content` in a turn is delivered to Telegram regardless of whether `tool_calls` are present.

---

## Deterministic Gateway Hook / Mechanical Guard Pattern
To mechanically prevent thought leakage across all future sessions without relying on model compliance or memory directives, an outbound filter hook must be applied at the Gateway egress layer:

```python
# Location: hermes_cli/gateway/platforms/telegram.py or pre-send hook
if turn.has_tool_calls() and not turn.is_final_turn():
    # Model is actively invoking tools; intermediate text is diagnostic/thought residue
    # Suppress intermediate chat dispatch to prevent spamming Telegram
    logger.debug(f"[TELEGRAM_GATEWAY] Suppressed intermediate text turn ({len(turn.content)} chars)")
    return
```

---

## Coordinator Prompting & Turn Invariants (Until Gateway Filter Active)
- **Zero Content on Tool Calls:** Whenever emitting `tool_calls`, the assistant `content` field should be strictly empty `""` or omitted.
- **Evidence-First Delivery:** Only post-execution results backed by actual tool outputs (test exit codes, OCR verifications, file inspections) are emitted in the final user-facing message.
- **Anti-Spam Discipline:** Never announce intermediate steps, discoveries, or excitement mid-turn. Consolidate facts into structured, labeled final reports.
