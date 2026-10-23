# Intermediate Thought Suppression & Monologue Discipline

## Context & Problem
During autonomous multi-step operations (such as farm audits, video rendering pipelines, cross-checking 640 accounts), LLM models (especially worker-tier or reasoning models like `omni-worker`, `luna`, `flash`) frequently exhibit **thought leakage**. 
The model emits intermediate discovery thoughts, raw data dumps, self-monologues, or excitement expressions (`BINGO`, `LOOK AT THAT DISCOVERY`, `THEY ALREADY EXIST IN...`) directly into the turn's `content` while executing tool calls.

Because chat gateways (Telegram/Discord/Slack) pass `response.content` directly to the user's messaging screen, this results in chat pollution, distracting the operator and making autonomous coordination look undisciplined.

---

## The Rule of Absolute Silence During Tool Calls
1. **Empty Content on Tool Calls:** 
   Whenever an agent turn issues one or more `tool_calls` (inspecting disk, running batch render, querying SQLite, scraping channels), the text `content` field must remain **strictly empty** (`""`).
2. **No Narrative Running Commentary:** 
   Do not narrate internal steps ("Now I will inspect folder 545", "Let me see what is inside..."). Execute the inspection tools silently.
3. **Consolidated Final Delivery Only:** 
   Only when all tool executions for the phase are complete, or when a tangible verified artifact / checkpoint (Gate 6) is reached, does the agent synthesize a clean, structured, labeled final message with verifiable evidence (`MEDIA:<path>`, exit codes, row diffs).
4. **Hermes Native Setting Limit:** 
   Hermes lacks a native config toggle to suppress plain-text thought leakage (settings like `display.show_reasoning: false` only suppress `<thought>` XML blocks). Therefore, prompt-level turn discipline (content=`""` during tool calls) is the primary line of defense.
