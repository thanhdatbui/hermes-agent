# Hermes Gateway Agent max_turns Budget Cap, Upstream refund() Bug & Runtime Desync

## 1. Problem Description & Root Cause
When an AI Coordinator or deep-reasoning coding agent performs complex multi-turn workflows in a single Telegram turn (e.g., Code patch -> Unit testing -> Closeout Gate AI Review -> Remediation loop), the agent suddenly gets paralyzed and stops with the system message:
```text
You've reached the maximum number of tool-calling iterations allowed. Please provide a final response summarizing what you've found and accomplished so far, without calling any more tools.
```
Log inspection in `~/.hermes/logs/agent.log`:
```text
Turn ended: reason=max_iterations_reached(20/20) model=omni-worker api_calls=20/20 budget=20/20 tool_turns=80
```
Even though the deploy template specifies 200 turns, the agent is cut off at exactly 20 tool iterations.

### Root Causes
1. **Runtime vs Deploy Settings Desync**:
   - The deploy template had `max_turns: 200`.
   - But the actual runtime settings file consumed by the running Gateway process under AppData had `agent.max_turns: 20`.
   - `gateway/run.py` translates `agent.max_turns` into `HERMES_MAX_ITERATIONS` environment variable, capping each agent turn to 20 API calls.
2. **Upstream refund() Counter Bug in `agent/conversation_loop.py`**:
   - The loop termination condition is:
     ```python
     while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0)
     ```
   - Around line 5018, when lightweight tools (like `execute_code`) are executed, the engine called:
     ```python
     if _tc_names == {"execute_code"}:
         agent.iteration_budget.refund()
     ```
   - **Bug**: It refunded `iteration_budget`, but **failed to decrement `api_call_count`**!
   - Other refund call sites (lines 1143, 1223, 4398, 4413) always execute:
     ```python
     api_call_count -= 1
     agent._api_call_count = api_call_count
     agent.iteration_budget.refund()
     ```
   - As a result, `api_call_count` relentlessly incremented towards 20 on every tool turn regardless of refunds, causing premature hard termination.
3. **Tool Stripping & Synthetic Prompt Injection (`turn_finalizer.py` & `chat_completion_helpers.py`)**:
   - Once `max_iterations` is hit, `handle_max_iterations()` strips all tools from the agent runtime and injects the synthetic user prompt, stripping away the agent's ability to call any more tools and forcing an immediate text-only apology/summary.

---

## 2. Standard Fix & Configuration Contract

### A. Set Optimal Budget in Runtime Settings
In the Hermes runtime settings manifest:
```yaml
agent:
  max_turns: 100       # 100 turns for Coordinator (generous for patch + review + remediation without runaway loop)

delegation:
  max_iterations: 60   # 60 turns for Worker subagents
```

### B. Upstream Fix in `agent/conversation_loop.py`
Ensure every `iteration_budget.refund()` decrements `api_call_count`:
```python
if _tc_names == {"execute_code"}:
    if api_call_count > 0:
        api_call_count -= 1
        agent._api_call_count = api_call_count
    agent.iteration_budget.refund()
```

### C. Live Verification
Ensure `agent.max_turns` returns `100`. Restart Gateway if in-memory daemon was running so it re-bridges the updated environment.
